{
    'name': 'Méthode Dashboard — Sales',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': "Quotation and order widgets for the Méthode home dashboard",
    'description': "Contributes the sales widgets, stat tile and shortcut to the "
                   "Methode home dashboard. Auto-installs when both "
                   "daf_uw_theme and sale are present.",
    'author': 'Méthode - Progiciel sur mesure',
    'website': 'https://methode.dev',
    'license': 'LGPL-3',
    'depends': ['daf_uw_theme', 'sale'],
    'data': [
        'data/dashboard_widget_type_data.xml',
    ],
    'auto_install': True,
    'installable': True,
    'application': False,
}
