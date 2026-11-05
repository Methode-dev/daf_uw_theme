from datetime import date, timedelta

from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardActivities(TransactionCase):
    """Assert the value, not just that it runs (HOMEPAGE_DASHBOARD_PLAN §4).

    Each test seeds known activities and checks the number the fetcher returns —
    the bucketing, the ordering, the per-group cap, the day delta, and the fact
    that one user never sees another's activities.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # new_test_user handles the group-assignment field rename across versions,
        # so this test does not care whether it is groups_id or group_ids.
        cls.user = new_test_user(
            cls.env, login="dash_user", name="Dash User", groups="base.group_user"
        )
        cls.other = new_test_user(
            cls.env, login="dash_other", name="Other User", groups="base.group_user"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Acme"})
        cls.Activity = cls.env["mail.activity"]

    def _make(self, user, days, summary="task"):
        """Schedule one To-Do on the partner, `days` from today, for `user`."""
        return self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today() + timedelta(days=days),
            summary=summary,
            user_id=user.id,
        )

    def _fetch(self, user, **kw):
        return self.Activity.with_user(user).dashboard_fetch_activities(**kw)

    def _group(self, res, key):
        return next(g for g in res["groups"] if g["key"] == key)

    def test_buckets_counts_and_user_isolation(self):
        # user: 2 overdue, 1 today, 3 planned
        self._make(self.user, -5)
        self._make(self.user, -1)
        self._make(self.user, 0)
        self._make(self.user, 2)
        self._make(self.user, 4)
        self._make(self.user, 9)
        # other user, same day: must NOT leak into user's dashboard
        self._make(self.other, 0)

        res = self._fetch(self.user)

        self.assertEqual(res["count"], 6, "only the caller's activities are counted")
        self.assertEqual(self._group(res, "overdue")["count"], 2)
        self.assertEqual(self._group(res, "today")["count"], 1)
        self.assertEqual(self._group(res, "planned")["count"], 3)

    def test_ordering_and_per_group_limit(self):
        # five planned activities, deliberately out of order
        for days in (10, 3, 7, 1, 5):
            self._make(self.user, days)

        res = self._fetch(self.user, limit=3)
        planned = self._group(res, "planned")

        self.assertEqual(planned["count"], 5, "count is the full total, not the page")
        self.assertEqual(len(planned["rows"]), 3, "rows are capped at limit")
        self.assertEqual(
            [row["days"] for row in planned["rows"]],
            [1, 3, 5],
            "rows are ordered by deadline ascending",
        )

    def test_total_cap_fills_by_urgency(self):
        # 4 overdue + 3 planned, cap of 5 total across the whole widget.
        for _ in range(4):
            self._make(self.user, -3)
        for _ in range(3):
            self._make(self.user, 5)

        res = self._fetch(self.user, limit=5)

        self.assertEqual(res["count"], 7, "the badge counts every open activity")
        overdue = self._group(res, "overdue")
        planned = self._group(res, "planned")
        # Overdue is more urgent, so it fills first; planned gets the one leftover slot.
        self.assertEqual(len(overdue["rows"]), 4)
        self.assertEqual(len(planned["rows"]), 1)
        self.assertEqual(planned["count"], 3, "the section still knows its true size")
        shown = sum(len(g["rows"]) for g in res["groups"])
        self.assertEqual(shown, 5, "no more than the cap is rendered")

    def test_day_delta_magnitude(self):
        self._make(self.user, -5)
        self._make(self.user, 8)

        res = self._fetch(self.user)
        self.assertEqual(self._group(res, "overdue")["rows"][0]["days"], 5)
        self.assertEqual(self._group(res, "planned")["rows"][0]["days"], 8)

    def test_row_carries_clickthrough_target(self):
        self._make(self.user, 0)  # summary="task"
        row = self._group(self._fetch(self.user), "today")["rows"][0]

        self.assertEqual(row["res_model"], "res.partner")
        self.assertEqual(row["res_id"], self.partner.id)
        # The summary is the human label and wins the title.
        self.assertEqual(row["title"], "task")
        self.assertEqual(row["state"], "today")

    def test_title_falls_back_to_record_when_summary_is_just_the_type(self):
        # ⚠ activity_schedule FILLS summary with the activity type's name when the
        # caller gives none — so "no summary" never actually reaches the fetcher.
        # A summary that only repeats the type must not become the title; the type
        # is the icon's job, so the record wins.
        activity = self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today(),
            user_id=self.user.id,
        )
        self.assertEqual(
            activity.summary, activity.activity_type_id.name,
            "guard: if Odoo stops auto-filling the summary, this rule is moot",
        )
        row = self._group(self._fetch(self.user), "today")["rows"][0]
        self.assertEqual(row["title"], self.partner.display_name)

    def test_real_summary_still_wins_the_title(self):
        self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today(),
            summary="Chase the signed quote",
            user_id=self.user.id,
        )
        row = self._group(self._fetch(self.user), "today")["rows"][0]
        self.assertEqual(row["title"], "Chase the signed quote")

    def test_subtitle_is_a_plaintext_note_preview(self):
        self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today(),
            summary="Call the client",
            note="<p>Discuss the <b>revised</b> pricing before Friday.</p>",
            user_id=self.user.id,
        )
        row = self._group(self._fetch(self.user), "today")["rows"][0]
        self.assertEqual(row["title"], "Call the client")
        # HTML flattened, tags gone, whitespace collapsed to one line.
        self.assertEqual(row["subtitle"], "Discuss the revised pricing before Friday.")

    def test_subtitle_strips_markdown_emphasis(self):
        # Odoo writes some notes with markdown bold (calendar meetings do), which
        # html2plaintext leaves alone — the asterisks would render literally.
        self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today(),
            summary="Business Lunch",
            note="<p>*Organisé par* Administrator and **the team**</p>",
            user_id=self.user.id,
        )
        row = self._group(self._fetch(self.user), "today")["rows"][0]
        self.assertEqual(row["subtitle"], "Organisé par Administrator and the team")

    def test_empty_state_is_all_zeros(self):
        res = self._fetch(self.user)
        self.assertEqual(res["count"], 0)
        self.assertTrue(all(g["count"] == 0 for g in res["groups"]))
        self.assertEqual({g["key"] for g in res["groups"]}, {"overdue", "today", "planned"})
