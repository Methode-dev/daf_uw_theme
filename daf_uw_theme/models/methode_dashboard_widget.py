from odoo import api, fields, models, _


class MethodeDashboardWidget(models.Model):
    """One widget on one user's dashboard: which type, where, how wide.

    This is the layout only.  Widget CONTENT is fetched separately (P8b), one
    method per widget type on its own model — §13.7's "one fetcher per widget
    type, on the model", so it is inheritable and testable through the ORM rather
    than over HTTP.

    ⚠ ondelete='cascade' on widget_type_id is a behaviour decision, not a default.
    §13.3 lists "graceful degradation" — Aura rendered a "no longer available"
    card when a widget's module had gone.  It had to: its layout rows stored a
    free-text widget id that could outlive the thing it named.  Here the row is a
    foreign key, so uninstalling an app takes its widget type AND every layout row
    pointing at it, and there is no dangling state left to degrade.  The
    unavailable card still earns its keep for the other half of §13.3 — a fetcher
    that errors at runtime — which P8b wires up.
    """

    _name = 'methode.dashboard.widget'
    _description = 'Dashboard Widget Placement'
    _order = 'position, id'

    user_id = fields.Many2one(
        'res.users', required=True, index=True, ondelete='cascade',
        default=lambda self: self.env.user,
        help="Owner of this placement.  Layouts are per user, never shared.")
    widget_type_id = fields.Many2one(
        'methode.dashboard.widget.type', required=True, index=True,
        ondelete='cascade')

    position = fields.Integer(default=10, help="Order within the grid.")
    col_span = fields.Integer(default=1, help="Columns occupied, 1 to 3.")

    # Free-form per-placement settings (a filter chip, a row limit).  Text rather
    # than a Json field so a widget type can define its own shape without this
    # model needing to know any of them.
    config_json = fields.Text(string="Configuration")

    _col_span_range = models.Constraint(
        'CHECK (col_span BETWEEN 1 AND 3)',
        "A dashboard widget must span between 1 and 3 columns.",
    )

    # ⚠ No unique(user_id, widget_type_id).  It is tempting and it would be
    # wrong: P8d's custom widgets are placements of one "custom" type configured
    # differently through config_json, so two rows of the same type on one
    # dashboard is a legitimate state.  The picker prevents accidental duplicates
    # of the BUILT-IN types instead, where the rule actually belongs.

    # -------------------------------------------------------------------------
    # Layout payload
    #
    # ⚠ This rides in session_info, NOT in the content RPC, and that is what makes
    # §13.4's skeleton improvement possible at all.  Aura shipped layout and
    # content together in one slow /data call, so at first paint it knew nothing
    # about the user's grid and drew a hardcoded 5/4/3/3/3 placeholder — which
    # then jumped when the real cards arrived.  Sending layout with the session
    # means the skeleton can draw the true number of cards, at the true spans, in
    # the true order, before a single widget has been fetched.
    #
    # session_info is rebuilt on every webclient load and is never cached client
    # -side, so there is no invalidation story to get wrong.
    # -------------------------------------------------------------------------
    @api.model
    def _layout_payload(self):
        """This user's grid: placements, plus the catalogue to render them from."""
        placements = self.search([('user_id', '=', self.env.uid)])
        if not placements:
            placements = self._ensure_default_layout()
        widget_type = self.env['methode.dashboard.widget.type']
        return {
            'placements': [
                {
                    'id': placement.id,
                    'code': placement.widget_type_id.code,
                    'name': placement.widget_type_id.name,
                    'icon': placement.widget_type_id.icon or 'fa-square-o',
                    'position': placement.position,
                    'col_span': placement.col_span,
                    'expected_rows': placement.widget_type_id.expected_rows,
                    'config_json': placement.config_json or '',
                    **placement.widget_type_id._dispatch_fields(),
                }
                for placement in placements
            ],
            # Stats tiles are chrome, not placements — they ride alongside.
            'stats': widget_type._stats_payload(),
            'catalogue': widget_type._catalogue_payload(),
        }

    @api.model
    def _ensure_default_layout(self):
        """Create this user's grid from the types flagged `is_default`.

        ⚠ Runs on first render, which means it WRITES during what the client
        thinks is a read.  That is safe here — session_info is served on a normal
        read/write cursor — but it is the reason this is not folded into
        _layout_payload's search: a future caller on a read-only cursor must be
        able to skip it.  Idempotent, so a concurrent second call is harmless
        beyond losing the race.
        """
        # Only grid types get placed; stats tiles are fixed chrome (§9).
        defaults = self.env['methode.dashboard.widget.type'].search(
            [('is_default', '=', True), ('zone', '=', 'grid')])
        if not defaults:
            return self.browse()
        return self.create([
            {
                'user_id': self.env.uid,
                'widget_type_id': widget_type.id,
                'position': (index + 1) * 10,
                'col_span': widget_type.default_col_span,
            }
            for index, widget_type in enumerate(defaults)
        ])

    # -------------------------------------------------------------------------
    # Chrome zones — public RPC entry points
    #
    # The insight and shortcut logic lives on its own abstract models, which is
    # where bridge modules extend it.  These two methods are just the doors: this
    # model is concrete and carries ir.model.access rows, so RPC reaches it under
    # normal access rights.  PUBLIC names, because Odoo refuses to dispatch RPC to
    # anything starting with an underscore.
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_fetch_insights(self, limit=3):
        """The insight banners for this user (§2.4)."""
        return self.env['methode.dashboard.insight']._visible_insights(limit=limit)

    @api.model
    def dashboard_fetch_shortcuts(self):
        """The quick-action row, as contributed by whatever is installed."""
        return {
            'shortcuts': self.env['methode.dashboard.shortcut']._collect_shortcuts(),
        }

    @api.model
    def dashboard_fetch_focus(self, limit=5, **kwargs):
        """"Today's Focus": urgent rows from every installed source, merged."""
        rows = self.env['methode.dashboard.focus']._collect_focus_rows()
        # Band first, then oldest within the band — an invoice 40 days late
        # outranks one 3 days late, and both outrank anything merely due today.
        rows.sort(key=lambda row: (row.get('urgency', 99), row.get('sort_date') or ''))

        return {
            'count': len(rows),
            'rows': [
                {key: value for key, value in row.items()
                 if key not in ('urgency', 'sort_date')}
                for row in rows[:limit]
            ],
            'empty': {
                'title': _("Nothing needs you"),
                'hint': _("No overdue work and nothing due today."),
            },
        }

    @api.model
    def dashboard_fetch_recent(self, limit=5, **kwargs):
        """"Continue Working": the records this user last edited (§8.1)."""
        rows = self.env['methode.dashboard.recent']._collect_recent_rows(limit=limit)
        return {
            'count': len(rows),
            'rows': [
                {key: value for key, value in row.items() if key != 'sort_date'}
                for row in rows
            ],
            'empty': {
                'title': _("Nothing recent"),
                'hint': _("Records you edit will show up here."),
            },
        }

    @api.model
    def action_reset_layout(self):
        """Discard this user's grid and rebuild it from the defaults (§13.3)."""
        self.search([('user_id', '=', self.env.uid)]).unlink()
        self._ensure_default_layout()
        return self._layout_payload()

    # -------------------------------------------------------------------------
    # Edit mode — public RPC surface
    #
    # ⚠ WHY THESE EXIST AT ALL, given the client could call create/write/unlink
    # directly (the access rights and the own-rows rule already make that safe):
    # POSITION ARITHMETIC.  Every one of these operations has to decide where a
    # widget lands relative to its neighbours, and doing that client-side means
    # the rule lives in JavaScript where it cannot be tested through the ORM —
    # which is the same mistake as putting business logic in a controller.
    #
    # Each returns the FRESH LAYOUT, because the layout normally arrives in
    # session_info and is therefore only as current as the last page load. Handing
    # it back on every mutation is what lets edit mode update without a reload.
    #
    # Ownership is enforced twice over: the record rule restricts every row to its
    # owner, and _own_placement filters on user_id explicitly rather than trusting
    # an id from the client.
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_fetch_layout(self):
        """This user's current grid — for refreshing after an edit."""
        return self._layout_payload()

    def _own_placement(self, placement_id):
        """A placement of this user's, or an empty recordset.

        Explicit `user_id` filter on purpose: the id comes from the client, and
        "the record rule would have caught it" is a worse answer than not looking
        at other people's rows in the first place.
        """
        return self.search([
            ('id', '=', int(placement_id)),
            ('user_id', '=', self.env.uid),
        ], limit=1)

    @api.model
    def dashboard_add_widget(self, widget_type_id):
        """Append a widget to the end of this user's grid."""
        widget_type = self.env['methode.dashboard.widget.type'].browse(int(widget_type_id))
        # zone='stats' types are chrome and cannot be placed (§9); the picker only
        # offers grid types, and this is the server refusing to trust that.
        if not widget_type.exists() or widget_type.zone != 'grid':
            return self._layout_payload()

        last = self.search(
            [('user_id', '=', self.env.uid)], order='position desc', limit=1)
        self.create({
            'user_id': self.env.uid,
            'widget_type_id': widget_type.id,
            'position': (last.position + 10) if last else 10,
            'col_span': widget_type.default_col_span,
        })
        return self._layout_payload()

    @api.model
    def dashboard_remove_widget(self, placement_id):
        self._own_placement(placement_id).unlink()
        return self._layout_payload()

    @api.model
    def dashboard_resize_widget(self, placement_id, col_span):
        col_span = max(1, min(int(col_span), 3))
        self._own_placement(placement_id).col_span = col_span
        return self._layout_payload()

    @api.model
    def dashboard_move_widget(self, placement_id, offset):
        """Move a widget one slot earlier or later in the grid.

        ⚠ ARROWS, NOT DRAG-AND-DROP, and that is a choice rather than a shortcut.
        A pointer-only reorder is unreachable by keyboard and unusable on a touch
        screen, and it would need either a drag library (a dependency this theme
        does not have) or a hand-rolled one (the kind of code Aura accumulated).
        Swapping with the neighbour is two lines, testable, and accessible.
        """
        placement = self._own_placement(placement_id)
        if not placement:
            return self._layout_payload()

        ordered = list(self.search([('user_id', '=', self.env.uid)]))
        index = ordered.index(placement)
        target = index + (1 if int(offset) > 0 else -1)
        if 0 <= target < len(ordered):
            ordered[index], ordered[target] = ordered[target], ordered[index]
            # Renumber the whole list rather than swapping two position values:
            # nothing stops two placements from sharing a position (the default is
            # 10 for every row created outside _ensure_default_layout), and swapping
            # equal numbers is a no-op that looks like a broken button.
            for slot, moved in enumerate(ordered, start=1):
                moved.position = slot * 10
        return self._layout_payload()

    @api.model
    def dashboard_reset_layout(self):
        """Restore defaults (§13.3), under the naming the client uses."""
        return self.action_reset_layout()
