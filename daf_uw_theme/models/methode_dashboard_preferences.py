import json

from odoo import api, fields, models

# What a client is allowed to write through dashboard_save_preferences.  A
# whitelist rather than a blanket write: the method is public (it has to be, to be
# reachable over RPC), so it must not become a way to set arbitrary fields.
WRITABLE_FIELDS = {
    'show_stats_row',
    'show_insights',
    'show_shortcuts',
    'layout_density',
    'row_limit',
}


class MethodeDashboardPreferences(models.Model):
    """Per-user dashboard preferences — the SECOND persistence model (§13.3).

    Distinct from methode.dashboard.widget, and deliberately so: that model holds
    WHERE things are (placements, spans, order), this one holds HOW the screen
    behaves (which chrome zones show, how dense, how many rows, which banners
    have been waved away).  §9's rule — a thing you can only show or hide is a
    section, not a widget — is why the stats row and the shortcut bar live here as
    booleans instead of as catalogue rows with a col_span.

    ⚠ What is NOT here: Aura's `dashboard_theme` / `theme_mode` /
    `effective_theme_*`.  THEME_PLAN §13.3 recommended dropping that second,
    competing theme layer, and it is dropped — the dashboard follows the site
    brand, full stop.
    """

    _name = 'methode.dashboard.preferences'
    _description = 'Dashboard Preferences'

    user_id = fields.Many2one(
        'res.users', required=True, index=True, ondelete='cascade',
        default=lambda self: self.env.user,
        help="Owner of these preferences.  One row per user, never shared.")

    # --- Chrome zones (§9: toggles, not positions) ---------------------------
    show_stats_row = fields.Boolean(string="Show Stats Row", default=True)
    show_insights = fields.Boolean(string="Show Insight Banners", default=True)
    show_shortcuts = fields.Boolean(string="Show Shortcuts", default=True)

    layout_density = fields.Selection(
        [('comfortable', 'Comfortable'), ('compact', 'Compact')],
        default='comfortable', required=True)

    row_limit = fields.Integer(
        string="Rows per Widget", default=5,
        help="How many rows a list widget shows before it offers '+ N others'.")

    # Dismissed insight banners, as {insight_key: 'YYYY-MM-DD'}.  Text rather than
    # a Json field so the shape can change without a migration; the date is what
    # makes dismissal a SNOOZE — a banner waved away today comes back tomorrow,
    # because "you have 4 invoices 30 days overdue" does not stop being true just
    # because it was inconvenient once.
    dismissed_json = fields.Text(string="Dismissed Insights")

    _user_uniq = models.Constraint(
        'unique (user_id)',
        "A user can only have one set of dashboard preferences.",
    )
    _row_limit_range = models.Constraint(
        'CHECK (row_limit BETWEEN 1 AND 20)',
        "Rows per widget must be between 1 and 20.",
    )

    # -------------------------------------------------------------------------
    # Access
    # -------------------------------------------------------------------------
    @api.model
    def _get_for_user(self):
        """This user's preferences row, created on first use.

        Same write-during-read caveat as _ensure_default_layout: it runs from
        session_info, which is served on a read/write cursor.  Idempotent bar a
        lost race, which the unique constraint then catches.
        """
        preferences = self.search([('user_id', '=', self.env.uid)], limit=1)
        if not preferences:
            preferences = self.create({'user_id': self.env.uid})
        return preferences

    @api.model
    def _preferences_payload(self):
        """The shape the client reads out of session_info."""
        preferences = self._get_for_user()
        return {
            'show_stats_row': preferences.show_stats_row,
            'show_insights': preferences.show_insights,
            'show_shortcuts': preferences.show_shortcuts,
            'layout_density': preferences.layout_density,
            'row_limit': preferences.row_limit,
        }

    def _dismissed(self):
        """Parsed dismissal map, tolerant of anything that is not valid JSON."""
        self.ensure_one()
        if not self.dismissed_json:
            return {}
        try:
            parsed = json.loads(self.dismissed_json)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @api.model
    def _dismissed_today(self):
        """Insight keys this user has waved away *today* (§ Iteration 3)."""
        preferences = self._get_for_user()
        today = fields.Date.to_string(fields.Date.context_today(preferences))
        return {
            key for key, dismissed_on in preferences._dismissed().items()
            if dismissed_on == today
        }

    # -------------------------------------------------------------------------
    # Public API — reachable over RPC, so PUBLIC names and a whitelist
    # -------------------------------------------------------------------------
    @api.model
    def dashboard_save_preferences(self, values):
        """Write the client's preference changes, ignoring anything not allowed."""
        if not isinstance(values, dict):
            return self._preferences_payload()
        allowed = {key: values[key] for key in values if key in WRITABLE_FIELDS}
        if allowed:
            self._get_for_user().write(allowed)
        return self._preferences_payload()

    @api.model
    def dashboard_dismiss_insight(self, key):
        """Snooze one insight banner for the rest of today."""
        if not key or not isinstance(key, str):
            return False
        preferences = self._get_for_user()
        dismissed = preferences._dismissed()
        dismissed[key] = fields.Date.to_string(fields.Date.context_today(preferences))
        preferences.dismissed_json = json.dumps(dismissed)
        return True
