{
    'name': 'FS HR Probation Review',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Structured probation review process for Odoo 17',
    'description': """
        Implements a structured probation review process:
        - Contract moves to 'Probation' after approval.
        - 3rd and 5th month review notifications.
        - Review wizard for line managers.
        - Automatic state change to 'Running' (Open) upon 5th month approval.
        - Automatic email and confirmation letter generation.
    """,
    'author': 'Antigravity',
    'depends': ['hr_contract', 'fs_hr_contract', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'wizard/hr_contract_probation_review_wizard_views.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
