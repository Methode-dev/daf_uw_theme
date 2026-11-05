from datetime import date, timedelta

from odoo import fields
from odoo.tests.common import new_test_user, tagged

from odoo.addons.daf_uw_theme.tests.common import DashboardCase


@tagged("post_install", "-at_install")
class TestDashboardCrm(DashboardCase):
    """Pipeline totals, stage grouping, user scoping, and the stalled-deal rule."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env, login="dash_crm", groups="base.group_user,sales_team.group_sale_salesman")
        cls.other = new_test_user(
            cls.env, login="dash_crm2", groups="base.group_user,sales_team.group_sale_salesman")
        cls.Lead = cls.env["crm.lead"]
        stages = cls.env["crm.stage"].search([], order="sequence", limit=2)
        cls.stage_a = stages[0]
        cls.stage_b = stages[1] if len(stages) > 1 else stages[0]

    def _lead(self, user, revenue, stage, name="Deal", write_date=None):
        lead = self.Lead.create({
            "name": name,
            "type": "opportunity",
            "user_id": user.id,
            "expected_revenue": revenue,
            "stage_id": stage.id,
        })
        if write_date:
            self._backdate(lead, write_date)
        return lead

    def _backdate(self, lead, write_date):
        """Force `write_date` into the past — see DashboardCase._stamp for why
        this cannot be done through the ORM, and why the flush/invalidate pair
        around it is load-bearing."""
        return self._stamp(lead, write_date=write_date)

    def _fetch(self, user):
        return self.Lead.with_user(user).dashboard_fetch_pipeline(limit=50)

    def test_pipeline_total_is_user_scoped(self):
        self._lead(self.user, 1000, self.stage_a)
        self._lead(self.user, 2500, self.stage_a)
        self._lead(self.other, 9999, self.stage_a)   # another rep's: excluded

        payload = self._fetch(self.user)
        self.assertEqual(payload["count"], 2, "only the caller's opportunities")

        stat = self.Lead.with_user(self.user).dashboard_fetch_pipeline_stat()
        self.assertIn("3", stat["value"], "1000 + 2500 = 3 500 is the caller's total")
        self.assertIn("2", stat["meta"])

    def test_grouped_by_stage_with_stage_totals(self):
        self._lead(self.user, 1000, self.stage_a, name="A1")
        self._lead(self.user, 500, self.stage_b, name="B1")

        payload = self._fetch(self.user)
        keys = {group["key"] for group in payload["groups"]}
        self.assertIn(str(self.stage_a.id), keys)
        group_a = next(g for g in payload["groups"] if g["key"] == str(self.stage_a.id))
        self.assertEqual(group_a["count"], 1)
        self.assertIn(self.stage_a.name, group_a["label"])
        self.assertEqual(group_a["rows"][0]["res_model"], "crm.lead")

    def test_won_opportunities_are_not_pipeline(self):
        lead = self._lead(self.user, 4000, self.stage_a)
        before = self._fetch(self.user)["count"]
        lead.probability = 100
        self.assertEqual(
            self._fetch(self.user)["count"], before - 1,
            "a won deal is no longer 'coming'",
        )

    def test_stalled_insight_needs_both_silence_and_no_plan(self):
        old = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=30))
        quiet = self._lead(self.user, 700, self.stage_a, name="Quiet", write_date=old)

        self.env.company.methode_dashboard_stalled_days = 7
        keys = [
            i["key"] for i in self.env["methode.dashboard.widget"]
            .with_user(self.user).dashboard_fetch_insights(limit=10)["insights"]
        ]
        self.assertIn("deals_stalled", keys, "no update for 30 days is stalled")

        # Schedule something on it: it is now waiting, not stalled (§8.2).
        quiet.activity_schedule(
            "mail.mail_activity_data_call",
            date_deadline=date.today() + timedelta(days=2),
            user_id=self.user.id,
        )
        # ⚠ Scheduling TOUCHES the record, so write_date jumps to now — which would
        # drop the deal from the domain via the silence half and let this test pass
        # without proving anything about activities. Push write_date back so the
        # ONLY thing that changed is that a next step exists.
        self._backdate(quiet, old)
        keys = [
            i["key"] for i in self.env["methode.dashboard.widget"]
            .with_user(self.user).dashboard_fetch_insights(limit=10)["insights"]
        ]
        self.assertNotIn(
            "deals_stalled", keys,
            "a deal with a booked next step must not raise the alarm",
        )

    def test_bridge_contributes_widget_and_shortcut(self):
        codes = self.env["methode.dashboard.widget.type"].search([]).mapped("code")
        self.assertIn("pipeline", codes)
        self.assertIn("stat_pipeline", codes)

        shortcuts = self.env["methode.dashboard.widget"].dashboard_fetch_shortcuts()
        self.assertIn("new_opportunity", [s["key"] for s in shortcuts["shortcuts"]])
