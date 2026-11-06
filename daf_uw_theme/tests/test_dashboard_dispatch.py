from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardDispatch(TransactionCase):
    """The catalogue drives rendering + fetching (Phase A generalization)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="dash_disp", groups="base.group_user")
        cls.Type = cls.env["methode.dashboard.widget.type"]
        cls.Widget = cls.env["methode.dashboard.widget"]

    def test_chrome_pseudo_widgets_are_gone(self):
        codes = self.Type.search([]).mapped("code")
        self.assertNotIn("quick_actions", codes, "quick actions is chrome, not a widget")
        self.assertNotIn("stats", codes, "stats is chrome, not a widget")

    def test_catalogue_carries_dispatch_fields(self):
        by_code = {c["code"]: c for c in self.Type.with_user(self.user)._catalogue_payload()}
        act = by_code["activities"]
        self.assertEqual(act["render"], "activities")
        self.assertEqual(act["fetch_model"], "mail.activity")
        self.assertEqual(act["fetch_method"], "dashboard_fetch_activities")
        # Every shipped widget is now wired to a fetcher; focus was the last one
        # still rendering the pending frame and gained its own in Phase C.
        self.assertEqual(by_code["focus"]["fetch_method"], "dashboard_fetch_focus")

    def test_a_type_without_a_fetcher_reports_none(self):
        """The pending-frame path still has to work: a bridge can ship a widget
        type before its fetcher exists, and the client must render the honest
        'no content yet' card rather than calling an empty method name."""
        self.Type.create({
            "name": "Probe", "code": "probe_no_fetch", "render": "list",
        })
        entry = next(
            item for item in self.Type.with_user(self.user)._catalogue_payload()
            if item["code"] == "probe_no_fetch"
        )
        self.assertEqual(entry["fetch_method"], "")
        self.assertEqual(entry["fetch_model"], "")

    def test_layout_payload_shape(self):
        payload = self.Widget.with_user(self.user)._layout_payload()
        self.assertEqual(set(payload) & {"placements", "stats", "catalogue"},
                         {"placements", "stats", "catalogue"})
        act = next(p for p in payload["placements"] if p["code"] == "activities")
        self.assertEqual(act["render"], "activities")
        self.assertEqual(act["fetch_method"], "dashboard_fetch_activities")

    def test_only_grid_types_are_placed(self):
        # A stats-zone type must never end up as a user placement.
        self.Type.create({
            "name": "Probe Stat", "code": "probe_stat", "zone": "stats",
            "render": "stat", "is_default": True,
        })
        self.Widget.search([("user_id", "=", self.user.id)]).unlink()
        placements = self.Widget.with_user(self.user)._ensure_default_layout()
        self.assertNotIn("probe_stat", placements.widget_type_id.mapped("code"))
        self.assertTrue(all(p.widget_type_id.zone == "grid" for p in placements))
