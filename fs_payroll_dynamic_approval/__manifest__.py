# -*- coding: utf-8 -*-
{
    "name": "Payroll Dynamic Approval",
    "version": "17.0.1.0.0",
    "summary": "Payroll batch approval, salary cut-off rules, and payment tracking",
    "description": """
        - Approval workflow for payroll batches (like Purchase Dynamic Approval)
        - Salary payment eligibility: join on/before 25th → paid same month; after 25th → next month
        - HR/Payroll override for cut-off rule
        - Display: Payroll booking month, First salary payment month, EOS accrual start date
        - Lock critical fields once payroll is processed
    """,
    "category": "Human Resources/Payroll",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": ["hr_payroll", "fs_base", "fs_hr_contract"],
    "data": [
        "security/ir.model.access.csv",
        "data/res_config_data.xml",
        "views/hr_payslip_run_views.xml",
        "views/hr_payslip_views.xml",
        "views/hr_contract_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
