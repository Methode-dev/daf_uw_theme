/**
 * Boot loader teardown (THEME_PLAN §13.5, P8e)
 *
 * views/boot_loader_templates.xml puts the Méthode mark in the body server-side,
 * so it paints before any JavaScript runs.  Nothing in that markup knows when the
 * wait is over, so this removes it once the webclient is actually mounted.
 *
 * ⚠ Removal is JS rather than a CSS state, and the node is DELETED rather than
 * hidden.  The mark is nineteen shapes on infinite animations; leaving it in the
 * DOM behind `display: none` would keep the whole set alive for the session.
 *
 * The signal is a main_components entry rather than a timer or a DOMContentLoaded
 * hook: those fire on a schedule that has nothing to do with whether the app is
 * ready, which is the one thing the loader is waiting for.  main_components are
 * rendered by the WebClient itself, so this onMounted IS "the webclient exists".
 */

import { registry } from "@web/core/registry";
import { Component, onMounted, xml } from "@odoo/owl";

/** Fade the boot loader out, then drop it. */
function removeBootLoader() {
    const el = document.getElementById("m-boot-loader");
    if (!el) {
        // Already gone, or we are on a page that never rendered one.
        return;
    }
    el.classList.add("m-boot-loader__done");

    // Whichever lands first wins; remove() on a detached node is a no-op, so the
    // double call is safe.  The timeout is not belt-and-braces — `transitionend`
    // genuinely never fires if the element is display:none'd by something else,
    // or if the opacity transition is optimised away.
    const drop = () => el.remove();
    el.addEventListener("transitionend", drop, { once: true });
    setTimeout(drop, 600);
}

class BootLoaderTeardown extends Component {
    // Renders nothing.  It exists only for its mount timing.
    static template = xml`<t/>`;
    static props = {};

    setup() {
        onMounted(removeBootLoader);
    }
}

registry.category("main_components").add("MethodeBootLoaderTeardown", {
    Component: BootLoaderTeardown,
});
