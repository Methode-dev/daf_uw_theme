from odoo import api, models, _
from odoo.tools import formatLang


class SaleOrder(models.Model):
    """Dashboard fetchers for "what is about to become revenue?" (§2.2, §3.6).

    Two questions, two fetchers: quotations still to close, and confirmed orders
    whose invoice has not been raised.  The second is the one that quietly loses
    money, which is why it gets its own widget rather than a line in the first.
    """

    _inherit = 'sale.order'

    @api.model
    def _dashboard_order_action(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'sale.order',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
            'target': 'current',
        }

    @api.model
    def _dashboard_order_rows(self, orders):
        currency = self.env.company.currency_id
        return [
            {
                'id': order.id,
                'icon': 'fa-file-text-o',
                'title': order.partner_id.display_name or order.name or '',
                'subtitle': order.name or '',
                'meta': formatLang(
                    self.env, order.amount_total or 0.0, currency_obj=currency),
                'res_model': 'sale.order',
                'res_id': order.id,
            }
            for order in orders
        ]

    # -------------------------------------------------------------------------
    # Quotations to send / close (§3.6)
    # -------------------------------------------------------------------------
    @api.model
    def _dashboard_quotation_domain(self):
        return [
            ('company_id', 'in', self.env.companies.ids),
            ('state', 'in', ['draft', 'sent']),
        ]

    @api.model
    def dashboard_fetch_quotations(self, limit=5, **kwargs):
        domain = self._dashboard_quotation_domain()
        count = self.search_count(domain)
        orders = self.search(domain, order='amount_total desc, id desc', limit=limit)

        rows = self._dashboard_order_rows(orders)
        # The pill separates "not sent yet" from "waiting on them" — different
        # problems with different next actions.
        for row, order in zip(rows, orders):
            row['pill'] = (
                {'tone': 'neutral', 'text': _("Sent")} if order.state == 'sent'
                else {'tone': 'overdue', 'text': _("Draft")}
            )

        return {
            'count': count,
            'rows': rows,
            'action': self._dashboard_order_action(domain, _("Quotations")),
            'empty': {
                'title': _("No open quotations"),
                'hint': _("Nothing waiting to be sent or signed."),
            },
        }

    # -------------------------------------------------------------------------
    # Orders to invoice (§3.6)
    # -------------------------------------------------------------------------
    @api.model
    def _dashboard_to_invoice_domain(self):
        # ⚠ 'to invoice' HAS A SPACE.  It is the stored selection value on
        # sale.order.invoice_status, not a typo, and 'to_invoice' silently matches
        # nothing.
        return [
            ('company_id', 'in', self.env.companies.ids),
            ('state', '=', 'sale'),
            ('invoice_status', '=', 'to invoice'),
        ]

    @api.model
    def dashboard_fetch_to_invoice(self, limit=5, **kwargs):
        domain = self._dashboard_to_invoice_domain()
        count = self.search_count(domain)
        orders = self.search(domain, order='date_order asc, id asc', limit=limit)

        return {
            'count': count,
            'rows': self._dashboard_order_rows(orders),
            'action': self._dashboard_order_action(domain, _("Orders to Invoice")),
            'empty': {
                'title': _("Nothing to invoice"),
                'hint': _("Every confirmed order has been billed."),
            },
        }

    @api.model
    def dashboard_fetch_to_invoice_stat(self, **kwargs):
        """Revenue that is earned but not yet billed."""
        domain = self._dashboard_to_invoice_domain()
        [(total, count)] = self._read_group(domain, [], ['amount_total:sum', '__count'])

        return {
            'value': formatLang(
                self.env, total or 0.0, currency_obj=self.env.company.currency_id),
            'label': _("To invoice"),
            'meta': (
                _("1 order") if count == 1 else _("%s orders", count)
            ),
            # Money sitting uninvoiced is a nudge, not an alarm — it becomes one
            # through the widget, not by painting the tile red.
            'tone': 'warning' if count else 'neutral',
            'action': self._dashboard_order_action(domain, _("Orders to Invoice")),
        }
