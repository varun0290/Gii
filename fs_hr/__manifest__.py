# -*- coding: utf-8 -*-
{
    "name": "Fidobe HR",
    "version": "17.0",
    "description": """Fidobe HR""",
    "summary": "Fidobe HR",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "category": "Base",
    "depends": [
        'hr',
        'ent_saudi_gosi',
        'ent_uae_wps_report',
        'ent_hr_employee_updation',
        "ent_hr_gratuity_settlement",
    ],
    "data": [
        "views/views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": True,
    "auto_install": False,
}
