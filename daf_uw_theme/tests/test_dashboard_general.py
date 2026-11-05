from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import new_test_user, tagged

from .common import DashboardCase


@tagged("post_install", "-at_install")
class TestDashboardGeneral(DashboardCase):
    """Today's Focus, Continue Working, and the activity trend."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ⚠ base.group_partner_manager is needed by the FIXTURE, not by the code
        # under test. Creating a contact requires "Contact/Creation" in Odoo 19,
        # while the recent-records fetcher only ever READS — so this grant makes
        # the test able to build its state, and does not paper over an access
        # problem in the widget (that path is covered in test_dashboard_chrome).
        cls.user = new_test_user(
            cls.env, login="dash_general",
            groups="base.group_user,base.group_partner_manager")
        cls.other = new_test_user(
            cls.env, login="dash_general2",
            groups="base.group_user,base.group_partner_manager")
        cls.partner = cls.env["res.partner"].create({"name": "Focus Co"})
        cls.Widget = cls.env["methode.dashboard.widget"]

    def _activity(self, user, days, summary="probe"):
        return self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today() + timedelta(days=days),
            summary=summary,
            user_id=user.id,
        )

    # --- Today's Focus -------------------------------------------------------
    def test_focus_holds_only_what_needs_me_now(self):
        self._activity(self.user, -2, "late")
        self._activity(self.user, 0, "now")
        self._activity(self.user, 5, "later")     # not urgent: excluded
        self._activity(self.other, -1, "theirs")  # not mine: excluded

        payload = self.Widget.with_user(self.user).dashboard_fetch_focus(limit=20)
        titles = [row["title"] for row in payload["rows"]]

        self.assertIn("late", titles)
        self.assertIn("now", titles)
        self.assertNotIn("later", titles, "due next week is not today's focus")
        self.assertNotIn("theirs", titles, "another user's work is never mine")

    def test_focus_puts_overdue_before_today(self):
        self._activity(self.user, 0, "now")
        self._activity(self.user, -9, "late")

        payload = self.Widget.with_user(self.user).dashboard_fetch_focus(limit=20)
        self.assertEqual(
            payload["rows"][0]["title"], "late",
            "urgency bands order the merged list, not insertion order",
        )
        self.assertEqual(payload["rows"][0]["pill"]["tone"], "overdue")

    def test_focus_hides_its_sorting_keys(self):
        self._activity(self.user, -1)
        row = self.Widget.with_user(self.user).dashboard_fetch_focus()["rows"][0]
        self.assertNotIn("urgency", row, "internal sort keys must not reach the client")
        self.assertNotIn("sort_date", row)

    def test_focus_rows_never_carry_false_strings(self):
        """⚠ REGRESSION GUARD. An unset Odoo Char reads as False, not '', and a
        False `subtitle` fails OWL's String prop validation — which does not
        degrade to a missing line, it throws and blanks the whole dashboard. The
        crash was reported from the browser, so the fetchers now owe this."""
        # A free activity: no linked record, so res_name is False.
        self.env["mail.activity"].create({
            "res_model_id": self.env["ir.model"]._get_id("res.partner"),
            "res_id": self.partner.id,
            "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
            "summary": "standalone",
            "date_deadline": date.today(),
            "user_id": self.user.id,
        })

        payload = self.Widget.with_user(self.user).dashboard_fetch_focus(limit=20)
        for row in payload["rows"]:
            for key in ("title", "subtitle", "icon"):
                self.assertIsInstance(
                    row.get(key, ""), str,
                    "%r must be a string, got %r" % (key, row.get(key)),
                )

    def test_focus_empty_state_is_designed(self):
        payload = self.Widget.with_user(self.user).dashboard_fetch_focus()
        self.assertEqual(payload["count"], 0)
        self.assertTrue(payload["empty"]["title"])

    # --- Continue Working ----------------------------------------------------
    def test_recent_shows_my_edits_not_other_peoples(self):
        mine = self.env["res.partner"].create({"name": "Mine Ltd"})
        theirs = self.env["res.partner"].create({"name": "Theirs Ltd"})
        # State the authorship rather than relying on which env happens to flush
        # the pending recomputes — see DashboardCase._stamp.
        self._stamp(mine, write_uid=self.user.id)
        self._stamp(theirs, write_uid=self.other.id)

        payload = self.Widget.with_user(self.user).dashboard_fetch_recent(limit=20)
        ids = [(row["res_model"], row["res_id"]) for row in payload["rows"]]

        self.assertIn(("res.partner", mine.id), ids)
        self.assertNotIn(("res.partner", theirs.id), ids, "write_uid is the whole point")

    def test_recent_is_ordered_newest_first(self):
        first = self.env["res.partner"].create({"name": "First"})
        second = self.env["res.partner"].create({"name": "Second"})

        # The transaction clock cannot produce two different timestamps, so the
        # "First was touched more recently" story is told explicitly.
        now = fields.Datetime.now()
        self._stamp(second, write_uid=self.user.id, write_date=now - timedelta(minutes=5))
        self._stamp(first, write_uid=self.user.id, write_date=now)

        payload = self.Widget.with_user(self.user).dashboard_fetch_recent(limit=20)
        ids = [row["res_id"] for row in payload["rows"]]
        self.assertLess(
            ids.index(first.id), ids.index(second.id),
            "most recently edited comes first",
        )

    # --- Activity trend ------------------------------------------------------
    def test_trend_buckets_by_horizon(self):
        self._activity(self.user, -3)
        self._activity(self.user, 0)
        self._activity(self.user, 2)    # this week
        self._activity(self.user, 30)   # later

        trend = self.env["mail.activity"].with_user(
            self.user).dashboard_fetch_activity_trend()
        by_label = {point["label"]: point["value"] for point in trend["points"]}

        self.assertEqual(trend["total"], 4)
        self.assertEqual(sum(by_label.values()), 4, "every activity lands in one bucket")
        self.assertEqual(list(by_label.values())[0], 1, "one overdue")

    def test_trend_is_all_zeros_when_nothing_is_scheduled(self):
        trend = self.env["mail.activity"].with_user(
            self.user).dashboard_fetch_activity_trend()
        self.assertEqual(trend["total"], 0)
        self.assertTrue(trend["points"], "the shape is still described, just empty")
