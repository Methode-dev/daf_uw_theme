from odoo import api, fields, models, _

# Urgency bands, used to merge rows from unrelated sources into one ordered list.
# Lower sorts first. They are coarse on purpose: the widget answers "what needs me
# now", and a false precision like "this invoice outranks that activity by 3
# points" would be arithmetic pretending to be judgement.
URGENCY_OVERDUE = 0
URGENCY_TODAY = 10
URGENCY_AT_RISK = 20


class MethodeDashboardFocus(models.AbstractModel):
    """"Today's Focus" — the one widget that reads across apps (§2.1).

    Every other widget answers a question about ONE model.  This one answers
    "what needs me now", which is not a property of any single model, so it is a
    collector: each installed bridge contributes its own urgent rows and they are
    merged into one list ordered by urgency band, then by date.

    ⚠ THIS IS NOT THE INSIGHT BANNERS, AND THE DIFFERENCE IS DELIBERATE.  Both
    surface "urgent", which is why the two could easily have collapsed into one
    thing.  They stayed separate because they answer differently: the banners
    INTERRUPT (a handful of dismissible strips, one action each), while this is a
    LIST YOU SCAN and work through, row by row, with the record one click away.
    Sharing the urgency vocabulary while keeping the presentations apart is the
    compromise; duplicating the queries would not have been.

    Contribution pattern is the same as the insights: inherit, super(), append.
    """

    _name = 'methode.dashboard.focus'
    _description = 'Dashboard Focus Collector'

    @api.model
    def _collect_focus_rows(self):
        """Urgent rows from every installed source, unordered.

        Each row is the normalized row shape plus `urgency` (band) and `sort_date`
        (a date string), both used only for merging and stripped before display.
        """
        rows = []
        today = fields.Date.context_today(self)

        activities = self.env['mail.activity'].search([
            ('user_id', '=', self.env.uid),
            ('active', '=', True),
            ('date_deadline', '<=', today),
        ], order='date_deadline asc, id asc', limit=10)

        for activity in activities:
            overdue = activity.date_deadline < today
            rows.append({
                'id': 'activity-%s' % activity.id,
                'icon': activity.icon or 'fa-clock-o',
                'title': activity.summary or activity.res_name or _("Activity"),
                # ⚠ `or ''`, not a bare field read: an unset Char in Odoo is
                # False, and False reaching the client fails OWL's String prop
                # validation and takes the whole widget down with it.
                'subtitle': (activity.res_name or '') if activity.summary else '',
                'res_model': activity.res_model or False,
                'res_id': activity.res_id or False,
                'pill': (
                    {'tone': 'overdue', 'text': _("Overdue")} if overdue
                    else {'tone': 'today', 'text': _("Today")}
                ),
                'urgency': URGENCY_OVERDUE if overdue else URGENCY_TODAY,
                'sort_date': fields.Date.to_string(activity.date_deadline),
            })

        return rows


class MethodeDashboardRecent(models.AbstractModel):
    """"Continue Working" — what this user touched last (§8.1).

    ⚠ THIS RESOLVES §8.1, WHICH HAD NO OBVIOUS SOURCE.  Odoo keeps no
    per-user recently-viewed log, so the three options were: read `write_date`
    across a few models, mine mail.message authorship, or cut the widget.  This
    takes the first, and the trade is worth stating plainly: it shows what you last
    CHANGED, not what you last LOOKED AT.  Opening a record and reading it leaves
    no trace here.  That is a weaker promise than the widget's title implies, which
    is why the empty state says "records you edited" rather than "recently viewed".

    Which models are scanned is a contribution point, so a bridge adds its own
    rather than this module knowing about apps it does not depend on.
    """

    _name = 'methode.dashboard.recent'
    _description = 'Dashboard Recent Records Collector'

    @api.model
    def _collect_recent_models(self):
        """Models worth offering as "continue working", most useful first.

        Core knows only about contacts — everything business-shaped arrives from a
        bridge, which is what keeps this module free of app dependencies.
        """
        return ['res.partner']

    @api.model
    def _collect_recent_rows(self, limit=5):
        rows = []
        insight = self.env['methode.dashboard.insight']

        for model_name in self._collect_recent_models():
            if not insight._dashboard_can_read(model_name):
                continue
            Model = self.env[model_name]
            if 'write_uid' not in Model._fields:
                continue

            # Per-model limit, not a global one: five contacts must not crowd out
            # the single invoice that was actually the last thing touched.
            records = Model.search(
                [('write_uid', '=', self.env.uid)],
                order='write_date desc', limit=limit)
            model_label = self.env['ir.model']._get(model_name).name or model_name

            for record in records:
                rows.append({
                    'id': '%s-%s' % (model_name.replace('.', '_'), record.id),
                    'icon': 'fa-history',
                    'title': record.display_name or model_label,
                    'subtitle': model_label,
                    'res_model': model_name,
                    'res_id': record.id,
                    'sort_date': fields.Datetime.to_string(record.write_date),
                })

        rows.sort(key=lambda row: row['sort_date'] or '', reverse=True)
        return rows[:limit]
