# -*- coding: utf-8 -*-
{
    "name": "Employee Cost Tracking",
    "version": "17.0.1.0.0",
    "summary": "Centralized employee cost tracking with approval workflow",
    "description": """
        Employee Cost Tracking:
        - Capture all employee-related costs (hiring, renewals, cancellations, medical, self/family)
        - Fields: Employee, Cost Type, Amount, Department, Cost Centre, Effective Date, Notes, Attachment
        - Costs entered manually by HR
        - Standard Approvals workflow (HR review and approval)
        - Link costs to employee record for reporting
        - List view, filtering, and pivot for Cost-to-Hire dashboards by department and cost centre
    """,
    "category": "Human Resources",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": [
        "hr",
        "fs_hr_contract",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/hr_cost_centre_views.xml",
        "views/hr_employee_cost_views.xml",
        "views/menus.xml",
        "views/hr_employee_views.xml",
        "views/hr_contribution_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
