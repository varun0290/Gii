# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrEmployeeCost(models.Model):
    _name = 'hr.employee.cost'
    _description = 'Employee Cost'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='employee_id.company_id',
        store=True,
    )
    cost_type = fields.Selection([
        ('hiring', 'Hiring'),
        ('renewal', 'Renewal'),
        ('cancellation', 'Cancellation'),
        ('medical_self', 'Medical - Self'),
        ('medical_family', 'Medical - Family'),
        ('other', 'Other'),
    ], required=True, default='other', tracking=True)
    amount = fields.Monetary(
        required=True,
        currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        tracking=True,
        help='Override department; defaults from employee if not set.',
    )
    cost_centre_id = fields.Many2one(
        'hr.cost.centre',
        string='Cost Centre',
        tracking=True,
    )
    effective_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    notes = fields.Text(tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('wait_hr', 'Waiting HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, tracking=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.employee.cost'
                ) or _('New')
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and not self.department_id:
            self.department_id = self.employee_id.department_id

    def action_submit_for_approval(self):
        for record in self:
            if record.state != 'draft':
                continue
            record.write({'state': 'wait_hr'})

    def action_approve(self):
        if not self.env.user.has_group('fs_hr_contract.group_head_of_hr') and not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only Head of HR can approve."))
        for record in self:
            if record.state != 'wait_hr':
                continue
            record.write({'state': 'approved'})

    def action_reject(self):
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or self.env.user.has_group('base.group_system')):
            raise UserError(_("You are not authorized to reject."))
        for record in self:
            if record.state not in ('wait_hr',):
                continue
            record.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or self.env.user.has_group('base.group_system')):
            raise UserError(_("You are not authorized to reset to draft."))
        for record in self:
            record.write({'state': 'draft'})
