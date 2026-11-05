from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDashboardStock(TransactionCase):
    """Reorder detection (filtered in Python) and receipt lateness."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Orderpoint = cls.env["stock.warehouse.orderpoint"]
        cls.Picking = cls.env["stock.picking"]
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "in", cls.env.companies.ids)], limit=1)
        cls.product = cls.env["product.product"].create({
            "name": "Reorder Probe",
            "is_storable": True,
        })

    def test_rule_below_minimum_is_reported_and_flagged(self):
        rule = self.Orderpoint.create({
            "product_id": self.product.id,
            "warehouse_id": self.warehouse.id,
            "product_min_qty": 10.0,
            "product_max_qty": 50.0,
        })
        # Nothing in stock, minimum of 10 -> below, and specifically out of stock.
        self.assertEqual(rule.qty_on_hand, 0.0)

        payload = self.Orderpoint.dashboard_fetch_reorder(limit=50)
        row = next((r for r in payload["rows"] if r["res_id"] == rule.id), None)
        self.assertIsNotNone(row, "a rule at zero stock must be reported")
        self.assertEqual(row["pill"]["tone"], "overdue")
        self.assertEqual(row["res_model"], "stock.warehouse.orderpoint")
        self.assertIn("10", row["meta"], "the row shows on-hand against the minimum")

    def test_healthy_rule_is_not_reported(self):
        healthy = self.Orderpoint.create({
            "product_id": self.product.id,
            "warehouse_id": self.warehouse.id,
            # A minimum below zero can never be breached by empty stock, which is
            # the cheapest way to assert the filter actually filters.
            "product_min_qty": -5.0,
            "product_max_qty": 0.0,
        })
        payload = self.Orderpoint.dashboard_fetch_reorder(limit=50)
        self.assertNotIn(
            healthy.id, [row["res_id"] for row in payload["rows"]],
            "stock above the minimum is not a reorder alert",
        )

    def test_late_receipt_is_flagged_and_early_one_is_not(self):
        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", "incoming"),
            ("warehouse_id", "=", self.warehouse.id),
        ], limit=1)
        partner = self.env["res.partner"].create({"name": "Supplier Co"})

        # ⚠ NO `name` ON THE MOVE.  stock.move.name is gone in Odoo 19 (the line
        # description lives on description_picking now), and passing it raises
        # "Invalid field 'name' on model 'stock.move'" during precompute — which is
        # a fixture error, not a finding about the fetcher.
        source = (
            picking_type.default_location_src_id
            or self.env.ref("stock.stock_location_suppliers")
        )
        destination = picking_type.default_location_dest_id

        def _picking(days):
            picking = self.Picking.create({
                "partner_id": partner.id,
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "scheduled_date": datetime.now() + timedelta(days=days),
                "move_ids": [(0, 0, {
                    "product_id": self.product.id,
                    "product_uom_qty": 1,
                    "location_id": source.id,
                    "location_dest_id": destination.id,
                })],
            })
            picking.action_confirm()
            return picking

        late = _picking(-4)
        soon = _picking(3)

        payload = self.Picking.dashboard_fetch_receipts(limit=50)
        rows = {row["res_id"]: row for row in payload["rows"]}

        self.assertIn(late.id, rows, "a confirmed incoming transfer is pending")
        self.assertEqual(rows[late.id]["pill"]["tone"], "overdue")
        self.assertIn("4", rows[late.id]["pill"]["text"])
        self.assertEqual(rows[soon.id]["pill"]["tone"], "neutral")

    def test_bridge_contributes_widgets_but_no_stat_tile(self):
        Type = self.env["methode.dashboard.widget.type"]
        codes = Type.search([]).mapped("code")
        self.assertIn("inventory_reorder", codes)
        self.assertIn("inventory_receipts", codes)
        # Deliberate: inventory ships no stat tile, and neither widget is default.
        stock_types = Type.search([("code", "in", ["inventory_reorder", "inventory_receipts"])])
        self.assertTrue(all(t.zone == "grid" for t in stock_types))
        self.assertFalse(any(t.is_default for t in stock_types))
