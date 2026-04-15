from odoo import models, fields, api, _
from odoo.exceptions import UserError


# Fields that may not be edited after the contract is submitted for approval
# (state in wait_hr, wait_finance, open, close, cancel)
PROTECTED_CONTRACT_FIELDS = frozenset({
    # Standard hr.contract
    'name', 'active', 'employee_id', 'date_start', 'date_end', 'trial_date_end',
    'wage', 'structure_type_id', 'resource_calendar_id', 'department_id', 'job_id',
    'contract_type_id', 'notes', 'hr_responsible_id',
    'permit_no', 'visa_no', 'company_id',
    # ent_ohrms_overtime
    'over_day', 'over_hour',
    # l10n_ae UAE localization (if installed)
    'l10n_ae_housing_allowance', 'l10n_ae_transportation_allowance', 'l10n_ae_other_allowances',
    # fs_hr_contract custom fields
    'probation_period_months',
    'vehicle_allowance', 'fixed_telephone_allowance', 'fixed_vacation_ticket_allowance',
    'leave_travel_allowance', 'medical_insurance_allowance', 'education_other_allowance',
    'arrears', 'leave_encashment', 'reimbursement', 'airfare', 'other_additions',
    'leave_deduction', 'late_coming_deduction', 'absent_days_deduction', 'loan_repayment',
    'gosi_deduction', 'other_deductions', 'vehicle_allowance_deduction', 'recurring_deductions',
    'employer_pension_contribution', 'employee_pension_contribution',
    'bonus', 'special_increment', 'promotion_adjustment', 'performance_incentives',
    'one_time_rewards',
})



class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Ensure notes and salary fields have tracking for field change history
    notes = fields.Html(tracking=True)
    wage = fields.Monetary(tracking=True)
    l10n_ae_housing_allowance = fields.Monetary(tracking=True)
    l10n_ae_transportation_allowance = fields.Monetary(tracking=True)
    l10n_ae_other_allowances = fields.Monetary(tracking=True)
    over_day = fields.Float(tracking=True)
    over_hour = fields.Float(tracking=True)

    state = fields.Selection(
        selection_add=[
            ('wait_hr', 'Waiting HR Approval'),
            ('wait_finance', 'Waiting Finance Approval'),
        ],
        ondelete={'wait_hr': 'set default', 'wait_finance': 'set default'},
    )

    # --- Employee Info ---
    employee_id_no = fields.Char(string="Employee ID No", related='employee_id.barcode', readonly=True)
    probation_period_months = fields.Selection([
        ('3', '3 Months'),
        ('6', '6 Months')
    ], string="Probation Period", default='3', tracking=True)

    # --- 1. Earnings ---
    vehicle_allowance = fields.Monetary(string="Vehicle Allowance", tracking=True)
    fixed_telephone_allowance = fields.Monetary(string="Fixed Telephone Allowance", tracking=True)
    fixed_vacation_ticket_allowance = fields.Monetary(string="Fixed Vacation Ticket Allowance", tracking=True)
    leave_travel_allowance = fields.Monetary(string="Leave Travel Allowance", tracking=True)
    medical_insurance_allowance = fields.Monetary(string="Medical Insurance Allowance", tracking=True)
    education_other_allowance = fields.Monetary(string="Education & Other Allowance", tracking=True)
    total_earnings = fields.Monetary(string="Total Earnings", compute='_compute_total_earnings', store=True, tracking=True)

    # --- 2. Additions ---
    arrears = fields.Monetary(string="Arrears", tracking=True)
    leave_encashment = fields.Monetary(string="Leave Encashment", tracking=True)
    reimbursement = fields.Monetary(string="Reimbursement", tracking=True)
    airfare = fields.Monetary(string="Airfare", tracking=True)
    other_additions = fields.Monetary(string="Other Additions", tracking=True)
    total_additions = fields.Monetary(string="Total Additions", compute='_compute_total_additions', store=True, tracking=True)

    # --- 3. Deductions ---
    leave_deduction = fields.Monetary(string="Leave Deduction", tracking=True)
    late_coming_deduction = fields.Monetary(string="Late Coming Deduction", tracking=True)
    absent_days_deduction = fields.Monetary(string="Absent Days Deduction", tracking=True)
    loan_repayment = fields.Monetary(string="Loan Repayment", tracking=True)
    gosi_deduction = fields.Monetary(string="GOSI Deduction (Social Security)", tracking=True)
    other_deductions = fields.Monetary(string="Other Deductions", tracking=True)
    vehicle_allowance_deduction = fields.Monetary(string="Vehicle Allowance Deduction", tracking=True)
    recurring_deductions = fields.Monetary(string="Recurring Deductions", tracking=True)
    total_deductions = fields.Monetary(string="Total Deductions", compute='_compute_total_deductions', store=True, tracking=True)

    # --- 4. Summary ---
    gross_salary = fields.Monetary(string="Gross Salary", compute='_compute_gross_salary', store=True, tracking=True)
    net_salary = fields.Monetary(string="Net Salary", compute='_compute_net_salary', store=True, tracking=True)
    total_cash_compensation = fields.Monetary(string="Total Cash Compensation", compute='_compute_total_cash_compensation', store=True, tracking=True)

    # --- 5. Pension ---
    employer_pension_contribution = fields.Monetary(string="Employer Pension Contribution", tracking=True)
    employee_pension_contribution = fields.Monetary(string="Employee Pension Contribution", tracking=True)

    # --- Increment/Bonus ---
    bonus = fields.Monetary(string="Bonus", tracking=True)
    special_increment = fields.Monetary(string="Special Increment", tracking=True)
    promotion_adjustment = fields.Monetary(string="Promotion Adjustment", tracking=True)
    performance_incentives = fields.Monetary(string="Performance Incentives", tracking=True)
    one_time_rewards = fields.Monetary(string="One-Time Rewards", tracking=True)


    @api.depends('wage', 'vehicle_allowance', 'fixed_telephone_allowance', 'fixed_vacation_ticket_allowance',
                 'leave_travel_allowance', 'medical_insurance_allowance', 'education_other_allowance',
                 'l10n_ae_housing_allowance', 'l10n_ae_transportation_allowance', 'l10n_ae_other_allowances')
    def _compute_total_earnings(self):
        for record in self:
            record.total_earnings = (
                (record.wage or 0.0) +
                (record.l10n_ae_housing_allowance or 0.0) +
                (record.l10n_ae_transportation_allowance or 0.0) +
                (record.l10n_ae_other_allowances or 0.0) +
                (record.vehicle_allowance or 0.0) +
                (record.fixed_telephone_allowance or 0.0) +
                (record.fixed_vacation_ticket_allowance or 0.0) +
                (record.leave_travel_allowance or 0.0) +
                (record.medical_insurance_allowance or 0.0) +
                (record.education_other_allowance or 0.0)
            )

    @api.depends('arrears', 'leave_encashment', 'reimbursement', 'airfare', 'other_additions')
    def _compute_total_additions(self):
        for record in self:
            record.total_additions = (
                record.arrears +
                record.leave_encashment +
                record.reimbursement +
                record.airfare +
                record.other_additions
            )

    @api.depends('leave_deduction', 'late_coming_deduction', 'absent_days_deduction', 'loan_repayment',
                 'gosi_deduction', 'other_deductions', 'vehicle_allowance_deduction', 'recurring_deductions')
    def _compute_total_deductions(self):
        for record in self:
            record.total_deductions = (
                record.leave_deduction +
                record.late_coming_deduction +
                record.absent_days_deduction +
                record.loan_repayment +
                record.gosi_deduction +
                record.other_deductions +
                record.vehicle_allowance_deduction +
                record.recurring_deductions
            )

    @api.depends('total_earnings')
    def _compute_gross_salary(self):
        for record in self:
            record.gross_salary = record.total_earnings

    @api.depends('gross_salary', 'total_additions', 'total_deductions')
    def _compute_net_salary(self):
        for record in self:
            record.net_salary = record.gross_salary + record.total_additions - record.total_deductions

    @api.depends('net_salary', 'employer_pension_contribution')
    def _compute_total_cash_compensation(self):
        for record in self:
            # Assuming Total Cash Compensation is Net Salary + Employer Pension Contribution?
            # Or just Net Salary? Usually Compensation means Cost to Company or Take Home.
            # I'll default to Net Salary + Employer Pension for "Total Package".
            # But "Cash Compensation" usually implies what the employee gets.
            # I'll set it as Net Salary for now, user can correct if needed.
            # Actually, "Total Cash Compensation" often strictly means base + variable cash.
            # I will assume it = Net Salary for now.
            record.total_cash_compensation = record.net_salary

    def write(self, vals):
        """Block editing of contract fields after submission for approval."""
        if not self._context.get('skip_hr_contract_lock') and vals:
            # We lock the contract if it is in any stage other than Draft or Probation
            locked_states = ('wait_hr', 'wait_finance', 'open', 'close', 'cancel')
            locked_records = self.filtered(lambda c: c.state in locked_states)
            
            if locked_records:
                protected_in_vals = (set(vals.keys()) & PROTECTED_CONTRACT_FIELDS) & set(self._fields.keys())
                other_than_state = protected_in_vals - {'state'}
                
                if other_than_state:
                    raise UserError(_(
                        "Contract fields (%s) cannot be modified after submission for approval. "
                        "Use 'Reset to Draft' to make changes."
                    ) % ", ".join(other_than_state))
        return super().write(vals)

    def action_submit_for_approval(self):
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'wait_hr'})

    def action_approve_hr(self):
        # Check permissions for Head of HR group
        if not self.env.user.has_group('fs_hr_contract.group_head_of_hr') and not self.env.user.has_group('base.group_system'):
             raise UserError(_("You are not authorized to perform this action. Only Head of HR can approve."))
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'wait_finance'})

    def action_approve_finance(self):
        # Check permissions for VP Finance group
        if not self.env.user.has_group('fs_hr_contract.group_vp_finance') and not self.env.user.has_group('base.group_system'):
             raise UserError(_("You are not authorized to perform this action. Only VP Finance can approve."))
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'open'})

    def action_reject(self):
        # Rejection moves back to draft
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or 
                self.env.user.has_group('fs_hr_contract.group_vp_finance') or
                self.env.user.has_group('base.group_system')):
             raise UserError(_("You are not authorized to reject."))
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'draft'})

    def action_reset_to_draft(self):
        # Allow relevant groups to reset to draft
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or 
                self.env.user.has_group('fs_hr_contract.group_vp_finance') or
                self.env.user.has_group('base.group_system')):
             raise UserError(_("You are not authorized to reset to draft."))
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'draft'})

    def sorted(self, key=None, reverse=False):
        """
        Targeted fix for Odoo Enterprise KeyError on custom states ('wait_hr', 'wait_finance').
        The hr_work_entry_holidays module hardcodes contract states in its write() sorting logic
        using a literal dictionary: {'open': 1, 'close': 2, 'draft': 3, 'cancel': 4}.
        We intercept the KeyError and provide a safe fallback priority (3, matching 'draft').
        """
        if key and callable(key):
            orig_key = key
            def wrapped_key(rec):
                try:
                    return orig_key(rec)
                except KeyError as e:
                    field_val = str(e).strip("'\"")
                    if field_val in ('wait_hr', 'wait_finance'):
                        return 3 # 'draft' priority
                    raise e
            return super().sorted(key=wrapped_key, reverse=reverse)
        return super().sorted(key=key, reverse=reverse)
