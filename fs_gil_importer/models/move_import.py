from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class JournalImport(models.Model):
    _name = 'journal.import'
    _description = 'Journal Import'

    name = fields.Char(string='Reference', required=True)
    date = fields.Date(string='Import Date', default=fields.Date.today)
    file_name = fields.Char(string='File Name')
    imported_lines = fields.Integer(string='Imported Lines')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('imported', 'Imported'),
            ('posted', 'Posted')
        ],
        string='Status',
        default='draft',
    )
    move_ids = fields.One2many(
        'account.move', 
        'journal_import_id', 
        string='Journal Entries'
    )
    account_payment_ids = fields.One2many(
        'account.payment', 
        'journal_import_id', 
        string='Payments'
    )


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    journal_import_id = fields.Many2one(
        'journal.import',
        string='Import Reference',
        readonly=True
    )
    apply_to_invoice = fields.Char(string="Apply To Invoice")

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    journal_import_id = fields.Many2one(
        'journal.import',
        string='Import Reference',
        readonly=True
    )
    apply_to_invoice = fields.Char(string="Apply To Invoice")