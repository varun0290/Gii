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
    employee_cost_count = fields.Integer(
        string='Employee Cost Count',
        compute='_compute_employee_cost_count',
    )

    def _compute_employee_cost_count(self):
        for employee in self:
            employee.employee_cost_count = len(employee.employee_cost_ids)

    def action_view_employee_costs(self):
        self.ensure_one()
        action = self.env.ref('fs_hr_employee_cost.action_hr_employee_cost').read()[0]
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action
