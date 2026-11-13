{
    'name': 'Méthode Theme',
    'version': '19.0.1.4.0',
    'category': 'Themes/Backend',
    'summary': 'Méthode brand identity for the Odoo backend',
    # Set explicitly, and keep it set.  Odoo's load_manifest() falls back to
    # slurping README.md into `description` whenever this key is empty, then
    # renders it as reStructuredText — so a Markdown README produces a burst of
    # docutils "Undefined substitution referenced" errors on every module load.
    # The README is developer documentation and is not valid RST by design.
    'description': 'Methode brand identity for the Odoo backend. '
                   'See README.md in this module for the design system.',
    'author': 'Méthode - Progiciel sur mesure',
    'website': 'https://methode.dev',
    'license': 'LGPL-3',
    # http_routing: views/error_templates.xml inherits http_routing.404.  It is
    # NOT pulled in by web, and without it a fresh install fails to load that
    # file with "External ID not found in the system: http_routing.404".
    # muk_web_appsbar: the app launcher is MuK's sidebar (it replaced the
    # in-house methode_apps_dropdown).  It hooks web.WebClient, not web.NavBar,
    # so it sits beside the two-row navbar below without touching it.
    # mail: static/src/views/form_chatter.js extends mail's FormRenderer patch
    # (it calls super.mailLayout), so mail's assets must load first.
    'depends': ['web', 'http_routing', 'mail', 'aura_backend_theme', 'muk_web_appsbar'],
    # The module was assets-only until the login rebrand (§3.3 / §15.2 B9).
    'data': [
        'views/login_templates.xml',
        # Tab + home-screen icons, on web.layout and both layouts derived from
        # it.  The PWA manifest half of the same change is Python
        # (controllers/webmanifest.py) and needs no entry here.
        'views/favicon_templates.xml',
        # The Odoo-rendered 404 (NOT nginx's — see the file header).  Frontend
        # QWeb, same brand surface as the login page.
        'views/error_templates.xml',
        # The animated DAF Under Writing mark ("Assemble"), t-called by the
        # boot loader below. Listed first so the one copy is registered before
        # anything calls it.
        'views/daf_mark_templates.xml',
        # Must be server-side QWeb: it has to paint before OWL exists (P8e).
        'views/boot_loader_templates.xml',
        # --- Home dashboard, P8a ------------------------------------------
        # Security first: the record rule is the only thing separating one
        # user's layout from another's (see dashboard_security.xml).
        'security/ir.model.access.csv',
        'security/dashboard_security.xml',
        'data/dashboard_widget_type_data.xml',
        # Dashboard alert thresholds, on the General Settings page (§2.4).
        'views/res_config_settings_views.xml',
        # The client action for tag `daf_uw_theme.home_dashboard`, registered in
        # static/src/dashboard/dashboard.js.  No menu points at it any more —
        # DAF is the landing app; see the note in the file.
        'views/dashboard_actions.xml',
        # MuK's sidebar footer: the DAF Under Writing lockup instead of Odoo's
        # "Your logo" placeholder.  Runs on every update; never overwrites a logo an
        # admin chose (see res_company.py::_m_seed_appbar_image).
        'data/appbar_image_data.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss',
            'daf_uw_theme/static/src/scss/brand_variables.scss'),
        ],
        'web.assets_backend': [
            # Order is load-bearing (§5.3): brand tokens -> base/typography ->
            # components -> views -> fixes.  Tokens must come first so every
            # later sheet can read them.
            'daf_uw_theme/static/src/scss/css_tokens.scss',
            'daf_uw_theme/static/src/scss/typography.scss',
            'daf_uw_theme/static/src/scss/buttons.scss',
            # The glass glint: writes the pointer position on hovered glass
            # controls; the look is --m-glass-glint in the sheets.
            'daf_uw_theme/static/src/js/glass_glint.js',
            'daf_uw_theme/static/src/scss/forms.scss',
            'daf_uw_theme/static/src/scss/cards.scss',
            'daf_uw_theme/static/src/scss/surfaces.scss',
            'daf_uw_theme/static/src/scss/navbar.scss',
            # Two-row navbar (§5.4).  The template MOVES stock nodes into two
            # rows; web.NavBar.AppsMenu is left as stock (the app sidebar is
            # muk_web_appsbar's, mounted on web.WebClient).
            'daf_uw_theme/static/src/navbar/navbar.js',
            'daf_uw_theme/static/src/navbar/navbar.xml',
            # muk_web_appsbar's sidebar in the navbar's material.  Overrides
            # only — MuK is vendored and its sheet is left untouched.
            'daf_uw_theme/static/src/scss/appsbar.scss',
            # The in-app loading snackbar.  ⚠ The BOOT loader's CSS is NOT here —
            # it is inlined in views/boot_loader_templates.xml, because this
            # bundle is a megabyte of render-blocking CSS and the mark has to
            # paint before it is parsed.  See that file for the measurement.
            'daf_uw_theme/static/src/scss/loader.scss',
            'daf_uw_theme/static/src/js/boot_loader.js',
            'daf_uw_theme/static/src/js/loading_indicator.js',
            # --- Home dashboard, P8a ------------------------------------------
            # The client action tag `daf_uw_theme.home_dashboard` is registered
            # in dashboard.js; views/dashboard_actions.xml depends on it existing.
            'daf_uw_theme/static/src/dashboard/dashboard.js',
            'daf_uw_theme/static/src/dashboard/dashboard.xml',
            'daf_uw_theme/static/src/dashboard/dashboard.scss',
            # Views come after components: they tune what the component sheets
            # above establish, so they must be able to win at equal specificity.
            'daf_uw_theme/static/src/scss/views/list_view.scss',
            'daf_uw_theme/static/src/scss/views/form_view.scss',
            # Chatter always below the form, full width.  JS + the rule at the
            # bottom of form_view.scss are one change; keep them together.
            'daf_uw_theme/static/src/views/form_chatter.js',
            # Forms open read-only: Edit, then Save / Cancel, instead of core's
            # always-editable form and its cloud / ✕ icons.  JS + XML are one
            # change; see form_edit_toggle.js's header for where it applies.
            'daf_uw_theme/static/src/views/form_edit_toggle.js',
            'daf_uw_theme/static/src/views/form_edit_toggle.xml',
            # Notebook pages animate on leave and on enter (every web.Notebook).
            # JS + SCSS are one change; the leave duration is mirrored in both.
            'daf_uw_theme/static/src/notebook/notebook_transition.js',
            'daf_uw_theme/static/src/notebook/notebook_transition.scss',
            'daf_uw_theme/static/src/scss/views/kanban_view.scss',
            'daf_uw_theme/static/src/scss/views/status_bar.scss',
            'daf_uw_theme/static/src/scss/views/settings_view.scss',
            # --- Empty states (§7) -------------------------------------------
            # The branded "no records" surface. TWO files on purpose: the sheet
            # brands the `.o_nocontent_help` wrapper every helper template in
            # the product shares, and the patch rewrites the string every one of
            # them is handed. Neither can be done by t-inheriting web's helper —
            # sale, hr and lunch ship their own, and their modules are not
            # dependencies here. Read both file headers before changing either.
            'daf_uw_theme/static/src/scss/views/no_content.scss',
            'daf_uw_theme/static/src/views/no_content_help.js',
            # --- Lists, control panel & breadcrumbs (global UX) ---------------
            # [ASSETS:CONTROL_PANEL]
            # List skeleton + row enter animation, on every list view and x2many
            # list.  JS + XML + SCSS are one change (list_loading.js header).
            'daf_uw_theme/static/src/list/list_loading.js',
            'daf_uw_theme/static/src/list/list_loading.xml',
            'daf_uw_theme/static/src/list/list_loading.scss',
            # "Open the list in a new tab" link on every x2many list in a form.
            # JS + XML + SCSS are one change; target: controllers/x2many_list.py.
            'daf_uw_theme/static/src/x2many/x2many_open_list.js',
            'daf_uw_theme/static/src/x2many/x2many_open_list.xml',
            'daf_uw_theme/static/src/x2many/x2many_open_list.scss',
            # Import / Export out of the cog, as buttons beside "New".  The cog
            # patch imports its keys from the buttons module.  ⚠ No dependency
            # on base_import: its cog entry is looked up at runtime.
            'daf_uw_theme/static/src/control_panel/data_transfer_buttons.js',
            'daf_uw_theme/static/src/control_panel/data_transfer_buttons.xml',
            'daf_uw_theme/static/src/control_panel/cog_menu.js',
            # Breadcrumbs: one "← previous page" link.  Extends web.Breadcrumbs,
            # which is also what the navbar row shows on mobile (t-portal).
            'daf_uw_theme/static/src/control_panel/breadcrumbs.xml',
            'daf_uw_theme/static/src/control_panel/control_panel.scss',
            # Form groups: label above its input, every form (CSS only).  After
            # form_view.scss (listed above) so it can retune the same groups.
            'daf_uw_theme/static/src/scss/views/form_labels.scss',
            # Bento boxes and sized fields for forms laid out in <div>s
            # (owner rules, 2026-11-07).  After form_view.scss: same panes.
            'daf_uw_theme/static/src/scss/views/form_bento.scss',
            # --- Simplified search bar (global UX) ----------------------------
            # [ASSETS:SEARCH]
            # Live search box + Filter… / Group by… typeaheads replace the stock
            # autocomplete-and-caret flow on every search bar (lists, kanban,
            # pivot, graph, x2many dialogs).  See search_bar_patch.js's header.
            'daf_uw_theme/static/src/search/search_model_patch.js',
            'daf_uw_theme/static/src/search/search_picker.js',
            'daf_uw_theme/static/src/search/search_picker.xml',
            # The "+N" chip's popover (every active facet, full label + ×).
            'daf_uw_theme/static/src/search/search_facet_overflow.js',
            'daf_uw_theme/static/src/search/search_facet_overflow.xml',
            'daf_uw_theme/static/src/search/search_bar_patch.js',
            'daf_uw_theme/static/src/search/search_bar.xml',
            'daf_uw_theme/static/src/search/search.scss',
            # Theme settings live on the Settings page, not in a systray popup —
            # see aura_backend_theme/views/res_config_settings_views.xml.
        ],
        # The login page (§3.3).  This is NOT optional polish: brand_variables
        # lives in _assets_primary_variables, which the frontend bundle also
        # includes, so the frontend CSS already says `font-family: Nunito` —
        # but the @font-face that actually fetches the woff2 is in
        # typography.scss.  Without it the login page asks for a font it never
        # loads and silently falls back to system sans, with no error anywhere.
        # Keep these three in sync with the backend list above.
        'web.assets_frontend': [
            'daf_uw_theme/static/src/scss/css_tokens.scss',
            'daf_uw_theme/static/src/scss/typography.scss',
            'daf_uw_theme/static/src/scss/buttons.scss',
            # .m-daf-loader + its keyframes, so a frontend page can show the
            # same animated mark as the backend boot loader.  The rest of this
            # sheet (.m-boot-loader, .o_loading_indicator) matches nothing on
            # the login page — inert there, not dead code.
            'daf_uw_theme/static/src/scss/loader.scss',
            # Frontend-ONLY, deliberately — its selectors exist only on the
            # login page, so shipping it to the backend too would be dead CSS.
            # The "add it to both bundles" warning above is about sheets the
            # login page NEEDS; see the header comment in login.scss.
            'daf_uw_theme/static/src/scss/login.scss',
            # Frontend-ONLY for the same reason: its selectors exist only on the
            # branded 404 (views/error_templates.xml).  Must load AFTER
            # login.scss — that sheet is what re-declares --body-bg, --primary
            # and the radii for the whole frontend, and this one builds on them.
            'daf_uw_theme/static/src/scss/error_pages.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}