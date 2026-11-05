from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardEdit(TransactionCase):
    """Edit mode: add, remove, resize, move, restore — and layout privacy."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="dash_edit", groups="base.group_user")
        cls.other = new_test_user(cls.env, login="dash_edit2", groups="base.group_user")
        cls.Widget = cls.env["methode.dashboard.widget"]
        cls.Type = cls.env["methode.dashboard.widget.type"]

    def _widget(self, user=None):
        return self.Widget.with_user(user or self.user)

    def _codes(self, payload):
        return [placement["code"] for placement in payload["placements"]]

    def test_add_appends_and_returns_the_new_layout(self):
        layout = self._widget().dashboard_fetch_layout()
        trend = self.Type.search([("code", "=", "activity_trend")], limit=1)
        self.assertNotIn("activity_trend", self._codes(layout), "not a default")

        after = self._widget().dashboard_add_widget(trend.id)
        self.assertEqual(self._codes(after)[-1], "activity_trend", "appended, not inserted")

    def test_stats_tiles_cannot_be_placed_on_the_grid(self):
        tile = self.Type.search([("zone", "=", "stats")], limit=1)
        before = self._codes(self._widget().dashboard_fetch_layout())
        after = self._codes(self._widget().dashboard_add_widget(tile.id))
        self.assertEqual(
            before, after,
            "chrome is not placeable, even if a client asks for it",
        )

    def test_remove_then_restore_defaults(self):
        layout = self._widget().dashboard_fetch_layout()
        victim = layout["placements"][0]

        after = self._widget().dashboard_remove_widget(victim["id"])
        self.assertNotIn(victim["id"], [p["id"] for p in after["placements"]])

        restored = self._widget().dashboard_reset_layout()
        self.assertIn(victim["code"], self._codes(restored))

    def test_resize_is_clamped_to_the_grid(self):
        placement = self._widget().dashboard_fetch_layout()["placements"][0]

        after = self._widget().dashboard_resize_widget(placement["id"], 3)
        resized = next(p for p in after["placements"] if p["id"] == placement["id"])
        self.assertEqual(resized["col_span"], 3)

        # A three-column grid cannot honour 9; clamping beats a CHECK violation
        # surfacing as a traceback in the user's face.
        after = self._widget().dashboard_resize_widget(placement["id"], 9)
        resized = next(p for p in after["placements"] if p["id"] == placement["id"])
        self.assertEqual(resized["col_span"], 3)

    def test_move_swaps_with_the_neighbour_and_stops_at_the_edges(self):
        before = self._codes(self._widget().dashboard_fetch_layout())
        self.assertGreaterEqual(len(before), 2, "guard: need two widgets to swap")

        first = self._widget().dashboard_fetch_layout()["placements"][0]
        after = self._codes(self._widget().dashboard_move_widget(first["id"], 1))
        self.assertEqual(after[0], before[1])
        self.assertEqual(after[1], before[0])

        # Already first: moving earlier must be a no-op, not an error or a wrap.
        top = self._widget().dashboard_fetch_layout()["placements"][0]
        unchanged = self._codes(self._widget().dashboard_move_widget(top["id"], -1))
        self.assertEqual(unchanged[0], top["code"])

    def test_a_user_cannot_touch_another_users_placement(self):
        """⚠ CLOSES §8.5. Until now "user A cannot read user B's layout" was
        asserted in a comment and never demonstrated — every earlier check ran as
        OdooBot, which bypasses record rules entirely."""
        mine = self._widget().dashboard_fetch_layout()["placements"][0]

        # The other user's mutation must not find my row...
        theirs_before = self._codes(self._widget(self.other).dashboard_fetch_layout())
        self._widget(self.other).dashboard_remove_widget(mine["id"])
        self.assertIn(
            mine["code"], self._codes(self._widget().dashboard_fetch_layout()),
            "another user removed my widget",
        )
        self.assertEqual(
            theirs_before, self._codes(self._widget(self.other).dashboard_fetch_layout()),
            "and their own layout was untouched",
        )

        # ...and a direct read is refused outright by the record rule.
        with self.assertRaises(AccessError):
            self.Widget.with_user(self.other).browse(mine["id"]).read(["col_span"])

    def test_layouts_are_independent(self):
        trend = self.Type.search([("code", "=", "activity_trend")], limit=1)
        self._widget().dashboard_add_widget(trend.id)
        self.assertNotIn(
            "activity_trend",
            self._codes(self._widget(self.other).dashboard_fetch_layout()),
            "adding a widget must not change anyone else's dashboard",
        )
