# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_cost_ids = fields.One2many(
        'hr.employee.cost',
        'employee_id',
        string='Employee Costs',
        readonly=True,
    )
