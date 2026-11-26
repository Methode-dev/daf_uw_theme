/**
 * Every one2many / many2many shown as a LIST in a form gets an icon link that
 * opens that model's list view in a new browser tab (owner call).  Global,
 * through one patch: no per-view wiring.  Markup in x2many_open_list.xml,
 * styles in x2many_open_list.scss.
 *
 * The link targets /daf_uw_theme/list/<model> (controllers/x2many_list.py),
 * which redirects to the menu action of that model, so the tab lands on the
 * same list as the menus.  A real <a target="_blank">, not a click handler:
 * no popup blocker, middle-click works, and nothing is fetched while the form
 * loads.  Kanban-mode x2manys (mobile) are left alone: "list view" there
 * would not match what the user is looking at.
 *
 * Only drawn when the user may open that list: session_info carries the
 * models they can (`m_list_link_models`, ir_http.py; `true` for an
 * administrator), so a broker never meets a link that ends on an error.
 */
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

patch(X2ManyField.prototype, {
    get mOpenListUrl() {
        if (this.props.viewMode !== "list") {
            return null;
        }
        const relation = this.props.record.fields[this.props.name].relation;
        const allowed = session.m_list_link_models;
        if (!relation || !(allowed === true || allowed?.includes(relation))) {
            return null;
        }
        return `/daf_uw_theme/list/${encodeURIComponent(relation)}`;
    },

    get mOpenListTitle() {
        return _t("Open the list in a new tab");
    },
});
