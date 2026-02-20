# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salary_cutoff_day = fields.Integer(
        string="Salary Cut-off Day",
        config_parameter='fs_payroll_dynamic_approval.salary_cutoff_day',
        default=25,
        help="Join on/before this day → paid same month. Join after → paid next month.",
    )
