from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HolidaysAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.onchange('holiday_status_id', 'number_of_days_display', 'date_from', 'date_to')
    def fs_check_zero_allocation(self):
        for record in self:
            # Skip validation if zero allocation is allowed
            if record.holiday_status_id.allow_zero_allocation:
                return

            # Check for zero or negative allocation
            if record.number_of_days_display <= 0:
                raise UserError(_("Zero allocation is not allowed"))