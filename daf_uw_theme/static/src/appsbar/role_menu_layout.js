/**
 * What the sidebar lists, and which entry is open (QA).
 *
 * Two fixed layouts, picked by what the user can reach:
 *  - DAF staff: four headings (not clickable) over their entries;
 *  - brokers: one flat list.
 * Anybody else (an Odoo administrator with no DAF role) keeps MuK's list of
 * apps and the stock navbar. An entry is the menu named by its xmlid, and is
 * left out when the user cannot reach that menu; one with no screen yet
 * (`tbd`) stays on, and says so when clicked.
 *
 * The entry that was clicked is the one open: the top navbar lists ITS
 * sub-menus (role_menu_navbar.js), not those of the app it sits in. It is kept
 * for the session; on a first load, or when the screen is no longer one of its
 * own, it is worked out from the screen on display.
 */

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

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
                    menu(_t("Brokers"), "daf_base.menu_daf_brokers"),
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
                    menu(_t("Products"), "daf_product.menu_daf_product"),
                ],
            },
            {
                items: [menu(_t("Signatures"), "sign_methode.menu_sign_root")],
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

const STORAGE_KEY = "daf_role_menu_active";

function readStored() {
    try {
        return browser.sessionStorage.getItem(STORAGE_KEY) || null;
    } catch {
        return null; // storage can be blocked: the screen decides then
    }
}

/** The open entry's key, shared by the sidebar and the navbar. */
export const roleMenuState = reactive({ activeKey: readStored() });

export function itemKey(item) {
    return item.xmlid || item.label.toString();
}

export function setActiveRoleItem(item) {
    roleMenuState.activeKey = itemKey(item);
    try {
        browser.sessionStorage.setItem(STORAGE_KEY, roleMenuState.activeKey);
    } catch {
        // kept in memory only
    }
}

/** The layout's sections, each entry resolved to its menu; [] = stock. */
export function getRoleSections(menuService) {
    const menus = new Map(
        menuService
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
}

/** The menu itself, or the first screen below it (a parent may have none). */
export function firstScreen(menuService, menu) {
    if (menu.actionID) {
        return menu;
    }
    for (const id of menu.children || []) {
        const found = firstScreen(menuService, menuService.getMenu(id));
        if (found) {
            return found;
        }
    }
    return null;
}

/** Is ``actionId`` the screen of ``menu`` or of one of its sub-menus? */
function belongsTo(menuService, menu, actionId) {
    return (
        menu.actionID === actionId ||
        (menu.children || []).some((id) =>
            belongsTo(menuService, menuService.getMenu(id), actionId)
        )
    );
}

/**
 * The entry that is open, or null when there is no layout or no entry owns the
 * screen (the stock navbar then stands in).
 */
export function activeRoleItem(menuService, actionService) {
    const items = getRoleSections(menuService)
        .flatMap((section) => section.items)
        .filter((item) => item.menu);
    if (!items.length) {
        return null;
    }
    const actionId = actionService.currentController?.action?.id;
    const clicked = items.find((item) => itemKey(item) === roleMenuState.activeKey);
    if (clicked && (!actionId || belongsTo(menuService, clicked.menu, actionId))) {
        return clicked;
    }
    // Not clicked, or left for a screen that is not its own: an entry that IS
    // that screen first ("Devis" before the "Portfolio" it sits in).
    return (
        items.find((item) => item.menu.actionID === actionId) ||
        items.find((item) => belongsTo(menuService, item.menu, actionId)) ||
        null
    );
}
