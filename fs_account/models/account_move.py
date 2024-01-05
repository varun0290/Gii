# -*- coding: utf-8 -*-

from odoo import fields, api, models, _


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_distribution = fields.Json(required=True)
