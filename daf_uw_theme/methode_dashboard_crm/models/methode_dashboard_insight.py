from datetime import timedelta

from odoo import api, fields, models, _


class MethodeDashboardInsight(models.AbstractModel):
    """CRM's contribution: deals that have gone quiet (§2.4, §3.5)."""

    _inherit = 'methode.dashboard.insight'

    @api.model
    def _collect_insights(self):
        insights = super()._collect_insights()

        if not self._dashboard_can_read('crm.lead'):
            return insights

        days = self.env.company.methode_dashboard_stalled_days or 7
        cutoff = fields.Datetime.now() - timedelta(days=days)

        Lead = self.env['crm.lead']
        # ⚠ THIS RESOLVES §8.2, WHICH WAS FLAGGED AS "NEEDS DESIGN".
        #
        # "Gone quiet" is two conditions, not one: nothing has been WRITTEN to the
        # deal for a while AND nothing is SCHEDULED on it.  A deal touched last
        # month with a call booked for tomorrow is not stalled — it is waiting —
        # and alarming about it would train the user to ignore the banner.
        #
        # ⚠ THE ABSENCE HALF IS NOT A DOMAIN LEAF.  An earlier version wrote
        # `('activity_ids', '=', False)` and it silently matched NOTHING, so the
        # banner never fired — exactly the trap §8.2 warned about ("absence of a
        # related record usually needs a subquery"). It is done in two explicit
        # steps instead: take the quiet deals, then subtract the ones that have an
        # activity. Bounded by the quiet set, so it stays cheap, and it is
        # verifiable — which the one-liner was not.
        quiet = Lead.search(
            Lead._dashboard_pipeline_domain()
            + [('write_date', '<', fields.Datetime.to_string(cutoff))]
        )
        stalled = quiet
        if quiet:
            scheduled_ids = set(self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', 'in', quiet.ids),
            ]).mapped('res_id'))
            stalled = quiet.filtered(lambda lead: lead.id not in scheduled_ids)

        count = len(stalled)
        # The banner's action must show exactly what the banner counted.
        domain = [('id', 'in', stalled.ids)]
        if count:
            insights.append({
                'key': 'deals_stalled',
                'icon': 'fa-clock-o',
                'tone': 'warning',
                'message': (
                    _("1 deal has had no update for %(days)s days", days=days)
                    if count == 1 else
                    _("%(count)s deals have had no update for %(days)s days",
                      count=count, days=days)
                ),
                'action_label': _("Review pipeline"),
                'action': Lead._dashboard_pipeline_action(domain, _("Stalled Deals")),
            })

        return insights


class MethodeDashboardRecent(models.AbstractModel):
    """Opportunities are the thing a salesperson resumes most."""

    _inherit = 'methode.dashboard.recent'

    @api.model
    def _collect_recent_models(self):
        return super()._collect_recent_models() + ['crm.lead']


class MethodeDashboardShortcut(models.AbstractModel):
    """"New Opportunity" in the quick-action row, present only while crm is."""

    _inherit = 'methode.dashboard.shortcut'

    @api.model
    def _collect_shortcuts(self):
        shortcuts = super()._collect_shortcuts()
        if not self._dashboard_can_read('crm.lead'):
            return shortcuts
        shortcuts.append({
            'key': 'new_opportunity',
            'label': _("New Opportunity"),
            'icon': 'fa-bullseye',
            'action': {
                'type': 'ir.actions.act_window',
                'name': _("New Opportunity"),
                'res_model': 'crm.lead',
                'views': [[False, 'form']],
                'target': 'current',
                'context': {'default_type': 'opportunity'},
            },
        })
        return shortcuts
