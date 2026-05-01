# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .salary_calendar_utils import (
    first_month_start_from_join,
    get_join_cutoff,
    month_label,
)

PROTECTED_PAYSLIP_FIELDS = frozenset({
    'payroll_booking_month',
    'first_salary_payment_month',
    'eos_accrual_start_date',
    'cut_off_override',
    'first_salary_month_override',
    'date_from',
    'date_to',
    'contract_id',
    'employee_id',
})

PROCESSED_SLIP_STATES = frozenset(('done', 'paid'))


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    payroll_booking_month = fields.Char(
        string="Payroll booking month",
        compute='_compute_payroll_info',
        store=True,
        readonly=True,
        help="Accounting month for this payslip (from the wage period date from).",
    )
    first_salary_payment_month = fields.Char(
        string="First salary payment month",
        compute='_compute_payroll_info',
        store=True,
        readonly=True,
        help="Calendar month used for first salary payout (join-day cut‑off vs override).",
    )
    eos_accrual_start_date = fields.Date(
        string="EOS accrual start date",
        compute='_compute_payroll_info',
        store=True,
        readonly=True,
        help="Usually the employee's contract start date for End of Service accrual.",
    )
    cut_off_override = fields.Boolean(
        string="Override on this payslip",
        default=False,
        help="When set, use “Manual first salary payment month” below instead of rules from the "
             "employee's contract.",
    )
    first_salary_month_override = fields.Date(
        string="Manual first salary payment month (payslip)",
        help="Any date inside the calendar month used for pay when this payslip override is enabled.",
    )

    @api.depends(
        'date_from',
        'contract_id',
        'contract_id.date_start',
        'contract_id.cut_off_override',
        'contract_id.manual_first_salary_month',
        'cut_off_override',
        'first_salary_month_override',
    )
    def _compute_payroll_info(self):
        join_cut = get_join_cutoff(self.env)
        for slip in self:
            if slip.date_from:
                slip.payroll_booking_month = slip.date_from.strftime('%B %Y')
            else:
                slip.payroll_booking_month = False

            contract = slip.contract_id
            if contract:
                slip.eos_accrual_start_date = contract.date_start
            else:
                slip.eos_accrual_start_date = False

            join = contract.date_start if contract else False
            if not join:
                slip.first_salary_payment_month = (
                    slip.date_from.strftime('%B %Y') if slip.date_from else False
                )
                continue

            if slip.cut_off_override and slip.first_salary_month_override:
                m = slip.first_salary_month_override.replace(day=1)
                slip.first_salary_payment_month = month_label(m)
            elif contract.cut_off_override and contract.manual_first_salary_month:
                m = contract.manual_first_salary_month.replace(day=1)
                slip.first_salary_payment_month = month_label(m)
            else:
                pay_m = first_month_start_from_join(join, join_cut)
                slip.first_salary_payment_month = month_label(pay_m)

    def write(self, vals):
        if vals and not self.env.context.get('skip_payroll_payslip_lock'):
            locked = self.filtered(lambda s: s.state in PROCESSED_SLIP_STATES)
            if locked:
                touched = set(vals) & PROTECTED_PAYSLIP_FIELDS & set(self._fields)
                if touched:
                    raise UserError(_(
                        "Cannot modify payroll eligibility / period fields once a payslip is Done or Paid."
                    ))
        return super().write(vals)
