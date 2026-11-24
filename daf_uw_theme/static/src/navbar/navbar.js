/**
 * Two-row navbar (§5.4). The split itself is in navbar.xml; this file adds the
 * search control and the company fallback the app row needs when no app is open.
 */

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

export class NavBarSearch extends Component {
    static template = "daf_uw_theme.NavBarSearch";
    static props = {};

    setup() {
        this.command = useService("command");
        this.hotkey = isMacOS() ? "⌘K" : "Ctrl K";
        this.title = _t("Search (%s)", this.hotkey);
    }

    open() {
        this.command.openMainPalette();
    }
}

patch(NavBar, {
    components: { ...NavBar.components, NavBarSearch },
});

patch(NavBar.prototype, {
    /**
     * Liquid glass: the page scrolls UNDER the navbar (navbar.scss, "Content
     * under the bar").  The action area now starts at the top of the window
     * and pads its page down by the navbar's height, so this publishes that
     * height as --m-navbar-h on <html>.  Measured, not hard-coded: the app row
     * collapses on small screens (navbar.scss), the banner row can appear, and
     * the font can change the rows' heights.
     */
    setup() {
        super.setup(...arguments);
        let observer = null;
        const publish = (el) => {
            const height = Math.ceil(el.getBoundingClientRect().height);
            document.documentElement.style.setProperty("--m-navbar-h", `${height}px`);
        };
        onMounted(() => {
            const el = document.querySelector(".o_web_client > .o_navbar");
            if (!el) {
                return;
            }
            publish(el);
            observer = new ResizeObserver(() => publish(el));
            observer.observe(el);
        });
        onWillUnmount(() => {
            observer?.disconnect();
            document.documentElement.style.removeProperty("--m-navbar-h");
        });
    },

    get companyName() {
        return user.activeCompany?.name || "";
    },
});
