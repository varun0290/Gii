# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrDocumentTemplate(models.Model):
    _name = 'hr.document.template'
    _description = 'HR Document Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'document_type, name'

    name = fields.Char(required=True, tracking=True)
    document_type = fields.Selection([
        ('offer_letter', 'Offer Letter'),
        ('employment_contract', 'Employment Contract'),
        ('aml', 'AML Policy'),
        ('nda', 'NDA'),
        ('hr_policy', 'HR Policy'),
        ('other', 'Other'),
    ], required=True, default='other', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        required=True, tracking=True,
    )
    active = fields.Boolean(default=True)
    version = fields.Integer(string='Version', default=1, readonly=True)
    # Configurable legal/entity fields
    legal_entity_name = fields.Char(
        string='Legal Entity Name',
        related='company_id.name',
        readonly=False,
    )
    legal_text = fields.Html(
        string='Legal Text / Disclaimer',
        help='Standard legal text appended to documents.',
    )
    stamp_image = fields.Binary(string='Stamp / Logo')
    signing_authority_id = fields.Many2one(
        'res.users',
        string='Signing Authority',
        help='User who signs on behalf of the company.',
    )
    signing_authority_title = fields.Char(string='Signing Authority Title')
    # Template content - report or custom body
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Linked Report',
        domain=[('model', '=', 'hr.employee')],
        help='Use existing QWeb report (e.g. Offer Letter).',
    )
    body_html = fields.Html(
        string='Custom Body (HTML)',
        sanitize=False,
        help='Alternative to report. Use ${object.xxx} for employee fields.',
    )
    template_line_ids = fields.One2many(
        'hr.document.template.version',
        'template_id',
        string='Version History',
        readonly=True,
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.legal_entity_name = self.company_id.name

    def action_new_version(self):
        """Create a new version snapshot."""
        self.ensure_one()
        self.env['hr.document.template.version'].create({
            'template_id': self.id,
            'version': self.version,
            'body_html': self.body_html,
            'legal_text': self.legal_text,
        })
        self.write({'version': self.version + 1})

    def _render_for_employee(self, employee):
        """Render template for a specific employee."""
        self.ensure_one()
        if self.report_id:
            return self.report_id._render_qweb_pdf(employee.ids, data={})[0]
        # Custom HTML - placeholder replacement, then use body report
        if self.body_html:
            html = self._replace_placeholders(self.body_html, employee)
            if self.legal_text:
                html += str(self.legal_text)
            report = self.env.ref('fs_hr_document_management.action_document_template_body')
            return report._render_qweb_pdf(
                employee.ids, data={'body': html}
            )[0]
        return b''

    def _replace_placeholders(self, html, employee):
        """Replace ${object.xxx} with employee field values."""
        fields = ['name', 'job_id', 'department_id', 'parent_id', 'work_email',
                  'company_id', 'employee_code', 'work_location']
        for field in fields:
            if not hasattr(employee, field):
                continue
            val = getattr(employee, field)
            if hasattr(val, 'name'):
                val = val.name
            html = html.replace('${object.%s}' % field, str(val or ''))
        return html
