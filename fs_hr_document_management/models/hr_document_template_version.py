# -*- coding: utf-8 -*-

from odoo import models, fields


class HrDocumentTemplateVersion(models.Model):
    _name = 'hr.document.template.version'
    _description = 'HR Document Template Version History'

    template_id = fields.Many2one(
        'hr.document.template',
        required=True,
        ondelete='cascade',
    )
    version = fields.Integer(required=True)
    body_html = fields.Html(sanitize=False)
    legal_text = fields.Html(sanitize=False)
