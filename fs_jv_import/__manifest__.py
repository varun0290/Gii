{
    'name': 'Journal Entry Import',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Import journal entries from Excel files',
    'description': """
        Import journal entries from Excel files with mapping to Odoo accounts
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account', 'base_import'],
    'data': [
        'security/ir.model.access.csv',
        'views/jv_import_views.xml',
        # 'wizard/jv_import_wizard.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}