from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Surface the dashboard thresholds on the Settings page (§2.4)."""

    _inherit = 'res.config.settings'

    methode_dashboard_overdue_days = fields.Integer(
        related='company_id.methode_dashboard_overdue_days',
        readonly=False,
    )
    methode_dashboard_stalled_days = fields.Integer(
        related='company_id.methode_dashboard_stalled_days',
        readonly=False,
    )
