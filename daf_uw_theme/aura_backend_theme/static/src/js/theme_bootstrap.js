/** @odoo-module **/

/**
 * Apply Aura theme CSS custom properties from session_info immediately,
 * before any OWL component renders, to avoid a flash of unstyled content.
 *
 * The data is injected into odoo.__session_info__.tbt_theme by
 * models/ir_http.py on every authenticated page load.
 */

(function applyTbtTheme() {
    const theme = window.odoo?.__session_info__?.tbt_theme;
    if (!theme) return;

    const root = document.documentElement;
    const s = root.style;

    // brand
    s.setProperty('--tbt-brand-color',          theme.brand);
    s.setProperty('--tbt-brand-color-rgb',       theme.brand_rgb);
    s.setProperty('--tbt-brand-color-dark',      theme.brand_dark);
    s.setProperty('--tbt-brand-color-emphasis',  theme.brand_dark);
    s.setProperty('--tbt-brand-color-soft',      `rgba(${theme.brand_rgb}, .10)`);
    s.setProperty('--tbt-brand-color-softer',    `rgba(${theme.brand_rgb}, .14)`);

    // odoo bootstrap overrides
    s.setProperty('--o-brand-primary',           theme.brand);
    s.setProperty('--o-brand-odoo',              theme.brand);
    s.setProperty('--o-action',                  theme.brand);
    s.setProperty('--o-brand-secondary',         theme.brand);
    s.setProperty('--o-community-color',         theme.brand);
    s.setProperty('--o-enterprise-color',        theme.brand);
    s.setProperty('--o-enterprise-action-color', theme.brand);
    s.setProperty('--bs-primary',                theme.brand);
    s.setProperty('--bs-primary-rgb',            theme.brand_rgb);
    s.setProperty('--bs-link-color',             theme.brand);
    s.setProperty('--bs-link-hover-color',       theme.brand_dark);
    s.setProperty('--bs-primary-text-emphasis',  theme.brand_dark);
    s.setProperty('--bs-primary-bg-subtle',      `rgba(${theme.brand_rgb}, .12)`);
    s.setProperty('--bs-primary-border-subtle',  `rgba(${theme.brand_rgb}, .28)`);
    s.setProperty('--bs-focus-ring-color',       `rgba(${theme.brand_rgb}, .25)`);

    // topbar
    s.setProperty('--tbt-topbar-bg-dynamic',     theme.topbar_bg);
    s.setProperty('--tbt-topbar-text-dynamic',   theme.topbar_text);

    // content
    s.setProperty('--tbt-content-bg-dynamic',    theme.content_bg);
    s.setProperty('--tbt-card-bg-dynamic',       theme.card_bg);
    s.setProperty('--tbt-dashboard-card-1',       theme.dashboard_card_1 || '#111827');
    s.setProperty('--tbt-dashboard-card-2',       theme.dashboard_card_2 || '#6B7280');
    s.setProperty('--tbt-dashboard-card-3',       theme.dashboard_card_3 || '#0A8FDC');
    s.setProperty('--tbt-dashboard-card-4',       theme.dashboard_card_4 || '#E3E9F6');
    s.setProperty('--tbt-dashboard-card-pattern', theme.dashboard_card_pattern === false ? 'none' : 'pattern');
    root.classList.toggle('tbt-dashboard-card-pattern-off', theme.dashboard_card_pattern === false);

    // loading
    s.setProperty('--tbt-loading-display-dynamic',  theme.loading_enabled ? 'inline-flex' : 'none');
    s.setProperty('--tbt-loading-text-dynamic',     theme.loading_text);
    s.setProperty('--tbt-loading-style-dynamic',    theme.loading_style);
    root.classList.toggle('tbt-high-contrast', !!theme.high_contrast);

    // sidebar palette
    s.setProperty('--tbt-sidebar-bg-dynamic',              theme.sidebar_bg);
    s.setProperty('--tbt-sidebar-border-dynamic',          theme.sidebar_border);
    s.setProperty('--tbt-sidebar-text-dynamic',            theme.sidebar_text);
    s.setProperty('--tbt-sidebar-text-muted-dynamic',      theme.sidebar_text_muted);
    s.setProperty('--tbt-sidebar-surface-dynamic',         theme.sidebar_surface);
    s.setProperty('--tbt-sidebar-surface-hover-dynamic',   theme.sidebar_surface_hover);
    s.setProperty('--tbt-sidebar-surface-active-dynamic',  theme.sidebar_surface_active);
    s.setProperty('--tbt-sidebar-active-text-dynamic',     theme.sidebar_active_text);
    s.setProperty('--tbt-sidebar-active-border-dynamic',   theme.sidebar_active_border);
    s.setProperty('--tbt-sidebar-icon-dynamic',            theme.sidebar_icon);
    s.setProperty('--tbt-sidebar-icon-hover-dynamic',      theme.sidebar_icon_hover);
    s.setProperty('--tbt-sidebar-icon-active-dynamic',     theme.sidebar_icon_active);
    s.setProperty('--tbt-sidebar-icon-bg-dynamic',         theme.sidebar_icon_bg);
    s.setProperty('--tbt-sidebar-brand-bg-dynamic',        theme.sidebar_brand_bg);
})();
