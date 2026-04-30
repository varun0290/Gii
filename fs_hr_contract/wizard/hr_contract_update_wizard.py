# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrContractUpdateWizard(models.TransientModel):
    _name = 'hr.contract.update.wizard'
    _description = 'Create new contract from existing (salary / dates)'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    source_contract_id = fields.Many2one(
        'hr.contract',
        string='Copy from contract',
        required=True,
        domain="[('employee_id', '=', employee_id), ('state', '!=', 'cancel'), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(related='employee_id.company_id', store=True)

    new_wage = fields.Monetary(
        string='New salary (wage)',
        required=True,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(related='employee_id.currency_id')

    effective_date_start = fields.Date(string='Effective start date', required=True)
    effective_date_end = fields.Date(string='End date')

    @api.onchange('employee_id')
    def _onchange_employee_id_contract(self):
        if self.employee_id:
            self.source_contract_id = self._guess_default_contract()

    def _guess_default_contract(self):
        self.ensure_one()
        emp = self.employee_id
        if not emp:
            return self.env['hr.contract']
        if emp.contract_id and emp.contract_id.state != 'cancel':
            return emp.contract_id
        open_c = emp.contract_ids.filtered(lambda c: c.state in ('open', 'probation'))
        if open_c:
            return open_c.sorted('date_start', reverse=True)[:1]
        candidates = emp.contract_ids.filtered(lambda c: c.state != 'cancel').sorted(
            key=lambda c: c.date_start or fields.Date.from_string('1970-01-01'),
            reverse=True,
        )
        return candidates[:1]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        eid = self.env.context.get('default_employee_id') or res.get('employee_id')
        if not eid and self.env.context.get('active_model') == 'hr.employee':
            aid = self.env.context.get('active_id')
            if aid:
                eid = aid
                if 'employee_id' in fields_list:
                    res['employee_id'] = eid

        if eid and not res.get('source_contract_id') and 'source_contract_id' in fields_list:
            emp = self.env['hr.employee'].browse(eid).exists()
            if emp:
                if emp.contract_id and emp.contract_id.state != 'cancel':
                    res['source_contract_id'] = emp.contract_id.id
                elif emp.contract_ids:
                    cand = emp.contract_ids.filtered(lambda c: c.state != 'cancel').sorted(
                        'date_start', reverse=True
                    )[:1]
                    if cand:
                        res['source_contract_id'] = cand.id

        tpl_id = res.get('source_contract_id')
        tpl = self.env['hr.contract'].browse(tpl_id).exists() if tpl_id else self.env['hr.contract']

        if tpl and ('new_wage' in fields_list) and not res.get('new_wage'):
            res['new_wage'] = tpl.wage

        today = fields.Date.today()
        if 'effective_date_start' in fields_list and not res.get('effective_date_start'):
            if tpl and tpl.date_start:
                res['effective_date_start'] = max(today, tpl.date_start)
            else:
                res['effective_date_start'] = today

        return res

    @api.constrains('effective_date_start', 'effective_date_end')
    def _check_wizard_dates(self):
        for wiz in self:
            if wiz.effective_date_end and wiz.effective_date_start and wiz.effective_date_end < wiz.effective_date_start:
                raise UserError(_('End date must be on or after the effective start date.'))

    def _prior_states_to_supersede(self):
        return frozenset(('open', 'probation'))

    def action_create_contract(self):
        self.ensure_one()
        src = self.source_contract_id
        if not src.exists() or src.employee_id != self.employee_id:
            raise UserError(_('Select a contract for this employee.'))
        start = self.effective_date_start
        end = self.effective_date_end or False

        if start <= src.date_start:
            raise UserError(_(
                'The effective start (%(start)s) must be after the source contract\'s start date (%(src)s).',
                start=start,
                src=src.date_start,
            ))

        if src.state in self._prior_states_to_supersede():
            close_day = start - relativedelta(days=1)
            src.with_context(skip_hr_contract_lock=True).write({
                'date_end': close_day,
                'state': 'close',
            })

        Contract = self.env['hr.contract']
        copy_vals = {
            'name': _('%s (new terms)', src.name)[:128],
            'wage': self.new_wage,
            'date_start': start,
            'date_end': end,
            'state': 'draft',
            'trial_date_end': False,
        }

        # Optional probation fields (when fs_hr_probation is installed)
        for fname in ('probation_review_3_feedback', 'probation_review_5_feedback'):
            if fname in Contract._fields:
                copy_vals[fname] = False
        if 'probation_final_decision' in Contract._fields:
            copy_vals['probation_final_decision'] = False
        for fname in ('probation_review_3_done', 'probation_review_5_done'):
            if fname in Contract._fields:
                copy_vals[fname] = False

        new_contract = src.with_context(skip_hr_contract_lock=True).copy(copy_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Contract'),
            'res_model': 'hr.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }
