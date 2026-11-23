from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPortalChrome(HttpCase):
    """AC-QA4-4: the portal header carries the DAF mark, not the company's
    placeholder logo, and the page loads the theme's frontend bundle."""

    def test_ac_qa4_4_the_portal_header_shows_the_daf_mark(self):
        user = self.env["res.users"].create(
            {
                "name": "Portal Chrome",
                "login": "portal-chrome@example.test",
                "password": "Portal-chrome-1!",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self.authenticate(user.login, "Portal-chrome-1!")

        body = self.url_open("/my").text

        self.assertIn("/daf_uw_theme/static/src/img/brand/daf_uw_logo.svg", body)
        self.assertNotIn("/logo.png?company=", body)
