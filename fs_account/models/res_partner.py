# -*- coding: utf-8 -*-

from odoo import fields, api, models, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    vat = fields.Char(
        string="Tax ID",
        index=True,
        size=15,
        help="The Tax Identification Number. Values here will be validated based on the country format. You can use '/' to indicate that the partner is not subject to tax.",
    )
