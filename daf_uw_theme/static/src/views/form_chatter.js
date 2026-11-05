/**
 * The chatter always sits UNDER the form, across the full width.
 *
 * Stock Odoo 19 moves it to a right-hand column once the window reaches the XXL
 * breakpoint (mail/static/src/chatter/web/form_renderer.js::mailLayout).  Owner
 * call: one position, whatever the screen — the record reads top to bottom and
 * its history follows it.
 *
 * mailLayout() is the single seam: the form compiler derives everything from
 * its return value (o-aside class, isChatterAside, whether the chatter lives in
 * the sheet background).  So every "side" layout is folded into its bottom
 * counterpart here, and the compiled template follows without being touched:
 *
 *   SIDE_CHATTER        -> BOTTOM_CHATTER
 *   EXTERNAL_COMBO_XXL  -> EXTERNAL_COMBO  (attachments stay in the pop-out)
 *   COMBO               -> BOTTOM_CHATTER
 *
 * ⚠ COMBO IS THE TRADE.  It is the attachment-preview layout (vendor bills and
 * the like: PDF on the right, chatter squeezed under the sheet).  Folding it
 * into BOTTOM_CHATTER drops the side preview so the chatter keeps its full
 * width; the attachments are still in the chatter, and the pop-out button still
 * opens them in their own window (EXTERNAL_COMBO).  No view in this build ships
 * an o_attachment_preview, so today this only affects core accounting forms.
 *
 * The renderer half of the XXL layout — `flex-nowrap h-100`, which puts the
 * sheet and the chatter side by side as a row — is a compiled class, not a
 * mailLayout() outcome, so it is undone in scss/views/form_view.scss.
 *
 * ⚠ Depends on `mail` in the manifest: this calls super.mailLayout(), which
 * only exists once mail's own patch has been applied, and asset order follows
 * module dependency order.
 */
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

const BOTTOM_LAYOUT = {
    SIDE_CHATTER: "BOTTOM_CHATTER",
    EXTERNAL_COMBO_XXL: "EXTERNAL_COMBO",
    COMBO: "BOTTOM_CHATTER",
};

patch(FormRenderer.prototype, {
    mailLayout(hasAttachmentContainer) {
        const layout = super.mailLayout(hasAttachmentContainer);
        return BOTTOM_LAYOUT[layout] || layout;
    },
});
