from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import pandas as pd
import io
import logging

_logger = logging.getLogger(__name__)

class JournalImportWizard(models.TransientModel):
    _name = 'journal.import.wizard'
    _description = 'Journal Import Wizard'

    file = fields.Binary(string='Excel File', required=True)
    file_name = fields.Char(string='File Name')
    import_type = fields.Selection(
        [
            ('journal_entry', 'Journal Entry'),
            ("vendor_payment", "Vendor Payment"),
            ("vendor_bill", "Vendor Bill"),
            # ("customer_invoice", "Customer Invoice"),
        ],
        string="Import Type",
        default="journal_entry",
    )
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal', 
        required=True,
    )
    date_format = fields.Selection([
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%Y/%m/%d', 'YYYY/MM/DD'),
    ], string='Date Format', default='%m/%d/%Y')

    def _find_or_create_analytic(self, analytic_account):
        """Find or create partner based on name"""
        if not analytic_account or str(analytic_account).strip() == '':
            return False
            
        analytic = self.env['account.analytic.account'].search([
            ('name', '=ilike', str(analytic_account).strip())
        ], limit=1)
        plan_id = self.env["account.analytic.plan"].search([('name', '=', 'Projects')], limit=1)
        if not analytic and plan_id:
            analytic = self.env['account.analytic.account'].create({
                'name': str(analytic_account).strip(),
                'plan_id': plan_id.id,
            })
            _logger.info(f"Created new partner: {analytic}")
            
        return analytic.id

    def _find_or_create_partner(self, partner_name):
        """Find or create partner based on name"""
        if not partner_name or partner_name.strip() == '':
            return False
            
        partner = self.env['res.partner'].search([
            ('name', '=ilike', partner_name.strip())
        ], limit=1)
        
        if not partner:
            partner = self.env['res.partner'].create({
                'name': partner_name.strip(),
                'company_type': 'company',
            })
            _logger.info(f"Created new partner: {partner_name}")
            
        return partner.id

    def _find_or_tax(self, tax_code):
        """Find or create tax based on name"""
        if not tax_code or str(tax_code).strip() == '':
            return False
            
        tax_ids = self.env['account.tax'].search([
            ('name', '=ilike', str(tax_code).strip())
        ], limit=1)
        
        if not tax_ids:
            return []
            
        return tax_ids.ids

    def _find_or_currency(self, currency_name):
        """Find or create currency based on name"""
        if not currency_name or str(currency_name).strip() == '':
            return False
            
        currency_id = self.env['res.currency'].search([
            ('name', '=ilike', str(currency_name).strip())
        ], limit=1)
        if not currency_id:
            return False
            
        return currency_id.id

    def _find_account(self, account_code):
        """Find account by code"""
        if not account_code:
            return False
            
        account = self.env['account.account'].search([
            ('code', '=', str(account_code).strip())
        ], limit=1)
        
        if not account:
            raise UserError(_(
                f"Account with code '{account_code}' not found. "
                f"Please create the account first."
            ))
            
        return account.id

    def _parse_excel_file(self, file_data):
        """Parse Excel file and return DataFrame"""
        try:
            file_content = base64.b64decode(file_data)
            df = pd.read_excel(io.BytesIO(file_content), sheet_name='Sheet1')
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Ensure required columns exist
            required_columns = []
            if self.import_type == "journal_entry":
                required_columns = ['date', 'voucher', 'account', 'final_code', 'debit', 'credit', 'narration']
            elif self.import_type == "vendor_payment":
                required_columns = ['date', 'voucher', 'account2_name', 'debit', 'credit', 'narration']
            elif self.import_type == "vendor_bill":
                required_columns = ['date', 'voucher', 'account2_name', 'account_code', 'debit', 'credit', 'narration']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise UserError(_(
                    f"Missing required columns: {', '.join(missing_columns)}"
                ))
                
            return df
            
        except Exception as e:
            raise UserError(_(f"Error reading Excel file: {str(e)}"))

    def _create_journal_entries(self, df, journal_id):
        """Create journal entries from DataFrame"""
        moves_created = []
        
        # Group by voucher to create one journal entry per voucher
        vouchers = df['voucher'].unique()
        
        for voucher in vouchers:
            if pd.isna(voucher):
                continue
                
            voucher_data = df[df['voucher'] == voucher]
            first_row = voucher_data.iloc[0]
            
            # Parse date
            try:
                move_date = pd.to_datetime(
                    first_row['date'], 
                    format=self.date_format
                ).date()
            except:
                move_date = pd.to_datetime(first_row['date']).date()
            
            # Prepare move lines
            move_lines = []
            total_debit = 0
            total_credit = 0
            
            for _, row in voucher_data.iterrows():
                account_id = self._find_account(row['final_code'])
                partner_id = self._find_or_create_partner(row['account'])
                tax_ids = self._find_or_tax(row['tax_code_name'])
                currency_id = self._find_or_currency(row["currency_name"])
                analytic_account = self._find_or_create_analytic(row['account_analytics'])
                
                debit = float(row['debit']) if pd.notna(row['debit']) else 0.0
                credit = float(row['credit']) if pd.notna(row['credit']) else 0.0
                
                total_debit += debit
                total_credit += credit
                
                move_lines.append((0, 0, {
                    'account_id': account_id,
                    'partner_id': partner_id,
                    'name': row['narration'] if pd.notna(row['narration']) else '',
                    'debit': debit,
                    'credit': credit,
                    'tax_ids': [(6, 0, tax_ids)],
                    'analytic_account_id': analytic_account if analytic_account else '',
                }))
            
            # Create journal entry
            move_vals = {
                'move_type': 'entry',
                'journal_id': journal_id.id,
                'date': move_date,
                'name': voucher,
                'line_ids': move_lines,
                'currency_id': currency_id if currency_id else '',
                'apply_to_invoice': row["apply_invoice"] if row.get('apply_invoice') else '',
            }
            invoice_id = self.env['account.move'].search([('name', '=', voucher)], limit=1)
            if invoice_id:
                invoice_id.write({"invoice_line_ids": move_lines})
            else:
                move = self.env['account.move'].create(move_vals)
            moves_created.append(move.id)
            
            _logger.info(f"Created vendor bill: {voucher} with {len(move_lines)} lines")
        
        return moves_created

    def _create_vendor_bill(self, df, journal_id):
        """Create journal entries from DataFrame"""
        moves_created = []
        
        # Group by voucher to create one journal entry per voucher
        vouchers = df['voucher'].unique()
        
        for voucher in vouchers:
            if pd.isna(voucher):
                continue
                
            voucher_data = df[df['voucher'] == voucher]
            first_row = voucher_data.iloc[0]
            
            # Parse date
            try:
                move_date = pd.to_datetime(
                    first_row['date'], 
                    format=self.date_format
                ).date()
            except:
                move_date = pd.to_datetime(first_row['date']).date()
            
            # Prepare move lines
            move_lines = []
            total_debit = 0
            total_credit = 0
            
            for _, row in voucher_data.iterrows():
                account_id = self._find_account(row['account_code'])
                partner_id = self._find_or_create_partner(row['account2_name'])
                tax_ids = self._find_or_tax(row['tax_code_name'])
                currency_id = self._find_or_currency(row["currency_name"])
                analytic_account = self._find_or_create_analytic(row['account_analytics'])
                
                debit = float(row['debit']) if pd.notna(row['debit']) else 0.0
                credit = float(row['credit']) if pd.notna(row['credit']) else 0.0
                
                total_debit += debit
                total_credit += credit
                invoice_id = self.env['account.move'].search([('name', '=', voucher)], limit=1)
                if invoice_id:
                    continue

                move_lines.append((0, 0, {
                    'account_id': account_id,
                    'name': row['narration'] if pd.notna(row['narration']) else '',
                    'price_unit': debit or credit,
                    'tax_ids': [(6, 0, tax_ids)],
                    'analytic_account_id': analytic_account if analytic_account else '',
                }))
            
                # Create journal entry
                move_vals = {
                    'move_type': 'in_invoice',
                    'ref': row['bill_no'] if row.get('bill_no') else '',
                    'partner_id': partner_id,
                    'journal_id': journal_id.id,
                    'invoice_date': move_date,
                    'date': move_date,
                    'name': voucher,
                    'invoice_line_ids': move_lines,
                    'currency_id': currency_id if currency_id else '',
                    # 'apply_to_invoice': row["apply_invoice"] if row.get('apply_invoice') else '',
                }
                move = self.env['account.move'].create(move_vals)
                # invoice_id = self.env['account.move'].search([('name', '=', voucher)], limit=1)
                # if invoice_id:
                #     invoice_id.write({"invoice_line_ids": move_lines})
                # else:
                moves_created.append(move.id)
            
            _logger.info(f"Created vendor bill: {voucher} with {len(move_lines)} lines")
        
        return moves_created

    def _create_vendor_payments(self, df, journal_id):
        """Create vendor payments from DataFrame"""
        moves_created = []
        
        # Group by voucher to create one journal entry per voucher
        vouchers = df['voucher'].unique()
        
        for voucher in vouchers:
            if pd.isna(voucher):
                continue
                
            voucher_data = df[df['voucher'] == voucher]
            first_row = voucher_data.iloc[0]
            
            # Parse date
            try:
                move_date = pd.to_datetime(
                    first_row['date'], 
                    format=self.date_format
                ).date()
            except:
                move_date = pd.to_datetime(first_row['date']).date()
            
            # Prepare move lines
            move_lines = []
            total_debit = 0
            total_credit = 0
            
            for _, row in voucher_data.iterrows():
                # account_id = self._find_account(row['final_code'])
                partner_id = self._find_or_create_partner(row['account2_name'])
                # tax_ids = self._find_or_tax(row['tax_code_name'])
                currency_id = self._find_or_currency(row["currency_name"])
                # analytic_account = self._find_or_create_analytic(row['account_analytics'])
                
                debit = float(row['debit']) if pd.notna(row['debit']) else 0.0
                credit = float(row['credit']) if pd.notna(row['credit']) else 0.0
                
                total_debit += debit
                total_credit += credit

                payment_id = self.env["account.payment"].search([('name', '=', voucher), ('company_id', '=', self.env.company.id)], limit=1)
                if payment_id:
                    continue
                
                # Create journal entry
                move_vals = {
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'partner_id': partner_id,
                    'journal_id': journal_id.id,
                    'date': move_date,
                    'name': voucher,
                    'amount': debit or credit,
                    'currency_id': currency_id if currency_id else '',
                    'apply_to_invoice': row["apply_invoice"] if row.get('apply_invoice') else '',
                }
                move = self.env['account.payment'].create(move_vals)
                moves_created.append(move.id)
            
            _logger.info(f"Created journal entry: {voucher} with {len(move_lines)} lines")
        
        return moves_created


    def action_import(self):
        """Main import action"""
        self.ensure_one()
        
        if not self.file:
            raise UserError(_("Please select a file to import."))
        
        try:
            # Parse Excel file
            df = self._parse_excel_file(self.file)
            _logger.info(f"Successfully parsed Excel file with {len(df)} rows")
            
            if self.import_type == "journal_entry":
                # Create journal entries
                move_ids = self._create_journal_entries(df, self.journal_id)
                
                # Create import record
                import_record = self.env['journal.import'].create({
                    'name': f"Import_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'file_name': self.file_name,
                    'imported_lines': len(df),
                    'state': 'imported',
                })
                
                # Link created moves to import record
                if move_ids:
                    moves = self.env['account.move'].browse(move_ids)
                    moves.write({'journal_import_id': import_record.id})
               
                # Return action to show created journal entries
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Imported Journal Entries'),
                    'res_model': 'account.move',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', move_ids)],
                    'context': {'create': False},
                }
            elif self.import_type == "vendor_payment":
                # Create vendor payments
                payment_ids = self._create_vendor_payments(df, self.journal_id)
                
                # Create import record
                import_record = self.env['journal.import'].create({
                    'name': f"Import_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'file_name': self.file_name,
                    'imported_lines': len(df),
                    'state': 'imported',
                })
                
                # Link created moves to import record
                if payment_ids:
                    payments = self.env['account.payment'].browse(payment_ids)
                    payments.write({'journal_import_id': import_record.id})
            
                # Return action to show created journal entries
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Imported Payments'),
                    'res_model': 'account.payment',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', payment_ids)],
                    'context': {'create': False},
                }
            elif self.import_type == "vendor_bill":
                # Create journal entries
                move_ids = self._create_vendor_bill(df, self.journal_id)
                
                # Create import record
                import_record = self.env['journal.import'].create({
                    'name': f"Import_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'file_name': self.file_name,
                    'imported_lines': len(df),
                    'state': 'imported',
                })
                
                # Link created moves to import record
                if move_ids:
                    moves = self.env['account.move'].browse(move_ids)
                    moves.write({'journal_import_id': import_record.id})
               
                # Return action to show created journal entries
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Imported Vendor Bills'),
                    'res_model': 'account.move',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', move_ids)],
                    'context': {'create': False},
                }
        except Exception as e:
            _logger.error(f"Import error: {str(e)}")
            raise UserError(_(f"Import failed: {str(e)}"))