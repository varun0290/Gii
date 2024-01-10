from odoo import fields, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    department_ids = fields.Many2many("hr.department", string="Departments")
