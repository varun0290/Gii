{
    'name': 'Gil Importer',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Import journal from Excel files',
    'description': """
        Import journal from Excel files with mapping to Odoo accounts
    """,
    'author': 'Fidobe Solutions LLC',
    'website': 'https://www.fidobe.com',
    'depends': ['account', 'base_import'],
    'data': [
        'security/ir.model.access.csv',
        'views/importer_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}