{
    'name': 'Méthode Dashboard — Inventory',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': "Reorder and receipt widgets for the Méthode home dashboard",
    'description': "Contributes the inventory widgets and shortcut to the "
                   "Methode home dashboard. Auto-installs when both "
                   "daf_uw_theme and stock are present.",
    'author': 'Méthode - Progiciel sur mesure',
    'website': 'https://methode.dev',
    'license': 'LGPL-3',
    'depends': ['daf_uw_theme', 'stock'],
    'data': [
        'data/dashboard_widget_type_data.xml',
    ],
    'auto_install': True,
    'installable': True,
    'application': False,
}
