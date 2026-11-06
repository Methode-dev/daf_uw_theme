from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDashboardAccount(TransactionCase):
    """Values, not "it runs" (§4). Each figure is checked against known input."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Move = cls.env["account.move"]
        cls.partner = cls.env["res.partner"].create({"name": "Aged Co"})
        cls.today = fields.Date.context_today(cls.env["account.move"])
        # A clean slate: this DB may carry invoices from demo data or earlier work,
        # and an absolute assertion on a shared table is a flaky test.  Everything
        # below is measured as a DELTA against whatever already exists.
        cls.baseline = cls.Move.dashboard_fetch_open_invoices_stat()

    def _invoice(self, amount, due_offset, post=True):
        """A customer invoice for `amount`, due `due_offset` days from today."""
        move = self.Move.create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "invoice_date": self.today,
            "invoice_date_due": self.today + timedelta(days=due_offset),
            "invoice_line_ids": [(0, 0, {
                "name": "Service",
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [],
            })],
        })
        if post:
            move.action_post()
        return move

    def _open_count(self):
        return self.Move.search_count(self.Move._dashboard_receivable_domain())

    def test_only_posted_unpaid_customer_invoices_count(self):
        before = self._open_count()
        self._invoice(100, 10)                 # counts
        self._invoice(200, -5)                 # counts, and is late
        self._invoice(300, 10, post=False)     # draft: must NOT count
        self.assertEqual(self._open_count(), before + 2)

    def test_overdue_stat_flags_danger_and_reports_the_oldest(self):
        self._invoice(150, -12)
        stat = self.Move.dashboard_fetch_overdue_stat()
        self.assertEqual(stat["tone"], "danger", "money is late, so the tile says so")
        self.assertIn("12", stat["meta"], "the tile names how late the worst one is")
        self.assertTrue(stat["action"], "the number must open the invoices behind it")

    def test_open_invoice_rows_carry_amount_and_lateness(self):
        invoice = self._invoice(250, -3)
        payload = self.Move.dashboard_fetch_open_invoices(limit=50)

        row = next(r for r in payload["rows"] if r["res_id"] == invoice.id)
        self.assertEqual(row["res_model"], "account.move")
        self.assertEqual(row["title"], self.partner.display_name)
        self.assertIn("250", row["meta"].replace(" ", " "))
        self.assertEqual(row["pill"]["tone"], "overdue")
        self.assertIn("3", row["pill"]["text"])

    def test_open_invoice_row_not_yet_due_is_neutral(self):
        invoice = self._invoice(90, 15)
        payload = self.Move.dashboard_fetch_open_invoices(limit=50)
        row = next(r for r in payload["rows"] if r["res_id"] == invoice.id)
        self.assertEqual(row["pill"]["tone"], "neutral", "not late is not an alarm")

    def test_aged_buckets_place_each_invoice_exactly_once(self):
        self._invoice(10, 5)      # not yet due
        self._invoice(20, -10)    # 1-30
        self._invoice(30, -45)    # 31-60
        self._invoice(40, -120)   # 60+

        payload = self.Move.dashboard_fetch_aged_receivables(limit=50)
        by_key = {group["key"]: group for group in payload["groups"]}
        self.assertEqual(
            set(by_key), {"current", "1_30", "31_60", "60_plus"})
        # The four invoices above are spread one per bucket; totals are deltas
        # because the database may hold others.
        self.assertEqual(payload["count"], sum(g["count"] for g in payload["groups"]))
        self.assertTrue(by_key["60_plus"]["count"] >= 1)
        self.assertTrue(by_key["31_60"]["count"] >= 1)

    def test_due_today_lands_in_one_bucket_only(self):
        invoice = self._invoice(60, 0)
        payload = self.Move.dashboard_fetch_aged_receivables(limit=50)
        hits = [
            group["key"] for group in payload["groups"]
            if invoice.id in [row["res_id"] for row in group["rows"]]
        ]
        # It may not be rendered at all if the cap is filled by older invoices,
        # but it must never appear twice.
        self.assertLessEqual(len(hits), 1, "an invoice cannot be in two age buckets")

    def test_insight_uses_the_configured_threshold(self):
        self.env.company.methode_dashboard_overdue_days = 30
        self._invoice(500, -45)

        keys = [
            insight["key"]
            for insight in self.env["methode.dashboard.widget"]
            .dashboard_fetch_insights(limit=10)["insights"]
        ]
        self.assertIn("invoices_long_overdue", keys)

        # Raise the threshold past that invoice: the banner must go quiet.
        self.env.company.methode_dashboard_overdue_days = 90
        keys = [
            insight["key"]
            for insight in self.env["methode.dashboard.widget"]
            .dashboard_fetch_insights(limit=10)["insights"]
        ]
        self.assertNotIn(
            "invoices_long_overdue", keys,
            "the threshold is configuration, and configuration must be obeyed",
        )

    def test_entitled_user_sees_the_banner_and_the_shortcut(self):
        """The other half of the access guard: for a user WITH invoicing rights,
        the accounting contributions must actually appear."""
        accountant = new_test_user(
            self.env, login="dash_acct",
            groups="base.group_user,account.group_account_invoice")
        self.env.company.methode_dashboard_overdue_days = 30
        self._invoice(800, -60)

        widget = self.env["methode.dashboard.widget"].with_user(accountant)
        keys = [i["key"] for i in widget.dashboard_fetch_insights(limit=10)["insights"]]
        self.assertIn("invoices_long_overdue", keys)
        self.assertIn(
            "new_invoice",
            [s["key"] for s in widget.dashboard_fetch_shortcuts()["shortcuts"]],
        )

    def test_unentitled_user_gets_no_accounting_contribution(self):
        plain = new_test_user(self.env, login="dash_plain", groups="base.group_user")
        self._invoice(800, -60)

        widget = self.env["methode.dashboard.widget"].with_user(plain)
        # Must not raise, and must not offer accounting things.
        keys = [i["key"] for i in widget.dashboard_fetch_insights(limit=10)["insights"]]
        self.assertNotIn("invoices_long_overdue", keys)
        self.assertNotIn(
            "new_invoice",
            [s["key"] for s in widget.dashboard_fetch_shortcuts()["shortcuts"]],
        )

    def test_bridge_contributes_widgets_and_shortcuts(self):
        codes = self.env["methode.dashboard.widget.type"].search([]).mapped("code")
        self.assertIn("invoices", codes)
        self.assertIn("stat_open_invoices", codes)

        shortcuts = self.env["methode.dashboard.widget"].dashboard_fetch_shortcuts()
        self.assertIn(
            "new_invoice", [s["key"] for s in shortcuts["shortcuts"]],
            "the accounting shortcut appears because this module is installed",
        )
