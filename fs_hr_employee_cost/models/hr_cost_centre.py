# -*- coding: utf-8 -*-

from odoo import models, fields


class HrCostCentre(models.Model):
    _name = 'hr.cost.centre'
    _description = 'HR Cost Centre'

    name = fields.Char(required=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
