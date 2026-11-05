import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class MethodeDashboardInsight(models.AbstractModel):
    """The insight banners — "what needs me before it becomes a problem?" (§2.4).

    Not a widget: these are the screen raising its hand, so they are chrome above
    the grid, dismissible, each with one action.

    ⚠ THE EXTENSION POINT IS `_collect_insights`, AND THE PATTERN MATTERS.  A
    bridge module contributes a signal by inheriting this model and appending to
    super()'s list:

        class MethodeDashboardInsight(models.AbstractModel):
            _inherit = 'methode.dashboard.insight'

            @api.model
            def _collect_insights(self):
                insights = super()._collect_insights()
                ...
                return insights

    That is what replaces Aura's `_installed_modules()` scan: a signal exists
    exactly when the module contributing it is installed, and uninstalling takes
    the override with it.  Nothing here ever asks "is account installed?".

    Abstract because there is nothing to store — the banners are computed per
    request from live data plus the per-user dismissal map.
    """

    _name = 'methode.dashboard.insight'
    _description = 'Dashboard Insights'

    # -------------------------------------------------------------------------
    # Internal API
    #
    # ⚠ The PUBLIC, RPC-reachable entry point is
    # methode.dashboard.widget.dashboard_fetch_insights, which delegates here.
    # Deliberate: this model is abstract, and access rights are declared against
    # concrete models — routing the call through the placement model keeps the
    # dashboard's RPC surface on a model with real ir.model.access rows, while the
    # contribution point stays here where it belongs.
    # -------------------------------------------------------------------------
    @api.model
    def _visible_insights(self, limit=3):
        """Visible banners for this user, capped, plus how many were held back.

        Dismissals are per user and expire at midnight (see
        methode.dashboard.preferences._dismissed_today), so a banner waved away
        today returns tomorrow if the underlying problem is still there.
        """
        dismissed = self.env['methode.dashboard.preferences']._dismissed_today()
        try:
            collected = self._collect_insights()
        except Exception:
            # ⚠ Last-resort net, and it should never fire: contributors are
            # expected to check _dashboard_can_read first.  It exists because the
            # contributions chain through super(), so ONE raising module takes
            # every banner with it — and a dashboard that 500s because a bridge
            # mis-declared an access check is worse than one missing a banner.
            _logger.exception("Dashboard insight collection failed")
            return {'insights': [], 'more': 0}

        visible = [
            insight for insight in collected
            if insight.get('key') not in dismissed
        ]
        return {
            'insights': visible[:limit],
            'more': max(len(visible) - limit, 0),
        }

    @api.model
    def _dashboard_can_read(self, model_name):
        """Whether this user may read `model_name` at all.

        ⚠ EVERY BRIDGE CONTRIBUTION MUST CALL THIS FIRST.  The banners are
        collected for whoever is looking at the dashboard, and an internal user
        with no accounting rights is normal — a warehouse operator, an HR officer.
        Without this guard their dashboard raised AccessError on account.move and
        lost the whole insight zone, including the banners they were entitled to.

        This is also why the guard belongs here rather than in each bridge's own
        idiom: one helper, one behaviour, and a bridge that forgets it is caught by
        the net in _visible_insights.
        """
        model = self.env.get(model_name)
        if model is None:
            return False
        try:
            return model.has_access('read')
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Contribution point
    # -------------------------------------------------------------------------
    @api.model
    def _collect_insights(self):
        """Every signal that currently applies, most urgent first.

        Core contributes the one signal that needs no app beyond mail: overdue
        activities.  Bridges append theirs (invoices 30d+ overdue, deals stalled
        7d+, …) by overriding this method.
        """
        insights = []

        today = fields.Date.context_today(self)
        overdue = self.env['mail.activity'].search_count([
            ('user_id', '=', self.env.uid),
            ('active', '=', True),
            ('date_deadline', '<', today),
        ])
        if overdue:
            insights.append({
                'key': 'activities_overdue',
                'icon': 'fa-clock-o',
                'tone': 'warning',
                'message': (
                    _("1 activity is overdue") if overdue == 1
                    else _("%s activities are overdue", overdue)
                ),
                'action_label': _("Review activities"),
                'action': 'mail.mail_activity_action_my',
            })

        return insights


class MethodeDashboardShortcut(models.AbstractModel):
    """The quick-action row: shortcuts to the things a user does most.

    Same contribution pattern as the insights above — a bridge appends to
    `_collect_shortcuts`, so a shortcut exists exactly when its app does.

    Deliberately the last thing built (§5, Iteration 5): it is the easiest zone on
    the screen and the least convincing, so it earns its place only once the
    screen already knows something.
    """

    _name = 'methode.dashboard.shortcut'
    _description = 'Dashboard Shortcuts'

    # Reached through methode.dashboard.widget.dashboard_fetch_shortcuts — see the
    # note on the insight model above for why the RPC entry point lives there.
    @api.model
    def _dashboard_can_read(self, model_name):
        """Delegates to the canonical guard; see the insight model.

        A shortcut needs it for a different reason than an insight does: not to
        avoid raising, but to avoid offering a button that lands the user on an
        access error.
        """
        return self.env['methode.dashboard.insight']._dashboard_can_read(model_name)

    @api.model
    def _dashboard_app_menu_id(self, xmlid):
        """The app a shortcut belongs to, for the navbar to switch to.

        ⚠ WITHOUT THIS THE TOP BAR LIES ABOUT WHERE THE USER IS.

        A shortcut's action is an anonymous act_window dict -- no id, no xmlid,
        no menu -- and action_service.doAction() never touches the menu
        service. setCurrentMenu() has exactly two callers in core
        (menu_service.selectMenu, from a real click on an app tile, and
        webclient.loadRouterState, on boot), so opening a quotation from this
        dashboard leaves currentAppId on whatever the webclient resolved at
        load: the Homepage menu.

        The visible damage is worse than a wrong title. NavBar.currentAppSections
        is the children of currentApp, this menu has none, and core's
        SectionsMenu is rendered under t-if="currentAppSections.length" -- so
        the Sales menus are not hidden, they are never mounted. Reported as
        "the module title says Accueil and the Sales menus have disappeared".

        raise_if_not_found: these bridges ship to templates that install
        different app sets, and a shortcut is still worth offering when the
        menu it would select is absent -- QuickActions.run() simply does not
        call setCurrentMenu, and menu_service ignores an unknown id anyway.
        """
        menu = self.env.ref(xmlid, raise_if_not_found=False)
        return menu.id if menu else False

    @api.model
    def _collect_shortcuts(self):
        """Always-available shortcuts.  Bridges append app-specific ones."""
        return [
            {
                'key': 'new_contact',
                'label': _("New Contact"),
                'icon': 'fa-user-plus',
                'menu_id': self._dashboard_app_menu_id('contacts.menu_contacts'),
                'action': {
                    'type': 'ir.actions.act_window',
                    'name': _("New Contact"),
                    'res_model': 'res.partner',
                    'views': [[False, 'form']],
                    'target': 'current',
                },
            },
            {
                'key': 'schedule_activity',
                'label': _("Schedule Activity"),
                'icon': 'fa-calendar-plus-o',
                'action': {
                    'type': 'ir.actions.act_window',
                    'name': _("Plan an activity"),
                    'res_model': 'mail.activity',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'context': {'default_user_id': self.env.uid},
                },
            },
        ]
