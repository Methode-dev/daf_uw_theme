/**
 * The sidebar lists what a person does, not the installed apps (QA): see
 * role_menu_layout.js for the layouts and which entry is open.
 *
 * muk_web_appsbar is vendored: this only patches AppsBar and extends its
 * template (role_menu.xml); it does not edit it.
 */

import { useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AppsBar } from "@muk_web_appsbar/webclient/appsbar/appsbar";
import {
    activeRoleItem,
    firstScreen,
    getRoleSections,
    itemKey,
    roleMenuState,
    setActiveRoleItem,
} from "./role_menu_layout";

patch(AppsBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.roleState = useState(roleMenuState);
        // The active entry follows the screen on display.
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => this.render());
    },

    get roleSections() {
        return getRoleSections(this.menuService);
    },

    isRoleItemActive(item) {
        const active = activeRoleItem(this.menuService, this.actionService);
        return Boolean(active && itemKey(active) === itemKey(item));
    },

    onRoleItemClick(item) {
        if (item.tbd) {
            this.notification.add(_t("Coming soon."), { type: "info" });
        } else if (item.href) {
            browser.location.assign(item.href);
        } else {
            const target = firstScreen(this.menuService, item.menu);
            if (target) {
                // First: the navbar lists this entry's sub-menus from now on.
                setActiveRoleItem(item);
                this.menuService.selectMenu(target);
            }
        }
    },
});
