/**
 * The "+N" popover of the simplified search bar: EVERY active facet, with its
 * full label and its own ×.
 *
 * From lg up the search box is one line high and chips never shrink below a
 * readable width (search.scss); the chips that do not fit are hidden by
 * search_bar_patch.js::mFitFacets and counted on the "+N" chip, which opens
 * this. It lists all facets, not only the hidden ones: one place to see the
 * whole search is what a beginner needs, and it avoids a list whose content
 * depends on the window width.
 *
 * ⚠ A POPOVER, NOT A Dropdown. The facets live inside the bar's own input
 * Dropdown (the stock autocomplete wraps the facet container), so a Dropdown
 * here became a nested sub-menu item: full-width `dropdown-item`, caret,
 * hover-open. A popover is rendered in the overlay container, outside that
 * tree. It is handed the search model and re-renders on its `update`, so a
 * removal shows at once; it closes itself when no facet is left.
 */
import { Component } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class FacetOverflowList extends Component {
    static template = "daf_uw_theme.FacetOverflowList";
    static props = {
        searchModel: Object,
        remove: Function,
        close: Function,
    };

    setup() {
        useBus(this.props.searchModel, "update", () => {
            if (!this.props.searchModel.facets.length) {
                this.props.close();
            } else {
                this.render();
            }
        });
    }

    get facets() {
        return this.props.searchModel.facets;
    }

    label(facet) {
        const values = facet.values.join(` ${facet.separator} `);
        return facet.title ? `${facet.title}: ${values}` : values;
    }
}
