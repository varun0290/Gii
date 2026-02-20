# -*- coding: utf-8 -*-

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError


# Fields locked once payslip is processed (done/paid)
PROTECTED_PAYSLIP_FIELDS = frozenset({
    'payroll_booking_month', 'first_salary_payment_month', 'eos_accrual_start_date',
    'cut_off_override', 'date_from', 'date_to', 'contract_id', 'employee_id',
})


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payroll_booking_month = fields.Char(
        string="Payroll Booking Month",
        compute="_compute_payroll_info",
        store=True,
        readonly=True,
        help="The month for which this payroll is booked.",
    )
    first_salary_payment_month = fields.Char(
        string="First Salary Payment Month",
        compute="_compute_payroll_info",
        store=True,
        readonly=False,
        help="Month when employee receives first salary. Based on join date and cut-off rule.",
    )
    eos_accrual_start_date = fields.Date(
        string="EOS Accrual Start Date",
        compute="_compute_payroll_info",
        store=True,
        readonly=True,
        help="Date from which End of Service accrual starts (typically contract start).",
    )
    cut_off_override = fields.Boolean(
        string="Override Cut-off Rule",
        default=False,
        help="When checked, HR/Payroll can set First Salary Payment Month manually.",
    )

    @api.depends('date_from', 'contract_id', 'employee_id', 'cut_off_override', 'first_salary_payment_month')
    def _compute_payroll_info(self):
        cut_off_day = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'fs_payroll_dynamic_approval.salary_cutoff_day', '25'
            )
        )
        for slip in self:
            # Payroll booking month
            if slip.date_from:
                slip.payroll_booking_month = slip.date_from.strftime('%B %Y')
            else:
                slip.payroll_booking_month = False

            # EOS accrual start date
            if slip.contract_id:
                slip.eos_accrual_start_date = slip.contract_id.date_start
            else:
                slip.eos_accrual_start_date = False

            # First salary payment month (cut-off rule)
            if slip.cut_off_override and slip.first_salary_payment_month:
                # Manual override - keep user value
                continue
            if slip.contract_id and slip.date_from:
                join_date = slip.contract_id.date_start
                if join_date.day <= cut_off_day:
                    # Join on/before cut-off → paid in same month
                    slip.first_salary_payment_month = join_date.strftime('%B %Y')
                else:
                    # Join after cut-off → paid next month
                    next_month = join_date + relativedelta(months=1)
                    slip.first_salary_payment_month = next_month.strftime('%B %Y')
            else:
                slip.first_salary_payment_month = (
                    slip.date_from.strftime('%B %Y') if slip.date_from else False
                )

    def write(self, vals):
        """Lock protected fields once payroll is processed."""
        if vals:
            locked = self.filtered(lambda s: s.state in ('done', 'paid'))
            if locked:
                protected = (set(vals.keys()) & PROTECTED_PAYSLIP_FIELDS) & set(self._fields.keys())
                if protected:
                    raise UserError(_(
                        "Cannot modify payroll data once payslip is processed (Done/Paid)."
                    ))
        return super().write(vals)
