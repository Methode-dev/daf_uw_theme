{
    'name': 'Méthode Dashboard — Accounting',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': "Invoice and receivable widgets for the Méthode home dashboard",
    'description': "Contributes the accounting widgets, stat tiles, insight "
                   "banners and shortcuts to the Methode home dashboard. "
                   "Auto-installs when both daf_uw_theme and account are "
                   "present, and uninstalls with either of them.",
    'author': 'Méthode - Progiciel sur mesure',
    'website': 'https://methode.dev',
    'license': 'LGPL-3',
    'depends': ['daf_uw_theme', 'account'],
    'data': [
        'data/dashboard_widget_type_data.xml',
    ],
    # ⚠ THIS IS THE GATE.  HOMEPAGE_DASHBOARD_PLAN §4: "A widget gated on an app
    # ships from a bridge module that depends on that app and auto-installs.
    # Presence is the gate."  So there is no module_name field and no
    # _installed_modules() scan anywhere — this module exists exactly when
    # `account` does, and uninstalling account takes the widget records, the
    # fetchers, the stat tiles and the insight rules with it in one move.
    'auto_install': True,
    'installable': True,
    'application': False,
}
