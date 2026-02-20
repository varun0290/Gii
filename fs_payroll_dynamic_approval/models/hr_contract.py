# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    cut_off_override = fields.Boolean(
        string="Override Salary Cut-off Rule",
        default=False,
        tracking=True,
        help="When checked, HR can set the first salary payment month manually for this employee.",
    )
    manual_first_salary_month = fields.Date(
        string="Manual First Salary Month",
        help="Use when override is set. First month in which employee will be paid.",
    )
