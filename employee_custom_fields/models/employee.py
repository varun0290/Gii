from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class EmployeeCustom(models.Model):
    _inherit = 'hr.employee'

    # Personal Information
    emid = fields.Char(string='EMID')
    personal_email = fields.Char(string='Personal Email')
    resume = fields.Binary(string='Resume')
    attested_degree = fields.Binary(string='Attested Educational Degree')
    international_address = fields.Text(string='International Home Address')
    uae_address = fields.Text(string='UAE Address')
    # next_of_kin_name = fields.Char(string='Next of Kin Name')
    # next_of_kin_relationship = fields.Char(string='Next of Kin Relationship')
    # next_of_kin_mobile = fields.Char(string='Next of Kin Mobile No.')
    # family_status = fields.Selection([
    #     ('single', 'Single'),
    #     ('married', 'Married'),
    #     ('divorced', 'Divorced'),
    #     ('widow', 'Widow')
    # ], string='Family Status')
    # passport_number = fields.Char(string='Passport Number')
    # passport_issue_date = fields.Date(string='Passport Issue Date')
    # passport_expiry_date = fields.Date(string='Passport Expiry Date')
    primary_language = fields.Char(string='Primary Language')
    secondary_language = fields.Char(string='Secondary Language')
    additional_languages = fields.Char(string='Additional Languages Spoken')
    education_body = fields.Char(string='Education Body Name')
    degree_type = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other')
    ], string='Degree Type')
    field_of_study = fields.Char(string='Field of Study')
    emid_number = fields.Char(string='EMID No.')
    emid_issue_date = fields.Date(string='EMID Issue Date')
    emid_expiry_date = fields.Date(string='EMID Expiry Date')
    golden_visa_number = fields.Char(string='Golden Visa No.')
    golden_visa_issue_date = fields.Date(string='Golden Visa Issue Date')
    golden_visa_expiry_date = fields.Date(string='Golden Visa Expiry Date')
    labor_card_number = fields.Char(string='Labor Card No.')
    labor_card_issue_date = fields.Date(string='Labor Card Issue Date')
    labor_card_expiry_date = fields.Date(string='Labor Card Expiry Date')
    spouse_passport = fields.Binary(string='Spouse Passport')
    spouse_contact = fields.Char(string='Spouse Contact Details')
    kids_details = fields.Text(string='Kids Details')
    place_of_birth = fields.Char(string='Place of Birth')

    # Bank Information
    # bank_name = fields.Char(string='Bank Name')
    # branch_location = fields.Char(string='Branch Location')
    # swift_code = fields.Char(string='SWIFT Code')
    # account_type = fields.Char(string='Account Type')
    # iban = fields.Char(string='IBAN')

    # Payroll Information
    employee_code = fields.Char(string='Employee No.', compute='_compute_employee_code', store=True)
    total_salary = fields.Monetary(string='Total Salary')
    basic_salary = fields.Monetary(string='Basic (60%)', compute='_compute_salary_components', store=True)
    housing_allowance = fields.Monetary(string='Housing Allowance (20%)', compute='_compute_salary_components', store=True)
    transport_allowance = fields.Monetary(string='Transportation Allowance (20%)', compute='_compute_salary_components', store=True)
    gosi_employee = fields.Float(string='GOSI Employee Contribution (%)')
    gosi_employer = fields.Float(string='GOSI Employer Contribution (%)')
    gpssa_employee = fields.Float(string='GPSSA Employee Contribution (%)')
    gpssa_employer = fields.Float(string='GPSSA Employer Contribution (%)')

    # Promotions and Transfers
    previous_job_title = fields.Char(string='Previous Job Title')
    new_job_title = fields.Char(string='New Job Title')
    previous_department = fields.Char(string='Previous Department')
    new_department = fields.Char(string='New Department')
    promotion_date = fields.Date(string='Effective Date')
    promotion_reason = fields.Selection([
        ('performance', 'Performance'),
        ('org_need', 'Organizational Need'),
        ('employee_request', 'Employee Request'),
        ('role_elimination', 'Role Elimination'),
        ('dept_restructuring', 'Department Restructuring'),
        ('skill_match', 'Skill Match'),
        ('career_dev', 'Career Development'),
        ('other', 'Other')
    ], string='Reason for Promotion/Transfer')
    previous_salary = fields.Monetary(string='Previous Salary')
    new_salary = fields.Monetary(string='New Salary')
    previous_supervisor = fields.Char(string='Previous Supervisor')
    new_supervisor = fields.Char(string='New Supervisor')
    promotion_comments = fields.Text(string='Comments')

    # Performance Management
    review_date = fields.Date(string='Review Date')
    reviewer = fields.Char(string='Reviewer')
    review_type = fields.Selection([
        ('annual', 'Annual'),
        ('semi_annual', 'Semi-Annual'),
        ('quarterly', 'Quarterly'),
        ('monthly', 'Monthly')
    ], string='Review Type')
    review_comments = fields.Text(string='Comments')
    goals_set = fields.Text(string='Goals Set')
    areas_for_improvement = fields.Text(string='Areas for Improvement')
    review_form = fields.Binary(string='Form Upload')
    performance_score = fields.Selection([
        ('1', '1 - Unsatisfactory'),
        ('2', '2 - Needs Improvement'),
        ('3', '3 - Meets Expectations'),
        ('4', '4 - Exceeds Expectations'),
        ('5', '5 - Outstanding')
    ], string='Final Performance Scoring')
    agreed_training = fields.Text(string='Agreed Training Programs')
    promotion_recommendation = fields.Boolean(string='Promotion Recommendation')
    promotion_narrative = fields.Text(string='Promotion Purpose/Narrative')
    recommended_job_title = fields.Char(string='Recommended New Job Title')
    recommended_salary_increase = fields.Monetary(string='Recommended Salary Increase')
    promotion_approval_status = fields.Selection([
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected')
    ], string='Approval Status')
    promotion_approval_date = fields.Date(string='Approval Date')
    promotion_approval_authority = fields.Selection([
        ('line_manager', 'Line Manager'),
        ('hod', 'Head of Department'),
        ('ceo', 'CEO'),
        ('hr', 'HR')
    ], string='Approval Authority')
    promotion_notes = fields.Text(string='Additional Notes')

    # Learning and Development
    training_program = fields.Char(string='Program Name')
    training_provider = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External')
    ], string='Provider')
    training_start_date = fields.Date(string='Start Date')
    training_end_date = fields.Date(string='End Date')
    training_status = fields.Selection([
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('not_started', 'Not Started')
    ], string='Completion Status')
    training_certification = fields.Boolean(string='Certification Received')
    training_feedback = fields.Text(string='Feedback')

    # Access Information
    biometric_access = fields.Boolean(string='Biometric Access')
    odoo_access_level = fields.Selection([
        ('end_user', 'End User'),
        ('super_user', 'Super User')
    ], string='Odoo Access Level')

    # Work Information
    time_in_role = fields.Char(string='Time in Role', compute='_compute_time_in_role')
    probation_review_date = fields.Date(string='Interim Probation Review', compute='_compute_probation_dates')
    final_probation_date = fields.Date(string='Final Probation Review', compute='_compute_probation_dates')
    work_location = fields.Selection([
        ('emaar', 'Emaar Square Building no. 4, 7th floor'),
        ('convention', 'Convention Tower DWC, 12 floor'),
        ('capital', 'Capital Plaza complex Office16-01 Corniche Rd E -Al Danah Zone 1 Abu Dhabi')
    ], string='Work Location')
    working_hours = fields.Selection([
        ('shift1', 'Shift 1: 8:00-17:00 (GMT+4)'),
        ('shift2', 'Shift 2: 9:00-18:00 (GMT+4)'),
        ('shift3', 'Shift 3: Flexible Hours')
    ], string='Working Hours')
    employment_type = fields.Selection([
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('remote', 'Remote'),
        ('intern', 'Intern'),
        ('temp', 'Temp')
    ], string='Employment Type')

    @api.depends('total_salary')
    def _compute_salary_components(self):
        for employee in self:
            employee.basic_salary = employee.total_salary * 0.6
            employee.housing_allowance = employee.total_salary * 0.2
            employee.transport_allowance = employee.total_salary * 0.2

    @api.depends('create_date')
    def _compute_employee_code(self):
        for employee in self:
            if not employee.employee_code:
                if employee.create_date:
                    # For new employees - generate code
                    employee.employee_code = self.env['ir.sequence'].next_by_code('employee.code')
                else:
                    # For existing employees - pad with zeros
                    employee.employee_code = f"{int(employee.id):06d}"

    @api.depends('job_id.write_date')
    def _compute_time_in_role(self):
        for employee in self:
            if employee.job_id and employee.job_id.write_date:
                delta = fields.Date.today() - employee.job_id.write_date.date()
                years = delta.days // 365
                months = (delta.days % 365) // 30
                employee.time_in_role = f"{years} years, {months} months"
            else:
                employee.time_in_role = "N/A"

    @api.depends('create_date')
    def _compute_probation_dates(self):
        for employee in self:
            if employee.create_date:
                join_date = fields.Date.from_string(employee.create_date)
                employee.probation_review_date = join_date + relativedelta(months=+3)
                employee.final_probation_date = join_date + relativedelta(months=+5)
            else:
                employee.probation_review_date = False
                employee.final_probation_date = False