/**
 * List views: a loading skeleton, and rows that ease in when data arrives.
 * Global — every list view and every x2many list — through two patches, no
 * per-view wiring.  Styles in list_loading.scss, first-load markup in
 * list_loading.xml.
 *
 * THREE STATES, THREE SEAMS (all found in web/static/src, Odoo 19):
 *
 * 1. FIRST LOAD -> skeleton markup.  ListController.modelOptions sets
 *    `lazy: true` for a list opened from an action (control panel shown, not in
 *    a dialog, not a controller restore).  useModelWithSampleData then does NOT
 *    await the load in willStart: the controller mounts at once with
 *    `model.isReady === false`, and web.ListView renders its control panel and
 *    *no renderer at all* (`t-if="model.isReady"`).  That empty hole is where
 *    the skeleton goes — see list_loading.xml.  Non-lazy loads (dialogs,
 *    breadcrumb restores) await willStart, are ready at first render, and so
 *    never show it: there is nothing on screen to replace.
 *
 * 2. RELOADS (search, filter, group by, pager, column sort, archive...) ->
 *    the CURRENT rows turn into skeleton bars.  Every one of those ends in a
 *    root load, and the RelationalModel announces every root load through its
 *    own hooks, `onWillLoadRoot` / `onRootLoaded` (relational_model.js: load()
 *    and _updateConfig() when `config.isRoot`).  The controller already passes
 *    `hooks` in modelParams, so this chains two more onto them.  Sub-list loads
 *    (unfolding one group) are not root loads and deliberately do not trigger.
 *    ⚠ The stale rows are reskinned in CSS rather than swapped for the skeleton
 *    markup: the renderer stays mounted, so column widths, the edited row,
 *    the selection and the scroll position all survive the reload.
 *
 * 3. ROWS ARRIVE -> `.m-list-enter` on the renderer for one animation's length
 *    (fade + 4px rise, staggered over the first rows — the CSS).  Played from:
 *      - the controller, after each root load (covers the pager, where the
 *        root list object is reused and only its records change);
 *      - the renderer, whenever its `list` prop is a different object (first
 *        mount; a new root after search; an x2many when the form moves to
 *        another record).
 *    ⚠ x2many lists in forms have no ListController, so they get the
 *    animation but never the skeleton — by design: their data comes with the
 *    form's own load, there is no separate wait to fill.
 *    ⚠ The animation is a class toggled for ~700ms, NOT a permanent rule on
 *    `tr`.  A permanent rule replays on every DOM insertion: adding a line to
 *    an editable list, dropping a row after a handle drag (the sortable
 *    re-inserts the node) and so on.  Keyed on "a load finished" instead, it
 *    plays exactly when the user is waiting to see new rows.
 *
 * Reduced motion: handled entirely in the SCSS (no rise, no stagger, no
 * shimmer — the skeleton is static).  Nothing here needs to know.
 */
import { onWillUnmount, toRaw, useEffect, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";

// A reload faster than this never shows the skeleton: flashing it for 60ms is
// worse than showing nothing.  Long enough to skip a warm-cache pager click,
// short enough that a real wait gets feedback well inside 300ms.
const RELOAD_SKELETON_DELAY = 150;
// Must cover the longest row: stagger cap (9 x 30ms) + 240ms run, plus slack.
// Kept in step with list_loading.scss.
const ENTER_DURATION = 700;

const enterTimers = new WeakMap();

/**
 * Restart the enter animation on a list renderer element.  Idempotent: two
 * callers in the same flush (controller + renderer after a search) just restart
 * it once more before anything is painted.
 * @param {HTMLElement | null} el the `.o_list_renderer`
 */
export function playListEnter(el) {
    if (!el) {
        return;
    }
    clearTimeout(enterTimers.get(el));
    el.classList.remove("m-list-enter");
    // ⚠ The forced reflow is what makes a REstart work: without it, remove +
    // add in one task is a no-op as far as the style engine is concerned, and
    // the second load in a row would not animate.
    void el.offsetWidth;
    el.classList.add("m-list-enter");
    enterTimers.set(
        el,
        setTimeout(() => el.classList.remove("m-list-enter"), ENTER_DURATION)
    );
}

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.mListLoad = useState({ reloading: false, loaded: 0 });
        this.mReloadTimer = null;
        this.mLoadSeq = 0;
        onWillUnmount(() => clearTimeout(this.mReloadTimer));
        this.mWatchRootLoadFailures();
        useEffect(
            (loaded) => {
                if (loaded) {
                    playListEnter(this.rootRef.el?.querySelector(".o_list_renderer"));
                }
            },
            () => [this.mListLoad.loaded]
        );
    },

    /**
     * ⚠ Read by super.setup() (useModelWithSampleData), i.e. BEFORE the code
     * after super.setup() above has run.  The hooks only close over `this`, and
     * the model's first load is in onWillStart — after setup — so mListLoad
     * exists by the time either of them fires.
     */
    get modelParams() {
        const params = super.modelParams;
        const hooks = params.hooks || {};
        params.hooks = {
            ...hooks,
            onWillLoadRoot: (config) => {
                hooks.onWillLoadRoot?.(config);
                this.mOnWillLoadRoot();
            },
            onRootLoaded: async (root) => {
                await hooks.onRootLoaded?.(root);
                this.mOnRootLoaded();
            },
        };
        return params;
    },

    /**
     * Clears the reload state when a root load FAILS (RPC error, access error
     * raised by a domain…).  The model has no error hook — onRootLoaded simply
     * never fires — so this wraps `_loadData` on THIS controller's model
     * instance (never the prototype: form x2many models are untouched).  Every
     * root load reaches it: model.load() and _updateConfig() both call
     * onWillLoadRoot and then _loadData() synchronously, with the root config.
     *
     * ⚠ The returned promise is the ORIGINAL one: the `.catch` hangs off a
     * branch, so the caller still sees the rejection (core's error dialog and
     * error handling are unchanged) and the branch, being handled, raises no
     * second "unhandled rejection".
     * ⚠ Sequence-guarded.  KeepLast discards superseded loads, but their inner
     * _loadData still settles; a superseded load failing must not clear the
     * state of the newer load still in flight.  `mLoadSeq` is bumped in
     * onWillLoadRoot, which runs just before the matching _loadData call.
     * ⚠ toRaw: assigning a method on the useState proxy would be a reactive
     * write (a pointless render, and a proxy-wrapped `this` inside core code).
     */
    mWatchRootLoadFailures() {
        const model = toRaw(this.model);
        const loadData = model._loadData;
        if (typeof loadData !== "function") {
            return;
        }
        model._loadData = (config, ...args) => {
            const promise = loadData.call(model, config, ...args);
            if (config?.isRoot) {
                const seq = this.mLoadSeq;
                promise.catch(() => {
                    if (seq === this.mLoadSeq) {
                        this.mOnRootLoadFailed();
                    }
                });
            }
            return promise;
        };
    },

    mOnRootLoadFailed() {
        // Restore the rows exactly as they were (they are still the last good
        // result); no enter animation, nothing new arrived.
        clearTimeout(this.mReloadTimer);
        this.mListLoad.reloading = false;
        // ⚠ The rows now show the LAST GOOD result, but the search model
        // already holds the query that failed (it updates before the load), so
        // the search box can say "Lyon" over unfiltered rows.  Reverting the
        // query belongs to the search bar (static/src/search/, not this
        // module's), so this only announces it on the search model's bus; a
        // listener there can restore the input to what the list shows.
        this.env.searchModel?.trigger?.("m-root-load-failed");
    },

    mOnWillLoadRoot() {
        this.mLoadSeq++;
        // First load is the skeleton markup's job (model not ready yet).
        if (!this.model?.isReady) {
            return;
        }
        clearTimeout(this.mReloadTimer);
        this.mReloadTimer = setTimeout(() => {
            this.mListLoad.reloading = true;
        }, RELOAD_SKELETON_DELAY);
    },

    mOnRootLoaded() {
        // ⚠ Boolean, not a counter.  The model's KeepLast drops superseded
        // loads (typing in the search box), so their onRootLoaded never fires:
        // N "will load" for 1 "loaded".  The last one clears the flag either
        // way.  A load that REJECTS never calls onRootLoaded either; that case
        // is mOnRootLoadFailed's (see mWatchRootLoadFailures).
        clearTimeout(this.mReloadTimer);
        this.mListLoad.reloading = false;
        this.mListLoad.loaded++;
    },

    get className() {
        const className = super.className;
        // ⚠ `loaded` is read here, during render, only to subscribe to it: a
        // useEffect deps function is evaluated outside render and does not
        // subscribe, so without this read nothing guarantees a patch after
        // the increment, and the enter animation could miss a load.
        const { reloading, loaded } = this.mListLoad || {};
        void loaded;
        // Not while a row is being edited: its inputs must stay usable/visible.
        if (reloading && !this.model.root.editedRecord) {
            return `${className || ""} m-list-reloading`;
        }
        return className;
    },

    /**
     * Placeholder columns for the first-load skeleton: as many as the view will
     * show (fields not hidden as optional), clamped so a 2-column view still
     * reads as a table and a 25-column one does not render 25 bars.
     */
    get mSkeletonColumns() {
        const count = this.archInfo.columns.filter(
            (col) => col.type === "field" && col.optional !== "hide" && col.widget !== "handle"
        ).length;
        return [...Array(Math.min(Math.max(count, 3), 7)).keys()];
    },

    get mSkeletonRows() {
        return [...Array(8).keys()];
    },
});

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        useEffect(
            () => playListEnter(this.rootRef.el),
            () => [this.props.list]
        );
    },
});
