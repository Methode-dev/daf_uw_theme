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


@tagged("post_install", "-at_install")
class TestX2ManyListLinkAccess(HttpCase):
    """The link is drawn, and leads somewhere, only when the user may open
    the list: a plain internal user gets no link and a 404 for a model they
    cannot read or whose only action is restricted to other groups."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "Utilisateur Test Liste",
                "login": "liste-test@example.test",
                "password": "liste-test-pw",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        Action = cls.env["ir.actions.act_window"]
        cls.open_action = Action.create(
            {
                "name": "Partenaires test",
                "res_model": "res.partner",
                "view_mode": "list,form",
            }
        )
        cls.open_menu = cls.env["ir.ui.menu"].create(
            {
                "name": "Partenaires test",
                "action": f"ir.actions.act_window,{cls.open_action.id}",
            }
        )
        # Same model, an action behind a menu of a group the user lacks:
        # created after, so a search that ignored visibility would pick it.
        cls.hidden_action = Action.create(
            {
                "name": "Partenaires admin",
                "res_model": "res.partner",
                "view_mode": "list,form",
            }
        )
        cls.env["ir.ui.menu"].create(
            {
                "name": "Partenaires admin",
                "action": f"ir.actions.act_window,{cls.hidden_action.id}",
                "group_ids": [(6, 0, [cls.env.ref("base.group_system").id])],
                "sequence": 0,
            }
        )
        # An unrestricted action whose only menu sits under an administrator
        # menu (as base's Technical > Attachments): not a list the user
        # reaches, though the menu itself has no group.
        cls.menuless_action = Action.create(
            {
                "name": "Devises test",
                "res_model": "res.currency",
                "view_mode": "list,form",
            }
        )
        admin_parent = cls.env["ir.ui.menu"].create(
            {
                "name": "Technique test",
                "group_ids": [(6, 0, [cls.env.ref("base.group_system").id])],
            }
        )
        cls.env["ir.ui.menu"].create(
            {
                "name": "Devises test",
                "parent_id": admin_parent.id,
                "action": f"ir.actions.act_window,{cls.menuless_action.id}",
            }
        )
        cls.admin_action = Action.create(
            {
                "name": "Banques test",
                "res_model": "res.bank",
                "view_mode": "list,form",
                "group_ids": [(6, 0, [cls.env.ref("base.group_system").id])],
            }
        )

    def _status(self, model):
        self.authenticate("liste-test@example.test", "liste-test-pw")
        response = self.url_open(f"/daf_uw_theme/list/{model}", allow_redirects=False)
        return response

    def test_models_in_session(self):
        models = self.env["ir.http"].with_user(self.user)._m_list_link_models()
        self.assertIn("res.partner", models)
        self.assertNotIn("ir.config_parameter", models)
        self.assertIs(self.env["ir.http"]._m_list_link_models(), True)

    def test_unreadable_model_is_not_found(self):
        self.assertEqual(self._status("ir.config_parameter").status_code, 404)

    def test_action_of_other_groups_is_not_found(self):
        """res.bank: readable by every user, but its only list actions here
        need the administrator group (or another group the user lacks)."""
        models = self.env["ir.http"].with_user(self.user)._m_list_link_models()
        if "res.bank" in models:
            self.skipTest("an open res.bank action exists in this database")
        self.assertEqual(self._status("res.bank").status_code, 404)

    def test_allowed_action(self):
        """The visible menu's action, never the one behind a hidden menu."""
        response = self._status("res.partner")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            urlsplit(response.headers["Location"]).path,
            f"/odoo/action-{self.open_action.id}",
        )

    def test_action_without_menu_is_not_a_link(self):
        """An unrestricted action no reachable menu of the user leads to
        (e.g. base's attachments, under Settings) is not a list they reach:
        no link, 404."""
        models = self.env["ir.http"].with_user(self.user)._m_list_link_models()
        visible = self.env["ir.ui.menu"].with_user(self.user)._visible_menu_ids()
        currency_menus = (
            self.env["ir.ui.menu"]
            .search([("id", "in", list(visible)), ("action", "like", "act_window")])
            .filtered(
                lambda m: m.action.res_model == "res.currency"
                and all(
                    int(i) in visible for i in m.parent_path.strip("/").split("/")
                )
            )
        )
        if currency_menus:
            self.skipTest("a reachable res.currency menu exists in this database")
        self.assertNotIn("res.currency", models)
        self.assertEqual(self._status("res.currency").status_code, 404)
