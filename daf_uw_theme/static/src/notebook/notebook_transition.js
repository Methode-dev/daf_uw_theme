/**
 * Notebook pages animate on leave AND on enter, everywhere a web.Notebook is
 * used (form notebooks, dialogs, settings-style vertical notebooks).  Styles in
 * notebook_transition.scss.
 *
 * WHY A PATCH AND NOT CSS ALONE.  Core renders only the current page, inside
 * ONE persistent `.tab-pane` (notebook.xml, t-ref="activePane"); switching
 * pages swaps that pane's content in a single render.  CSS can animate the new
 * content in, but by the time anything could animate OUT, the old content is
 * already gone.  So the leave has to happen BEFORE `state.currentPage`
 * changes: play it, wait for it, then let core swap the page.
 *
 * ⚠ activatePage() IS RE-STATED, NOT WRAPPED.  The leave must sit between
 * core's veto and core's state change:
 *
 *   onWillActivatePage(page)   ← a form SAVES here when dirty, and may refuse
 *   ── leave animation ──       ← only once we know the switch will happen
 *   state.currentPage = page   ← core's swap
 *
 * Animating before the veto would play "leave" and then stay on the page
 * whenever a save failed.  There is no seam between those two steps in core,
 * so the method is re-stated from web/static/src/core/notebook/notebook.js
 * (Odoo 19) with the leave inserted.  If core's activatePage changes, port the
 * change here — it is twelve lines.
 *
 * DIRECTION.  Pages slide the way the tabs are laid out: going to a tab on the
 * right, the old page leaves to the left and the new one enters from the
 * right; going back, the reverse.  Vertical notebooks slide on the y axis.
 *
 * NOT ANIMATED, on purpose:
 *  - the first render of a notebook (opening a form must not "slide in" a
 *    page nobody switched to);
 *  - page changes core makes without a click (onWillUpdateProps: another
 *    record loaded, the default page changed, the current page hidden);
 *  - anything at all under prefers-reduced-motion — core's swap runs as is.
 */
import { onPatched, status, useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { Notebook } from "@web/core/notebook/notebook";
import { patch } from "@web/core/utils/patch";

// Must match the leave animation's duration in notebook_transition.scss.
// Short on purpose: it delays the page the user asked for, so it is half the
// enter's length.
export const NOTEBOOK_LEAVE_MS = 170;

const DIR_CLASSES = ["m-page--forward", "m-page--back"];
const STAGE_CLASSES = ["m-page-leave", "m-page-enter"];

function prefersReducedMotion() {
    return Boolean(browser.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
}

/**
 * Play the enter animation on the pane; the classes remove themselves when it
 * ends.  Returns a cleanup that detaches the listener early.
 */
function playEnter(pane, direction) {
    pane.classList.remove(...STAGE_CLASSES, ...DIR_CLASSES);
    // Force a style flush so re-adding the class restarts the animation even
    // when two switches land back to back.
    void pane.offsetWidth;
    pane.classList.add("m-page-enter", `m-page--${direction}`);
    const done = (ev) => {
        if (ev.target !== pane) {
            return; // an animation bubbling up from the page's own content
        }
        pane.classList.remove("m-page-enter", ...DIR_CLASSES);
        pane.removeEventListener("animationend", done);
    };
    pane.addEventListener("animationend", done);
    return () => pane.removeEventListener("animationend", done);
}

patch(Notebook.prototype, {
    setup() {
        super.setup(...arguments);
        // Set by a user-initiated switch, consumed by the effect below.  Null
        // means "this page change was not a click": no enter animation.
        this._mEnterDirection = null;
        this._mSwitchToken = null;

        useEffect(
            () => {
                const pane = this.activePane.el;
                const direction = this._mEnterDirection;
                this._mEnterDirection = null;
                if (!pane || !direction) {
                    return;
                }
                return playEnter(pane, direction);
            },
            () => [this.state.currentPage]
        );

        // ⚠ SAFETY NET for a switch that never got to render.  Click B, then
        // click back to A before B's render has committed (a slow page, a busy
        // form): the state goes A → B → A, the committed render is A again, and
        // every effect keyed on currentPage — core's included — sees "no
        // change" and does not run.  Core would then leave the pane without
        // `show` (opacity 0, an empty page); with the leave class on top, the
        // page would stay hidden for good.  onPatched runs on EVERY committed
        // render, so it heals the pane whenever no switch is still pending.
        // Registered after the effects above, so on a normal switch they have
        // already done the work and this is a no-op.
        onPatched(() => {
            const pane = this.activePane.el;
            if (!pane || this._mSwitchToken) {
                return;
            }
            if (pane.classList.contains("m-page-leave")) {
                const direction = this._mEnterDirection || "forward";
                this._mEnterDirection = null;
                playEnter(pane, direction);
            }
            pane.classList.add("show");
        });
    },

    async activatePage(pageIndex) {
        // --- added: back to the current tab while its leave is playing -------
        // Cancel the pending switch and bring the page back, instead of
        // landing on the tab clicked before (core would ignore this click).
        if (this.state.currentPage === pageIndex && this._mSwitchToken) {
            this._mSwitchToken = null;
            const pane = this.activePane.el;
            if (pane) {
                // Come back from where it left to.
                playEnter(pane, pane.classList.contains("m-page--forward") ? "back" : "forward");
            }
            return;
        }

        // --- core, unchanged -------------------------------------------------
        if (this.disabledPages.includes(pageIndex) || this.state.currentPage === pageIndex) {
            return;
        }
        const prom = (async () => this.props.onWillActivatePage(pageIndex))();
        const canProceed = await this.keepLastPageTransition.add(prom);
        if (canProceed === false) {
            return;
        }

        // --- leave (added) ---------------------------------------------------
        const pane = this.activePane.el;
        if (pane && !prefersReducedMotion()) {
            const order = this.navItems.map(([id]) => id);
            const direction =
                order.indexOf(pageIndex) >= order.indexOf(this.state.currentPage)
                    ? "forward"
                    : "back";
            // A later click supersedes this one: only the newest switch may
            // finish, so rapid clicking lands on the LAST tab clicked.
            const token = (this._mSwitchToken = {});
            pane.classList.remove(...STAGE_CLASSES, ...DIR_CLASSES);
            pane.classList.add("m-page-leave", `m-page--${direction}`);
            await new Promise((resolve) => browser.setTimeout(resolve, NOTEBOOK_LEAVE_MS));
            if (token !== this._mSwitchToken || status(this) === "destroyed") {
                return;
            }
            this._mSwitchToken = null;
            this._mEnterDirection = direction;
        }

        // --- core, unchanged -------------------------------------------------
        this.activePane.el?.classList.remove("show");
        this.state.currentPage = pageIndex;
    },
});
