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
        return result
