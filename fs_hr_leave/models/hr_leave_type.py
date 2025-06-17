
from odoo import api, fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    is_sick_leave = fields.Boolean(string="Supporting Documentn Mandatory")