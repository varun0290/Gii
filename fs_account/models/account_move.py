# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        for line in self.invoice_line_ids:
            if line.analytic_distribution:
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
    debit_account_id = fields.Many2one(
        "account.account",
        string="Debit Account",
        default=lambda self: self.env.company.deferred_expense_account_id,
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

    def _generate_deferred_entries(self):
        """
        Generates the deferred entries for the invoice.
        """
        self.ensure_one()
        if self.is_entry():
            raise UserError(
                _(
                    "You cannot generate deferred entries for a miscellaneous journal entry."
                )
            )
        assert (
            not self.deferred_move_ids
        ), "The deferred entries have already been generated for this document."
        is_deferred_expense = self.is_purchase_document()
        deferred_account = (
            self.debit_account_id
            if is_deferred_expense
            else self.company_id.deferred_revenue_account_id
        )
        deferred_journal = self.company_id.deferred_journal_id
        if not deferred_journal:
            raise UserError(
                _("Please set the deferred journal in the accounting settings.")
            )
        if not deferred_account:
            raise UserError(
                _("Please set the deferred accounts in the accounting settings.")
            )

        for line in self.line_ids.filtered(
            lambda l: l.deferred_start_date and l.deferred_end_date
        ):
            periods = line._get_deferred_periods()
            if not periods:
                continue

            ref = _("Deferral of %s", line.move_id.name or "")
            # Defer the current invoice
            move_fully_deferred = self.create(
                {
                    "move_type": "entry",
                    "deferred_original_move_ids": [Command.set(line.move_id.ids)],
                    "journal_id": deferred_journal.id,
                    "company_id": self.company_id.id,
                    "partner_id": line.partner_id.id,
                    "date": line.move_id.date,
                    "auto_post": "at_date",
                    "ref": ref,
                }
            )
            # We write the lines after creation, to make sure the `deferred_original_move_ids` is set.
            # This way we can avoid adding taxes for deferred moves.
            move_fully_deferred.write(
                {
                    "line_ids": [
                        Command.create(
                            self.env["account.move.line"]._get_deferred_lines_values(
                                account.id,
                                coeff * line.balance,
                                ref,
                                line.analytic_distribution,
                                line,
                            )
                        )
                        for (account, coeff) in [
                            (line.account_id, -1),
                            (deferred_account, 1),
                        ]
                    ],
                }
            )

            # Create the deferred entries for the periods [deferred_start_date, deferred_end_date]
            deferral_moves = self.create(
                [
                    {
                        "move_type": "entry",
                        "deferred_original_move_ids": [Command.set(line.move_id.ids)],
                        "journal_id": deferred_journal.id,
                        "partner_id": line.partner_id.id,
                        "date": period[1],
                        "auto_post": "at_date",
                        "ref": ref,
                    }
                    for period in periods
                ]
            )
            remaining_balance = line.balance
            for period_index, (period, deferral_move) in enumerate(
                zip(periods, deferral_moves)
            ):
                # For the last deferral move the balance is forced to remaining balance to avoid rounding errors
                force_balance = (
                    remaining_balance if period_index == len(periods) - 1 else None
                )
                # Same as before, to avoid adding taxes for deferred moves.
                deferral_move.write(
                    {
                        "line_ids": self._get_deferred_lines(
                            line,
                            deferred_account,
                            period,
                            ref,
                            force_balance=force_balance,
                        ),
                    }
                )
                remaining_balance -= deferral_move.line_ids[0].balance

            deferred_moves = move_fully_deferred + deferral_moves
            line.move_id.deferred_move_ids |= deferred_moves
            deferred_moves._post(soft=True)


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
