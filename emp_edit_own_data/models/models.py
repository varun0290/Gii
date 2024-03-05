from lxml import etree
from odoo import models, api, SUPERUSER_ID

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id, view_type, **options)
        if view_type in ['tree', 'form']:
            add_attr_to_arch = True
            arch = etree.fromstring(res["arch"])

            if any([
                self.env.user.has_group('emp_edit_own_data.group_emp_allow_edit_own_data'),
                self.env.user.has_group('hr.group_hr_manager'),
                self.env.user.id == SUPERUSER_ID,
            ]):
                add_attr_to_arch = False

            if add_attr_to_arch:
                for view in arch.xpath(f'//{view_type}'):
                    view.set('edit', "0")

            res["arch"] = etree.tostring(arch)
        return res
