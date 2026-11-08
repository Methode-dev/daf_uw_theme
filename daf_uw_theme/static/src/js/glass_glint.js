/**
 * Liquid glass: the glint — a highlight that follows the pointer across a glass
 * control while it is hovered.
 *
 * This file only MEASURES: it writes the pointer position, relative to the
 * hovered glass element, into two custom properties on that element
 * (--m-px / --m-py).  Every visual decision is in the stylesheets, through
 * --m-glass-glint (css_tokens.scss), which they layer in on :hover.  Without
 * this script the glint still renders, centred above the element.
 *
 * One delegated, passive listener for the whole client, coalesced to one write
 * per animation frame; no component patches, nothing to wire per view.
 *
 * Skipped entirely for touch / pen (no hover there) and under
 * prefers-reduced-motion (a light that chases the cursor is motion).
 */
import { browser } from "@web/core/browser/browser";

// Keep in sync with the stylesheets that use --m-glass-glint on :hover.
const GLASS_SELECTOR = [
    ".btn-primary",
    ".btn-secondary",
    ".btn-info",
    ".btn-accent",
    ".o_kanban_record",
    ".m-nav-search",
    ".mk_apps_sidebar_menu > li > a",
    ".o_notebook .nav-link",
    ".o_statusbar_status .o_arrow_button",
    ".o_daf_kpi",
    ".o_daf_chip",
    ".o_daf_button",
    ".o_daf_panel",
    ".o_daf_recent",
    ".m-dash-card",
    ".m-dash-stat",
    ".m-dash-shortcut",
    // Form groups and x2many lists (views/form_view.scss).
    ".o_form_view .o_inner_group",
    ".o_form_view .o_field_x2many .o_list_renderer",
    // Bento boxes (views/form_bento.scss).
    ".o_form_view .o_daf_box",
].join(",");

let pending = null;
let frame = 0;

function flush() {
    frame = 0;
    if (!pending) {
        return;
    }
    const { el, x, y } = pending;
    pending = null;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--m-px", `${Math.round(x - rect.left)}px`);
    el.style.setProperty("--m-py", `${Math.round(y - rect.top)}px`);
}

function onPointerMove(ev) {
    if (ev.pointerType !== "mouse") {
        return;
    }
    const el = ev.target instanceof Element ? ev.target.closest(GLASS_SELECTOR) : null;
    if (!el) {
        return;
    }
    pending = { el, x: ev.clientX, y: ev.clientY };
    if (!frame) {
        frame = browser.requestAnimationFrame(flush);
    }
}

const reducedMotion = browser.matchMedia?.("(prefers-reduced-motion: reduce)");
if (!reducedMotion?.matches) {
    browser.addEventListener("pointermove", onPointerMove, { passive: true });
}
