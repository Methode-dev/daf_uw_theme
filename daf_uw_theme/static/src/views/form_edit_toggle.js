/**
 * Forms open READ-ONLY: an explicit "Edit" button, then "Save" / "Cancel".
 *
 * Replaces Odoo 19's always-editable form and its two icon buttons (cloud =
 * save, ✕ = discard) that only appear once something is dirty.  Owner call: a
 * record is read first, and changing it is a deliberate step.
 *
 * Built on core's own readonly mode — record.config.mode, which every field
 * already honours (Field passes `readonly: !record.isInEdition`) — so no field,
 * widget or x2many needs touching.  Three seams:
 *
 *   modelParams          load existing records in "readonly" (core: "edit").
 *                        New records stay editable: opened directly, they are
 *                        left in "edit" here; created from a record ("New"),
 *                        core forces "edit" itself (_getNextConfig).
 *   saveButtonClicked    on success, back to readonly.  Failure (validation,
 *   discard              server error) leaves the form in edit, as it should.
 *   onPagerUpdate        the next/previous record opens read-only too.
 *
 * The buttons themselves are the stock FormStatusIndicator, re-templated in
 * form_edit_toggle.xml; it reads `env.mFormEditToggle` set below and falls
 * back to the stock markup without it.
 *
 * WHERE IT APPLIES: every form in the main action area that the user can edit.
 * Not in dialogs (they have their own Save / Discard footer and no control
 * panel), not for `readonly` / no-edit forms (nothing to toggle), and not on
 * the Settings page (SettingsFormController: a transient record with its own
 * Save / Discard flow — read-only there would make it unusable).
 *
 * ⚠ KEPT FROM CORE, ON PURPOSE: leaving a dirty form (breadcrumb, menu, pager,
 * header action button, browser tab hidden or closed) still SAVES it, exactly
 * as stock does.  "Cancel" is the only way to throw edits away.  Changing that
 * would mean adding a "discard changes?" prompt on every exit path.
 */
import { useRef, useSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { FormStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";
import { SettingsFormController } from "@web/webclient/settings_form_view/settings_form_controller";

patch(FormStatusIndicator.prototype, {
    setup() {
        super.setup(...arguments);
        // ⚠ Core's effect toggles `disabled` on this.saveButton.el with no null
        // check — fine in core, where the button is always in the DOM (merely
        // `invisible`).  In read-only mode ours is not rendered at all, so the
        // ref falls back to a detached button instead of crashing the form.
        const saveRef = useRef("save");
        const detached = document.createElement("button");
        this.saveButton = {
            get el() {
                return saveRef.el || detached;
            },
        };
    },

    async mEdit() {
        await this.props.model.root.switchMode("edit");
    },
});

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.mEditToggle) {
            useSubEnv({ mFormEditToggle: true });
        }
    },

    /**
     * A getter, not a flag set in setup(): core reads modelParams from inside
     * super.setup(), before anything after it would run.  canEdit is assigned
     * earlier in that same setup(), so it is available here.
     */
    get mEditToggle() {
        return (
            this.canEdit &&
            !this.props.readonly &&
            !this.env.inDialog &&
            !(this instanceof SettingsFormController)
        );
    },

    get modelParams() {
        const params = super.modelParams;
        // ⚠ Only for an existing record.  A form opened straight on a new one
        // (".../new", a "Create" action) has no resId, and an explicit
        // "readonly" beats the no-resId rule in record.isInEdition — it would
        // open a blank form behind an Edit button.
        if (this.mEditToggle && params.config.resId) {
            params.config.mode = "readonly";
        }
        return params;
    },

    async mLeaveEdition() {
        const root = this.model.root;
        if (this.mEditToggle && root.resId && root.isInEdition) {
            await root.switchMode("readonly");
        }
    },

    async saveButtonClicked() {
        const saved = await super.saveButtonClicked(...arguments);
        if (saved) {
            await this.mLeaveEdition();
        }
        return saved;
    },

    async discard() {
        await super.discard(...arguments);
        // A discarded NEW record has already navigated back (core); resId is
        // false there and mLeaveEdition is a no-op.
        await this.mLeaveEdition();
    },

    async onPagerUpdate() {
        const result = await super.onPagerUpdate(...arguments);
        await this.mLeaveEdition();
        return result;
    },
});
