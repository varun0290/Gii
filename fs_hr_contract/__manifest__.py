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
    'depends': ['hr_contract', 'hr_payroll', 'l10n_ae_hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/hr_contract_view.xml',
        'views/hr_contract_update_wizard_views.xml',
        'views/hr_employee_views.xml',
        'data/hr_salary_rule_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
