import re

from odoo import api, fields, models, _
from odoo.tools import html2plaintext


class MailActivity(models.Model):
    """The "My Activities" dashboard fetcher lives here, on the model.

    HOMEPAGE_DASHBOARD_PLAN §4 / THEME_PLAN §13.7: business logic is an
    `@api.model` method on the relevant model, called through standard ORM RPC —
    never a bespoke controller.  This makes it inheritable (a bridge module could
    extend the row shape) and testable through the ORM, which is the whole reason
    the dashboard is being rewritten off Aura's 2,034 lines of HTTP handlers.

    Only ONE question is answered here — "what is scheduled for me, and what is
    late?" (§2.1 / §3.1).  Other widgets get their own fetcher on their own model;
    this file never grows a second unrelated method.
    """

    _inherit = "mail.activity"

    @api.model
    def dashboard_fetch_activities(self, limit=5):
        """The current user's open activities, bucketed for the dashboard.

        ⚠ PUBLIC NAME ON PURPOSE. Odoo's `get_public_method` refuses to dispatch
        any RPC to a method whose name starts with `_` ("Private methods cannot
        be called remotely"), and the dashboard calls this straight from OWL via
        the ORM (§4 — no bespoke controller). Safe to expose: `@api.model` plus a
        domain pinned to `user_id = uid` mean a caller only ever reads their own
        activities, under their own access rights. The row serialiser below stays
        private — it is only ever reached from here, never over the wire.

        Returns::

            {
                "count": <total open activities>,
                "groups": [
                    {"key": "overdue", "label": ..., "count": N, "rows": [row, ...]},
                    {"key": "today",   ...},
                    {"key": "planned", ...},
                ],
            }

        Read as the calling user, so `ir.model.access` and record rules apply; the
        domain also pins `user_id` to the caller, so a user only ever sees their
        own activities.  `state` is a non-stored computed field and cannot be used
        in a domain, so the buckets are expressed as date ranges against the
        user-timezone "today" — the same boundary the `state` field itself uses
        (see mail.activity._compute_state_from_date).
        """
        uid = self.env.uid
        today = fields.Date.context_today(self)
        base = [("user_id", "=", uid), ("active", "=", True)]

        buckets = (
            ("overdue", _("Overdue"), [("date_deadline", "<", today)]),
            ("today", _("Today"), [("date_deadline", "=", today)]),
            ("planned", _("Planned"), [("date_deadline", ">", today)]),
        )

        groups = []
        total = 0
        # `limit` is the TOTAL number of rows shown across the whole widget, not
        # a per-bucket cap. Buckets are already in urgency order (overdue → today
        # → planned), so filling from the top means an inbox full of overdue
        # items shows the five most urgent, not five of each. What overflows is
        # summed into the single "+ N others" link the client renders.
        slots_left = max(limit, 0)
        for key, label, extra in buckets:
            domain = base + extra
            # Full count for the section header and the badge, regardless of how
            # many rows this bucket actually gets to render.
            count = self.search_count(domain)
            total += count

            rows = []
            if slots_left:
                activities = self.search(
                    domain, order="date_deadline asc, id asc", limit=slots_left
                )
                rows = [
                    self._dashboard_activity_row(activity, key, today)
                    for activity in activities
                ]
                slots_left -= len(rows)

            groups.append({"key": key, "label": label, "count": count, "rows": rows})

        return {"count": total, "groups": groups}

    @api.model
    def dashboard_fetch_activities_stat(self, **kwargs):
        """The "My Activities" KPI tile: what is on me now, and how much is late.

        A stat tile answers one number and offers one door into the records behind
        it (§1 — a figure you cannot click through to is decoration).  `kwargs` is
        swallowed so the client can call every stat fetcher the same way.
        """
        today = fields.Date.context_today(self)
        base = [('user_id', '=', self.env.uid), ('active', '=', True)]
        overdue = self.search_count(base + [('date_deadline', '<', today)])
        due_today = self.search_count(base + [('date_deadline', '=', today)])

        # `tone` is how the tile earns colour: semantic, not decorative.  Red
        # appears only when something actually is late (§13.2 — a widget type has
        # no say in palette; a widget's DATA does).
        if overdue:
            meta = _("1 overdue") if overdue == 1 else _("%s overdue", overdue)
            tone = 'danger'
        elif due_today:
            meta = _("due today")
            tone = 'neutral'
        else:
            meta = _("nothing due")
            tone = 'neutral'

        return {
            'value': overdue + due_today,
            'label': _("Activities due"),
            'meta': meta,
            'tone': tone,
            'action': 'mail.mail_activity_action_my',
        }

    @api.model
    def dashboard_fetch_activity_trend(self, **kwargs):
        """The shape of this user's workload, as counts per horizon.

        ⚠ NOT A TIME SERIES, and the name is inherited rather than chosen.  Aura's
        "trend" widget hand-rolled markup with no chart library behind it
        (THEME_PLAN §13.6), and a real trend needs history this database does not
        keep — activities are deleted or archived when completed, so "how many were
        open last Tuesday" is unanswerable without a snapshot table nobody asked
        for.  What IS answerable, and useful, is the distribution across horizons:
        how much of the load is already late versus still ahead.
        """
        today = fields.Date.context_today(self)
        base = [('user_id', '=', self.env.uid), ('active', '=', True)]
        week = fields.Date.add(today, days=7)

        buckets = (
            (_("Overdue"), base + [('date_deadline', '<', today)], 'danger'),
            (_("Today"), base + [('date_deadline', '=', today)], 'accent'),
            (_("This week"), base + [
                ('date_deadline', '>', today), ('date_deadline', '<=', week),
            ], 'neutral'),
            (_("Later"), base + [('date_deadline', '>', week)], 'neutral'),
        )

        points = [
            {'label': label, 'value': self.search_count(domain), 'tone': tone}
            for label, domain, tone in buckets
        ]

        return {
            'points': points,
            'total': sum(point['value'] for point in points),
            'action': 'mail.mail_activity_action_my',
            'empty': {
                'title': _("Nothing scheduled"),
                'hint': _("You're all caught up."),
            },
        }

    @api.model
    def _dashboard_activity_row(self, activity, bucket, today):
        """Serialise one activity into the dashboard row contract (§3.1).

        The activity TYPE is carried by the icon — a call shows a phone, a to-do a
        check — so it is never repeated in the text.  The title is the human
        label: the summary the user typed, else the record the activity sits on.
        The subtitle is a one-line plain-text preview of the description.
        `res_model`/`res_id` ride along so the row opens the record (§1: every row
        is a link).
        """
        # ⚠ `summary` IS NOT RELIABLY THE USER'S OWN WORDS.  activity_schedule
        # fills it with the activity TYPE's name when the caller gives none, so a
        # plain "Call" reaches us as summary="Call" — and putting that in the title
        # renders the type as text, which is the icon's job (owner: "if it is a
        # To-Do, we should have a checkmark icon").  So a summary that merely
        # repeats the type is treated as absent and the RECORD wins the title.
        type_name = activity.activity_type_id.name or ""
        summary = activity.summary or ""
        if summary and summary.strip().casefold() == type_name.strip().casefold():
            summary = ""
        title = summary or activity.res_name or type_name or _("Activity")

        # The description is HTML; flatten it, collapse whitespace, clip to one
        # line so a long note cannot blow out the row height.
        subtitle = html2plaintext(activity.note or "").strip()
        if subtitle:
            subtitle = " ".join(subtitle.split())
            # ⚠ Strip markdown emphasis markers.  Odoo generates some activity
            # notes with markdown-style bold (calendar's "**Organisé par** X"),
            # and html2plaintext only removes HTML — so the asterisks survive and
            # render literally in the row.  Nothing here interprets markdown, so
            # the markers are noise either way.
            subtitle = re.sub(r"(\*{1,3}|_{2,3})(.+?)\1", r"\2", subtitle)
            if len(subtitle) > 120:
                subtitle = subtitle[:119].rstrip() + "…"

        # abs() so both directions read as a magnitude; the client phrases it from
        # `state` ("5 days late" vs "in 5 days").
        days = abs((activity.date_deadline - today).days)

        return {
            "id": activity.id,
            "icon": activity.icon or "fa-clock-o",
            "title": title,
            "subtitle": subtitle,
            "res_model": activity.res_model or False,
            "res_id": activity.res_id or False,
            "date_deadline": fields.Date.to_string(activity.date_deadline),
            "days": days,
            "state": bucket,
        }
