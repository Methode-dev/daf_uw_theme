from odoo import api, models, _
from odoo.tools import formatLang


class CrmLead(models.Model):
    """Dashboard fetchers for the pipeline questions (§2.3, §3.4).

    ⚠ USER-SCOPED, and that is not an oversight — it is the opposite choice from
    the accounting bridge.  "How much am I owed" is a fact about the business, so
    the invoice fetchers read the whole company; "what is MY pipeline worth" is a
    fact about a salesperson, and answering it company-wide would tell a rep
    nothing they can act on.  §8.4 lists a manager's team view as an open
    question; when it is answered it belongs here as an option, not as a change to
    the default.
    """

    _inherit = 'crm.lead'

    @api.model
    def _dashboard_pipeline_domain(self):
        return [
            ('type', '=', 'opportunity'),
            ('user_id', '=', self.env.uid),
            ('active', '=', True),
            # An opportunity at 100% is won and no longer "coming".
            ('probability', '<', 100),
        ]

    @api.model
    def _dashboard_pipeline_action(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'crm.lead',
            'views': [[False, 'kanban'], [False, 'list'], [False, 'form']],
            'domain': domain,
            'context': {'default_type': 'opportunity'},
            'target': 'current',
        }

    @api.model
    def dashboard_fetch_pipeline(self, limit=5, **kwargs):
        """Open opportunities grouped by stage — what is coming, and where it sits.

        Grouped rather than flat because §2.3 asks two questions at once: what is
        the pipeline worth, and where is it stuck.  A flat list of five deals
        answers neither.
        """
        domain = self._dashboard_pipeline_domain()
        currency = self.env.company.currency_id

        # _read_group gives stage totals in one query; the rows are then fetched
        # per stage, capped globally, so a 200-deal pipeline never loads 200 rows.
        stage_groups = self._read_group(
            domain, ['stage_id'], ['expected_revenue:sum', '__count'],
            order='stage_id asc')

        groups = []
        total = 0
        slots_left = max(limit, 0)
        for stage, revenue, count in stage_groups:
            total += count
            rows = []
            if slots_left and stage:
                leads = self.search(
                    domain + [('stage_id', '=', stage.id)],
                    order='expected_revenue desc, id desc', limit=slots_left)
                for lead in leads:
                    rows.append({
                        'id': lead.id,
                        'icon': 'fa-bullseye',
                        'title': lead.name or '',
                        'subtitle': lead.partner_id.display_name or '',
                        'meta': formatLang(
                            self.env, lead.expected_revenue or 0.0,
                            currency_obj=currency),
                        'res_model': 'crm.lead',
                        'res_id': lead.id,
                    })
                slots_left -= len(rows)

            groups.append({
                'key': str(stage.id) if stage else 'none',
                # The stage total is the useful label here, not just its name.
                'label': '%s · %s' % (
                    stage.name if stage else _("Unassigned"),
                    formatLang(self.env, revenue or 0.0, currency_obj=currency),
                ),
                'count': count,
                'rows': rows,
            })

        return {
            'count': total,
            'groups': groups,
            'action': self._dashboard_pipeline_action(domain, _("My Pipeline")),
            'empty': {
                'title': _("No open opportunities"),
                'hint': _("Nothing in your pipeline yet."),
            },
        }

    @api.model
    def dashboard_fetch_pipeline_stat(self, **kwargs):
        """What the pipeline is worth, as one number."""
        domain = self._dashboard_pipeline_domain()
        [(revenue, count)] = self._read_group(
            domain, [], ['expected_revenue:sum', '__count'])

        return {
            'value': formatLang(
                self.env, revenue or 0.0,
                currency_obj=self.env.company.currency_id),
            'label': _("Pipeline"),
            'meta': (
                _("1 open opportunity") if count == 1
                else _("%s open opportunities", count)
            ),
            'tone': 'neutral',
            'action': self._dashboard_pipeline_action(domain, _("My Pipeline")),
        }
