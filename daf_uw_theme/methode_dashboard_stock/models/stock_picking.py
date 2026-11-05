from odoo import api, fields, models, _


class StockPicking(models.Model):
    """Incoming shipments that are ready, and how late they are running."""

    _inherit = 'stock.picking'

    @api.model
    def _dashboard_receipt_domain(self):
        return [
            ('company_id', 'in', self.env.companies.ids),
            ('picking_type_code', '=', 'incoming'),
            # Ready to act on, rather than every draft/waiting transfer — the
            # widget answers "what can I receive", not "what exists".
            ('state', 'in', ['assigned', 'confirmed']),
        ]

    @api.model
    def dashboard_fetch_receipts(self, limit=5, **kwargs):
        domain = self._dashboard_receipt_domain()
        today = fields.Date.context_today(self)

        count = self.search_count(domain)
        pickings = self.search(domain, order='scheduled_date asc, id asc', limit=limit)

        rows = []
        for picking in pickings:
            scheduled = picking.scheduled_date
            scheduled_date = scheduled.date() if scheduled else False
            late_days = (today - scheduled_date).days if scheduled_date and scheduled_date < today else 0
            rows.append({
                'id': picking.id,
                'icon': 'fa-truck',
                'title': picking.partner_id.display_name or picking.name or '',
                'subtitle': picking.name or '',
                'meta': fields.Date.to_string(scheduled_date) if scheduled_date else '',
                'res_model': 'stock.picking',
                'res_id': picking.id,
                'pill': (
                    {
                        'tone': 'overdue',
                        'text': (
                            _("1 day late") if late_days == 1
                            else _("%s days late", late_days)
                        ),
                    }
                    if late_days else
                    {'tone': 'neutral', 'text': _("Ready")}
                ),
            })

        return {
            'count': count,
            'rows': rows,
            'action': {
                'type': 'ir.actions.act_window',
                'name': _("Pending Receipts"),
                'res_model': 'stock.picking',
                'views': [[False, 'list'], [False, 'form']],
                'domain': domain,
                'target': 'current',
            },
            'empty': {
                'title': _("Nothing to receive"),
                'hint': _("No incoming shipments are waiting."),
            },
        }
