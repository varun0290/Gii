# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salary_join_cutoff_day = fields.Integer(
        string="Salary payment join cut-off day",
        config_parameter='fs_payroll_dynamic_approval.salary_join_cutoff_day',
        default=20,
        help="Join on or before this calendar day → first salary paid in that month. Join after "
             "this day → first salary moves to next month.",
    )
    payroll_booking_cutoff_day = fields.Integer(
        string="Payroll booking cut-off day",
        config_parameter='fs_payroll_dynamic_approval.payroll_booking_cutoff_day',
        default=25,
        help="Used only for previewing payroll booking timing from contract start. "
             "The employee contract form shows booked vs payable month when these differ.",
    )
