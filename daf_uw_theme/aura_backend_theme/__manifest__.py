# -*- coding: utf-8 -*-
{
    'name': 'Aura Backend Theme - Community Edition',
    # 19.0.1.8.0 moves the stored brand colour to the DAF Under Writing logo
    # blue (#0E58F0); 19.0.1.7.0 had moved it to the owner's blue palette.
    # Each migration only fires because this number moved.
    'version': '19.0.1.8.0',
    'category': 'Themes/Backend',
    'summary': 'Premium backend theme for Odoo 19 Community',
    'description': """
Aura Backend Theme - Community Edition
======================
A premium backend theme for Odoo 19 Community Edition.

Covers:
- Login page
- Top navigation bar
- App menu
- Form views
- List views
- Kanban views
- Buttons, badges, alerts
- Typography and icons
    """,
    'author': 'LATI',
    'website': 'https://latitibabu.com',
    'live_test_url': 'https://aurademoform.latitibabu.com',
    'support': 'support@latitibabu.com',
    'price': 49.99,
    'currency': 'USD',
    'depends': ['web', 'base_setup', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        # Loads the FA6 webfont that fa_v6_shim.scss assumes is present, and
        # server-renders the :root palette so the page paints on-brand before
        # theme_bootstrap.js runs.  Dropped by mistake alongside the login and
        # dashboard templates; THEME_PLAN §3.2 keeps it.
        'views/web_assets.xml',
        # Theme Settings block on Settings > General Settings. Replaces the
        # systray + ThemeSettingsDialog entry point (§9.7).
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aura_backend_theme/static/src/js/theme_bootstrap.js',

            'aura_backend_theme/static/src/scss/fa_v6_shim.scss',

            # ⚠ loading_style.js was REMOVED here in P8e, along with the file.
            # THEME_PLAN §13.5 planned to keep it and rebuild the six
            # .tbt-loading-style-* rule sets it depends on; P8e retired the six
            # styles instead, in favour of the single brand loader in
            # daf_uw_theme/static/src/scss/loader.scss.  That left the script
            # writing two class families — tbt-loading-style-<name> and
            # tbt-loading-active — that nothing anywhere reads.
            #
            # It was not merely inert.  To maintain tbt-loading-active it ran a
            # MutationObserver over document.documentElement with subtree:true
            # AND attributes:true, so every DOM mutation in the SPA woke a
            # callback that did a querySelector + getComputedStyle, to set a
            # class with no consumer.  Deleting it is a performance fix as much
            # as a cleanup.
            #
            # --tbt-loading-style-dynamic is still injected by views/web_assets.xml
            # and tbt_loading_style still stores its column; both are harmless and
            # left alone so no migration is needed.
            'aura_backend_theme/static/src/webclient/theme_settings/theme_settings_dialog.js',
            'aura_backend_theme/static/src/webclient/theme_settings/theme_settings_dialog.xml',
            'aura_backend_theme/static/src/webclient/theme_settings/theme_settings_dialog.scss',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'license': 'OPL-1',
}
