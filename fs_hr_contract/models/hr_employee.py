# -*- coding: utf-8 -*-
from odoo import models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_open_contract_update_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update contract'),
            'res_model': 'hr.contract.update.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
