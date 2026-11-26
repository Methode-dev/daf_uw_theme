from urllib.parse import quote

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Ship the user's dashboard layout with the session.

        See the long note on methode.dashboard.widget._layout_payload for why the
        LAYOUT travels here while the CONTENT does not: it is what lets the
        loading skeleton draw the user's real grid instead of a placeholder
        (§13.4), which is the one thing Aura's skeleton never managed.

        Internal users only.  Portal and public users have no dashboard, and
        _ensure_default_layout would otherwise create rows for them on any
        page load.

        The models whose x2many lists get the "open the list in a new tab"
        link ride here too (``m_list_link_models``), for the same reason: the
        form draws the link without an RPC (see x2many_open_list.js).
        """
        result = super().session_info()
        if result.get('uid') and self.env.user._is_internal():
            payload = self.env['methode.dashboard.widget']._layout_payload()
            # Preferences ride with the layout for the same reason: the client has
            # to know which chrome zones to draw BEFORE it draws the skeleton, or
            # the stats row appears a moment late and the page jumps (§13.4).
            payload['preferences'] = \
                self.env['methode.dashboard.preferences']._preferences_payload()
            result['methode_dashboard'] = payload
            result['m_list_link_models'] = self._m_list_link_models()
        return result

    # ------------------------------------------------------------------
    # "Open the list in a new tab" (controllers/x2many_list.py)
    # ------------------------------------------------------------------
    def _m_list_actions(self):
        """The window actions with a list view the current user may open, by
        model, the one of their first visible menu first: a model they
        cannot read is left out, and so is an action restricted to groups
        they are not in.

        Users other than administrators only get the actions behind a menu
        they can see: the link lands on a list they could reach from their
        menus, never on a technical list (e.g. base's attachments) that an
        unrestricted action would open.

        ⚠ ``ir.ui.menu.search`` does NOT filter on visibility in Odoo 19 (a
        broker's search returns staff menus too), and ``_visible_menu_ids``
        checks a menu's own groups only: a menu counts when it and all its
        ancestors are visible.

        sudo: ``ir.actions.act_window`` and the menus' action reference are
        readable by administrators only; this reads them to filter by the
        user's own groups, menus and access rights, and returns ids only.
        """
        user = self.env.user
        actions = self.env['ir.actions.act_window'].sudo().search(
            [('view_mode', 'ilike', 'list'), ('res_model', '!=', False)],
            order='id',
        )
        groups = user.all_group_ids
        readable = {}
        allowed = {}
        for action in actions:
            model = action.res_model
            if model not in readable:
                readable[model] = (
                    model in self.env and self.env[model].has_access('read')
                )
            if not readable[model]:
                continue
            if action.group_ids and not (action.group_ids & groups):
                continue
            allowed.setdefault(model, []).append(action.id)
        Menu = self.env['ir.ui.menu']
        visible = Menu._visible_menu_ids()
        menus = Menu.sudo().search([
            ('id', 'in', list(visible)),
            ('action', 'in', [
                f'ir.actions.act_window,{action_id}'
                for ids in allowed.values() for action_id in ids
            ]),
        ]).filtered(
            # ⚠ _visible_menu_ids checks each menu's own groups, not its
            # parents': base's Technical > Attachments has none and would
            # pass for a broker. Reachable = every ancestor visible too.
            lambda menu: all(
                int(menu_id) in visible
                for menu_id in menu.parent_path.strip('/').split('/')
            )
        )
        by_menu = {}
        for menu in menus:
            action = menu.action
            ids = by_menu.setdefault(action.res_model, [])
            if action.id not in ids:
                ids.append(action.id)
        if not user.has_group('base.group_system'):
            return by_menu
        return {
            model: by_menu.get(model, [])
            + [i for i in ids if i not in by_menu.get(model, [])]
            for model, ids in allowed.items()
        }

    def _m_list_link_models(self):
        """The models whose x2many lists show the link: every model for an
        administrator (the default list is their fallback), else the models
        of their visible menus' list actions."""
        if self.env.user.has_group('base.group_system'):
            return True
        return sorted(self._m_list_actions())

    def _m_list_link_target(self, model):
        """Where the link of ``model`` leads the current user, or None when
        they may not open its list."""
        if model not in self.env:
            return None
        actions = self._m_list_actions().get(model)
        if actions:
            return f'/odoo/action-{actions[0]}'
        if self.env.user.has_group('base.group_system'):
            # Models without a dot (e.g. "website") need the m- prefix to be
            # read as a model, not an action path (web/.../core/browser/router.js).
            path = model if '.' in model else f'm-{model}'
            return f'/odoo/{quote(path)}?view_type=list'
        return None
