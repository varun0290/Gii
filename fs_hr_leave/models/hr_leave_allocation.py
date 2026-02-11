from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.constrains('number_of_days_display', 'date_from', 'date_to')
    def check_zero_allocation(self):
        for record in self:
            if not record.holiday_status_id.allow_zero_allocation and record.number_of_days_display <= 0:
                raise UserError(_("Zero allocation is not allowed"))
