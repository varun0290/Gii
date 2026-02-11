{
    'name': 'Fidobe HR Contract',
    'version': '17.0.1.0.0',
    'summary': 'Customizations for HR Contract',
    'description': """
        This module adds custom fields and approval process to HR Contracts.
    """,
    'category': 'Human Resources/Contracts',
    'author': 'Fidobe Solutions LLC',
    'website': 'https://www.fidobe.com/',
    'depends': ['hr_contract'],
    'data': [
        'security/security.xml',
        'views/hr_contract_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
