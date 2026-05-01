# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .salary_calendar_utils import (
    first_month_start_from_join,
    get_booking_cutoff,
    get_join_cutoff,
    month_label,
)

CTX_SKIP_PAYROLL_LOCK = 'skip_payroll_eligibility_field_lock'

# Contract fields HR may no longer edit after any payslip is done/paid on this contract
PAYROLL_ELIGIBILITY_LOCK_FIELDS = frozenset({
    'cut_off_override',
    'manual_first_salary_month',
})


class HrContract(models.Model):
    _inherit = 'hr.contract'

    cut_off_override = fields.Boolean(
        string="Override salary payment month rule",
        default=False,
        tracking=True,
        help="HR/Payroll can override the automated join-day cut-off rule for this contract.",
    )
    manual_first_salary_month = fields.Date(
        string="Manual first salary payment month",
        help="Any date in the month when the employee should first be paid (used when override is enabled).",
        tracking=True,
    )

    payroll_dates_locked = fields.Boolean(
        string="Payroll eligibility locked",
        compute='_compute_payroll_dates_locked',
        help="True once at least one payslip for this contract is Done or Paid.",
    )
    preview_payroll_booking_month = fields.Char(
        string="Payroll booking month (preview)",
        compute='_compute_payroll_eligibility_preview',
        help="Expected accounting/booking month for the first payroll run from contract start, "
             "using the payroll booking cut-off (Settings).",
    )
    preview_first_salary_payment_month = fields.Char(
        string="First salary payment month (preview)",
        compute='_compute_payroll_eligibility_preview',
        help="Expected first month in which salary is paid, using the join cut-off (Settings) "
             "or the manual month when override is enabled.",
    )
    preview_eos_accrual_start_date = fields.Date(
        string="EOS accrual start (preview)",
        compute='_compute_payroll_eligibility_preview',
        help="Date from which End of Service accrual is recognised (contract start).",
    )

    def _compute_payroll_dates_locked(self):
        real_ids = [rid for rid in self.ids if isinstance(rid, int) and rid > 0]
        if not real_ids:
            for contract in self:
                contract.payroll_dates_locked = False
            return
        PaySlip = self.env['hr.payslip'].sudo()
        processed_ids = PaySlip.search([
            ('contract_id', 'in', real_ids),
            ('state', 'in', ('done', 'paid')),
        ]).mapped('contract_id').ids
        frozen = frozenset(processed_ids)
        for contract in self:
            cid = contract.id
            contract.payroll_dates_locked = cid in frozen if isinstance(cid, int) and cid > 0 else False

    @api.depends(
        'date_start',
        'cut_off_override',
        'manual_first_salary_month',
    )
    def _compute_payroll_eligibility_preview(self):
        for contract in self:
            contract.preview_eos_accrual_start_date = contract.date_start
            if not contract.date_start:
                contract.preview_payroll_booking_month = False
                contract.preview_first_salary_payment_month = False
                continue

            join_c = get_join_cutoff(contract.env)
            book_c = get_booking_cutoff(contract.env)

            if contract.cut_off_override and contract.manual_first_salary_month:
                m = contract.manual_first_salary_month.replace(day=1)
                contract.preview_first_salary_payment_month = month_label(m)
                contract.preview_payroll_booking_month = month_label(m)
            else:
                pay_m = first_month_start_from_join(contract.date_start, join_c)
                book_m = first_month_start_from_join(contract.date_start, book_c)
                contract.preview_first_salary_payment_month = month_label(pay_m)
                contract.preview_payroll_booking_month = month_label(book_m)

    def write(self, vals):
        if not self.env.context.get(CTX_SKIP_PAYROLL_LOCK) and vals:
            locked = self.filtered(lambda c: c.payroll_dates_locked)
            if locked:
                touched = set(vals) & PAYROLL_ELIGIBILITY_LOCK_FIELDS & set(self._fields)
                if touched:
                    raise UserError(_(
                        "Payroll eligibility settings cannot be changed after payslips have been "
                        "processed (Done/Paid) for this contract: %(fields)s",
                    ) % {'fields': ", ".join(touched)})
        return super().write(vals)
