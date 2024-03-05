from odoo import models, fields

class HrContact(models.Model):
    _inherit = 'hr.contract'

    probation_date = fields.Date()

    def _crone_send_mail_to_hr_managers(self):
        employee_names = [contract.employee_id.name for 
            contract in self.search([('probation_date', '=', fields.Date.today())])]
        employee_names = list(filter(lambda x: isinstance(x, str) and len(x.strip()) > 0, employee_names))

        hr_managers = self.env.ref('hr.group_hr_manager').users or []
        hr_managers = list(filter(lambda x: isinstance(x.partner_id.email, str) and len(x.partner_id.email.strip()) > 0, hr_managers))

        if len(employee_names) > 0 and len(hr_managers) > 0:
            for hr_manager in hr_managers:
                self.env['mail.template'].browse([
                    self.env.ref('probation_date.probation_date_mail_template').id
                ]).with_context({
                    'hr_manager_name': hr_manager.name,
                    'email_from': self.env.company.email_formatted,
                    'email_to': hr_manager.partner_id.email,
                    'employee_names': ', '.join(employee_names or []),
                }).send_mail(False)
