# -*- coding: utf-8 -*-
{
    "name": "HR Document Management & E-Sign",
    "version": "17.0.1.0.0",
    "summary": "Document templates, deployment, e-signatures & compliance tracking",
    "description": """
        Template Management:
        - Offer letters, employment contracts, AML, NDA, HR policies
        - Configurable per business entity (name, legal text, stamp, signing authority)
        - Templates dynamically populate employee data

        Document Deployment:
        - Bulk deployment to all employees or selected workgroups (department, location, role)
        - Narration and effective date per deployment

        Electronic Signatures & Audit:
        - Employees acknowledge / e-sign documents
        - Capture full name, employee code, date/time, signature confirmation
        - Track status: sent / viewed / signed
        - Automated reminders for pending acknowledgments

        Version Control & Storage:
        - Historical versions
        - Store signed documents against employee profile
        - Reports on deployment status, compliance, historical versions
    """,
    "category": "Human Resources",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": [
        "base",
        "hr",
        "mail",
        "portal",
        "website",
    ],
    "data": [
        "report/report_document_template_body.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/document_types_data.xml",
        "data/ir_cron_data.xml",
        "views/hr_document_template_views.xml",
        "views/hr_document_deployment_views.xml",
        "views/hr_employee_views.xml",
        "views/res_company_views.xml",
        "views/menus.xml",
        "report/deployment_status_report.xml",
        "views/portal_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "fs_hr_document_management/static/src/css/document_portal.css",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": True,
}
