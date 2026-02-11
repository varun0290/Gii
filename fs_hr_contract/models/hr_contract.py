from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrContract(models.Model):
    _inherit = 'hr.contract'

    state = fields.Selection(selection_add=[
        ('wait_hr', 'Waiting HR Approval'),
        ('wait_finance', 'Waiting Finance Approval')
    ], ondelete={'wait_hr': 'set default', 'wait_finance': 'set default'})

    # --- Employee Info ---
    employee_id_no = fields.Char(string="Employee ID No", related='employee_id.barcode', readonly=True)
    probation_period_months = fields.Selection([
        ('3', '3 Months'),
        ('6', '6 Months')
    ], string="Probation Period", default='3')

    # --- 1. Earnings ---
    vehicle_allowance = fields.Monetary(string="Vehicle Allowance")
    fixed_telephone_allowance = fields.Monetary(string="Fixed Telephone Allowance")
    fixed_vacation_ticket_allowance = fields.Monetary(string="Fixed Vacation Ticket Allowance")
    leave_travel_allowance = fields.Monetary(string="Leave Travel Allowance")
    medical_insurance_allowance = fields.Monetary(string="Medical Insurance Allowance")
    education_other_allowance = fields.Monetary(string="Education & Other Allowance")
    total_earnings = fields.Monetary(string="Total Earnings", compute='_compute_total_earnings', store=True)

    # --- 2. Additions ---
    arrears = fields.Monetary(string="Arrears")
    leave_encashment = fields.Monetary(string="Leave Encashment")
    reimbursement = fields.Monetary(string="Reimbursement")
    airfare = fields.Monetary(string="Airfare")
    other_additions = fields.Monetary(string="Other Additions")
    total_additions = fields.Monetary(string="Total Additions", compute='_compute_total_additions', store=True)

    # --- 3. Deductions ---
    leave_deduction = fields.Monetary(string="Leave Deduction")
    late_coming_deduction = fields.Monetary(string="Late Coming Deduction")
    absent_days_deduction = fields.Monetary(string="Absent Days Deduction")
    loan_repayment = fields.Monetary(string="Loan Repayment")
    gosi_deduction = fields.Monetary(string="GOSI Deduction (Social Security)")
    other_deductions = fields.Monetary(string="Other Deductions")
    vehicle_allowance_deduction = fields.Monetary(string="Vehicle Allowance Deduction")
    recurring_deductions = fields.Monetary(string="Recurring Deductions")
    total_deductions = fields.Monetary(string="Total Deductions", compute='_compute_total_deductions', store=True)

    # --- 4. Summary ---
    gross_salary = fields.Monetary(string="Gross Salary", compute='_compute_gross_salary', store=True)
    net_salary = fields.Monetary(string="Net Salary", compute='_compute_net_salary', store=True)
    total_cash_compensation = fields.Monetary(string="Total Cash Compensation", compute='_compute_total_cash_compensation', store=True)

    # --- 5. Pension ---
    employer_pension_contribution = fields.Monetary(string="Employer Pension Contribution")
    employee_pension_contribution = fields.Monetary(string="Employee Pension Contribution")

    # --- Increment/Bonus ---
    bonus = fields.Monetary(string="Bonus")
    special_increment = fields.Monetary(string="Special Increment")
    promotion_adjustment = fields.Monetary(string="Promotion Adjustment")
    performance_incentives = fields.Monetary(string="Performance Incentives")
    one_time_rewards = fields.Monetary(string="One-Time Rewards")


    @api.depends('wage', 'vehicle_allowance', 'fixed_telephone_allowance', 'fixed_vacation_ticket_allowance',
                 'leave_travel_allowance', 'medical_insurance_allowance', 'education_other_allowance')
    def _compute_total_earnings(self):
        for record in self:
            record.total_earnings = (
                record.wage +
                record.vehicle_allowance +
                record.fixed_telephone_allowance +
                record.fixed_vacation_ticket_allowance +
                record.leave_travel_allowance +
                record.medical_insurance_allowance +
                record.education_other_allowance
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

    def action_submit_for_approval(self):
        for record in self:
            record.write({'state': 'wait_hr'})

    def action_approve_hr(self):
        # Check permissions for Head of HR group
        if not self.env.user.has_group('fs_hr_contract.group_head_of_hr') and not self.env.user.has_group('base.group_system'):
             raise UserError(_("You are not authorized to perform this action. Only Head of HR can approve."))
        for record in self:
            record.write({'state': 'wait_finance'})

    def action_approve_finance(self):
        # Check permissions for VP Finance group
        if not self.env.user.has_group('fs_hr_contract.group_vp_finance') and not self.env.user.has_group('base.group_system'):
             raise UserError(_("You are not authorized to perform this action. Only VP Finance can approve."))
        for record in self:
            record.write({'state': 'open'})

    def action_reject(self):
        # Rejection moves back to draft
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or 
                self.env.user.has_group('fs_hr_contract.group_vp_finance') or
                self.env.user.has_group('base.group_system')):
             raise UserError(_("You are not authorized to reject."))
        for record in self:
            record.write({'state': 'draft'})
