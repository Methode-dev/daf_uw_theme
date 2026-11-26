from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request


class X2ManyListLink(http.Controller):
    """Target of the "open the list in a new tab" link that
    static/src/x2many/x2many_open_list.js adds to every x2many list in a form.

    A plain link (``<a target="_blank">``) rather than a click handler that
    looks the action up first: a ``window.open`` after an RPC can be eaten by
    popup blockers, a link cannot, and a link also does middle-click and
    "open in new window".  So the lookup happens here, at click time.

    Lands on the list a user would reach from the menus: the window action of
    a menu they can see, then a window action they may open.  Administrators
    fall back to the model's default list.  Anything else is a 404: the link
    is only drawn for the models ``ir.http._m_list_link_models`` returns, so
    a user only gets here by typing the URL.  The new tab shows the model's
    whole list: an Odoo URL carries no domain.
    """

    @http.route("/daf_uw_theme/list/<string:model>", type="http", auth="user")
    def open_list(self, model):
        target = request.env["ir.http"]._m_list_link_target(model)
        if not target:
            raise NotFound()
        return request.redirect(target, local=True)
