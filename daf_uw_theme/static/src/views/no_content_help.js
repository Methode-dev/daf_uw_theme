/**
 * Empty states — the branded "no records" message (§7).
 *
 * Odoo builds an empty state out of two pieces: the `help` stored on the
 * ir.actions.act_window record, and a helper component that renders it.  There
 * is no single component to patch — web ships `ActionHelper`, and sale,
 * hr_recruitment, hr_attendance, lunch, board and dms each replace it with one
 * of their own.  But every one of them is handed the same string, by the same
 * line of `View.loadView`, so THAT is the seam.  Rewriting it here reaches all
 * of them at once, including the templates this module cannot t-inherit
 * because their modules are not dependencies.
 *
 * The look — the Méthode mark, the card, and the removal of Sales' YouTube
 * teaser — is scss/views/no_content.scss.  Read its header too.
 *
 * ⚠ WHY THE ACTION'S OWN HELP IS DISCARDED RATHER THAN DECORATED.
 * On a stock database that text is Odoo's marketing copy, not guidance.  The
 * Quotations action (sale.action_quotations_with_onboarding) is the one the
 * brief named, and its `help` is verbatim:
 *
 *     <h2>Beat competitors with stunning quotations!</h2>
 *     <p>Boost sales with online payments or signatures, upsells, ...</p>
 *     <a class="btn btn-secondary" href="https://www.odoo.com/documentation/...
 *        sample_quotation.pdf">Check a sample. It's clean!</a>
 *
 * — an English pitch, from another vendor, with a button that navigates a
 * prospect out of the demo to odoo.com.  Keeping it and adding a French line
 * above would have produced a bilingual empty state advertising a competitor.
 * The trade is real and worth stating: the handful of actions whose help IS
 * useful (per-model "create your first X" wording) now say the generic line
 * too.  Deleting this file restores every one of them.
 *
 * ⚠ FRENCH IN THE SOURCE, NOT IN i18n/fr.po — the same call as
 * views/error_templates.xml, for the same measured reason, and it is worth
 * re-checking rather than assuming.  Every database this product ships has
 * exactly one active language:
 *
 *     demo, demo_tmpl_btp, demo_tmpl_hotel,
 *     demo_tmpl_restaurant, demo_tmpl_sales   ->  en_US, and every user row
 *                                                 carries lang=en_US
 *
 * A msgstr in fr.po is only ever read for a user whose lang is fr_FR, so the
 * English source is what would have rendered — the module convention would
 * have silently produced an English empty state.  If fr_FR is ever installed
 * and made the default, this text is already the wanted output; nothing here
 * needs undoing.
 */

import { markup } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { View } from "@web/views/view";

// The classes are ours, not Odoo's: no_content.scss styles the card and the
// mark on the shared `.o_nocontent_help` wrapper, and only reaches inside it
// for the first and last paragraph. Markup, not a plain string — every helper
// renders this with t-out, which escapes anything not flagged as safe HTML.
const NO_CONTENT_HELP = markup`
    <p class="m-nocontent__title">Rien à afficher pour le moment</p>
    <p class="m-nocontent__lead">Créez un premier enregistrement, ou ajustez les filtres de la barre de recherche.</p>
`;

patch(View.prototype, {
    async loadView(props) {
        await super.loadView(props);
        // `componentProps` is what loadView leaves the controller props in
        // (view.js: `this.componentProps = finalProps`), and `info` is where
        // the action's help was copied. Optional-chained because a view type
        // may reshape the props through its own `descr.props()`.
        //
        // ⚠ Setting this unconditionally does more than swap words: the LIST
        // renderer gates its whole empty state on the help being truthy
        // (`showNoContentHelper` in list_renderer.js), so a list whose action
        // defines no help used to render a bare empty grid. Those views now
        // get the branded message too, which is the point of the change.
        if (this.componentProps?.info) {
            this.componentProps.info.noContentHelp = NO_CONTENT_HELP;
        }
    },
});
