{
    'name': 'Employee Custom Fields',
    'version': '1.0',
    'summary': 'Extended employee fields for GII',
    'description': """
        Adds all custom employee fields as per GII requirements
        including employment information, personal details, payroll, etc.
    """,
    'author': 'Fidobe Solutions LLC',
    'website': 'https://www.fidobe.com',
    'category': 'Human Resources',
    'depends': ['base', 'hr', 'hr_contract', 'hr_payroll'],
    'data': [
        'views/employee_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}