from urllib.parse import quote

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class X2ManyListLink(http.Controller):
    """Target of the "open the list in a new tab" link that
    static/src/x2many/x2many_open_list.js adds to every x2many list in a form.

    A plain link (``<a target="_blank">``) rather than a click handler that
    looks the action up first: a ``window.open`` after an RPC can be eaten by
    popup blockers, a link cannot, and a link also does middle-click and
    "open in new window".  So the lookup happens here, at click time, and the
    form itself pays nothing when it loads.

    Lands on the list a user would reach from the menus: the window action of
    a menu they can see (ir.ui.menu searches only return visible menus), then
    any window action with a list view, then the model's default list.  The
    new tab shows the model's whole list: an Odoo URL carries no domain.
    """

    @http.route("/daf_uw_theme/list/<string:model>", type="http", auth="user")
    def open_list(self, model):
        if model not in request.env:
            raise NotFound()
        Action = request.env["ir.actions.act_window"]
        actions = Action.search(
            [("res_model", "=", model), ("view_mode", "ilike", "list")], order="id"
        )
        action = Action
        if actions:
            menus = request.env["ir.ui.menu"].search(
                [
                    (
                        "action",
                        "in",
                        [f"ir.actions.act_window,{a.id}" for a in actions],
                    )
                ],
                limit=1,
            )
            action = menus.action if menus else actions[:1]
        if action:
            return request.redirect(f"/odoo/action-{action.id}", local=True)
        # Models without a dot (e.g. "website") need the m- prefix to be read
        # as a model, not an action path (web/.../core/browser/router.js).
        path = model if "." in model else f"m-{model}"
        return request.redirect(f"/odoo/{quote(path)}?view_type=list", local=True)
