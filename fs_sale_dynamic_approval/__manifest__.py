# -*- coding: utf-8 -*-

{
    "name": "Sales Dynamic Approval",
    "version": "17.0.1.0",
    "author": "Livbuzz Pvt. Ltd.",
    "website": "https://www.livbuzz.com",
    "support": "support@fidobe.com",
    "category": "Sales",
    "summary": "Sales Dynamic Approval",
    "description": """Sales Dynamic Approval""",
    "depends": ["sale", "bus"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_data.xml",
        "views/sale_approval_line.xml",
        "views/sale_approval_config.xml",
        "views/res_config_setting.xml",
        "views/approval_info.xml",
        "views/rejection_wizard.xml",
        "views/inherit_sale_view.xml",
    ],
    "license": "OPL-1",
    "images": [
        "static/description/background.png",
    ],
    "auto_install": False,
    "installable": True,
    "application": True,
}
