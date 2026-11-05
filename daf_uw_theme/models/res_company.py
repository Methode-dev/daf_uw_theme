import base64
import hashlib

from odoo import api, fields, models
from odoo.tools import file_open

# MuK's sidebar footer image. muk_web_appsbar's install hook seeds it with
# Odoo's own "Your logo" placeholder; this is that file, and ours.
APPBAR_PLACEHOLDER = 'base/static/img/res_company_logo.png'
APPBAR_LOGO = 'daf_uw_theme/static/src/img/brand/appbar_logo.png'

# Lockups this module itself seeded in earlier versions, by SHA-256 of the raw
# PNG bytes.  They count as "nobody chose a logo" too: without this, every
# database seeded before the DAF Under Writing rebrand would keep the old
# Méthode lockup forever, because the seed only ever replaced the placeholder.
# Add the digest of appbar_logo.png here whenever that file is replaced.
SUPERSEDED_APPBAR_SHA256 = frozenset({
    # Méthode lockup (tree mark + "Méthode"), 726x192 — until 19.0.1.2.0.
    'fc110c4ff34e92b9d2b0eaccd216ccfc79990f02a7a6d00649b40ac345d13f7b',
})

# HOMEPAGE_DASHBOARD_PLAN §2.4: "Thresholds are configuration, not constants — a
# business with 90-day terms does not want a 30-day alarm."  These are the
# defaults, not the rule.
DEFAULT_OVERDUE_DAYS = 30
DEFAULT_STALLED_DAYS = 7


class ResCompany(models.Model):
    """Company-level thresholds for the dashboard's insight banners.

    On the company rather than per user: "when is a receivable late" is a
    property of how the business bills, not of who is looking at the screen.
    """

    _inherit = 'res.company'

    methode_dashboard_overdue_days = fields.Integer(
        string="Overdue Invoice Alert (days)",
        default=DEFAULT_OVERDUE_DAYS,
        help="An unpaid customer invoice raises a dashboard banner once it is "
             "this many days past its due date.")
    methode_dashboard_stalled_days = fields.Integer(
        string="Stalled Deal Alert (days)",
        default=DEFAULT_STALLED_DAYS,
        help="An open opportunity with no update for this many days raises a "
             "dashboard banner.")

    @api.model
    def _m_seed_appbar_image(self):
        """Put the DAF Under Writing lockup in the app sidebar's footer, where
        MuK left Odoo's "Your logo" placeholder.

        Called from data/appbar_image_data.xml, i.e. on install AND on every
        update, so databases that predate this get fixed by a plain upgrade.

        ⚠ ONLY an empty image, MuK's untouched placeholder, or a lockup this
        module seeded itself (SUPERSEDED_APPBAR_SHA256) is replaced. A company
        whose admin uploaded a real logo keeps it; the comparison is on the
        stored bytes, so a re-upload of the same placeholder counts as
        untouched, which is the intent.
        """
        with file_open(APPBAR_PLACEHOLDER, 'rb') as file:
            placeholder = base64.b64encode(file.read())
        with file_open(APPBAR_LOGO, 'rb') as file:
            logo = base64.b64encode(file.read())
        for company in self.sudo().search([]):
            current = company.appbar_image
            if (not current or current == placeholder
                    or self._m_is_superseded_appbar(current)):
                if current != logo:
                    company.appbar_image = logo

    @api.model
    def _m_is_superseded_appbar(self, image_b64):
        """True when ``image_b64`` is a lockup an earlier version seeded."""
        try:
            raw = base64.b64decode(image_b64)
        except (TypeError, ValueError):
            return False
        return hashlib.sha256(raw).hexdigest() in SUPERSEDED_APPBAR_SHA256
