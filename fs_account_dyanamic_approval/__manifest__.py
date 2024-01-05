# -*- coding: utf-8 -*-

{
    "name": "Account Dynamic Approval",
    "version": "17.0.1.0",
    "author": "Livbuzz Pvt. Ltd.",
    "website": "https://www.livbuzz.com",
    "support": "chirag@livbuzz.com",
    "category": "Accounting",
    "summary": "Dynamic Account Order Approval",
    "description": """Dynamic Account Order Approval""",
    "depends": [
        "base",
        "account",
        "bus",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_data.xml",
        "views/account_approval_line.xml",
        "views/account_approval_config.xml",
        "views/res_config_setting.xml",
        "views/account_approval_info.xml",
        "views/account_rejection_wizard.xml",
        "views/account_move_view.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
}
