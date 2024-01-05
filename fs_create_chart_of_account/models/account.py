from odoo import fields, api, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def button_create_coa(self):
        for account in self:
            companies = self.env["res.company"].sudo().search([])
            for company in companies:
                account_id = (
                    self.env["account.account"]
                    .sudo()
                    .search(
                        [("code", "=", account.code), ("company_id", "=", company.id)]
                    )
                )
                if not account_id:
                    self.env["account.account"].sudo().create(
                        {
                            "code": account.code,
                            "name": account.name,
                            "account_type": account.account_type,
                            "reconcile": account.reconcile,
                            "currency_id": account.currency_id.id,
                            "company_id": company.id,
                        }
                    )
