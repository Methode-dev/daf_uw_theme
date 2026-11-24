/**
 * The current app's menu, listed in the app sidebar under the app itself
 * (QA: replaces the stock .o_menu_sections row of the navbar, see navbar.js).
 *
 * A "primary" entry is a menu that has children: it renders as a heading, and
 * its children are listed below it.  An entry without children is a plain link.
 * muk_web_appsbar is vendored, so this only patches AppsBar and extends its
 * template (appsbar_sections.xml); it does not edit it.
 */

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AppsBar } from "@muk_web_appsbar/webclient/appsbar/appsbar";

patch(AppsBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.menuService = useService("menu");
    },

    /** Menu tree of one app: [{ id, name, childrenTree, ... }] */
    appSections(app) {
        return this.menuService.getMenuAsTree(app.id).childrenTree || [];
    },

    onSectionClick(section) {
        this.menuService.selectMenu(section);
    },
});
