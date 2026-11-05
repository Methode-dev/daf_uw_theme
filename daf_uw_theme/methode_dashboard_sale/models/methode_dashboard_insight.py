from odoo import api, models, _


class MethodeDashboardShortcut(models.AbstractModel):
    """"New Quotation" in the quick-action row, present only while sale is."""

    _inherit = 'methode.dashboard.shortcut'

    @api.model
    def _collect_shortcuts(self):
        shortcuts = super()._collect_shortcuts()
        if not self._dashboard_can_read('sale.order'):
            return shortcuts
        shortcuts.append({
            'key': 'new_quotation',
            'label': _("New Quotation"),
            'icon': 'fa-shopping-cart',
            'action': {
                'type': 'ir.actions.act_window',
                'name': _("New Quotation"),
                'res_model': 'sale.order',
                'views': [[False, 'form']],
                'target': 'current',
            },
        })
        return shortcuts


class MethodeDashboardRecent(models.AbstractModel):
    """Quotations and orders are resumable work."""

    _inherit = 'methode.dashboard.recent'

    @api.model
    def _collect_recent_models(self):
        return super()._collect_recent_models() + ['sale.order']


class MethodeDashboardInsight(models.AbstractModel):
    """Sales contributes no banner, deliberately.

    ⚠ THIS ABSENCE IS A DECISION, NOT AN OVERSIGHT.  §2.4 says the banners are
    "the small number of things that should interrupt", and uninvoiced orders do
    not qualify: they are a queue to work through, which is what the "Orders to
    Invoice" widget and its stat tile are for.  Adding a fourth banner for
    something no one has to act on TODAY is how the zone becomes wallpaper and the
    two banners that do matter stop being read.

    The class stays as the marker for that reasoning, and as the place a
    genuinely-urgent sales signal would go (an order blocked past its commitment
    date, say — not "there is work in the queue").
    """

    _inherit = 'methode.dashboard.insight'
