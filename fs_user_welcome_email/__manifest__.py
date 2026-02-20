# -*- coding: utf-8 -*-
{
    "name": "User Welcome / Invitation Email",
    "version": "17.0.1.0.0",
    "summary": "Custom welcome email for new users with company intro and login instructions",
    "description": """
        Customizes the invitation email sent when creating new users or when clicking
        "Send an Invitation Email". The email includes:
        - Welcome message
        - Introduction about the company / Odoo system
        - Login credentials (username) and link to set password
        - Clear login instructions
    """,
    "category": "Human Resources",
    "author": "Fidobe Solutions LLC",
    "website": "https://www.fidobe.com/",
    "depends": ["auth_signup", "mail"],
    "data": [
        "data/mail_template_data.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
