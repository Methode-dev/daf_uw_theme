from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardSale(TransactionCase):
    """Quotation states, the to-invoice queue, and the space in 'to invoice'."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["sale.order"]
        cls.partner = cls.env["res.partner"].create({"name": "Quote Co"})
        cls.product = cls.env["product.product"].create({
            "name": "Dashboard Widget",
            "type": "service",
            "list_price": 100.0,
            "invoice_policy": "order",
        })

    def _order(self, qty=1, confirm=False):
        order = self.Order.create({
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "product_uom_qty": qty,
                "price_unit": 100.0,
            })],
        })
        if confirm:
            order.action_confirm()
        return order

    def test_draft_and_sent_are_both_open_quotations(self):
        before = self.Order.search_count(self.Order._dashboard_quotation_domain())
        draft = self._order()
        sent = self._order()
        sent.state = "sent"
        self._order(confirm=True)  # confirmed: no longer a quotation

        payload = self.Order.dashboard_fetch_quotations(limit=50)
        self.assertEqual(payload["count"], before + 2)

        ids = [row["res_id"] for row in payload["rows"]]
        self.assertIn(draft.id, ids)
        self.assertIn(sent.id, ids)

    def test_quotation_pill_separates_draft_from_sent(self):
        draft = self._order()
        payload = self.Order.dashboard_fetch_quotations(limit=50)
        row = next(r for r in payload["rows"] if r["res_id"] == draft.id)
        self.assertEqual(row["pill"]["tone"], "overdue", "a draft is on US to send")

        draft.state = "sent"
        payload = self.Order.dashboard_fetch_quotations(limit=50)
        row = next(r for r in payload["rows"] if r["res_id"] == draft.id)
        self.assertEqual(row["pill"]["tone"], "neutral", "sent is waiting on THEM")

    def test_to_invoice_queue_and_stat_agree(self):
        # invoice_policy='order' means a confirmed order is immediately billable.
        order = self._order(confirm=True)
        self.assertEqual(
            order.invoice_status, "to invoice",
            "guard: the fixture must actually land in the queue being tested",
        )

        payload = self.Order.dashboard_fetch_to_invoice(limit=50)
        self.assertIn(order.id, [row["res_id"] for row in payload["rows"]])

        stat = self.Order.dashboard_fetch_to_invoice_stat()
        self.assertEqual(stat["tone"], "warning", "money earned but not billed")
        self.assertTrue(stat["action"])

    def test_invoiced_order_leaves_the_queue(self):
        order = self._order(confirm=True)
        before = self.Order.search_count(self.Order._dashboard_to_invoice_domain())
        order._create_invoices()
        self.assertEqual(
            self.Order.search_count(self.Order._dashboard_to_invoice_domain()),
            before - 1,
            "once billed, an order is not 'to invoice'",
        )

    def test_bridge_contributes_widgets_and_shortcut(self):
        codes = self.env["methode.dashboard.widget.type"].search([]).mapped("code")
        self.assertIn("sale_quotations", codes)
        self.assertIn("stat_to_invoice", codes)

        shortcuts = self.env["methode.dashboard.widget"].dashboard_fetch_shortcuts()
        self.assertIn("new_quotation", [s["key"] for s in shortcuts["shortcuts"]])

    def test_no_sales_rights_no_sales_shortcut(self):
        plain = new_test_user(self.env, login="dash_nosale", groups="base.group_user")
        shortcuts = self.env["methode.dashboard.widget"].with_user(
            plain).dashboard_fetch_shortcuts()
        self.assertNotIn("new_quotation", [s["key"] for s in shortcuts["shortcuts"]])
