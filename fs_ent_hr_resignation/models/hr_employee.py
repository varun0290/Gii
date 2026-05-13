# -*- coding: utf-8 -*-
from odoo import api, models

CTX_SKIP = 'skip_fs_ent_resignation_sync'


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def write(self, vals):
        if self.env.context.get(CTX_SKIP):
            return super().write(vals)

        res = super().write(vals)
        touched = frozenset(vals) & frozenset({'departure_reason_id', 'active'})
        if touched and 'resigned' in self._fields:
            self._sync_openhr_flags_from_standard_reason()
        return res

    @api.model
    def _bootstrap_resign_flags_from_departure_reason(self):
        """Align OpenHR booleans after employees were archived via the standard wizard."""
        env = self.env
        # Archived employees are the exact records that drive the "Resigned" /
        # "Fired" filters, so the bootstrap must ignore the default active_test.
        Employee = env['hr.employee'].sudo().with_context(active_test=False)
        if 'resigned' not in Employee._fields or 'departure_reason_id' not in Employee._fields:
            return

        resigned_ref = Employee.env.ref('hr.departure_resigned', raise_if_not_found=False)
        fired_ref = Employee.env.ref('hr.departure_fired', raise_if_not_found=False)

        if resigned_ref:
            chunk = Employee.search([('departure_reason_id', '=', resigned_ref.id)])
            if chunk:
                chunk.with_context(**{CTX_SKIP: True}).with_context(mail_create_nolog=True).write({
                    'resigned': True, 'fired': False,
                })
        if fired_ref:
            chunk_f = Employee.search([('departure_reason_id', '=', fired_ref.id)])
            if chunk_f:
                chunk_f.with_context(**{CTX_SKIP: True}).with_context(mail_create_nolog=True).write({
                    'fired': True, 'resigned': False,
                })

    def _sync_openhr_flags_from_standard_reason(self):
        if 'resigned' not in self._fields or 'departure_reason_id' not in self._fields:
            return

        resigned_ref = self.env.ref('hr.departure_resigned', raise_if_not_found=False)
        fired_ref = self.env.ref('hr.departure_fired', raise_if_not_found=False)

        for emp in self:
            if resigned_ref and emp.departure_reason_id == resigned_ref:
                target_r, target_f = True, False
            elif fired_ref and emp.departure_reason_id == fired_ref:
                target_r, target_f = False, True
            elif emp.departure_reason_id:
                target_r, target_f = False, False
            elif not emp.departure_reason_id:
                continue

            if emp.resigned == target_r and emp.fired == target_f:
                continue
            emp.with_context(**{CTX_SKIP: True}).write({'resigned': target_r, 'fired': target_f})
