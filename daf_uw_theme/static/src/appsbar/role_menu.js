/**
 * The sidebar lists what a person does, not the installed apps (QA).
 *
 * Two fixed layouts, picked by what the user can reach:
 *  - DAF staff: four headings (not clickable) over their entries;
 *  - brokers: one flat list.
 * Anybody else (an Odoo administrator with no DAF role) keeps MuK's list of
 * apps. An entry is the menu named by its xmlid, and is left out when the user
 * cannot reach that menu; one with no screen yet (`tbd`) stays on, and says so
 * when clicked. The top navbar keeps the stock section row of the app the
 * entry belongs to.
 *
 * muk_web_appsbar is vendored: this only patches AppsBar and extends its
 * template (role_menu.xml); it does not edit it.
 */

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { AppsBar } from "@muk_web_appsbar/webclient/appsbar/appsbar";

// A menu that only exists for DAF staff / for brokers: what tells them apart.
const STAFF_ROOT = "daf_base.menu_daf_root";
const BROKER_ROOT = "daf_policy.menu_daf_client_broker";

const tbd = (label) => ({ label, tbd: true });
const menu = (label, xmlid) => ({ label, xmlid });

export const LAYOUTS = [
    {
        root: STAFF_ROOT,
        sections: [
            {
                heading: _t("Dashboard"),
                items: [
                    tbd(_t("Statistics")),
                    tbd(_t("Announcements")),
                    tbd(_t("Service status")),
                ],
            },
            {
                heading: _t("User management"),
                items: [
                    // The DAF staff list (visible to the User Manager role).
                    menu(_t("Admins"), "daf_base.menu_daf_staff"),
                    tbd(_t("Users")),
                    menu(_t("Brokers"), "daf_base.menu_daf_cabinet"),
                    menu(_t("Clients"), "daf_base.menu_daf_client"),
                ],
            },
            {
                heading: _t("Financial management"),
                items: [
                    menu(_t("Contracts"), "daf_base.menu_daf_contract"),
                    menu(_t("Quotes"), "daf_base.menu_daf_quote"),
                    menu(_t("Portfolio"), "daf_base.menu_daf_portfolio"),
                    tbd(_t("Billing")),
                ],
            },
            {
                heading: _t("Product management"),
                items: [
                    menu(_t("Price grids"), "daf_pricing.menu_daf_price_grid"),
                    menu(_t("Products"), "daf_product.menu_daf_product_catalogue"),
                ],
            },
        ],
    },
    {
        root: BROKER_ROOT,
        sections: [
            {
                items: [
                    { label: _t("Home"), href: "/odoo" },
                    menu(_t("Products"), "daf_product.menu_daf_product_tiles"),
                    menu(_t("Clients"), "daf_policy.menu_daf_client_broker"),
                    menu(_t("Quotes"), "daf_policy.menu_daf_quote_broker"),
                    tbd(_t("Contracts")),
                    tbd(_t("Portfolio")),
                    tbd(_t("Statistics")),
                ],
            },
        ],
    },
];

patch(AppsBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.notification = useService("notification");
        // The active entry follows the screen on display.
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => this.render());
    },

    /** The layout's sections, each entry resolved to its menu; [] = stock. */
    get roleSections() {
        const menus = new Map(
            this.menuService
                .getAll()
                .filter((m) => m.xmlid)
                .map((m) => [m.xmlid, m])
        );
        const layout = LAYOUTS.find((l) => menus.has(l.root));
        if (!layout) {
            return [];
        }
        const sections = [];
        for (const section of layout.sections) {
            const items = [];
            for (const item of section.items) {
                const target = item.xmlid ? menus.get(item.xmlid) : null;
                if (item.xmlid && !target) {
                    continue; // the user cannot reach that screen
                }
                items.push({ ...item, menu: target });
            }
            if (items.length) {
                sections.push({ heading: section.heading, items });
            }
        }
        return sections;
    },

    isRoleItemActive(item) {
        const current = this.actionService.currentController?.action?.id;
        const target = item.menu && this.firstScreen(item.menu);
        return Boolean(current && target && target.actionID === current);
    },

    /** The menu itself, or the first screen below it (a parent has none). */
    firstScreen(menu) {
        if (menu.actionID) {
            return menu;
        }
        for (const id of menu.children || []) {
            const found = this.firstScreen(this.menuService.getMenu(id));
            if (found) {
                return found;
            }
        }
        return null;
    },

    onRoleItemClick(item) {
        if (item.tbd) {
            this.notification.add(_t("Coming soon."), { type: "info" });
        } else if (item.href) {
            browser.location.assign(item.href);
        } else {
            const target = this.firstScreen(item.menu);
            if (target) {
                this.menuService.selectMenu(target);
            }
        }
    },
});
