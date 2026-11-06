from odoo import api, models, _

# How many reordering rules to examine before giving up.  Needed because the
# filtering below happens in PYTHON, not SQL (see the note in the fetcher), so an
# unbounded scan would read every rule in the database to render five rows.
SCAN_LIMIT = 500


class StockWarehouseOrderpoint(models.Model):
    """Products at or below their minimum — "what will I run out of?"."""

    _inherit = 'stock.warehouse.orderpoint'

    @api.model
    def dashboard_fetch_reorder(self, limit=5, **kwargs):
        """Reordering rules whose stock has fallen to the minimum.

        ⚠ THE FILTER CANNOT BE A DOMAIN.  `qty_on_hand` is computed and NOT
        stored, so `[('qty_on_hand', '<=', 'product_min_qty')]` is impossible
        twice over — the field has no column, and a domain cannot compare two
        fields anyway.  So the rules are read (bounded by SCAN_LIMIT) and filtered
        in Python.  This is the one fetcher whose count is therefore an
        approximation on a very large database, and that is a deliberate trade: the
        alternative is a stored computed field recomputed on every stock move.
        """
        rules = self.search(
            [('company_id', 'in', self.env.companies.ids)], limit=SCAN_LIMIT)
        below = rules.filtered(lambda rule: rule.qty_on_hand <= rule.product_min_qty)
        # Worst first: the further below the minimum, the more urgent.
        below = below.sorted(lambda rule: rule.qty_on_hand - rule.product_min_qty)

        rows = []
        for rule in below[:limit]:
            uom = rule.product_uom.name if rule.product_uom else ''
            rows.append({
                'id': rule.id,
                'icon': 'fa-cubes',
                'title': rule.product_id.display_name or '',
                'subtitle': rule.warehouse_id.name or '',
                'meta': _("%(on_hand)s / %(min)s %(uom)s",
                          on_hand=rule.qty_on_hand, min=rule.product_min_qty, uom=uom),
                'res_model': 'stock.warehouse.orderpoint',
                'res_id': rule.id,
                'pill': (
                    {'tone': 'overdue', 'text': _("Out of stock")}
                    if rule.qty_on_hand <= 0 else
                    {'tone': 'neutral', 'text': _("Low")}
                ),
            })

        return {
            'count': len(below),
            'rows': rows,
            'action': {
                'type': 'ir.actions.act_window',
                'name': _("Reordering Rules"),
                'res_model': 'stock.warehouse.orderpoint',
                'views': [[False, 'list'], [False, 'form']],
                'domain': [('id', 'in', below.ids)],
                'target': 'current',
            },
            'empty': {
                'title': _("Stock is healthy"),
                'hint': _("Nothing has fallen to its reorder point."),
            },
        }
