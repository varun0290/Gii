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
            ("customer_payment", "Customer Payment"),
            ("customer_invoice", "Customer Invoice"),
        ],
        string="Import Type",
        default="journal_entry",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company.id
    )
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal', 
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    date_format = fields.Selection([
        ('%m/%d/%Y', 'MM/DD/YYYY'),
        ('%d/%m/%Y', 'DD/MM/YYYY'),
        ('%Y/%m/%d', 'YYYY/MM/DD'),
    ], string='Date Format', default='%m/%d/%Y')

    def _find_or_project(self, analytic_project):
        """Find or create project based on name"""
        if not analytic_project or pd.isna(analytic_project) or str(analytic_project).strip() == '':
            return False
            
        project_name = str(analytic_project).strip()
        analytic_project = self.env['project.project'].search([
            ('name', '=ilike', project_name)
        ], limit=1)
        if not analytic_project:
            analytic_project = self.env['project.project'].create({
                'name': project_name,
            })
            _logger.info(f"Created project: {analytic_project.name}")
            
        return analytic_project.id

    def _find_or_create_analytic(self, analytic_account):
        """Find or create analytic account based on name"""
        if not analytic_account or pd.isna(analytic_account) or str(analytic_account).strip() == '':
            return False
            
        analytic_name = str(analytic_account).strip()
        analytic = self.env['account.analytic.account'].search([
            ('name', '=ilike', analytic_name)
        ], limit=1)
        
        if not analytic:
            plan_id = self.env["account.analytic.plan"].search([], limit=1)
            analytic_vals = {
                'name': analytic_name,
            }
            if plan_id:
                analytic_vals['plan_id'] = plan_id.id
                
            analytic = self.env['account.analytic.account'].create(analytic_vals)
            _logger.info(f"Created analytic account: {analytic.name}")
            
        return analytic.id

    def _find_or_create_partner(self, partner_name):
        """Find or create partner based on name"""
        if not partner_name or pd.isna(partner_name) or str(partner_name).strip() == '':
            return False
            
        partner_name_clean = str(partner_name).strip()
        partner = self.env['res.partner'].search([
            ('name', '=ilike', partner_name_clean)
        ], limit=1)
        
        if not partner:
            partner = self.env['res.partner'].create({
                'name': partner_name_clean,
                'company_type': 'company',
            })
            _logger.info(f"Created new partner: {partner_name_clean}")
            
        return partner.id

    def _find_or_tax(self, tax_code):
        """Find tax based on name"""
        if not tax_code or pd.isna(tax_code) or str(tax_code).strip() == '':
            return [(6, 0, [])]  # Return empty tax assignment
        
        tax_name = str(tax_code).strip()
        tax_ids = self.env['account.tax'].search([
            ('name', '=ilike', tax_name)
        ])
        
        # Return the tax_ids directly, not as a function call
        return [(6, 0, tax_ids.ids)] if tax_ids else [(6, 0, [])]

    def _find_or_currency(self, currency_name):
        """Find currency based on name"""
        if not currency_name or pd.isna(currency_name) or str(currency_name).strip() == '':
            return self.env.company.currency_id.id
            
        currency_id = self.env['res.currency'].search([
            ('name', '=ilike', str(currency_name).strip())
        ], limit=1)
        
        return currency_id.id if currency_id else self.env.company.currency_id.id

    def _find_account(self, account_code):
        """Find account by code"""
        if not account_code or pd.isna(account_code):
            raise UserError(_(f"Account code is required but missing."))
            
        account_code_clean = str(account_code).strip()
        account = self.env['account.account'].search([
            ('code', '=', account_code_clean)
        ], limit=1)
        
        if not account:
            raise UserError(_(
                f"Account with code '{account_code_clean}' not found. "
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
            elif self.import_type in ("vendor_payment", 'customer_payment'):
                required_columns = ['date', 'voucher', 'account2_name', 'debit', 'credit', 'narration']
            elif self.import_type in ("vendor_bill", 'customer_invoice'):
                required_columns = ['date', 'voucher', 'account2_name', 'account_code', 'debit', 'credit', 'narration']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise UserError(_(
                    f"Missing required columns: {', '.join(missing_columns)}"
                ))
                
            # Fill NaN values with empty string or 0
            df = df.fillna({'debit': 0.0, 'credit': 0.0, 'narration': ''})
                
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
                tax_ids = self._find_or_tax(row.get('tax_code_name', ''))
                currency_id = self._find_or_currency(row.get("currency_name", ""))
                analytic_account = self._find_or_create_analytic(row.get('account_analytics', ''))
                analytic_project = self._find_or_project(row.get('project', ''))
                
                debit = float(row['debit']) if pd.notna(row['debit']) else 0.0
                credit = float(row['credit']) if pd.notna(row['credit']) else 0.0
                amount_currency = debit if debit > 0 else credit
                total_debit += debit
                total_credit += credit
                currency = self.env["res.currency"].browse(currency_id)
                if debit:
                    debit = currency._convert(
                        debit,
                        self.env.company.currency_id,
                        self.journal_id.company_id,
                        move_date
                    )
                elif credit:
                    credit = currency._convert(
                        credit,
                        self.env.company.currency_id,
                        self.journal_id.company_id,
                        move_date
                    )
                
                move_lines.append((0, 0, {
                    'account_id': account_id,
                    'partner_id': partner_id,
                    'name': row['narration'] if pd.notna(row['narration']) else '/',
                    'amount_currency': -(amount_currency) if credit else abs(amount_currency),
                    'debit': debit,
                    'credit': credit,
                    'currency_id': currency_id,
                    'tax_ids': tax_ids,
                    'analytic_account_id': analytic_account if analytic_account else False,
                    'project_id': analytic_project if analytic_project else False,
                }))
            
            # Create journal entry
            move_vals = {
                'move_type': 'entry',
                'journal_id': journal_id.id,
                'date': move_date,
                'name': voucher,
                'line_ids': move_lines,
                'currency_id': currency_id,
            }

            move = self.env['account.move'].create(move_vals)
            moves_created.append(move.id)
            
            _logger.info(f"Created journal entry: {voucher} with {len(move_lines)} lines")
        
        return moves_created

    def _create_invoice_bill(self, df, journal_id):
        """Create vendor bills or customer invoices from DataFrame"""
        moves_created = []
        
        # Group by voucher to create one invoice per voucher
        vouchers = df['voucher'].unique()
        
        for voucher in vouchers:
            if pd.isna(voucher):
                continue
                
            voucher_data = df[df['voucher'] == voucher]
            first_row = voucher_data.iloc[0]
            
            # Check if invoice already exists
            existing_invoice = self.env['account.move'].search([
                ('name', '=', voucher), 
                ('state', '!=', 'cancel'), 
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if existing_invoice:
                _logger.info(f"Invoice {voucher} already exists, skipping")
                continue
            
            # Parse date
            try:
                invoice_date = pd.to_datetime(
                    first_row['date'], 
                    format=self.date_format
                ).date()
            except:
                invoice_date = pd.to_datetime(first_row['date']).date()
            
            # Determine partner
            partner_id = False
            if self.import_type == "vendor_bill":
                partner_id = self._find_or_create_partner(first_row.get('account_name', first_row.get('account2_name', '')))
            else:  # customer_invoice
                partner_id = self._find_or_create_partner(first_row.get('customer', ''))
            
            if not partner_id:
                raise UserError(_(f"Partner is required for {self.import_type} but not found in row."))

            currency_id = self._find_or_currency(first_row.get("currency_name", ""))
            
            # Prepare invoice lines
            invoice_lines = []
            for _, row in voucher_data.iterrows():
                account_id = self._find_account(row['account_code'])
                tax_ids = self._find_or_tax(row.get('tax_code_name', ''))
                analytic_account_id = self._find_or_create_analytic(row.get('account_analytics', ''))
                project_id = self._find_or_project(row.get('project', ''))
                
                debit = float(row['debit']) if pd.notna(row['debit']) else 0.0
                credit = float(row['credit']) if pd.notna(row['credit']) else 0.0
                
                if self.import_type == "vendor_bill" and not debit:
                    continue
                elif self.import_type == "customer_invoice" and not credit:
                    continue
                # For invoices, use the non-zero amount as price_unit
                price_unit = debit if debit > 0 else credit
                label = row['narration'] if pd.notna(row['narration']) and str(row['narration']).strip() != '' else '/',

                line_vals = {
                    'account_id': account_id,
                    'name': label,
                    'quantity': 1.0,
                    'price_unit': price_unit,
                    'tax_ids': tax_ids,
                }
                
                # Add analytic distribution if available
                if analytic_account_id:
                    line_vals['analytic_account_id'] = analytic_account_id

                if project_id:
                    line_vals['project_id'] = project_id
                
                invoice_lines.append((0, 0, line_vals))
            
            if not invoice_lines:
                _logger.warning(f"No invoice lines created for voucher {voucher}")
                continue
            
            # Create invoice
            move_vals = {
                'move_type': 'in_invoice' if self.import_type == 'vendor_bill' else 'out_invoice',
                'partner_id': partner_id,
                'journal_id': self.journal_id.id,
                'invoice_date': invoice_date,
                'date': invoice_date,
                'name': voucher,
                'invoice_line_ids': invoice_lines,
            }
            
            if currency_id:
                move_vals["currency_id"] = currency_id
                
            # Add bill reference if available
            if self.import_type == 'vendor_bill' and 'bill_no' in first_row and pd.notna(first_row['bill_no']):
                move_vals['ref'] = str(first_row['bill_no'])
                
            _logger.info(f"Creating {self.import_type} with values: {move_vals}")
            
            try:
                move = self.env['account.move'].create(move_vals)
                moves_created.append(move.id)
                _logger.info(f"✅ Created {self.import_type}: {voucher} with {len(invoice_lines)} lines")
            except Exception as e:
                _logger.error(f"❌ Failed to create {self.import_type} {voucher}: {str(e)}")
                raise UserError(_(f"Failed to create {self.import_type}: {str(e)}"))
        
        return moves_created

    def _create_customer_vendor_payments(self, df, journal_id):
        """Create vendor/customer payments from DataFrame"""
        payments_created = []
        
        # Group by voucher to create one payment per voucher
        vouchers = df['voucher'].unique()
        
        for voucher in vouchers:
            if pd.isna(voucher):
                continue
                
            voucher_data = df[df['voucher'] == voucher]
            first_row = voucher_data.iloc[0]
            
            # Check if payment already exists
            existing_payment = self.env["account.payment"].search([
                ('name', '=', voucher), 
                ('company_id', '=', self.env.company.id), 
                ('state', '!=', 'cancel')
            ], limit=1)
            
            if existing_payment:
                _logger.info(f"Payment {voucher} already exists, skipping")
                continue
            
            # Parse date
            try:
                payment_date = pd.to_datetime(
                    first_row['date'], 
                    format=self.date_format
                ).date()
            except:
                payment_date = pd.to_datetime(first_row['date']).date()
            
            # Determine partner and payment type
            partner_id = self._find_or_create_partner(first_row['account2_name'])
            if not partner_id:
                raise UserError(_(f"Partner is required for payment but not found for voucher {voucher}"))

            currency_id = self._find_or_currency(first_row.get("currency_name", ""))
            # Calculate amount from first row (assuming one payment per voucher)
            debit = float(first_row['debit']) if pd.notna(first_row['debit']) else 0.0
            credit = float(first_row['credit']) if pd.notna(first_row['credit']) else 0.0
            amount = debit if debit > 0 else credit
            
            # Determine payment type based on import type and amount
            if self.import_type == "vendor_payment":
                payment_type = 'outbound'
                partner_type = 'supplier'
            else:  # customer_payment
                payment_type = 'inbound'
                partner_type = 'customer'
            
            # Create payment
            payment_vals = {
                'payment_type': payment_type,
                'partner_type': partner_type,
                'partner_id': partner_id,
                'journal_id': journal_id.id,
                'currency_id': currency_id,
                'date': payment_date,
                'amount': amount,
                'name': voucher,
                'apply_to_invoice': first_row.get("apply_invoice", ""),
            }
            
            # Handle invoice linking if specified
            # if first_row.get('apply_invoice') and pd.notna(first_row['apply_invoice']):
            #     # You would need to implement invoice matching logic here
            #     _logger.info(f"Apply to invoice field found: {first_row['apply_invoice']}")
            
            try:
                payment = self.env['account.payment'].create(payment_vals)
                payments_created.append(payment.id)
                _logger.info(f"✅ Created {self.import_type}: {voucher} with amount {amount}")
            except Exception as e:
                _logger.error(f"❌ Failed to create payment {voucher}: {str(e)}")
                raise UserError(_(f"Failed to create payment: {str(e)}"))
        
        return payments_created

    def action_import(self):
        """Main import action"""
        self.ensure_one()
        
        if not self.file:
            raise UserError(_("Please select a file to import."))
        
        try:
            # Parse Excel file
            df = self._parse_excel_file(self.file)
            _logger.info(f"Successfully parsed Excel file with {len(df)} rows for {self.import_type}")
            
            created_ids = []
            model_name = ''
            
            if self.import_type == "journal_entry":
                created_ids = self._create_journal_entries(df, self.journal_id)
                model_name = 'account.move'
                view_name = _('Imported Journal Entries')
                
            elif self.import_type in ("vendor_payment", "customer_payment"):
                created_ids = self._create_customer_vendor_payments(df, self.journal_id)
                model_name = 'account.payment'
                view_name = _('Imported Payments')
                
            elif self.import_type in ("vendor_bill", "customer_invoice"):
                print("\n\n\n df", df, self.journal_id)
                created_ids = self._create_invoice_bill(df, self.journal_id)
                model_name = 'account.move'
                view_name = _('Imported Invoices') if self.import_type == 'customer_invoice' else _('Imported Vendor Bills')
            
            # Create import record
            import_record = self.env['journal.import'].create({
                'name': f"Import_{fields.Datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'file_name': self.file_name,
                # 'import_type': self.import_type,
                'imported_lines': len(df),
                'state': 'imported',
            })
            
            # Link created records to import record
            if created_ids and hasattr(self.env[model_name], 'journal_import_id'):
                records = self.env[model_name].browse(created_ids)
                records.write({'journal_import_id': import_record.id})
            
            # Return action to show created records
            if created_ids:
                return {
                    'type': 'ir.actions.act_window',
                    'name': view_name,
                    'res_model': model_name,
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', created_ids)],
                    'context': {'create': False},
                }
            else:
                raise UserError(_("No records were created during import. Please check your data and try again."))
                
        except Exception as e:
            _logger.error(f"Import error: {str(e)}", exc_info=True)
            raise UserError(_(f"Import failed: {str(e)}"))