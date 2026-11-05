/**
 * Méthode home dashboard — root component + shared primitives
 * (THEME_PLAN §13 / HOMEPAGE_DASHBOARD_PLAN)
 *
 * The catalogue is DATA-DRIVEN: each placement carries `render` (which component
 * draws it) and `fetch_model`/`fetch_method` (a public @api.model returning a
 * normalized payload). So a new widget is a record + one method with NO new core
 * JS — the §5 promise, "a fetcher plus the row primitive."
 *
 * Two primitives are written ONCE and reused everywhere: WidgetFrame (the card
 * chrome) and WidgetRow (leading icon, title/subtitle, trailing figure, status
 * pill, action slot). Writing the row per widget is how Aura reached 4,641 lines
 * of SCSS.
 *
 * ⚠ THE LAYOUT IS NOT FETCHED. It arrives in session_info, already resolved for
 * this user (methode.dashboard.widget._layout_payload), which lets the skeleton
 * draw the real grid so nothing moves when content lands (§13.4). Only widget
 * CONTENT is fetched here, in the root's onWillStart. Do not move the layout into
 * the content RPC for symmetry — that reintroduces the load jump.
 */

import { Component, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

// ---------------------------------------------------------------------------
// WidgetFrame — the shared card. Header (icon, title, count badge, a `lead`
// slot next to the title, and a trailing `action` slot) above a body slot. The
// grid child, so it carries the col_span class; the skeleton mirrors this shell.
// ---------------------------------------------------------------------------
export class WidgetFrame extends Component {
    static template = "daf_uw_theme.WidgetFrame";
    static props = {
        colSpan: { type: Number, optional: true },
        icon: { type: String, optional: true },
        title: { type: String },
        // Optional headline total. 0 is a real value (loaded but empty), so the
        // template tests `=== 0`, not falsiness; the pending frame omits it.
        count: { type: Number, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = { colSpan: 1, icon: "fa-square-o" };
}

// ---------------------------------------------------------------------------
// WidgetRow — one line in a widget. Leading icon, title + subtitle, an optional
// trailing figure (meta, e.g. an amount), a status pill, and an action slot.
// `onClick`, when given, makes the whole row a click target (§1: every row is a
// link). Reused by every list widget.
// ---------------------------------------------------------------------------
export class WidgetRow extends Component {
    static template = "daf_uw_theme.WidgetRow";
    static props = {
        icon: { type: String, optional: true },
        title: { type: String },
        subtitle: { type: String, optional: true },
        // A trailing figure shown before the pill, e.g. a formatted amount.
        meta: { type: String, optional: true },
        // { text, tone } where tone ∈ overdue | today | planned | neutral
        pill: { type: Object, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = { icon: "fa-circle-o", subtitle: "", meta: "" };

    onMainClick() {
        if (this.props.onClick) {
            this.props.onClick();
        }
    }

    onKeydown(ev) {
        if (this.props.onClick && (ev.key === "Enter" || ev.key === " ")) {
            ev.preventDefault();
            this.props.onClick();
        }
    }
}

// ---------------------------------------------------------------------------
// PendingWidget — a placement whose type has no fetcher yet. An honest "no
// content" frame rather than a convincing-but-fake body (§0).
// ---------------------------------------------------------------------------
export class PendingWidget extends Component {
    static template = "daf_uw_theme.WidgetPending";
    static components = { WidgetFrame };
    static props = {
        placement: { type: Object },
        data: { type: Object, optional: true },
    };
}

// ---------------------------------------------------------------------------
// ListWidget — the generic list renderer for `render='list'` widgets. Consumes
// the normalized payload (flat `rows` or grouped `groups`, each row a WidgetRow
// with an optional amount + status pill), a "+ N others" overflow, and a
// designed empty state. Most app widgets are just a fetcher returning this.
// ---------------------------------------------------------------------------
export class ListWidget extends Component {
    static template = "daf_uw_theme.WidgetList";
    static components = { WidgetFrame, WidgetRow };
    static props = {
        placement: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.action = useService("action");
        const data = this.props.data || {};
        this.state = useState({
            count: data.count || 0,
            groups: data.groups || null,
            rows: data.rows || null,
            action: data.action || null,
            empty: data.empty || null,
        });
    }

    get isEmpty() {
        return this.state.count === 0;
    }

    get emptyTitle() {
        return (this.state.empty && this.state.empty.title) || _t("Nothing here");
    }

    get shownCount() {
        if (this.state.groups) {
            return this.state.groups.reduce((total, group) => total + group.rows.length, 0);
        }
        return this.state.rows ? this.state.rows.length : 0;
    }

    get remaining() {
        return Math.max(this.state.count - this.shownCount, 0);
    }

    openRecord(row) {
        if (!row.res_model || !row.res_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: row.res_model,
            res_id: row.res_id,
            views: [[false, "form"]],
            view_mode: "form",
        });
    }

    /** The header link and the "+ N others" both open the fetcher-provided action. */
    viewAll() {
        if (this.state.action) {
            // An xmlid string or a server-built act_window dict; doAction takes both.
            this.action.doAction(this.state.action);
        }
    }
}

// ---------------------------------------------------------------------------
// ActivitiesWidget — the "My Activities" widget (render='activities'). A list
// with two extras: a "Plan…" primary and a per-row mark-done that refills the
// cap. Kept as its own component because of those interactions; it reuses the
// same WidgetFrame/WidgetRow primitives.
// ---------------------------------------------------------------------------
export class ActivitiesWidget extends Component {
    static template = "daf_uw_theme.WidgetActivities";
    static components = { WidgetFrame, WidgetRow };
    static props = {
        placement: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const data = this.props.data || { count: 0, groups: [] };
        this.state = useState({
            count: data.count,
            groups: data.groups,
        });
    }

    get isEmpty() {
        return this.state.count === 0;
    }

    get shownCount() {
        return this.state.groups.reduce((total, group) => total + group.rows.length, 0);
    }

    get remaining() {
        return Math.max(this.state.count - this.shownCount, 0);
    }

    pillFor(row) {
        if (row.state === "overdue") {
            return {
                tone: "overdue",
                text: row.days === 1 ? _t("1 day late") : _t("%s days late", row.days),
            };
        }
        if (row.state === "today") {
            return { tone: "today", text: _t("Today") };
        }
        return {
            tone: "planned",
            text: row.days === 1 ? _t("in 1 day") : _t("in %s days", row.days),
        };
    }

    async reload() {
        const data = await this.orm.call(
            "mail.activity",
            "dashboard_fetch_activities",
            [],
            { limit: 5 }
        );
        this.state.count = data.count;
        this.state.groups = data.groups;
    }

    async markDone(row, group) {
        group.rows = group.rows.filter((candidate) => candidate.id !== row.id);
        group.count -= 1;
        this.state.count -= 1;
        await this.orm.call("mail.activity", "action_feedback", [[row.id]]);
        await this.reload();
    }

    openRecord(row) {
        if (row.res_model && row.res_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: row.res_model,
                res_id: row.res_id,
                views: [[false, "form"]],
                view_mode: "form",
            });
            return;
        }
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "mail.activity",
                res_id: row.id,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => this.reload() }
        );
    }

    plan() {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Plan an activity"),
                res_model: "mail.activity",
                views: [[false, "form"]],
                target: "new",
                context: { default_user_id: user.userId },
            },
            { onClose: () => this.reload() }
        );
    }

    viewAll() {
        this.action.doAction("mail.mail_activity_action_my");
    }
}

// ---------------------------------------------------------------------------
// ChartWidget — horizontal bars, in CSS. No charting library: §13.6 established
// Aura's trend widgets were hand-rolled markup with no dependency behind them,
// and four bars do not justify adding one. Bars are proportional to the largest
// value, so the shape is readable without an axis.
// ---------------------------------------------------------------------------
export class ChartWidget extends Component {
    static template = "daf_uw_theme.WidgetChart";
    static components = { WidgetFrame };
    static props = {
        placement: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.action = useService("action");
    }

    get points() {
        const points = (this.props.data && this.props.data.points) || [];
        const peak = Math.max(...points.map((point) => point.value), 0);
        return points.map((point) => ({
            ...point,
            // Guard the all-zero case: 0/0 is NaN and would blank the widget.
            percent: peak ? Math.round((point.value / peak) * 100) : 0,
        }));
    }

    get total() {
        return (this.props.data && this.props.data.total) || 0;
    }

    open() {
        if (this.props.data && this.props.data.action) {
            this.action.doAction(this.props.data.action);
        }
    }
}

// ---------------------------------------------------------------------------
// StatCard — one KPI tile in the stats row. A value, its label, one line of
// meta, and a door into the records behind it (§1: every number is a link).
// ---------------------------------------------------------------------------
export class StatCard extends Component {
    static template = "daf_uw_theme.StatCard";
    static props = {
        tile: { type: Object },
        data: { type: Object, optional: true },
    };

    setup() {
        this.action = useService("action");
    }

    get hasAction() {
        return Boolean(this.props.data && this.props.data.action);
    }

    open() {
        if (this.hasAction) {
            this.action.doAction(this.props.data.action);
        }
    }
}

// ---------------------------------------------------------------------------
// InsightBanners — the screen raising its hand (§2.4). Dismissible strips, each
// with one action. Dismissal is a snooze: it is remembered for the rest of the
// day and the banner returns tomorrow if the problem is still there.
// ---------------------------------------------------------------------------
export class InsightBanners extends Component {
    static template = "daf_uw_theme.InsightBanners";
    static props = {
        insights: { type: Array },
        more: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ hidden: [] });
    }

    get visible() {
        return this.props.insights.filter((insight) => !this.state.hidden.includes(insight.key));
    }

    async dismiss(insight) {
        this.state.hidden.push(insight.key);
        await this.orm.call(
            "methode.dashboard.preferences",
            "dashboard_dismiss_insight",
            [insight.key]
        );
    }

    run(insight) {
        if (insight.action) {
            this.action.doAction(insight.action);
        }
    }
}

// ---------------------------------------------------------------------------
// QuickActions — the shortcut row. Deliberately the least clever zone on the
// screen: a handful of buttons that start the things a user does most.
// ---------------------------------------------------------------------------
export class QuickActions extends Component {
    static template = "daf_uw_theme.QuickActions";
    static props = {
        shortcuts: { type: Array },
    };

    setup() {
        this.action = useService("action");
        this.menu = useService("menu");
    }

    /**
     * ⚠ setCurrentMenu IS NOT COSMETIC, AND doAction WILL NOT DO IT FOR YOU.
     *
     * A shortcut's action is an anonymous act_window dict built server-side,
     * so nothing links it to a menu, and action_service never consults the
     * menu service anyway. Left alone, opening "Nouveau devis" from here keeps
     * currentApp on the Homepage: the module title still reads "Accueil", and
     * because that menu has no children NavBar.currentAppSections is empty and
     * core's SectionsMenu is not rendered at all -- the Sales menus vanish.
     *
     * Done through onActionReady rather than after the await, mirroring
     * menu_service.selectMenu(): it fires once the controller is ready but
     * before the UPDATE that swaps the screen, so the title changes with the
     * content instead of a frame after it.
     */
    run(shortcut) {
        if (!shortcut.action) {
            return;
        }
        const menuId = shortcut.menu_id;
        this.action.doAction(
            shortcut.action,
            menuId ? { onActionReady: () => this.menu.setCurrentMenu(menuId) } : {}
        );
    }
}

// The render → component map. A widget-type's `render` picks its component; new
// render kinds register here as they are added.
const WIDGET_COMPONENTS = {
    list: ListWidget,
    activities: ActivitiesWidget,
    chart: ChartWidget,
};

// ---------------------------------------------------------------------------
// Grid packing: a card is measured and given a row span, so a short card stops
// reserving the height of the tallest card beside it.
//
// Not CSS, because CSS cannot: `grid-template-rows: masonry` is not shippable,
// and `column-count` masonry cannot express col_span.
// ---------------------------------------------------------------------------
const PACK_ROW_PX = 4;

function usePackedGrid(refName) {
    const gridRef = useRef(refName);
    let frame = null;

    const pack = () => {
        const grid = gridRef.el;
        if (!grid) {
            return;
        }
        for (const card of grid.children) {
            // The row gap is a margin in packed mode — see the SCSS.
            const gapBelow = parseFloat(getComputedStyle(card).marginBottom) || 0;
            const height = card.getBoundingClientRect().height;
            card.style.gridRowEnd = `span ${Math.max(
                1,
                Math.ceil((height + gapBelow) / PACK_ROW_PX)
            )}`;
        }
        // After the first measurement only: 4px rows before it paint slivers.
        grid.classList.add("is-packed");
    };

    // Writing layout straight from a ResizeObserver callback loops.
    const packOnNextFrame = () => {
        if (frame === null) {
            frame = requestAnimationFrame(() => {
                frame = null;
                pack();
            });
        }
    };

    // No dependencies: re-runs on every patch, when cards may have changed.
    useEffect(() => {
        const grid = gridRef.el;
        if (!grid) {
            return;
        }
        const observer = new ResizeObserver(packOnNextFrame);
        for (const card of grid.children) {
            observer.observe(card);
        }
        pack();
        return () => observer.disconnect();
    });

    onWillUnmount(() => {
        if (frame !== null) {
            cancelAnimationFrame(frame);
        }
    });
}

// ---------------------------------------------------------------------------
// HomeDashboard — root. Draws the grid from the session layout, fetches content
// for every wired widget, and dispatches each placement to its component.
// ---------------------------------------------------------------------------
export class HomeDashboard extends Component {
    static template = "daf_uw_theme.HomeDashboard";
    static components = {
        PendingWidget,
        ListWidget,
        ActivitiesWidget,
        ChartWidget,
        StatCard,
        InsightBanners,
        QuickActions,
    };
    // Client actions are handed action/actionId/className/globalState by the
    // action service; none are used here, so accept and ignore them.
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        const payload = session.methode_dashboard || {};
        const preferences = payload.preferences || {};

        this.state = useState({
            // Starts true so the first paint is the skeleton, not an empty grid.
            loading: true,
            placements: payload.placements || [],
            stats: payload.stats || [],
            catalogue: payload.catalogue || [],
            preferences,
            // Keyed by placement id; filled by onWillStart before first render.
            data: {},
            // Keyed by stat code.
            statsData: {},
            insights: [],
            insightsMore: 0,
            shortcuts: [],
            // Edit mode and its two overlays. All client-side: the server holds
            // the layout, not the fact that someone is currently rearranging it.
            editing: false,
            picking: false,
            configuring: false,
        });

        this.userName = user.name;

        usePackedGrid("grid");

        onWillStart(async () => {
            // Everything the screen needs, in parallel — one slow zone must not
            // hold the others back, and `loading` covers them all so the skeleton
            // is shown until the page can be drawn in full.
            await Promise.all([
                ...this.state.placements.map((placement) => this._fetchWidget(placement)),
                ...(preferences.show_stats_row === false
                    ? []
                    : this.state.stats.map((tile) => this._fetchStat(tile))),
                preferences.show_insights === false ? null : this._fetchInsights(),
                preferences.show_shortcuts === false ? null : this._fetchShortcuts(),
            ]);
            this.state.loading = false;
        });
    }

    async _fetchStat(tile) {
        if (!tile.fetch_method) {
            return;
        }
        try {
            this.state.statsData[tile.code] = await this.orm.call(
                tile.fetch_model,
                tile.fetch_method,
                []
            );
        } catch (error) {
            console.error(`Dashboard stat "${tile.code}" failed to load`, error);
        }
    }

    async _fetchInsights() {
        try {
            const result = await this.orm.call(
                "methode.dashboard.widget",
                "dashboard_fetch_insights",
                []
            );
            this.state.insights = result.insights || [];
            this.state.insightsMore = result.more || 0;
        } catch (error) {
            console.error("Dashboard insights failed to load", error);
        }
    }

    async _fetchShortcuts() {
        try {
            const result = await this.orm.call(
                "methode.dashboard.widget",
                "dashboard_fetch_shortcuts",
                []
            );
            this.state.shortcuts = result.shortcuts || [];
        } catch (error) {
            console.error("Dashboard shortcuts failed to load", error);
        }
    }

    /** Independent of `statsData` on purpose: gating on loaded data would leave
     *  the row out of the skeleton and pop it in afterwards. */
    get showStats() {
        return this.state.preferences.show_stats_row !== false && this.state.stats.length > 0;
    }

    get showInsights() {
        return this.state.preferences.show_insights !== false && this.state.insights.length > 0;
    }

    get showShortcuts() {
        return (
            this.state.preferences.show_shortcuts !== false && this.state.shortcuts.length > 0
        );
    }

    async _fetchWidget(placement) {
        if (!placement.fetch_method) {
            return; // No fetcher yet — renders the pending frame.
        }
        const kwargs = { limit: this.state.preferences.row_limit || 5 };
        if (placement.needs_config) {
            try {
                kwargs.config = JSON.parse(placement.config_json || "{}");
            } catch {
                kwargs.config = {};
            }
        }
        try {
            this.state.data[placement.id] = await this.orm.call(
                placement.fetch_model,
                placement.fetch_method,
                [],
                kwargs
            );
        } catch (error) {
            // One widget failing must not blank the whole dashboard; it falls
            // back to its pending frame. §13.3 graceful degradation.
            console.error(`Dashboard widget "${placement.code}" failed to load`, error);
        }
    }

    /** The component that draws a placement: its render kind, or pending. */
    componentFor(placement) {
        if (!placement.fetch_method) {
            return PendingWidget;
        }
        return WIDGET_COMPONENTS[placement.render] || PendingWidget;
    }

    /**
     * Greeting by local time. Uses the browser clock on purpose — the user's
     * wall clock is being greeted, not the server's timezone.
     */
    get greeting() {
        const hour = new Date().getHours();
        if (hour < 12) {
            return _t("Good morning");
        }
        if (hour < 18) {
            return _t("Good afternoon");
        }
        return _t("Good evening");
    }

    /**
     * Rows for the skeleton, as a plain array so the template can t-foreach it.
     * expected_rows comes from the widget TYPE, so a five-row activity list is
     * drawn five rows tall before it has loaded anything.
     */
    skeletonRows(placement) {
        return Array.from({ length: Math.max(placement.expected_rows || 3, 1) });
    }

    get isEmpty() {
        return !this.state.loading && this.state.placements.length === 0;
    }

    // -----------------------------------------------------------------------
    // Edit mode (§13.3: resize, move, remove, add, restore defaults)
    //
    // Every mutation is one RPC that returns the WHOLE layout, and the client
    // adopts it wholesale rather than patching its own state. That is why there is
    // no reconciliation logic here and no chance of the screen disagreeing with
    // the database: the server is the only thing that decides where widgets are.
    // -----------------------------------------------------------------------
    async _applyLayout(payload) {
        this.state.placements = payload.placements || [];
        this.state.stats = payload.stats || [];
        this.state.catalogue = payload.catalogue || [];
        // A newly added widget has no data yet; fetch only what is missing.
        await Promise.all(
            this.state.placements
                .filter((placement) => !(placement.id in this.state.data))
                .map((placement) => this._fetchWidget(placement))
        );
    }

    async _mutate(method, args = []) {
        const payload = await this.orm.call("methode.dashboard.widget", method, args);
        await this._applyLayout(payload);
    }

    toggleEdit() {
        this.state.editing = !this.state.editing;
        if (!this.state.editing) {
            this.state.picking = false;
            this.state.configuring = false;
        }
    }

    /** The add-widget picker, grouped the way the catalogue declares. */
    get catalogueGroups() {
        const placed = new Set(this.state.placements.map((p) => p.code));
        const groups = new Map();
        for (const entry of this.state.catalogue) {
            const name = entry.group_name || "General";
            if (!groups.has(name)) {
                groups.set(name, []);
            }
            groups.get(name).push({ ...entry, placed: placed.has(entry.code) });
        }
        return [...groups.entries()].map(([name, items]) => ({ name, items }));
    }

    async addWidget(entry) {
        await this._mutate("dashboard_add_widget", [entry.id]);
    }

    async removeWidget(placement) {
        delete this.state.data[placement.id];
        await this._mutate("dashboard_remove_widget", [placement.id]);
    }

    async resizeWidget(placement, colSpan) {
        await this._mutate("dashboard_resize_widget", [placement.id, colSpan]);
    }

    async moveWidget(placement, offset) {
        await this._mutate("dashboard_move_widget", [placement.id, offset]);
    }

    async resetLayout() {
        this.state.data = {};
        await this._mutate("dashboard_reset_layout");
    }

    /**
     * Preferences (§13.3's second persistence model). Saved immediately — a
     * dashboard preference with an OK button is a dashboard preference nobody
     * changes twice.
     */
    async savePreference(key, value) {
        this.state.preferences[key] = value;
        const saved = await this.orm.call(
            "methode.dashboard.preferences",
            "dashboard_save_preferences",
            [{ [key]: value }]
        );
        this.state.preferences = saved;

        // Zones that were switched on may never have been fetched this session.
        if (key === "show_stats_row" && value) {
            await Promise.all(this.state.stats.map((tile) => this._fetchStat(tile)));
        } else if (key === "show_insights" && value) {
            await this._fetchInsights();
        } else if (key === "show_shortcuts" && value) {
            await this._fetchShortcuts();
        } else if (key === "row_limit") {
            // Every list widget is capped by this, so they all have to be re-read.
            this.state.data = {};
            await Promise.all(
                this.state.placements.map((placement) => this._fetchWidget(placement))
            );
        }
    }

    onRowLimitChange(ev) {
        const value = parseInt(ev.target.value, 10);
        if (!Number.isNaN(value) && value >= 1 && value <= 20) {
            this.savePreference("row_limit", value);
        }
    }
}

registry.category("actions").add("daf_uw_theme.home_dashboard", HomeDashboard);
