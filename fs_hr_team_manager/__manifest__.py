# -*- coding: utf-8 -*-
{
    "name": "HR Team Manager Access",
    "version": "17.0.1.0.0",
    "summary": "Dedicated HR access group scoped to the manager's team (reporting hierarchy)",
    "category": "Human Resources",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": [
        "hr",
        "hr_contract",
        "hr_holidays",
        "hr_payroll",
        "hr_work_entry_contract_enterprise",
        "fs_hr_leave",
        "fs_hr_contract",
        "fs_hr_document_management",
        "fs_hr_employee_cost",
    ],
    "data": [
        "security/fs_hr_team_manager_groups.xml",
        "security/ir.model.access.csv",
        "security/fs_hr_team_manager_rules.xml",
        "views/fs_hr_team_manager_menus.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
