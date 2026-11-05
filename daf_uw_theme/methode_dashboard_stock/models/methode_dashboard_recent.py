from odoo import api, models


class MethodeDashboardRecent(models.AbstractModel):
    """Transfers are resumable work, so they belong in "Continue Working"."""

    _inherit = 'methode.dashboard.recent'

    @api.model
    def _collect_recent_models(self):
        return super()._collect_recent_models() + ['stock.picking']
