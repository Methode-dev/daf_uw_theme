/**
 * Page transitions between actions: every time the action manager swaps the
 * screen (open a record, breadcrumb back, menu click, app switch, a
 * `doAction` redirect such as pricelist save -> price sheet), the old page
 * leaves and the new one arrives, instead of a hard cut.  Styles in
 * action_transition.scss.
 *
 * WHY A GHOST.  web.ActionContainer (Odoo 19, action_container.js) renders ONE
 * child keyed on `info.id`; on ACTION_MANAGER:UPDATE it re-renders and OWL
 * replaces the old controller's DOM with the new one in a single patch.  There
 * is no moment where both exist, so nothing can animate out.  So, right before
 * the patch (onWillPatch) the old page is CLONED, and right after it
 * (onPatched, same frame, nothing painted in between) the clone is laid UNDER
 * the new page and animated away while the new page dissolves in on top.  The clone is
 * inert, aria-hidden and has no ids/names: it is a picture, not a page.
 *
 * DIRECTION, from breadcrumb depth (controller stack committed in the new
 * controller's onMounted, which OWL runs before the container's onPatched):
 *   deeper            -> "forward"  (old slides left, new comes from the right)
 *   shallower         -> "back"     (mirrored)
 *   same depth / root -> "switch"   (old sinks and frosts, new rises)
 *
 * THE BLANK SCREEN.  A menu or app click is `clearBreadcrumbs`, and core then
 * mounts an empty BlankComponent and waits for it before loading the new
 * action (action_service.js, "noEmptyTransition").  That empty frame was the
 * harshest part of switching.  When the incoming component is that blank, the
 * ghost is HELD instead: the old page stays on screen, dimmed and slightly
 * frosted ("working on it"), the blank is hidden, and the real page takes over
 * from the held ghost when it arrives.  A safety timeout releases a ghost held
 * for too long (an action that errors, a download, a URL action).
 *
 * NOT ANIMATED: the first page of the session (the boot loader covers it),
 * dialogs (target="new" does not go through the container), and everything
 * under prefers-reduced-motion.
 */
import { onPatched, onWillPatch, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { ActionContainer } from "@web/webclient/actions/action_container";

// ⚠ Mirrored in action_transition.scss (leave / enter durations + enter delay).
// The timers below are only the fallback for a missed `animationend`.
const LEAVE_MS = 240;
const ENTER_MS = 360;
const ENTER_DELAY_MS = 0;
// A blank held longer than this is released anyway.
const HOLD_MAX_MS = 8000;

const DIRECTIONS = ["forward", "back", "switch"];
const ENTER_CLASSES = ["m-action-enter", ...DIRECTIONS.map((d) => `m-action--${d}`)];
// The elements that may carry a scroll offset in a view or a client action.
const SCROLLERS =
    ".o_content, .o_list_renderer, .o_kanban_renderer, .o_form_view_container, .o_form_renderer, .o_action_delegate_scroll";

function prefersReducedMotion() {
    return Boolean(browser.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
}

/** BlankComponent is not exported; it is the only child with exactly these props. */
function isBlank(info) {
    const props = info?.componentProps;
    if (!info?.Component || !props) {
        return false;
    }
    const keys = Object.keys(props);
    return keys.length <= 2 && "onMounted" in props && "withControlPanel" in props;
}

/** The page currently shown by the container (never a ghost). */
function livePage(manager) {
    for (const child of manager.children) {
        if (!child.classList.contains("m-action-ghost")) {
            return child;
        }
    }
    return null;
}

function depthOf(actionService) {
    const ctrl = actionService.currentController;
    return ctrl ? { id: ctrl.jsId, depth: ctrl.config?.breadcrumbs?.length ?? 0 } : null;
}

/**
 * Snapshot the old page: a deep clone, made safe to coexist with the new page
 * for a few hundred milliseconds, plus what cloning loses (scroll, canvases).
 */
function snapshot(el) {
    const clone = el.cloneNode(true);
    clone.classList.remove(...ENTER_CLASSES);
    clone.classList.add("m-action-ghost");
    clone.setAttribute("aria-hidden", "true");
    clone.inert = true;
    // Duplicate ids break label/aria lookups; a cloned checked radio sharing a
    // `name` would uncheck its live twin.
    for (const node of clone.querySelectorAll("[id]")) {
        node.removeAttribute("id");
    }
    for (const node of clone.querySelectorAll("[name]")) {
        node.removeAttribute("name");
    }
    for (const node of clone.querySelectorAll("[autofocus]")) {
        node.removeAttribute("autofocus");
    }
    // A cloned iframe reloads its document (html fields, PDF previews): blank it.
    for (const frame of clone.querySelectorAll("iframe")) {
        frame.removeAttribute("src");
        frame.removeAttribute("srcdoc");
    }
    for (const media of clone.querySelectorAll("video, audio")) {
        media.removeAttribute("autoplay");
    }

    const liveScrollers = [el, ...el.querySelectorAll(SCROLLERS)];
    const ghostScrollers = [clone, ...clone.querySelectorAll(SCROLLERS)];
    const scroll = liveScrollers.map((node) => [node.scrollTop, node.scrollLeft]);

    const liveCanvases = el.querySelectorAll("canvas");
    const ghostCanvases = clone.querySelectorAll("canvas");
    liveCanvases.forEach((canvas, i) => {
        const copy = ghostCanvases[i];
        try {
            copy.width = canvas.width;
            copy.height = canvas.height;
            copy.getContext("2d")?.drawImage(canvas, 0, 0);
        } catch {
            // WebGL or a tainted canvas: the ghost shows it empty, harmless.
        }
    });

    return {
        el: clone,
        /** Re-apply the scroll offsets; call once the clone is in the DOM. */
        restoreScroll() {
            ghostScrollers.forEach((node, i) => {
                const [top, left] = scroll[i] || [0, 0];
                if (top || left) {
                    node.scrollTop = top;
                    node.scrollLeft = left;
                }
            });
        },
    };
}

/** Run `fn` once, on the element's own animationend or after `ms`. */
function onAnimationDone(el, ms, fn) {
    let done = false;
    const finish = () => {
        if (done) {
            return;
        }
        done = true;
        el.removeEventListener("animationend", onEnd);
        browser.clearTimeout(timer);
        fn();
    };
    const onEnd = (ev) => ev.target === el && finish();
    el.addEventListener("animationend", onEnd);
    const timer = browser.setTimeout(finish, ms + 120);
    return finish;
}

patch(ActionContainer.prototype, {
    setup() {
        super.setup(...arguments);
        this._mAction = this.env.services.action;
        this._mSeenId = null; // info.id last rendered
        this._mPending = null; // snapshot taken in willPatch
        this._mFrom = null; // depth before the swap
        this._mHeld = null; // ghost held over a BlankComponent
        this._mLeaving = new Set();
        this._mEnterDone = null;

        onWillPatch(() => {
            this._mPending = null;
            const id = this.info?.id;
            if (id === this._mSeenId || prefersReducedMotion()) {
                return;
            }
            const manager = document.querySelector(".o_web_client > .o_action_manager");
            const old = manager && livePage(manager);
            // First page of the session, or the blank we are already holding over.
            if (!old || this._mSeenId === null || this._mHeld) {
                return;
            }
            this._mFrom = depthOf(this._mAction);
            this._mPending = snapshot(old);
        });

        onPatched(() => {
            const info = this.info;
            const firstRender = this._mSeenId === null;
            if (info?.id === this._mSeenId) {
                return;
            }
            this._mSeenId = info?.id ?? null;
            if (firstRender || prefersReducedMotion()) {
                this._mPending = null;
                return;
            }
            const manager = document.querySelector(".o_web_client > .o_action_manager");
            if (!manager) {
                return;
            }

            // --- Nothing to show (core's error fallback): no animation ---------
            if (!info?.Component) {
                if (this._mHeld) {
                    this._releaseHeld(manager, "switch");
                }
                this._mPending = null;
                return;
            }

            // --- Incoming blank: hold the old page over it ---------------------
            if (isBlank(info)) {
                if (!this._mHeld && this._mPending) {
                    this._mHeld = this._mPending;
                    manager.append(this._mHeld.el);
                    this._mHeld.restoreScroll();
                    manager.classList.add("m-action-holding");
                    // Next frame, so the dim transitions instead of snapping.
                    browser.requestAnimationFrame(() =>
                        this._mHeld?.el.classList.add("m-action-ghost--hold")
                    );
                    const held = this._mHeld;
                    held.timer = browser.setTimeout(() => {
                        if (this._mHeld === held) {
                            this._releaseHeld(manager, "switch");
                        }
                    }, HOLD_MAX_MS);
                }
                this._mPending = null;
                return;
            }

            // --- A real page arrived -------------------------------------------
            const page = livePage(manager);
            const to = depthOf(this._mAction);
            const ghost = this._mPending;
            const from = this._mFrom;
            // Over a held blank it was a menu / app switch: always "switch".
            let direction = "switch";
            if (!this._mHeld && from && to && from.id !== to.id) {
                if (to.depth > from.depth) {
                    direction = "forward";
                } else if (to.depth < from.depth) {
                    direction = "back";
                }
            }

            if (this._mHeld) {
                this._releaseHeld(manager, direction);
            } else if (ghost) {
                manager.append(ghost.el);
                ghost.restoreScroll();
                this._leave(ghost.el, direction);
            }
            this._mPending = null;
            if (page) {
                this._enter(page, direction);
            }
        });

        onWillUnmount(() => {
            for (const el of this._mLeaving) {
                el.remove();
            }
            this._mLeaving.clear();
            if (this._mHeld) {
                browser.clearTimeout(this._mHeld.timer);
                this._mHeld = null;
            }
        });
    },

    _releaseHeld(manager, direction) {
        const held = this._mHeld;
        this._mHeld = null;
        browser.clearTimeout(held.timer);
        manager.classList.remove("m-action-holding");
        this._leave(held.el, direction);
    },

    _leave(el, direction) {
        // A ghost from a previous, still-running switch: drop it, one is enough.
        for (const other of this._mLeaving) {
            if (other !== el) {
                other.remove();
                this._mLeaving.delete(other);
            }
        }
        this._mLeaving.add(el);
        el.classList.add("m-action-leave", `m-action--${direction}`);
        onAnimationDone(el, LEAVE_MS, () => {
            el.remove();
            this._mLeaving.delete(el);
        });
    },

    _enter(page, direction) {
        this._mEnterDone?.();
        page.classList.remove(...ENTER_CLASSES);
        // Restart even when two switches land back to back.
        void page.offsetWidth;
        page.classList.add("m-action-enter", `m-action--${direction}`);
        this._mEnterDone = onAnimationDone(page, ENTER_DELAY_MS + ENTER_MS, () => {
            page.classList.remove(...ENTER_CLASSES);
            this._mEnterDone = null;
        });
    },
});
