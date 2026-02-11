from odoo import models, fields

class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    is_carry_forward = fields.Boolean(string="Is Carry Forward")
