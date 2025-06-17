import datetime
from datetime import date

from odoo import models, fields, api, _


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    attachment_required = fields.Boolean(compute="_compute_attachment_required")

    @api.depends('number_of_days_display')
    def _compute_attachment_required(self):
        for leave in self:
            leave.attachment_required = False
            if leave.holiday_status_id.is_sick_leave and leave.number_of_days_display > 3:
                leave.attachment_required = True