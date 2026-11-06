/**
 * Loading snackbar timing (THEME_PLAN §13.5, P8e)
 *
 * Odoo waits 250ms of pending RPC before showing its loading indicator
 * (web/…/loading_indicator.js, `requestCall`).  Owner-reported as too slow once
 * the indicator became a snackbar worth looking at, so the threshold drops here.
 *
 * ⚠ THIS REIMPLEMENTS AN UPSTREAM METHOD, WHICH IS A MAINTENANCE COST — take it
 * seriously on upgrade.  The 250 is a bare literal inside `requestCall`, with no
 * option, prop or variable in front of it, so there is no seam to override; the
 * whole method has to be restated to change one number.  The body below is
 * upstream's, unchanged apart from the delay.  If a future Odoo changes what
 * `requestCall` does, this silently keeps doing the old thing — diff it.
 *
 * The patch is safe against `useBus`: hooks.js:91 binds `this.requestCall` at
 * setup() time, which runs long after module-level asset JS, so the component
 * picks up the patched prototype method rather than the original.
 */

import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";

/**
 * Milliseconds of pending RPC before the snackbar appears.  Upstream is 250.
 *
 * Not lower than this on purpose: the snackbar has a 400ms leave transition, so
 * at very short thresholds a fast action shows it for a few frames and then
 * spends longer fading than it did being useful.  150 is about where a load
 * stops feeling instant, which is the thing worth reporting.
 */
const SHOW_DELAY = 150;

patch(LoadingIndicator.prototype, {
    requestCall({ detail }) {
        if (detail.settings.silent) {
            return;
        }
        if (this.state.count === 0) {
            browser.clearTimeout(this.startShowTimer);
            this.startShowTimer = browser.setTimeout(() => {
                if (this.state.count) {
                    this.state.show = true;
                }
            }, SHOW_DELAY);
        }
        this.rpcIds.add(detail.data.id);
        this.state.count++;
    },
});
