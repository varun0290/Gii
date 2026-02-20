# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    document_signing_authority_id = fields.Many2one(
        'res.users',
        string='Default Signing Authority',
        help='Default user who signs documents on behalf of the company.',
    )
    document_legal_text = fields.Html(
        string='Default Legal Text',
        help='Default legal text for HR documents.',
    )
    document_stamp_image = fields.Binary(string='Default Stamp / Logo')
