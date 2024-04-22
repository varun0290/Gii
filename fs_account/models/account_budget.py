# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class CrossoveredBudgetLines(models.Model):
    _inherit = "crossovered.budget.lines"

    balance = fields.Float(compute="_compute_balance", string="Balance")

    def _compute_balance(self):
        for line in self:
            line.balance = line.planned_amount + line.practical_amount

class CrossoveredBudget(models.Model):
    _inherit = "crossovered.budget"

    total_balance = fields.Float(compute="_compute_totals", string="Total Balance")
    total_planned_amount = fields.Float(compute="_compute_totals", string="Total Planned Amount")

    def _compute_totals(self):
        for cb in self:
            cb.total_balance = 0.0
            cb.total_planned_amount = 0.0
            for line in cb.crossovered_budget_line:
                cb.total_balance += line.balance
                cb.total_planned_amount += line.planned_amount
