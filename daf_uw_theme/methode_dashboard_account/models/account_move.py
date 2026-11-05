from odoo import api, fields, models, _
from odoo.tools import formatLang

# Unpaid, in the customer's court.  `payment_state` is the field that moved across
# versions, so it is stated once here and reused by every fetcher below.
UNPAID_STATES = ('not_paid', 'partial')


class AccountMove(models.Model):
    """Dashboard fetchers for the money questions (§2.2, §3.2, §3.3).

    On the model, as public `@api.model` methods, so the ORM's access rules apply
    and each one is testable without HTTP (§4).  Aura answered these from a
    controller; the domains here are the same, the architecture is not.

    ⚠ NOT SCOPED TO THE CURRENT USER, deliberately.  §3.2 asks "how much am I
    owed?" — that is a question about the business, not about who is looking, so
    these read the whole company.  (Aura filtered on `invoice_user_id`, which
    quietly answers a different question and shows a manager nothing.)  The
    pipeline widget IS user-scoped, because "what is MY pipeline worth" genuinely
    is personal — see the crm bridge.
    """

    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # Shared domain
    # -------------------------------------------------------------------------
    @api.model
    def _dashboard_receivable_domain(self):
        return [
            ('company_id', 'in', self.env.companies.ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', UNPAID_STATES),
        ]

    @api.model
    def _dashboard_money(self, amount):
        """Format an amount in the company currency, for a row's trailing figure."""
        return formatLang(
            self.env, amount, currency_obj=self.env.company.currency_id)

    @api.model
    def _dashboard_invoice_action(self, domain, name):
        """A real list of the records behind a number (§1: every number is a link).

        Built as an act_window dict rather than referencing an accounting action
        xmlid, so the click-through cannot break when Odoo renames one.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'account.move',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # Open invoices — widget + stat (§3.2)
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_fetch_open_invoices(self, limit=5, **kwargs):
        """Unpaid customer invoices, oldest due first — the money to chase."""
        domain = self._dashboard_receivable_domain()
        today = fields.Date.context_today(self)

        count = self.search_count(domain)
        invoices = self.search(
            domain, order='invoice_date_due asc, id asc', limit=limit)

        rows = []
        for invoice in invoices:
            due = invoice.invoice_date_due
            overdue_days = (today - due).days if due and due < today else 0
            rows.append({
                'id': invoice.id,
                'icon': 'fa-file-text-o',
                'title': invoice.partner_id.display_name or invoice.name or '',
                'subtitle': invoice.name or '',
                'meta': self._dashboard_money(invoice.amount_residual),
                'res_model': 'account.move',
                'res_id': invoice.id,
                'pill': (
                    {
                        'tone': 'overdue',
                        'text': (
                            _("1 day late") if overdue_days == 1
                            else _("%s days late", overdue_days)
                        ),
                    }
                    if overdue_days else
                    {'tone': 'neutral', 'text': _("Open")}
                ),
            })

        return {
            'count': count,
            'rows': rows,
            'action': self._dashboard_invoice_action(domain, _("Open Invoices")),
            'empty': {
                'title': _("Nothing outstanding"),
                'hint': _("Every posted invoice has been paid."),
            },
        }

    @api.model
    def dashboard_fetch_open_invoices_stat(self, **kwargs):
        """How much is outstanding, and how much of it is already late."""
        domain = self._dashboard_receivable_domain()
        today = fields.Date.context_today(self)

        [(total, count)] = self._read_group(domain, [], ['amount_residual:sum', '__count'])
        overdue_domain = domain + [('invoice_date_due', '<', today)]
        [(overdue_total, overdue_count)] = self._read_group(
            overdue_domain, [], ['amount_residual:sum', '__count'])

        if overdue_count:
            meta = _("%(amount)s overdue", amount=self._dashboard_money(overdue_total or 0.0))
            tone = 'danger'
        else:
            meta = (
                _("1 open invoice") if count == 1
                else _("%s open invoices", count)
            )
            tone = 'neutral'

        return {
            'value': self._dashboard_money(total or 0.0),
            'label': _("Outstanding"),
            'meta': meta,
            'tone': tone,
            'action': self._dashboard_invoice_action(domain, _("Open Invoices")),
        }

    # -------------------------------------------------------------------------
    # Overdue receivables — stat (§3.3)
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_fetch_overdue_stat(self, **kwargs):
        """How much is late, and how late the worst of it is."""
        today = fields.Date.context_today(self)
        domain = self._dashboard_receivable_domain() + [('invoice_date_due', '<', today)]

        [(total, count)] = self._read_group(domain, [], ['amount_residual:sum', '__count'])
        oldest = self.search(domain, order='invoice_date_due asc', limit=1)

        if oldest:
            days = (today - oldest.invoice_date_due).days
            meta = _("oldest %s days late", days)
            tone = 'danger'
        else:
            meta = _("nothing late")
            tone = 'neutral'

        return {
            'value': self._dashboard_money(total or 0.0),
            'label': _("Overdue"),
            'meta': meta,
            'tone': tone,
            'action': self._dashboard_invoice_action(domain, _("Overdue Invoices")),
        }

    # -------------------------------------------------------------------------
    # Aged receivables — widget, grouped by age
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_fetch_aged_receivables(self, limit=5, **kwargs):
        """Open invoices bucketed by how long they have been late.

        Buckets rather than a flat list because the question is "how bad is this",
        and a 90-day debt is a different problem from a 10-day one.
        """
        today = fields.Date.context_today(self)
        base = self._dashboard_receivable_domain()

        # (key, label, days late from, days late to).  `None` from = not yet due;
        # `None` to = open-ended.  The ranges are half-open on the recent side so
        # an invoice due TODAY lands in exactly one bucket — with `<= today` and
        # `>= today` on adjacent buckets it would be counted twice.
        buckets = (
            ('current', _("Not yet due"), None, None),
            ('1_30', _("1-30 days late"), 1, 30),
            ('31_60', _("31-60 days late"), 31, 60),
            ('60_plus', _("60+ days late"), 61, None),
        )

        groups = []
        total_count = 0
        slots_left = max(limit, 0)
        for key, label, late_from, late_to in buckets:
            if late_from is None:
                domain = base + [('invoice_date_due', '>=', today)]
            else:
                # "N days late" means the due date is N days in the past.
                domain = base + [
                    ('invoice_date_due', '<=', fields.Date.subtract(today, days=late_from)),
                ]
                if late_to is not None:
                    domain += [
                        ('invoice_date_due', '>=', fields.Date.subtract(today, days=late_to)),
                    ]

            count = self.search_count(domain)
            total_count += count

            rows = []
            if slots_left and count:
                for invoice in self.search(
                        domain, order='invoice_date_due asc, id asc', limit=slots_left):
                    rows.append({
                        'id': invoice.id,
                        'icon': 'fa-file-text-o',
                        'title': invoice.partner_id.display_name or invoice.name or '',
                        'subtitle': invoice.name or '',
                        'meta': self._dashboard_money(invoice.amount_residual),
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                    })
                slots_left -= len(rows)

            groups.append({'key': key, 'label': label, 'count': count, 'rows': rows})

        return {
            'count': total_count,
            'groups': groups,
            'action': self._dashboard_invoice_action(base, _("Aged Receivables")),
            'empty': {
                'title': _("Nothing outstanding"),
                'hint': _("No unpaid customer invoices."),
            },
        }
