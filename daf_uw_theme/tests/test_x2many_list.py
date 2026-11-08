from urllib.parse import urlsplit

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestX2ManyListLink(HttpCase):
    """/daf_uw_theme/list/<model>: the target of the "open the list in a new
    tab" link of x2many lists (controllers/x2many_list.py)."""

    def setUp(self):
        super().setUp()
        self.authenticate("admin", "admin")

    def _location(self, model):
        response = self.url_open(f"/daf_uw_theme/list/{model}", allow_redirects=False)
        self.assertEqual(response.status_code, 303, response.text[:200])
        location = urlsplit(response.headers["Location"])
        return location.path, location.query

    def test_menu_action(self):
        """A model with a menu lands on the window action of a visible menu."""
        path, _query = self._location("res.users")
        self.assertTrue(path.startswith("/odoo/action-"), path)
        action = self.env["ir.actions.act_window"].browse(
            int(path.removeprefix("/odoo/action-"))
        )
        self.assertEqual(action.res_model, "res.users")
        self.assertIn("list", action.view_mode)
        self.assertTrue(
            self.env["ir.ui.menu"].search(
                [("action", "=", f"ir.actions.act_window,{action.id}")]
            )
        )

    def test_model_without_action(self):
        """A model with no window action opens its default list view."""
        with_action = set(
            self.env["ir.actions.act_window"].search([]).mapped("res_model")
        )
        model = next(
            name
            for name in self.env["ir.model"]
            .search([("transient", "=", False)])
            .mapped("model")
            if "." in name and name not in with_action and not self.env[name]._abstract
        )
        path, query = self._location(model)
        self.assertEqual(path, f"/odoo/{model}")
        self.assertEqual(query, "view_type=list")

    def test_unknown_model(self):
        response = self.url_open(
            "/daf_uw_theme/list/no.such.model", allow_redirects=False
        )
        self.assertEqual(response.status_code, 404)
