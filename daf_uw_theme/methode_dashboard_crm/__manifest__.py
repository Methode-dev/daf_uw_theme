{
    'name': 'Méthode Dashboard — CRM',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': "Pipeline widgets for the Méthode home dashboard",
    'description': "Contributes the CRM pipeline widget, stat tile, stalled-deal "
                   "insight and shortcut to the Methode home dashboard. "
                   "Auto-installs when both daf_uw_theme and crm are present.",
    'author': 'Méthode - Progiciel sur mesure',
    'website': 'https://methode.dev',
    'license': 'LGPL-3',
    'depends': ['daf_uw_theme', 'crm'],
    'data': [
        'data/dashboard_widget_type_data.xml',
    ],
    # Presence is the gate — see the note in the accounting bridge's manifest.
    'auto_install': True,
    'installable': True,
    'application': False,
}
