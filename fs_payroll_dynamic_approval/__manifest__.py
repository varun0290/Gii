# -*- coding: utf-8 -*-
{
    "name": "Payroll Dynamic Approval",
    "version": "17.0.1.0.0",
    "summary": "Payroll batch approval, salary cut-off rules, and payment tracking",
    "description": """
        - Approval workflow for payroll batches (like Purchase Dynamic Approval)
        - Join vs booking cut-offs: configure salary payment (default 20) vs booking preview (default 25)
        - Contract previews: payroll booking month, first salary payment month, EOS accrual start
        - HR/Payroll overrides per contract or per payslip until payroll is Done/Paid
        - Locks eligibility fields after payroll is processed
    """,
    "category": "Human Resources/Payroll",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": [
        "hr_work_entry_contract_enterprise",
        "hr_payroll",
        "fs_base",
        "fs_hr_contract",
    ],
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
    "post_init_hook": "post_init_hook",
}
