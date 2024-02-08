# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    balance = fields.Float(compute="_compute_balance", string="Balance")

    def _compute_balance(self):
        for line in self:
            line.balance = line.planned_amount + line.practical_amount
