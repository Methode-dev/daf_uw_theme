import base64
import hashlib
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import file_open

from odoo.addons.daf_uw_theme.models import res_company as res_company_module
from odoo.addons.daf_uw_theme.models.res_company import (
    APPBAR_LOGO,
    APPBAR_PLACEHOLDER,
)


def _b64(path):
    with file_open(path, "rb") as file:
        return base64.b64encode(file.read())


@tagged("post_install", "-at_install")
class TestAppbarImage(TransactionCase):
    """The sidebar footer gets the DAF Under Writing lockup, and ONLY where
    nobody chose a logo: an empty image, MuK's untouched "Your logo"
    placeholder, or a lockup an earlier version of this module seeded."""

    def _company(self, image):
        # Unique names: res.company has a unique-name constraint, and one test
        # creates two companies.
        self._count = getattr(self, "_count", 0) + 1
        return self.env["res.company"].create(
            {"name": f"Logo Co {self._count}", "appbar_image": image}
        )

    def test_placeholder_and_empty_are_replaced(self):
        placeholder = self._company(_b64(APPBAR_PLACEHOLDER))
        empty = self._company(False)
        self.env["res.company"]._m_seed_appbar_image()
        self.assertEqual(placeholder.appbar_image, _b64(APPBAR_LOGO))
        self.assertEqual(empty.appbar_image, _b64(APPBAR_LOGO))

    def test_a_chosen_logo_is_kept(self):
        # Any other image: the theme's own favicon stands in for "the admin's".
        chosen = _b64("daf_uw_theme/static/src/img/favicon/favicon-32x32.png")
        company = self._company(chosen)
        self.env["res.company"]._m_seed_appbar_image()
        self.assertEqual(company.appbar_image, chosen)

    def test_a_previously_seeded_lockup_is_replaced(self):
        # The old Méthode lockup is no longer shipped, so stand in for it with
        # another file and register that file's digest as superseded.
        old = _b64("daf_uw_theme/static/src/img/favicon/favicon-16x16.png")
        digest = hashlib.sha256(base64.b64decode(old)).hexdigest()
        company = self._company(old)
        with patch.object(res_company_module, "SUPERSEDED_APPBAR_SHA256",
                          frozenset({digest})):
            self.env["res.company"]._m_seed_appbar_image()
        self.assertEqual(company.appbar_image, _b64(APPBAR_LOGO))
