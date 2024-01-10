# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        inv_analytic_account_id = self.invoice_line_ids.filtered(
            lambda l: not l.analytic_account_id
        )
        if self.move_type != "entry" and inv_analytic_account_id:
            raise ValidationError(_("Please add analytic account in line."))

        line_analytic_account_id = self.invoice_line_ids.filtered(
            lambda l: not l.analytic_account_id
        )
        if self.move_type == "entry" and line_analytic_account_id:
            raise ValidationError(_("Please add analytic account in line."))
        return super(AccountMove, self).action_post()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Account Analytic",
    )

    @api.constrains("analytic_account_id")
    def _check_analytic_account(self):
        for record in self:
            if record.currency_id.id != record.analytic_account_id.currency_id.id:
                raise ValidationError(
                    _(
                        "Project Currency (%s) should be same as transaction currency"
                        % (record.analytic_account_id.currency_id.name)
                    )
                )

    def _prepare_analytic_lines(self):
        if not self.analytic_account_id:
            return super(AccountMoveLine, self)._prepare_analytic_lines()
        distribution = 100
        account_ids = str(self.analytic_account_id.id)
        distribution_on_each_plan = {}
        analytic_line_vals = []
        line_values = self._prepare_analytic_distribution_line(
            float(distribution), account_ids, distribution_on_each_plan
        )
        if not self.currency_id.is_zero(line_values.get("amount")):
            analytic_line_vals.append(line_values)
        return analytic_line_vals
