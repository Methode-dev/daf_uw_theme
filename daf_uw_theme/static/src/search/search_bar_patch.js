/**
 * Simplified, beginner-friendly search bar, on every view that has one.
 *
 * Owner brief: "Odoo search is complicated for noobs." Stock Odoo has two entry
 * points. Typing opens an autocomplete of "Search <field> for: …" lines that must
 * be picked or Entered. The caret opens one panel with every filter, group-by,
 * favourite and the custom-filter tools. Both are replaced by three inputs:
 *
 *   [ 🔍 Search…            × ] [ ⏷ Filter… ] [ ⊞ Group by… ]
 *
 *   * The main input is a LIVE search. Each keystroke re-filters the view after
 *     LIVE_DELAY ms, with no Enter needed. The term is matched against the search
 *     view's own text fields, OR-ed (search_model_patch.js has which fields and
 *     why). It stays as text in the input, with a × to clear it, and gets no chip
 *     (see the model patch for why). The input's tooltip names the fields it
 *     searches.
 *   * Filter… / Group by… are typeaheads over the predefined options
 *     (search_picker.js). Whatever they apply shows as a stock facet chip,
 *     removable with its ×.
 *
 * Where the template seams are (search_bar.xml):
 *   * web.SearchBarMenu (the caret + the big panel) is REPLACED by the two
 *     pickers. That one node is also the only route in this bar to "Custom
 *     Filter…", the custom group-by <select>, "Save current search", and
 *     favourite edit/delete. Customisation goes with it, as briefed.
 *   * The facet "pencil" overlay is removed and onFacetLabelClick no longer
 *     opens the domain editor. Clicking a group-by chip still flips its
 *     count-sort where the view supports it: that is a sort, not a domain edit.
 *   * The autocomplete keeps a fallback role only. It still appears when the view
 *     has no text-like <field> to live-search (rare: a search view of dates or
 *     numbers only), and even then without its "Add a custom filter" line.
 *
 * ⚠ ENTER. The stock bar binds Enter (with no dropdown open) to
 * searchModel.search(), which reloads the view. That is kept: Enter still
 * "searches". If a keystroke is still waiting out the debounce, Enter applies it
 * at once and stops there, so one key press does not cause two reloads.
 *
 * ⚠ THE DMS FILE EXPLORER ALREADY PATCHES onSearchInput into its OWN live search
 * (dms/static/src/js/views/file_explorer_search_bar.esm.js, gated on
 * `searchModel.isFileExplorer`). Live mode stands down there, so the explorer's
 * storage-wide search keeps working. It still gets the two pickers and loses the
 * caret, like every other view. Asset order between the two modules is not
 * guaranteed (neither depends on the other). Each patch calls super when it is
 * not its case, so either order works.
 *
 * x2many "Add a line" dialogs (SelectCreateDialog) render a stock list or
 * kanban controller, so they get the same bar through the same patch. That is
 * deliberate: picking a record in a dialog is where a beginner most needs
 * type-to-filter. Favourites there come from the dialog's loadIrFilters, as stock.
 */
import { onMounted, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { useDebounced } from "@web/core/utils/timing";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { FacetOverflowList } from "./search_facet_overflow";
import { SearchPicker } from "./search_picker";

/** Debounce of the live search, in ms. 250–300 is the brief's band. */
const LIVE_DELAY = 280;
/**
 * Width reserved for the "+N" chip when deciding what fits ("+99" fits).
 * ⚠ A constant, NOT the rendered chip's width: when nothing fits the chip
 * reads "5 filters", and measuring THAT made the fit keep reserving the wide
 * label after the box grew. A fresh load and a resize must agree.
 */
const MORE_CHIP_RESERVE = 40;

patch(SearchBar, {
    components: { ...SearchBar.components, SearchPicker },
});

patch(SearchBar.prototype, {
    setup() {
        super.setup(...arguments);
        const sm = this.env.searchModel;
        const liveFieldIds = sm.isFileExplorer ? [] : sm.getLiveSearchFieldIds();
        const fieldNames = liveFieldIds.map((id) => sm.searchItems[id].description);
        this.simpleSearch = {
            live: liveFieldIds.length > 0,
            title: fieldNames.length ? _t("Searches in: %s", fieldNames.join(", ")) : "",
            showFilter: sm.searchMenuTypes.has("filter") || sm.searchMenuTypes.has("favorite"),
            showGroupBy: sm.searchMenuTypes.has("groupBy"),
        };
        // --- One-line chips with "+N" (QA round 3) -----------------------
        // ⚠ From lg up the box is one line high (search.scss). Chips keep their
        // natural width; this decides how many fit and moves the rest out of
        // the flow (data-m-overflow), reachable through the "+N" chip. It runs
        // after EVERY render (facets added/removed, live term typed) and on
        // resize. Setting the same count does not re-render, so it settles in
        // one extra pass at most.
        this.mFacetFit = useState({ visible: Infinity });
        useEffect(() => this.mFitFacets());
        const resizeObserver = new ResizeObserver(() => this.mFitFacets());
        onMounted(() => {
            if (this.facetContainerRef.el) {
                resizeObserver.observe(this.facetContainerRef.el);
            }
        });
        onWillUnmount(() => resizeObserver.disconnect());
        this.mMorePopover = usePopover(FacetOverflowList, {
            position: "bottom-start",
            popoverClass: "m-facet-more-popover",
        });

        // A query rolled back after a failed load (search_model_patch.js)
        // comes with no `update`, so the chips, and the input in live mode,
        // re-render here. Every mode: a failed load after adding a chip
        // disagrees with the list just as much.
        useBus(sm, "m-query-restored", () => {
            if (this.simpleSearch.live) {
                this.syncLiveInput();
            }
            this.render();
        });
        if (!this.simpleSearch.live) {
            return;
        }
        this.livePending = false;
        this.applyLiveDebounced = useDebounced(this.applyLiveSearch, LIVE_DELAY);
        // Breadcrumb back-navigation restores the model with the term in it.
        // The input must show it again.
        onMounted(() => this.syncLiveInput());
        // ...and so must every outside change: "Clear filters", a favourite
        // (it replaces the whole query), the model being reloaded.
        useBus(sm, "update", () => this.syncLiveInput());
    },

    // --- One-line chips with "+N" ------------------------------------------

    get mOverflowCount() {
        const total = this.env.searchModel.facets.length;
        const visible = this.mFacetFit.visible;
        return visible < total ? total - visible : 0;
    },

    /**
     * "+N" next to visible chips. When NO chip fits (the narrowest control
     * panels, e.g. Contacts at 1000px, where the pager and three view switches
     * leave the box at its floor), a bare "+3" would read as nothing; the chip
     * then names what it holds: "3 filters". Its popover lists them in full.
     */
    get mOverflowLabel() {
        const count = this.mOverflowCount;
        if (this.mFacetFit.visible > 0) {
            return `+${count}`;
        }
        return count === 1 ? _t("1 filter") : _t("%s filters", count);
    },

    get mOverflowTitle() {
        return _t("Show all active filters");
    },

    onFacetMoreClick(ev) {
        if (this.mMorePopover.isOpen) {
            this.mMorePopover.close();
            return;
        }
        this.mMorePopover.open(ev.currentTarget, {
            searchModel: this.env.searchModel,
            remove: (facet) => this.removeFacet(facet),
        });
    },

    mFitFacets() {
        const container = this.facetContainerRef.el;
        if (!container) {
            return;
        }
        // Stacked layouts (below lg) wrap as stock: nothing to fit.
        if (window.matchMedia("(max-width: 991.98px)").matches) {
            this.mFacetFit.visible = Infinity;
            return;
        }
        const facets = [...container.querySelectorAll(":scope > .o_searchview_facet")];
        const gap = parseFloat(window.getComputedStyle(container).columnGap) || 0;
        const input = container.querySelector(".o_searchview_input");
        const clear = container.querySelector(".m-search-clear");
        const inputMin = input ? parseFloat(window.getComputedStyle(input).minWidth) || 0 : 0;
        const fixed = inputMin + (clear ? clear.offsetWidth + gap : 0);
        const moreWidth = MORE_CHIP_RESERVE + gap;
        const available = container.clientWidth - fixed;
        let used = 0;
        let visible = 0;
        for (const [index, facet] of facets.entries()) {
            // Counted at its CSS floor (search.scss): the chips shown share
            // the space by shrinking, never below it.
            const floor = parseFloat(window.getComputedStyle(facet).minWidth) || 0;
            const width = (floor || facet.getBoundingClientRect().width) + gap;
            const isLast = index === facets.length - 1;
            // Room for this chip, plus the "+N" chip if more would follow.
            if (used + width + (isLast ? 0 : moreWidth) > available) {
                break;
            }
            used += width;
            visible++;
        }
        this.mFacetFit.visible = visible === facets.length ? Infinity : visible;
    },

    // --- Live search -------------------------------------------------------

    applyLiveSearch() {
        this.livePending = false;
        this.env.searchModel.setLiveSearch(this.inputRef.el?.value || "");
    },

    /** Apply a pending keystroke now. @returns {boolean} whether one was pending */
    flushLiveSearch() {
        const wasPending = this.livePending;
        this.applyLiveDebounced.cancel();
        this.applyLiveSearch();
        return wasPending;
    },

    syncLiveInput() {
        const input = this.inputRef.el;
        // Never overwrite what the user is in the middle of typing.
        if (!input || this.livePending) {
            return;
        }
        const term = this.env.searchModel.liveSearchTerm;
        if (input.value.trim() !== term) {
            input.value = term;
        }
        this.state.query = input.value;
    },

    onSimpleSearchClear() {
        this.inputRef.el.value = "";
        this.state.query = "";
        this.flushLiveSearch();
        this.inputRef.el.focus();
    },

    onSimpleSearchKeydown(ev) {
        if (ev.key === "Enter" && !ev.isComposing && this.flushLiveSearch()) {
            // The flush already reloads; the stock Enter hotkey would reload again.
            ev.stopPropagation();
            ev.preventDefault();
        }
    },

    // --- Stock handlers, rerouted in live mode -------------------------------

    onSearchInput(ev) {
        if (!this.simpleSearch.live) {
            return super.onSearchInput(...arguments);
        }
        // Kept in sync because the stock arrow-key facet navigation compares
        // the caret position with state.query.length.
        this.state.query = ev.target.value;
        if (ev.isComposing) {
            return; // IME: wait for compositionend
        }
        if (!ev.target.value.trim()) {
            // Emptying the box restores the full list at once. Waiting for the
            // debounce feels like lag on the one action that should not.
            this.flushLiveSearch();
            return;
        }
        this.livePending = true;
        this.applyLiveDebounced();
    },

    onCompositionEnd(ev) {
        if (!this.simpleSearch.live) {
            return super.onCompositionEnd(...arguments);
        }
        this.state.query = ev.target.value;
        this.livePending = true;
        this.applyLiveDebounced();
    },

    onSearchClick() {
        // Stock: an empty input opens the big panel, which no longer exists,
        // and a non-empty one reopens the autocomplete (fallback mode only).
        if (!this.simpleSearch.live) {
            return super.onSearchClick(...arguments);
        }
    },

    onClickSearchIcon() {
        if (!this.simpleSearch.live) {
            return super.onClickSearchIcon(...arguments);
        }
        if (!this.flushLiveSearch()) {
            this.env.searchModel.search();
        }
    },

    resetState(options = { focus: true }) {
        if (!this.simpleSearch.live) {
            return super.resetState(...arguments);
        }
        // Stock resetState() empties the input. In live mode the input IS the
        // search term, so only keep the focus behaviour.
        if (options.focus) {
            this.inputRef.el?.focus();
        }
    },

    // --- Customisation removed ---------------------------------------------

    async computeState() {
        await super.computeState(...arguments);
        // Fallback autocomplete: drop the "Add a custom filter" line.
        const index = this.items.findIndex((item) => item.isAddCustomFilterButton);
        if (index >= 0) {
            this.items.splice(index, 1);
        }
    },

    onFacetLabelClick(target, facet) {
        // Keep the group-by count-sort switch. Never open the domain editor.
        if (this.env.searchModel.canOrderByCount && facet.type === "groupBy") {
            return super.onFacetLabelClick(...arguments);
        }
    },
});
