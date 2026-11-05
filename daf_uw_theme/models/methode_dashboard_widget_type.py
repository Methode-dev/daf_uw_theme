from odoo import api, fields, models


class MethodeDashboardWidgetType(models.Model):
    """The dashboard's widget catalogue, as records.

    THEME_PLAN §13.7: "The widget catalogue is data, not a Python constant."
    Aura kept it as WIDGET_CATALOG, a 22-entry dict in a controller, gated at
    runtime by scanning installed modules.  Here each widget type is a record, so
    a module contributes a widget by shipping one.

    ⚠ THERE IS DELIBERATELY NO `module_name` GATE, and adding one back would undo
    the point of the rewrite.  Aura needed it because every widget lived in one
    module whether or not its app was installed, so something had to hide them at
    runtime.  With records, presence IS the gate: an `account` widget ships from a
    bridge module that depends on `account` and auto-installs, so it exists
    exactly when the app does, and uninstalling the app removes the record with
    it.  A `module_name` string cannot do the second half — the rows would linger.

    ⚠ AND NO COLOUR FIELD.  Owner-decided in P8: Aura's catalogue carried seven
    colour tokens (brand/blue/orange/red/gray/green/purple) against a brand that
    is monochrome plus one orange accent (§13.2).  Identity is carried by the
    icon and by the material language; a widget type has no say in palette.
    """

    _name = 'methode.dashboard.widget.type'
    _description = 'Dashboard Widget Type'
    _order = 'sequence, name, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True, copy=False,
        help="Stable technical key, e.g. 'activities'.  Referenced by fetchers "
             "and by the client; unlike the name it is never translated.")
    description = fields.Char(
        translate=True,
        help="One line, shown in the add-widget picker.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    icon = fields.Char(
        help="Icon class, e.g. 'fa-bolt'.  Font Awesome 6 is available through "
             "aura_backend_theme's shim.")

    group_name = fields.Char(
        string="Group", translate=True, default="General",
        help="Heading the picker files this widget under, e.g. 'Accounting'.")

    default_col_span = fields.Integer(
        string="Default Width", default=1,
        help="Columns this widget occupies when first added, 1 to 3.")

    # §13.4's improvement depends on this.  The skeleton draws the user's real
    # layout, so it needs to know how tall each card will be BEFORE any content
    # arrives; without a per-type row count it would be back to guessing, which is
    # the thing Aura's fixed 5/4/3/3/3 placeholder got wrong.
    expected_rows = fields.Integer(
        string="Skeleton Rows", default=3,
        help="Roughly how many rows this widget renders.  Used only to size its "
             "loading skeleton, so the page does not jump when data lands.")

    is_default = fields.Boolean(
        string="In Default Layout", default=False,
        help="Included when a user's dashboard is first created, or reset.")

    # --- Dispatch: what renders this widget, and where its data comes from -----
    # The catalogue drives both rendering and fetching, so a new widget is a
    # record + one method with no new core JS.  A `grid` type is user-placed and
    # arrangeable; a `stats` type is a fixed KPI tile in the stats chrome zone,
    # never a placement (§9).
    zone = fields.Selection(
        [('grid', 'Grid'), ('stats', 'Stats row')],
        default='grid', required=True,
        help="grid = a placeable widget; stats = a fixed KPI tile in the stats row.")
    render = fields.Selection(
        [('list', 'List'), ('activities', 'Activities'),
         ('stat', 'Stat'), ('chart', 'Chart'), ('custom', 'Custom')],
        default='list', required=True,
        help="Which client component renders this widget.")
    fetch_model = fields.Char(
        help="Model exposing the fetch method the client calls over RPC, e.g. "
             "'mail.activity'.  Empty means the widget has no data yet and "
             "renders the pending frame.")
    fetch_method = fields.Char(
        help="Public @api.model method on fetch_model returning this widget's "
             "payload.  MUST be public — Odoo refuses to dispatch RPC to _names.")
    needs_config = fields.Boolean(
        default=False,
        help="Pass the placement's parsed config_json to the fetcher (custom "
             "widgets build their query from it).")

    _code_uniq = models.Constraint(
        'unique (code)',
        "The widget type code must be unique.",
    )
    _col_span_range = models.Constraint(
        'CHECK (default_col_span BETWEEN 1 AND 3)',
        "A widget's default width must be between 1 and 3 columns.",
    )
    _expected_rows_positive = models.Constraint(
        'CHECK (expected_rows >= 0)',
        "Skeleton rows cannot be negative.",
    )

    def _dispatch_fields(self):
        """The render/fetch descriptor the client needs to draw and load a type."""
        self.ensure_one()
        return {
            'render': self.render,
            'fetch_model': self.fetch_model or '',
            'fetch_method': self.fetch_method or '',
            'needs_config': self.needs_config,
        }

    @api.model
    def _catalogue_payload(self):
        """The GRID catalogue as plain dicts, for the picker and the grid.

        Read as the current user: `active` and record rules both apply, so a
        widget type an installed module removed simply is not here.  Only `grid`
        types — you place those; stats tiles are chrome, offered separately.
        """
        return [
            {
                'id': widget_type.id,
                'code': widget_type.code,
                'name': widget_type.name,
                'description': widget_type.description or '',
                'icon': widget_type.icon or 'fa-square-o',
                'group_name': widget_type.group_name or '',
                'default_col_span': widget_type.default_col_span,
                'expected_rows': widget_type.expected_rows,
                **widget_type._dispatch_fields(),
            }
            for widget_type in self.search([('zone', '=', 'grid')])
        ]

    @api.model
    def _stats_payload(self):
        """The stats-row tiles this user can actually see.

        Two gates, and they are different things: a tile EXISTS because its bridge
        module is installed, and it is SHOWN because this user may read the model
        behind it.  Installed is not permitted — a warehouse operator has no
        accounting rights, and offering them an "Outstanding" tile that can only
        render "—" is worse than not offering it.

        The grid is left alone on purpose: those are placements the user chose (or
        inherited from the defaults), and a widget that cannot load falls back to
        its pending frame rather than vanishing from a layout they arranged.
        """
        insight = self.env['methode.dashboard.insight']
        tiles = []
        for widget_type in self.search([('zone', '=', 'stats')]):
            if widget_type.fetch_model and not insight._dashboard_can_read(
                    widget_type.fetch_model):
                continue
            tiles.append({
                'id': widget_type.id,
                'code': widget_type.code,
                'name': widget_type.name,
                'icon': widget_type.icon or 'fa-square-o',
                **widget_type._dispatch_fields(),
            })
        return tiles
