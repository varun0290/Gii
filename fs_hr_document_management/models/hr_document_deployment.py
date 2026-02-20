# -*- coding: utf-8 -*-

import base64
import secrets

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrDocumentDeployment(models.Model):
    _name = 'hr.document.deployment'
    _description = 'HR Document Deployment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Deployment Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    template_id = fields.Many2one(
        'hr.document.template',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='template_id.company_id',
        store=True,
    )
    narration = fields.Text(
        string='Narration',
        help='Short description or message for this deployment.',
        tracking=True,
    )
    effective_date = fields.Date(
        string='Effective Date',
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    # Employee selection
    employee_selection = fields.Selection([
        ('all', 'All Employees'),
        ('department', 'By Department'),
        ('location', 'By Location'),
        ('job', 'By Job / Role'),
        ('manual', 'Manual Selection'),
    ], default='all', required=True, tracking=True)
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter by departments when selection is By Department.',
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Jobs / Roles',
        help='Filter by job when selection is By Job.',
    )
    work_location = fields.Selection([
        ('emaar', 'Emaar'),
        ('convention', 'Convention'),
        ('capital', 'Capital'),
        ('other', 'Other'),
    ], string='Work Location', help='Filter by location if employee_custom_fields provides work_location.')
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_document_deployment_employee_rel',
        'deployment_id',
        'employee_id',
        string='Employees (Manual)',
        help='Manually selected employees when selection is Manual.',
    )
    line_ids = fields.One2many(
        'hr.document.deployment.line',
        'deployment_id',
        string='Deployment Lines',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'hr.document.deployment'
                ) or _('New')
        return super().create(vals_list)

    def _get_employee_ids(self):
        """Compute employees to deploy based on selection criteria."""
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ]
        if self.employee_selection == 'all':
            pass
        elif self.employee_selection == 'department' and self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        elif self.employee_selection == 'job' and self.job_ids:
            domain.append(('job_id', 'in', self.job_ids.ids))
        elif self.employee_selection == 'location' and self.work_location:
            if hasattr(self.env['hr.employee'], 'work_location'):
                domain.append(('work_location', '=', self.work_location))
            else:
                raise UserError(_('Work Location filter requires employee_custom_fields module.'))
        elif self.employee_selection == 'manual' and self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        else:
            raise UserError(_('Please configure employee selection filters.'))
        return self.env['hr.employee'].search(domain)

    def action_prepare_lines(self):
        """Create deployment lines for selected employees."""
        for rec in self:
            if rec.state != 'draft':
                continue
            employees = rec._get_employee_ids()
            if not employees:
                raise UserError(_('No employees match the selection criteria.'))
            existing = rec.line_ids.mapped('employee_id')
            to_add = employees - existing
            for emp in to_add:
                self.env['hr.document.deployment.line'].create({
                    'deployment_id': rec.id,
                    'employee_id': emp.id,
                })

    def action_send(self):
        """Send documents to all employees (generate PDFs, create attachments, send emails)."""
        for rec in self:
            if rec.state != 'draft':
                continue
            if not rec.line_ids:
                rec.action_prepare_lines()
            rec._send_to_lines()
            rec.write({'state': 'sent'})

    def _send_to_lines(self):
        """Generate PDF per line, attach, and notify employee."""
        self.ensure_one()
        for line in self.line_ids:
            line._generate_and_send()

    def action_send_reminders(self):
        """Send reminder to employees with pending acknowledgment."""
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.state in ('sent', 'viewed')):
                line._send_reminder()


class HrDocumentDeploymentLine(models.Model):
    _name = 'hr.document.deployment.line'
    _description = 'HR Document Deployment Line'
    _rec_name = 'employee_id'

    deployment_id = fields.Many2one(
        'hr.document.deployment',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='cascade',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
    ], default='draft', required=True)
    # E-sign data
    signed_full_name = fields.Char(string='Signed Name')
    signed_employee_code = fields.Char(string='Employee Code (at sign)')
    signed_datetime = fields.Datetime(string='Signed On')
    signed_confirmation = fields.Boolean(string='Signature Confirmed', default=False)
    document_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Document PDF',
        ondelete='set null',
    )
    signed_document_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Signed Document',
        ondelete='set null',
    )
    # Tracking
    sent_datetime = fields.Datetime(string='Sent On', readonly=True)
    viewed_datetime = fields.Datetime(string='Viewed On', readonly=True)
    access_token = fields.Char(copy=False)

    def _generate_and_send(self):
        """Generate PDF from template, attach to line, send portal link to employee."""
        self.ensure_one()
        pdf = self.deployment_id.template_id._render_for_employee(self.employee_id)
        if not pdf:
            return
        attach = self.env['ir.attachment'].create({
            'name': '%s - %s.pdf' % (
                self.deployment_id.template_id.name,
                self.employee_id.name or 'Employee'
            ),
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'res_model': 'hr.document.deployment.line',
            'res_id': self.id,
        })
        self.write({
            'document_attachment_id': attach.id,
            'state': 'sent',
            'sent_datetime': fields.Datetime.now(),
            'access_token': secrets.token_urlsafe(32),
        })
        # TODO: Send email with portal link; use mail.mail or chatter
        # For now we store the PDF. Portal will use access_token for secure view.

    def _send_reminder(self):
        """Send reminder email for pending acknowledgment."""
        self.ensure_one()
        # TODO: mail.mail with reminder message
        pass

    @api.model
    def _cron_send_reminders(self):
        """Cron: send reminders for pending acknowledgments."""
        pending = self.search([('state', 'in', ('sent', 'viewed'))])
        for line in pending:
            line._send_reminder()

    def action_mark_viewed(self):
        """Called when employee opens the document in portal."""
        self.write({
            'state': 'viewed',
            'viewed_datetime': fields.Datetime.now(),
        })

    def action_acknowledge(self, full_name, employee_code):
        """E-sign / acknowledge the document."""
        self.ensure_one()
        self.write({
            'state': 'signed',
            'signed_full_name': full_name,
            'signed_employee_code': employee_code,
            'signed_datetime': fields.Datetime.now(),
            'signed_confirmation': True,
        })
        # Store signed copy on employee profile
        doc_attach = self.document_attachment_id or self.signed_document_attachment_id
        if doc_attach:
            self.employee_id._store_signed_document(
                self.deployment_id,
                doc_attach,
            )
