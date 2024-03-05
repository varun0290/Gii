# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Probation date",
    "version": "17.0",
    "author": "Harprit",
    "summary": "Probation date",
    "website": "www.livbuzz.com",
    "license": "AGPL-3",
    "depends": ['hr_payroll'],
    "category": "Employees",
    "data": [
        "data/mail_template.xml",
        "data/ir_cron.xml",
        "views/views.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
