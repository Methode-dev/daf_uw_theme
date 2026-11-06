/**
 * The cog (gear) dropdown, minus "Export All" and "Import records" — those are
 * buttons now (data_transfer_buttons.js).  Everywhere: list, kanban, and any
 * other view whose cog would have listed them.
 *
 * ⚠ FILTERED, NOT UNREGISTERED.  `registry.category("cogMenu").remove(key)`
 * would be shorter, but the buttons read those very entries' isDisplayed()
 * to stay on core's availability rules — the registry must keep them.  It
 * would also be order-dependent for base_import, which is not a dependency
 * of this module and may well register its item after this file runs.
 *
 * The filter matches on the entries' Component classes, resolved from the
 * registry on each call: CogMenu._registryItems() returns {Component,
 * groupNumber, key: Component.name} without the registry key, and the class is
 * the only stable identity in that shape (a class `name` survives
 * minification in Odoo bundles today, but nothing guarantees it).
 *
 * "If the cog ends up empty, it should not render": already core behaviour,
 * nothing to add.  web.CogMenu's root is `t-if="hasItems"`, and hasItems is
 * cogItems.length || print items — with the two entries filtered out of
 * registryItems, a view with no other actions has no items and no cog.
 * Form views and lists WITH a selection are untouched: their items are action
 * menu items (props.items), not these registry entries.
 */
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { EXPORT_COG_KEY, IMPORT_COG_KEY } from "./data_transfer_buttons";

const cogMenuRegistry = registry.category("cogMenu");

function promotedComponents() {
    return new Set(
        [EXPORT_COG_KEY, IMPORT_COG_KEY]
            .filter((key) => cogMenuRegistry.contains(key))
            .map((key) => cogMenuRegistry.get(key).Component)
    );
}

patch(CogMenu.prototype, {
    async _registryItems() {
        const items = await super._registryItems();
        const promoted = promotedComponents();
        return items.filter((item) => !promoted.has(item.Component));
    },
});
