# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrContribution(models.Model):
    _name = 'hr.contribution'
    _description = 'Employee Contribution'
    _order = 'date desc, id desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    date = fields.Date(
        string='Contribution Date',
        required=True,
        default=fields.Date.context_today,
    )
    contribution_month = fields.Char(
        string='Contribution Month',
        compute='_compute_contribution_month',
        store=True,
    )
    employee_share = fields.Monetary(
        string='Employee Share',
        required=True,
        currency_field='currency_id',
    )
    employer_share = fields.Monetary(
        string='Employer Share',
        required=True,
        currency_field='currency_id',
    )
    total = fields.Monetary(
        string='Total',
        compute='_compute_total',
        store=True,
        currency_field='currency_id',
    )
    contribution_type = fields.Selection([
        ('gosi', 'GOSI'),
        ('pension', 'Pension'),
        ('social_security', 'Social Security'),
        ('other', 'Other'),
    ], string='Contribution Type', required=True, default='gosi')
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.company_id.currency_id',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='employee_id.company_id',
        store=True,
        readonly=True,
    )

    @api.depends('date')
    def _compute_contribution_month(self):
        for record in self:
            if record.date:
                record.contribution_month = record.date.strftime('%B %Y')
            else:
                record.contribution_month = False

    @api.depends('employee_share', 'employer_share')
    def _compute_total(self):
        for record in self:
            record.total = record.employee_share + record.employer_share
