from odoo import _, models
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def write(self, vals):
        if "registration_number" in vals and not self.env.su:
            allowed = (
                self.env.user.has_group("base.group_system")
                or self.env.user.can_edit_employee_registration_number
            )
            if not allowed:
                for employee in self:
                    if employee.registration_number != vals["registration_number"]:
                        raise AccessError(
                            _(
                                "You are not allowed to change the employee registration number."
                            )
                        )
        return super().write(vals)
