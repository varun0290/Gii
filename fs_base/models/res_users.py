from odoo import fields, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    department_ids = fields.Many2many("hr.department", string="Departments")
    can_edit_employee_registration_number = fields.Boolean(
        string="Can Edit Employee Registration Number",
        help="Allow this user to change the employee registration number field.",
    )
