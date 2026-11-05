/**
 * Simplified search — the model half: live search and two small helpers.
 *
 * The search bar (search_bar_patch.js) filters the view AS THE USER TYPES. This
 * file holds the model-side state for that. It is a patch on SearchModel, so it
 * works for every model built from it: list, kanban, pivot, graph, calendar,
 * activity, the x2many "Add a line" dialog, and the DMS file explorer's subclass,
 * although the explorer opts out (see the bar's header).
 *
 * HOW THE LIVE TERM IS STORED
 * It is ONE ordinary query element `{searchItemId, autocompleteValue}` in
 * `this.query`. Odoo's own autocomplete stores a picked "Search Name for: foo"
 * line in exactly this shape. It points at a search item of type "field" that is
 * created lazily on the first keystroke and flagged `isLiveSearch`. Nothing else
 * reads that flag. Because the term is ordinary query state, it gets everything
 * for free: the domain, the search panel's counters (_reloadSections),
 * exportState/importState on breadcrumb back-navigation, and the AND with every
 * other facet.
 *
 * ⚠ THE LIVE ITEM IS ITS OWN SEARCH ITEM AND ITS OWN GROUP. It is NOT the
 * view's first <field> item. The values of one field item are OR-ed together, so
 * reusing the `name` item would silently OR the live term with a
 * `search_default_name` that a menu action pre-set. A separate group keeps the
 * native rule that facets are AND-ed.
 *
 * ⚠ WHICH FIELDS ARE SEARCHED. The live domain is an OR over up to
 * LIVE_MAX_FIELDS of the search view's own visible <field> entries:
 *   * the first one whose type is text-like (char/text/html, or relational,
 *     which matches on display name). This is exactly the field Odoo's first
 *     "Search X for: …" line targets, filter_domain included. Most views make
 *     that line already OR name/ref/email;
 *   * then the next plain char/text/html ones (email, phone, ref…). Relational
 *     fields after the first are skipped on purpose: an ilike on partner_id or
 *     user_id makes "a" match every record and costs a name_search join each.
 * Each field contributes the domain Odoo would build for it (_getFieldDomain:
 * its filter_domain if it has one, else `field ilike term` or its own
 * `operator=`). The view author's search semantics are reused, not reinvented.
 * The ids are frozen into the item when it is created, so they survive
 * exportState with it.
 *
 * ⚠ The live facet is HIDDEN from `facets`. The term stays visible as text in
 * the search input, and a chip that re-renders at every debounce tick would
 * shift the input sideways while the user types. It is filtered here, in the
 * getter, rather than in the template, so the facet list and its indexes stay
 * consistent for every reader: the bar's backspace/arrow navigation indexes
 * `searchModel.facets` directly, and clearFilters() iterates it.
 *
 * ⚠ ROLLBACK AFTER A FAILED LOAD. The search model updates its query BEFORE
 * the view loads, so when that load fails (server error, abort) the list keeps
 * showing the last good rows (Dev A's list/list_loading.js restores them) while
 * the query, and so the search box and the chips, describe the request that
 * failed: "Lyon" over unfiltered rows. Two halves, both here:
 *   * CONFIRM: RelationalModel.load() is patched to record, on SUCCESS, the
 *     query it was started with (snapshot taken when the load starts, because
 *     the user may have typed again by the time it resolves). load() is the
 *     search-driven entry point; sort and pager reloads go through _loadData
 *     only, so they never "confirm" anything, and a failure of one of those
 *     finds the query already equal to the confirmed one and changes nothing.
 *     Superseded loads (KeepLast) never resolve, so they never confirm either.
 *   * RESTORE: on Dev A's `m-root-load-failed` bus event, the query goes back
 *     to the last confirmed one and `m-query-restored` is triggered. NOT
 *     `update`: `update` makes the view reload, and the point is to describe
 *     what is already on screen, not to search again. The bar listens to
 *     `m-query-restored` to re-render its chips and its input.
 * This restores the WHOLE query, chips included: a failed load after adding
 * a filter has the same disagreement as one after typing.
 */
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { deepCopy } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { SearchModel } from "@web/search/search_model";

/** Can be the FIRST live field: anything that matches on text. */
const LIVE_PRIMARY_TYPES = ["char", "text", "html", "many2one", "many2many", "one2many"];
/** Can be an ADDITIONAL live field: plain text columns only (see header). */
const LIVE_EXTRA_TYPES = ["char", "text", "html"];
const LIVE_MAX_FIELDS = 4;

patch(SearchModel.prototype, {
    setup() {
        super.setup(...arguments);
        this.mConfirmedQuery = null;
        this.addEventListener("m-root-load-failed", () => this.mRestoreConfirmedQuery());
    },

    // --- Rollback after a failed load (see the header) -----------------------

    /** @param {Object[]} query the query a SUCCESSFUL load was started with */
    mConfirmQuery(query) {
        this.mConfirmedQuery = query;
    },

    /** @returns {boolean} whether the query changed */
    mRestoreConfirmedQuery() {
        const confirmed = this.mConfirmedQuery;
        if (!confirmed || JSON.stringify(confirmed) === JSON.stringify(this.query)) {
            return false;
        }
        this.query = deepCopy(confirmed);
        this._checkOrderByCountStatus();
        this._reset();
        this.trigger("m-query-restored");
        return true;
    },

    // --- Live search -------------------------------------------------------

    /** The flagged live item, if a keystroke has created one already. */
    get liveSearchItem() {
        return Object.values(this.searchItems).find((item) => item.isLiveSearch) || null;
    },

    /** The term currently applied by the live search ("" when none). */
    get liveSearchTerm() {
        const item = this.liveSearchItem;
        const elem = item && this.query.find((q) => q.searchItemId === item.id);
        return elem ? elem.autocompleteValue.label : "";
    },

    /**
     * The ids of the <field> search items a live term is matched against, or
     * [] when the view has no text-like field. In that case the bar falls back
     * to the stock autocomplete. Once the live item exists, its frozen list is
     * returned.
     * @returns {number[]}
     */
    getLiveSearchFieldIds() {
        if (this.liveSearchItem) {
            return this.liveSearchItem.liveFieldIds;
        }
        const typeOf = (item) => this.searchViewFields[item.fieldName]?.type;
        const fieldItems = this.getSearchItems((item) => item.type === "field");
        const primary = fieldItems.find((item) => LIVE_PRIMARY_TYPES.includes(typeOf(item)));
        if (!primary) {
            return [];
        }
        const ids = [primary.id];
        for (const item of fieldItems) {
            if (ids.length >= LIVE_MAX_FIELDS) {
                break;
            }
            if (item.id !== primary.id && LIVE_EXTRA_TYPES.includes(typeOf(item))) {
                ids.push(item.id);
            }
        }
        return ids;
    },

    /**
     * Replace the live term. An empty or blank term removes it. A no-op (no
     * reload) when the trimmed term did not change: trailing spaces and the
     * Enter key both hit this.
     * @param {string} term
     */
    setLiveSearch(term) {
        const trimmed = (term || "").trim();
        if (trimmed === this.liveSearchTerm) {
            return;
        }
        let item = this.liveSearchItem;
        if (!item) {
            if (!trimmed) {
                return;
            }
            const liveFieldIds = this.getLiveSearchFieldIds();
            if (!liveFieldIds.length) {
                return;
            }
            const primary = this.searchItems[liveFieldIds[0]];
            item = {
                id: this.nextId,
                groupId: this.nextGroupId,
                groupNumber: this.nextGroupNumber,
                type: "field",
                fieldName: primary.fieldName,
                fieldType: primary.fieldType,
                description: _t("Search"),
                // Keeps it out of getSearchItems(), so it is out of the bar's
                // autocomplete list and of the Filter/Group by pickers.
                invisible: "True",
                isLiveSearch: true,
                liveFieldIds,
            };
            this.searchItems[item.id] = item;
            this.nextId++;
            this.nextGroupId++;
            this.nextGroupNumber++;
        }
        this.query = this.query.filter((q) => q.searchItemId !== item.id);
        if (trimmed) {
            this.query.push({
                searchItemId: item.id,
                autocompleteValue: { label: trimmed, value: trimmed, operator: "ilike" },
            });
        }
        this._notify();
    },

    /**
     * Remove every query element of ONE search item: all the periods of a
     * date filter, or all the intervals of a date group-by. Not
     * deactivateGroup(): that would also drop the item's siblings in the same
     * <separator> group, e.g. "My orders" next to "Order date".
     * @param {number} searchItemId
     */
    clearSearchItem(searchItemId) {
        this.query = this.query.filter((q) => q.searchItemId !== searchItemId);
        this._checkOrderByCountStatus();
        this._notify();
    },

    // --- Overrides ---------------------------------------------------------

    get facets() {
        const item = this.liveSearchItem;
        const facets = super.facets;
        return item ? facets.filter((facet) => facet.groupId !== item.groupId) : facets;
    },

    /** "Clear filters" also clears the live term, though its facet is hidden. */
    clearFilters() {
        const item = this.liveSearchItem;
        if (item) {
            this.query = this.query.filter((q) => q.searchItemId !== item.id);
        }
        return super.clearFilters(...arguments);
    },

    _getSearchItemDomain(activeItem) {
        const searchItem = this.searchItems[activeItem.searchItemId];
        if (!searchItem.isLiveSearch) {
            return super._getSearchItemDomain(...arguments);
        }
        const domains = [];
        for (const fieldItemId of searchItem.liveFieldIds) {
            const fieldItem = this.searchItems[fieldItemId];
            if (!fieldItem) {
                continue;
            }
            // Same value objects for every field. Only the operator is the
            // field's own (an `operator="="` barcode field stays exact).
            const values = activeItem.autocompleteValues.map(({ label, value }) => ({
                label,
                value,
                operator: fieldItem.operator || "ilike",
            }));
            domains.push(this._getFieldDomain(fieldItem, values));
        }
        return domains.length ? Domain.or(domains) : null;
    },
});

patch(RelationalModel.prototype, {
    async load() {
        const searchModel = this.env?.searchModel;
        const query = searchModel?.query ? deepCopy(searchModel.query) : null;
        const result = await super.load(...arguments);
        if (query) {
            searchModel.mConfirmQuery?.(query);
        }
        return result;
    },
});
