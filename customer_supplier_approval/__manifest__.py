# -*- coding: utf-8 -*-

{
    "name": "Customer/Supplier Approval",
    "version": "17.0.1.0",
    "summary": """ This module allows Users to validate or approve customers """,
    "description": """
        By this module, you can grant access to users to validate
        or approve partners. Then you will be able to select only
        approved partners on sales orders, purchase orders, 
        invoices, bills or delivery orders.
    """,
    "category": "Extra Tools",
    "author": " Cybrosys Techno Solutions",
    "company": "Cybrosys Techno Solutions",
    "maintainer": "Cybrosys Techno Solutions",
    "website": "https://www.cybrosys.com",
    "depends": [
        "base",
        "contacts",
        "stock",
        "sale_management",
        "account",
        "purchase",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
    ],
    "license": "AGPL-3",
    "images": ["static/description/banner.png"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
