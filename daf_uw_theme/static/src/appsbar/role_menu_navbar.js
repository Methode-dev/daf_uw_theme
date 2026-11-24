/**
 * The top navbar lists the sub-menus of the sidebar entry that is open, not
 * those of the app it belongs to (QA): "Portefeuille" in the sidebar gives
 * "Assurés | Véhicules | Devis | …" on top. See role_menu_layout.js.
 *
 * Phones keep the stock list (the burger menu reads the same getter), and so
 * does anybody with no layout.
 */

import { useEffect, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { activeRoleItem, itemKey, roleMenuState } from "./role_menu_layout";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.roleState = useState(roleMenuState);
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => this.render());
        // The stock navbar measures its row only when the app changes (to fold
        // what does not fit into "More"): the sections changed under the same
        // app, so say it again.
        useEffect(
            () => this.env.bus.trigger("MENUS:APP-CHANGED"),
            () => [this.roleActiveKey]
        );
    },

    get roleActiveItem() {
        return this.ui.isSmall ? null : activeRoleItem(this.menuService, this.actionService);
    },

    get roleActiveKey() {
        const item = this.roleActiveItem;
        return item ? itemKey(item) : null;
    },

    get currentAppSections() {
        const item = this.roleActiveItem;
        if (item?.menu) {
            return this.menuService.getMenuAsTree(item.menu.id).childrenTree || [];
        }
        return super.currentAppSections;
    },

    // The stock class declares this dummy setter; a patched getter needs it too.
    set currentAppSections(_) {},
});
