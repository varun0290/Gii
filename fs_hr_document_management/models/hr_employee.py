# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployeeDocument(models.Model):
    _name = 'hr.employee.document'
    _description = 'Employee Signed Document'

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        ondelete='cascade',
    )
    deployment_id = fields.Many2one(
        'hr.document.deployment',
        ondelete='set null',
    )
    template_id = fields.Many2one(
        'hr.document.template',
        related='deployment_id.template_id',
        store=True,
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        required=True,
        ondelete='cascade',
    )
    signed_datetime = fields.Datetime(string='Signed On')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    document_deployment_line_ids = fields.One2many(
        'hr.document.deployment.line',
        'employee_id',
        string='Document Deployments',
        readonly=True,
    )
    signed_document_ids = fields.One2many(
        'hr.employee.document',
        'employee_id',
        string='Signed Documents',
        readonly=True,
    )

    def _store_signed_document(self, deployment, attachment):
        """Store signed document reference on employee profile."""
        self.ensure_one()
        line = self.env['hr.document.deployment.line'].search([
            ('deployment_id', '=', deployment.id),
            ('employee_id', '=', self.id),
        ], limit=1)
        self.env['hr.employee.document'].create({
            'employee_id': self.id,
            'deployment_id': deployment.id,
            'attachment_id': attachment.id,
            'signed_datetime': line.signed_datetime,
        })
