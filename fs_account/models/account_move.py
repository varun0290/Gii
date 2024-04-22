# -*- coding: utf-8 -*-

from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        for line in self.invoice_line_ids:
            for account, distribution in line.analytic_distribution.items():
                analytic_account_id = self.env["account.analytic.account"].search(
                    [("id", "=", int(account))], limit=1
                )
                line.analytic_account_id = analytic_account_id.id
        inv_analytic_account_id = self.invoice_line_ids.filtered(
            lambda l: not l.analytic_account_id
        )
        if self.move_type != "entry" and inv_analytic_account_id:
            raise ValidationError(_("Please add analytic account in line."))

        return super(AccountMove, self).action_post()

    is_petty_cash = fields.Boolean(
        default=lambda self: self._context.get("is_petty_cash")
    )
    is_journal_entry = fields.Boolean(
        default=lambda self: self._context.get("is_journal_entry")
    )

    def _search_default_journal(self):
        journal = super(AccountMove, self)._search_default_journal()
        if self._context.get("is_journal_entry"):
            journal = self.env["account.journal"].search(
                [
                    ("name", "=", "Miscellaneous Operations"),
                    ("type", "=", "general"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
        elif self._context.get("is_petty_cash"):
            journal = self.env["account.journal"].search(
                [
                    ("name", "=", "Petty Cash"),
                    ("type", "=", "general"),
                    ("company_id", "=", self.env.company.id),
                ],
                limit=1,
            )
        return journal

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Account Analytic",
    )

    @api.constrains("analytic_account_id", "price_subtotal", "state")
    def _check_analytic_account_budget(self):
        for record in self:
            if record.move_type in ("out_invoice", "out_refund"):
                continue
            if not record.analytic_account_id:
                continue
            crossovered_budget_line = False
            crossovered_budget_line = (
                record.analytic_account_id.crossovered_budget_line.filtered(
                    lambda line: record.product_id.property_account_expense_id.id
                    in line.general_budget_id.account_ids.ids
                )
            )
            if (
                crossovered_budget_line
                and (
                    crossovered_budget_line[0].planned_amount
                    + crossovered_budget_line[0].practical_amount
                )
                < record.price_subtotal
            ):
                planned_amount = "{:,}".format(
                    crossovered_budget_line[0].planned_amount
                )
                raise ValidationError(
                    _(
                        "Transaction exceeds project budget (%s %s)"
                        % (
                            planned_amount,
                            record.currency_id.name,
                        )
                    )
                )
            elif (
                crossovered_budget_line
                and (
                    crossovered_budget_line[0].planned_amount
                    + crossovered_budget_line[0].practical_amount
                )
                < record.credit
            ):
                planned_amount = "{:,}".format(
                    crossovered_budget_line[0].planned_amount
                )
                raise ValidationError(
                    _(
                        "Transaction exceeds project budget (%s %s)"
                        % (
                            planned_amount,
                            record.currency_id.name,
                        )
                    )
                )
            elif (
                crossovered_budget_line
                and (
                    crossovered_budget_line[0].planned_amount
                    + crossovered_budget_line[0].practical_amount
                )
                < record.debit
            ):
                planned_amount = "{:,}".format(
                    crossovered_budget_line[0].planned_amount
                )
                raise ValidationError(
                    _(
                        "Transaction exceeds project budget (%s %s)"
                        % (
                            planned_amount,
                            record.currency_id.name,
                        )
                    )
                )

    # @api.constrains("analytic_account_id")
    # def _check_analytic_account(self):
    #     for record in self:
    #         if (
    #             record.analytic_account_id.currency_id
    #             and record.currency_id.id != record.analytic_account_id.currency_id.id
    #         ):
    #             raise ValidationError(
    #                 _(
    #                     "Project Currency (%s) should be same as transaction currency"
    #                     % (record.analytic_account_id.currency_id.name)
    #                 )
    #             )

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
