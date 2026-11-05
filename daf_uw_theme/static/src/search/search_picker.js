/**
 * The "Filter…" and "Group by…" inputs of the simplified search bar.
 *
 * Each one is a small typeahead over the options the stock Filters / Group By
 * panel (web.SearchBarMenu) would list. The user types a keyword, sees only the
 * matching options, and picks one. That replaces the stock panel, which shows
 * every filter, every group-by and every favourite at once, behind a caret.
 *
 * ⚠ APPLYING AN OPTION CALLS EXACTLY WHAT THE STOCK PANEL CALLS
 * (search_bar_menu.js::onFilterSelected / onGroupBySelected): toggleSearchItem,
 * toggleDateFilter and toggleDateGroupBy. So the semantics stay
 * native and are not re-implemented. Filters in the same <separator> group are
 * OR-ed, groups are AND-ed, a favourite replaces the whole query, and group-bys
 * stack in the order they were picked. Picking an option that is already active
 * toggles it off, as the stock checkbox does. The ✓ in the list shows which
 * options are active.
 *
 * What each picker lists:
 *   Filter    the view's <filter>s (not group-bys); date filters with their
 *             default period, plus each period ("Order date: March") once the
 *             user is typing; then the saved favourites, applied only, never
 *             edited (see the bar's header).
 *   Group by  the view's group-by <filter>s; date group-bys with their default
 *             interval, plus each interval once typing. NOTHING ELSE: grouping
 *             by an arbitrary field (stock "Add Custom Group", i.e.
 *             createNewGroupBy) is customisation, and the owner disabled it
 *             (QA, spec item 4). Do not add it back as a typeahead section.
 * Options that only appear while typing are the ones that would flood the list
 * if shown on focus. An empty input lists only the short, curated part.
 *
 * Built on web's AutoComplete rather than a hand-rolled dropdown. It already
 * does keyboard navigation (↑ ↓ Enter Esc), positioning, outside-click closing
 * and the "skip unselectable rows" logic that the section headers rely on.
 * `resetOnSelect` empties the input after a pick. The result is the facet chip.
 *
 * Matching: every whitespace-separated word of the query must appear in the
 * label, case- and accent-insensitively. "echeance" finds "Échéance" and
 * "date mars" finds "Date de commande : mars".
 */
import { Component } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { FACET_ICONS } from "@web/search/utils/misc";

/**
 * Items the stock panel never applies directly. A "properties" item only
 * opens a sub-menu of property definitions (PropertiesGroupByItem); toggling
 * it as such groups by a property named None and the server raises
 * ("Wrong property field value name 'None'", QA round 2). Their children are
 * `isProperty` items, which are excluded too: picking a property is a
 * sub-choice this flat typeahead does not offer.
 */
function isDirectlyApplicable(item) {
    return item.fieldType !== "properties" && !item.isProperty && !item.isInvalid;
}

function normalize(str) {
    return (str || "")
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase();
}

function makeMatcher(term) {
    const words = normalize(term).split(/\s+/).filter(Boolean);
    return (label) => {
        const haystack = normalize(label);
        return words.every((word) => haystack.includes(word));
    };
}

export class SearchPicker extends Component {
    static template = "daf_uw_theme.SearchPicker";
    static components = { AutoComplete };
    static props = {
        kind: { type: String, validate: (kind) => ["filter", "groupBy"].includes(kind) },
    };

    setup() {
        this.isFilter = this.props.kind === "filter";
        this.icon = this.isFilter ? FACET_ICONS.filter : FACET_ICONS.groupBy;
        this.placeholder = this.isFilter ? _t("Filter…") : _t("Group by…");
        this.sources = [
            { options: (term) => this.getOptions(term), optionSlot: "option" },
        ];
    }

    /**
     * ⚠ AutoComplete opens its list on input CLICK, not focus. Between lg and
     * xl the folded picker's input jumps below its slot as soon as it is
     * focused (search.scss), i.e. on mousedown, so the mouseup lands elsewhere
     * and no click ever reaches it. In exactly that case (a press ON the input
     * while the picker is folded) the list is opened with a click of our own
     * once the real click had its chance.
     *
     * Narrow on purpose: focus also comes back to the input after an option is
     * picked (the option's pointerdown), and reopening there would pop the
     * list straight back up. Keyboard focus is left alone too: typing opens it.
     */
    onPointerDown(ev) {
        this.pressedInput = ev.target.matches("input");
    }

    onFocus(ev) {
        const input = ev.target;
        const folded = input.closest(".m-search-picker")?.offsetWidth < 60;
        if (!this.pressedInput || !folded) {
            return;
        }
        this.pressedInput = false;
        browser.setTimeout(() => {
            if (document.activeElement === input && input.getAttribute("aria-expanded") !== "true") {
                input.click();
            }
        }, 150);
    }

    get searchModel() {
        return this.env.searchModel;
    }

    /**
     * @param {string} term the trimmed input value
     * @returns {Object[]} AutoComplete options. An option without `onSelect`
     *      is unselectable: section headers and the "no match" row.
     */
    getOptions(term) {
        const match = makeMatcher(term);
        const typing = Boolean(term);
        const options = this.isFilter
            ? this.getFilterOptions(match, typing)
            : this.getGroupByOptions(match, typing);
        if (!options.some((option) => option.onSelect)) {
            return [
                {
                    label: this.isFilter ? _t("No matching filter") : _t("No matching grouping"),
                    cssClass: "m-search-picker-empty",
                },
            ];
        }
        return options;
    }

    getFilterOptions(match, typing) {
        const sm = this.searchModel;
        const items = sm.searchMenuTypes.has("filter")
            ? sm.getSearchItems(
                  (item) =>
                      ["filter", "dateFilter"].includes(item.type) && isDirectlyApplicable(item)
              )
            : [];
        const options = this.optionsForItems(items, match, typing, {
            toggle: (item) => sm.toggleSearchItem(item.id),
            toggleDate: (item) => sm.toggleDateFilter(item.id),
            toggleDateOption: (item, option) => sm.toggleDateFilter(item.id, option.id),
        });
        if (sm.searchMenuTypes.has("favorite")) {
            const favorites = sm
                .getSearchItems((item) => item.type === "favorite" && !item.isInvalid)
                .filter((item) => match(item.description))
                .map((item) =>
                    this.makeOption(item.description, item.isActive, () =>
                        sm.toggleSearchItem(item.id)
                    )
                );
            if (favorites.length) {
                options.push(this.makeHeader(_t("Favorites"), FACET_ICONS.favorite), ...favorites);
            }
        }
        return options;
    }

    getGroupByOptions(match, typing) {
        const sm = this.searchModel;
        const items = sm.getSearchItems(
            (item) => ["groupBy", "dateGroupBy"].includes(item.type) && isDirectlyApplicable(item)
        );
        return this.optionsForItems(items, match, typing, {
            toggle: (item) => sm.toggleSearchItem(item.id),
            toggleDate: (item) => sm.toggleDateGroupBy(item.id),
            toggleDateOption: (item, option) => sm.toggleDateGroupBy(item.id, option.id),
        });
    }

    /**
     * The shared part of both pickers: plain items toggle, and date items get
     * a default entry plus, while typing, one entry per period or interval.
     * A thin rule separates <separator> groups, as the stock dropdown does.
     */
    optionsForItems(items, match, typing, { toggle, toggleDate, toggleDateOption }) {
        const sm = this.searchModel;
        const options = [];
        let previousGroup = null;
        for (const item of items) {
            const itemOptions = [];
            if (match(item.description)) {
                if (item.options) {
                    // Active date item: picking it again clears ALL its
                    // periods/intervals. Toggling only the defaults would
                    // leave the user's other picks behind.
                    itemOptions.push(
                        this.makeOption(item.description, item.isActive, () =>
                            item.isActive ? sm.clearSearchItem(item.id) : toggleDate(item)
                        )
                    );
                } else {
                    itemOptions.push(
                        this.makeOption(item.description, item.isActive, () => toggle(item))
                    );
                }
            }
            if (item.options && typing) {
                for (const option of item.options) {
                    const label = `${item.description}: ${option.description}`;
                    if (match(label)) {
                        const onSelect = () => toggleDateOption(item, option);
                        itemOptions.push(this.makeOption(label, option.isActive, onSelect));
                    }
                }
            }
            if (!itemOptions.length) {
                continue;
            }
            if (previousGroup !== null && previousGroup !== item.groupNumber) {
                itemOptions[0].cssClass += " m-search-picker-sep";
            }
            previousGroup = item.groupNumber;
            options.push(...itemOptions);
        }
        return options;
    }

    makeOption(label, isActive, onSelect) {
        return { label, onSelect, cssClass: "", data: { isActive } };
    }

    makeHeader(label, icon = "") {
        return { label, cssClass: "m-search-picker-header", data: { isHeader: true, icon } };
    }
}
