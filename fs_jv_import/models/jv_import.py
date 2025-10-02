from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class JVImport(models.Model):
    _name = 'jv.import'
    _description = 'Journal Entry Import'

    name = fields.Char(string='Reference', required=True)
    date = fields.Date(string='Import Date', default=fields.Date.today)
    file_name = fields.Char(string='File Name')
    imported_lines = fields.Integer(string='Imported Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('posted', 'Posted')
    ], string='Status', default='draft')
    
    journal_entry_ids = fields.One2many(
        'account.move', 
        'jv_import_id', 
        string='Journal Entries'
    )


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    jv_import_id = fields.Many2one(
        'jv.import',
        string='Import Reference',
        readonly=True
    )
    apply_to_invoice = fields.Char(string="Apply To Invoice")