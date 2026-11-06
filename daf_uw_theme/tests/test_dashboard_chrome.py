from datetime import date, timedelta

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardChrome(TransactionCase):
    """Stats tiles, insight banners, shortcuts and per-user preferences."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="dash_chrome", groups="base.group_user")
        cls.other = new_test_user(cls.env, login="dash_chrome2", groups="base.group_user")
        cls.partner = cls.env["res.partner"].create({"name": "Chrome Co"})
        cls.Prefs = cls.env["methode.dashboard.preferences"]
        # The RPC-reachable entry points live on the concrete placement model; the
        # tests go through the same door the client does.
        cls.Insight = cls.env["methode.dashboard.widget"]

    def _activity(self, user, days):
        return self.partner.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=date.today() + timedelta(days=days),
            summary="chrome probe",
            user_id=user.id,
        )

    # --- Stats ---------------------------------------------------------------
    def test_stat_counts_overdue_and_today_only(self):
        self._activity(self.user, -2)
        self._activity(self.user, 0)
        self._activity(self.user, 6)      # planned: not "due"
        self._activity(self.other, -1)    # another user's: never counted

        stat = self.env["mail.activity"].with_user(self.user).dashboard_fetch_activities_stat()
        self.assertEqual(stat["value"], 2)
        self.assertTrue(stat["action"], "a stat must open the records behind it")
        self.assertEqual(stat["tone"], "danger", "something IS late, so the tile says so")

    def test_stat_tone_is_neutral_when_nothing_is_late(self):
        self._activity(self.user, 0)
        stat = self.env["mail.activity"].with_user(self.user).dashboard_fetch_activities_stat()
        self.assertEqual(stat["value"], 1)
        self.assertEqual(stat["tone"], "neutral", "red is for late, not for busy")

    def test_stats_tiles_are_not_placements(self):
        stats = self.env["methode.dashboard.widget.type"]._stats_payload()
        codes = [tile["code"] for tile in stats]
        self.assertIn("stat_activities_due", codes)
        self.assertTrue(all(tile["render"] == "stat" for tile in stats))

    def test_stats_hide_tiles_the_user_may_not_read(self):
        # A plain internal user has no accounting rights. Any tile whose model
        # they cannot read must be dropped rather than rendered as a dead "—".
        tiles = self.env["methode.dashboard.widget.type"].with_user(
            self.user)._stats_payload()
        for tile in tiles:
            self.assertTrue(
                self.env["methode.dashboard.insight"].with_user(
                    self.user)._dashboard_can_read(tile["fetch_model"]),
                "a tile was offered for a model this user cannot read: %s" % tile["code"],
            )

    def test_insights_survive_a_user_with_no_app_rights(self):
        # ⚠ REGRESSION GUARD. The bridge contributions chain through super(), so an
        # unguarded query on account.move raised AccessError for a plain internal
        # user and took EVERY banner down with it — including the activity banner
        # they were entitled to. This asserts the zone still works for them.
        self._activity(self.user, -3)
        result = self.Insight.with_user(self.user).dashboard_fetch_insights(limit=10)
        keys = [insight["key"] for insight in result["insights"]]
        self.assertIn("activities_overdue", keys, "the banner they CAN see must show")
        self.assertNotIn("invoices_long_overdue", keys, "and no accounting banner")

    # --- Insights ------------------------------------------------------------
    def test_insight_fires_only_when_overdue(self):
        quiet = self.Insight.with_user(self.user).dashboard_fetch_insights()
        self.assertEqual(quiet["insights"], [], "no overdue work, no interruption")

        self._activity(self.user, -4)
        loud = self.Insight.with_user(self.user).dashboard_fetch_insights()
        keys = [insight["key"] for insight in loud["insights"]]
        self.assertIn("activities_overdue", keys)

    def test_dismissal_hides_for_today_and_is_per_user(self):
        self._activity(self.user, -4)
        self._activity(self.other, -4)

        self.Prefs.with_user(self.user).dashboard_dismiss_insight("activities_overdue")

        mine = self.Insight.with_user(self.user).dashboard_fetch_insights()
        self.assertEqual([i["key"] for i in mine["insights"]], [])

        theirs = self.Insight.with_user(self.other).dashboard_fetch_insights()
        self.assertIn(
            "activities_overdue", [i["key"] for i in theirs["insights"]],
            "one user's dismissal must not silence another's banner",
        )

    def test_dismissal_expires_the_next_day(self):
        self._activity(self.user, -4)
        prefs = self.Prefs.with_user(self.user)
        prefs.dashboard_dismiss_insight("activities_overdue")
        # Rewrite the stored date as yesterday: the snooze should have lapsed.
        row = prefs._get_for_user()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        row.dismissed_json = '{"activities_overdue": "%s"}' % yesterday

        back = self.Insight.with_user(self.user).dashboard_fetch_insights()
        self.assertIn("activities_overdue", [i["key"] for i in back["insights"]])

    def test_insight_cap_reports_the_remainder(self):
        self._activity(self.user, -4)
        capped = self.Insight.with_user(self.user).dashboard_fetch_insights(limit=0)
        self.assertEqual(capped["insights"], [])
        self.assertEqual(capped["more"], 1, "held-back banners are counted, not lost")

    # --- Shortcuts -----------------------------------------------------------
    def test_shortcuts_are_actionable(self):
        result = self.Insight.with_user(self.user).dashboard_fetch_shortcuts()
        self.assertTrue(result["shortcuts"])
        for shortcut in result["shortcuts"]:
            self.assertTrue(shortcut["action"], "a shortcut with no action is decoration")

    # --- Preferences ---------------------------------------------------------
    def test_preferences_default_and_are_created_once(self):
        payload = self.Prefs.with_user(self.user)._preferences_payload()
        self.assertTrue(payload["show_stats_row"])
        self.assertEqual(payload["layout_density"], "comfortable")
        self.assertEqual(payload["row_limit"], 5)
        # Idempotent: a second read must not create a second row.
        self.Prefs.with_user(self.user)._preferences_payload()
        self.assertEqual(
            self.Prefs.with_context(active_test=False).search_count(
                [("user_id", "=", self.user.id)]
            ),
            1,
        )

    def test_save_preferences_whitelists_fields(self):
        saved = self.Prefs.with_user(self.user).dashboard_save_preferences({
            "show_stats_row": False,
            "row_limit": 8,
            # Not writable through the client: must be ignored, not written.
            "user_id": self.other.id,
        })
        self.assertFalse(saved["show_stats_row"])
        self.assertEqual(saved["row_limit"], 8)
        row = self.Prefs.with_user(self.user)._get_for_user()
        self.assertEqual(row.user_id, self.user, "user_id is not client-writable")

    def test_preferences_are_private_to_their_owner(self):
        mine = self.Prefs.with_user(self.user)._get_for_user()
        # Exercises the record rule for real, as a non-superuser (closes §8.5 for
        # this model): another user cannot read my preferences row.
        with self.assertRaises(AccessError):
            self.Prefs.with_user(self.other).browse(mine.id).read(["row_limit"])
