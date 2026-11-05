from odoo import api, fields, models, _

from odoo.addons.daf_uw_theme.models.methode_dashboard_focus import URGENCY_OVERDUE


class MethodeDashboardInsight(models.AbstractModel):
    """Accounting's contribution to the insight banners (§2.4).

    THE CONTRIBUTION PATTERN: inherit, call super(), append.  Nothing here asks
    whether `account` is installed — this override only exists while this module
    does, and this module only exists while account does.  That is what replaced
    Aura's runtime module scan.
    """

    _inherit = 'methode.dashboard.insight'

    @api.model
    def _collect_insights(self):
        insights = super()._collect_insights()

        # ⚠ ACCESS FIRST, ALWAYS.  Installed does not mean permitted: plenty of
        # internal users have no accounting rights at all, and querying
        # account.move as one of them raises AccessError — which, because these
        # contributions chain through super(), would take EVERY banner down with
        # it, including the ones that user is entitled to.  Skip quietly instead.
        if not self._dashboard_can_read('account.move'):
            return insights

        # Threshold is CONFIGURATION, not a constant (§2.4): a business on 90-day
        # terms does not want a 30-day alarm.  Settings > General Settings >
        # Dashboard Alerts.
        days = self.env.company.methode_dashboard_overdue_days or 30
        cutoff = fields.Date.subtract(fields.Date.context_today(self), days=days)

        Move = self.env['account.move']
        domain = Move._dashboard_receivable_domain() + [
            ('invoice_date_due', '<', cutoff),
        ]
        count = Move.search_count(domain)
        if count:
            insights.append({
                'key': 'invoices_long_overdue',
                'icon': 'fa-exclamation-circle',
                'tone': 'warning',
                'message': (
                    _("1 invoice is more than %(days)s days overdue", days=days)
                    if count == 1 else
                    _("%(count)s invoices are more than %(days)s days overdue",
                      count=count, days=days)
                ),
                'action_label': _("Review invoices"),
                'action': Move._dashboard_invoice_action(
                    domain, _("Long Overdue Invoices")),
            })

        return insights


class MethodeDashboardFocus(models.AbstractModel):
    """Overdue invoices belong in "Today's Focus" — they are work, not just news."""

    _inherit = 'methode.dashboard.focus'

    @api.model
    def _collect_focus_rows(self):
        rows = super()._collect_focus_rows()
        if not self._dashboard_can_read('account.move'):
            return rows

        today = fields.Date.context_today(self)
        Move = self.env['account.move']
        overdue = Move.search(
            Move._dashboard_receivable_domain() + [('invoice_date_due', '<', today)],
            order='invoice_date_due asc', limit=5)

        for invoice in overdue:
            days = (today - invoice.invoice_date_due).days
            rows.append({
                'id': 'invoice-%s' % invoice.id,
                'icon': 'fa-file-text-o',
                'title': invoice.partner_id.display_name or invoice.name or '',
                'subtitle': invoice.name or '',
                'meta': Move._dashboard_money(invoice.amount_residual),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'pill': {
                    'tone': 'overdue',
                    'text': _("1 day late") if days == 1 else _("%s days late", days),
                },
                'urgency': URGENCY_OVERDUE,
                'sort_date': fields.Date.to_string(invoice.invoice_date_due),
            })

        return rows

    @api.model
    def _dashboard_can_read(self, model_name):
        return self.env['methode.dashboard.insight']._dashboard_can_read(model_name)


class MethodeDashboardRecent(models.AbstractModel):
    """Invoices are worth resuming, so add them to "Continue Working"."""

    _inherit = 'methode.dashboard.recent'

    @api.model
    def _collect_recent_models(self):
        return super()._collect_recent_models() + ['account.move']


class MethodeDashboardShortcut(models.AbstractModel):
    """"New Invoice" in the quick-action row, present only while account is."""

    _inherit = 'methode.dashboard.shortcut'

    @api.model
    def _collect_shortcuts(self):
        shortcuts = super()._collect_shortcuts()
        # Do not offer a button that lands on an access error.
        if not self._dashboard_can_read('account.move'):
            return shortcuts
        shortcuts.append({
            'key': 'new_invoice',
            'label': _("New Invoice"),
            'icon': 'fa-file-text-o',
            'action': {
                'type': 'ir.actions.act_window',
                'name': _("New Invoice"),
                'res_model': 'account.move',
                'views': [[False, 'form']],
                'target': 'current',
                'context': {'default_move_type': 'out_invoice'},
            },
        })
        return shortcuts
