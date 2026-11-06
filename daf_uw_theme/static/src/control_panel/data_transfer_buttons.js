/**
 * "Import" and "Export" as real buttons beside "New", instead of lines buried
 * in the cog (gear) dropdown and the selection Actions menu.  List and kanban.
 *
 * WHERE THE STOCK ENTRIES COME FROM (Odoo 19):
 *   - "Export All" (cog, no selection): web/static/src/views/list/export_all/
 *     export_all.js, cogMenu registry key "export-all-menu".  Downloads an xlsx
 *     of the default columns AT ONCE, no dialog ("direct-export-data").
 *   - "Export" (Actions menu, with a selection): the `export` entry of
 *     List/KanbanController.actionMenuItems, which calls the controller's
 *     `exportRecords()` (view_hook.js::useExportRecords) — the field-picking
 *     ExportDataDialog.
 *   - "Import records" (cog): base_import/static/src/import_records/
 *     import_records.js, cogMenu registry key "import-menu".
 *
 * EXPORT = THE DIALOG, ALWAYS (owner decision, QA round 1).
 *   The button calls the controller's own `exportRecords()`, passed in as a
 *   prop, so it is exactly core's Actions -> Export.  That function already
 *   covers both cases: with records selected it exports their ids; with none
 *   (or "select all" on the domain) it exports every record matching the
 *   current domain — which is what "Export All" meant, plus the field picker.
 *   Availability = core's for that entry: `isExportEnable`, i.e. the user is
 *   in base.group_allow_export (computed by the controller in onWillStart).
 *   It stays visible while records are selected, and Export is removed from
 *   the selection Actions menu (patch at the bottom) so it lives in one place.
 *   The cog's "Export All" is still removed (cog_menu.js).
 *
 * IMPORT = core's cog entry, availability READ AT RUNTIME, NOT COPIED.  The
 * button calls that registry entry's own isDisplayed(env) with the env the cog
 * would pass: act_window action, list/kanban, the view's `import` and `create`
 * attributes, not mobile.  Hidden while records are selected (owner decision:
 * importing is not an action ON a selection).
 *
 * ⚠ NO DEPENDENCY ON base_import.  Its entry is looked up by key when the
 * buttons start, i.e. long after every asset module has loaded, so asset order
 * does not matter, and without base_import the key is simply absent: no
 * Import button, nothing in the cog to hide.  The one thing that cannot be
 * borrowed is the click handler (ImportRecords.importRecords lives in a module
 * this one cannot import without depending on it), so onImport() below
 * restates its five lines — the client action `import` with the same params.
 * If base_import ever changes that call, change it here too.
 *
 * NOT IN DIALOGS: data_transfer_buttons.xml renders nothing when
 * `env.inDialog` — the x2many "Add a line" SelectCreateDialog is a record
 * picker, and Import/Export there is clutter (QA round 1).
 */
import { Component, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from "@web/views/list/list_controller";

export const EXPORT_COG_KEY = "export-all-menu";
export const IMPORT_COG_KEY = "import-menu";

const cogMenuRegistry = registry.category("cogMenu");

/** Same contract as CogMenu._registryItems: no predicate means "shown". */
async function isCogItemDisplayed(key, env) {
    if (!cogMenuRegistry.contains(key)) {
        return false;
    }
    const item = cogMenuRegistry.get(key);
    return "isDisplayed" in item ? Boolean(await item.isDisplayed(env)) : true;
}

export class DataTransferButtons extends Component {
    static template = "daf_uw_theme.DataTransferButtons";
    static props = {
        // The controller's isExportEnable (core's rule for Actions -> Export).
        canExport: { type: Boolean, optional: true },
        // The controller's exportRecords(): opens core's ExportDataDialog.
        onExport: { type: Function, optional: true },
        hasSelection: { type: Boolean, optional: true },
    };

    setup() {
        this.action = useService("action");
        this.importTitle = _t("Import records");
        this.exportTitle = _t("Export");
        // ⚠ Evaluated once, at start: everything the import predicate reads is
        // fixed for the controller's life (arch, action type, screen size class).
        // The selection is a prop, so selecting re-renders without re-asking.
        onWillStart(async () => {
            this.canImport = await isCogItemDisplayed(IMPORT_COG_KEY, this.env);
        });
    }

    get showImport() {
        return this.canImport && !this.props.hasSelection;
    }

    get showExport() {
        return Boolean(this.props.canExport && this.props.onExport);
    }

    /** Mirrors base_import's ImportRecords.importRecords() — see header. */
    onImport() {
        const { context, resModel } = this.env.searchModel;
        this.action.doAction({
            type: "ir.actions.client",
            tag: "import",
            params: { active_model: resModel, context },
        });
    }

    onExportClick() {
        this.props.onExport();
    }
}

// ⚠ Exposed as a PROTOTYPE getter used through `t-component`, not added to
// `static components`.  Many controllers subclass these two with their own
// `static components = { ...ListController.components, ... }`, evaluated when
// THEIR module loads — possibly before this file — and they reuse web.ListView /
// web.KanbanView, which data_transfer_buttons.xml extends.  A static-components
// patch would miss those snapshots and the template would fail with "Cannot
// find the definition of component".  A prototype getter reaches every
// subclass whatever the load order.
// ⚠ A FACTORY, one fresh object per target.  web/core/utils/patch.js binds
// `super` by calling Object.setPrototypeOf() ON the extension object itself, so
// one object shared by two patch() calls is re-parented by the second: the
// first target's `super` then resolves on the wrong class.
const dataTransferButtonsPatch = () => ({
    get mDataTransferButtons() {
        return DataTransferButtons;
    },
    /**
     * Export lives in the control panel button now (header): drop core's
     * `export` entry from the selection Actions menu.  Everything else in that
     * menu (duplicate, archive, delete, server actions…) is untouched.
     * ⚠ getStaticActionMenuItems(), NOT the `actionMenuItems` getter: the
     * getter returns the already-built `{ action: [...], print }` lists; the
     * keyed `{ export, duplicate, archive, … }` map is this method's, and it
     * is also what subclasses extend through super (project's list does), so
     * the removal reaches them too.
     */
    getStaticActionMenuItems() {
        const { export: _promoted, ...items } = super.getStaticActionMenuItems(...arguments);
        return items;
    },
});
patch(ListController.prototype, dataTransferButtonsPatch());
patch(KanbanController.prototype, dataTransferButtonsPatch());
