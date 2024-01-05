from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    approval_level_id = fields.Many2one(
        "account.sh.approval.config",
        string="Approval Level",
        compute="compute_approval_level",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("reject", "Reject"),
            ("to_approve", "To Approve"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    is_approval = fields.Boolean(compute="compute_approval_level", string="Approval")
    level = fields.Integer(string="Next Approval Level", readonly=True)
    user_ids = fields.Many2many("res.users", string="Users", readonly=True)
    group_ids = fields.Many2many("res.groups", string="Groups", readonly=True)
    is_boolean = fields.Boolean(
        string="Boolean", compute="compute_is_boolean", search="_search_is_boolean"
    )
    approval_info_line = fields.One2many(
        "account.sh.approval.info", "account_move_id", readonly=True
    )
    rejection_date = fields.Datetime(string="Reject Date", readonly=True)
    reject_by = fields.Many2one("res.users", string="Reject By", readonly=True)
    reject_reason = fields.Char(string="Reject Reason", readonly=True)

    def compute_is_boolean(self):
        if self.env.user.id in self.user_ids.ids or any(
            item in self.env.user.groups_id.ids for item in self.group_ids.ids
        ):
            self.is_boolean = True
        else:
            self.is_boolean = False

    def _search_is_boolean(self, operator, value):
        results = []

        if value:
            move_ids = self.env["account.move"].search([])
            if move_ids:
                for move in move_ids:
                    if self.env.user.id in move.user_ids.ids or any(
                        item in self.env.user.groups_id.ids
                        for item in move.group_ids.ids
                    ):
                        results.append(move.id)
        return [("id", "in", results)]

    def action_post(self):
        template_id = self.env.ref(
            "fs_account_dyanamic_approval.email_template_for_approve_account_move"
        )

        if self.approval_level_id.account_approval_line:
            self.write({"state": "to_approve"})
            lines = self.approval_level_id.account_approval_line
            self.approval_info_line = False
            for line in lines:
                dictt = []
                if line.approve_by == "group":
                    dictt.append(
                        (
                            0,
                            0,
                            {
                                "level": line.level,
                                "user_ids": False,
                                "group_ids": [(6, 0, line.group_ids.ids)],
                            },
                        )
                    )

                if line.approve_by == "user":
                    dictt.append(
                        (
                            0,
                            0,
                            {
                                "level": line.level,
                                "user_ids": [(6, 0, line.user_ids.ids)],
                                "group_ids": False,
                            },
                        )
                    )

                self.update({"approval_info_line": dictt})

            if lines[0].approve_by == "group":
                self.write(
                    {
                        "level": lines[0].level,
                        "group_ids": [(6, 0, lines[0].group_ids.ids)],
                        "user_ids": False,
                    }
                )

                users = self.env["res.users"].search(
                    [("groups_id", "in", lines[0].group_ids.ids)]
                )

                if template_id and users:
                    for user in users:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                            },
                        )

                notifications = []
                if users:
                    for user in users:
                        notifications.append(
                            [
                                self.invoice_user_id.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for %s %s"
                                    )
                                    % (self.journal_id.name, self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)

            if lines[0].approve_by == "user":
                self.write(
                    {
                        "level": lines[0].level,
                        "user_ids": [(6, 0, lines[0].user_ids.ids)],
                        "group_ids": False,
                    }
                )

                if template_id and lines[0].user_ids:
                    for user in lines[0].user_ids:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                            },
                        )

                notifications = []
                if lines[0].user_ids:
                    for user in lines[0].user_ids:
                        notifications.append(
                            [
                                self.invoice_user_id.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for %s %s"
                                    )
                                    % (self.journal_id.name, self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)
        else:
            super(AccountMove, self).action_post()

    @api.depends("amount_untaxed", "amount_total")
    def compute_approval_level(self):
        for move in self:
            if move.company_id.account_approval_based_on:
                if move.company_id.account_approval_based_on == "untaxed_amount":
                    account_approvals = self.env["account.sh.approval.config"].search(
                        [
                            ("min_amount", "<=", move.amount_untaxed),
                            ("journal_ids", "in", move.journal_id.ids),
                            ("company_ids", "in", self.env.company.ids),
                        ]
                    )
                    listt = []
                    for move_approval in account_approvals:
                        listt.append(move_approval.min_amount)

                    if listt:
                        move_approval = account_approvals.filtered(
                            lambda x: x.min_amount == max(listt)
                        )
                        move.is_approval = True
                        move.update({"approval_level_id": move_approval[0].id})
                    else:
                        move.approval_level_id = False
                        move.is_approval = False

                if move.company_id.account_approval_based_on == "total":
                    account_approvals = self.env["account.sh.approval.config"].search(
                        [
                            ("min_amount", "<=", move.amount_total),
                            ("journal_ids", "in", move.journal_id.ids),
                            ("company_ids", "in", self.env.company.ids),
                        ]
                    )

                    listt = []
                    for move_approval in account_approvals:
                        listt.append(move_approval.min_amount)

                    if listt:
                        move_approval = account_approvals.filtered(
                            lambda x: x.min_amount == max(listt)
                        )
                        move.is_approval = True
                        move.update({"approval_level_id": move_approval[0].id})
                    else:
                        move.is_approval = False
                        move.approval_level_id = False
            else:
                move.is_approval = False
                move.approval_level_id = False

    def action_approve_order(self):
        template_id = self.env.ref(
            "fs_account_dyanamic_approval.email_template_for_approve_account_move"
        )

        info = self.approval_info_line.filtered(lambda x: x.level == self.level)

        if info:
            info.status = True
            info.approval_date = datetime.now()
            info.approved_by = self.env.user

        line_id = self.env["account.sh.approval.line"].search(
            [
                ("account_approval_config_id", "=", self.approval_level_id.id),
                ("level", "=", self.level),
            ]
        )

        next_line = self.env["account.sh.approval.line"].search(
            [
                ("account_approval_config_id", "=", self.approval_level_id.id),
                ("id", ">", line_id.id),
            ],
            limit=1,
        )

        if next_line:
            if next_line.approve_by == "group":
                self.write(
                    {
                        "level": next_line.level,
                        "group_ids": [(6, 0, next_line.group_ids.ids)],
                        "user_ids": False,
                    }
                )
                users = self.env["res.users"].search(
                    [("groups_id", "in", next_line.group_ids.ids)]
                )

                if template_id and users and self.approval_level_id.is_boolean:
                    for user in users:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                                "email_cc": self.user_id.email_formatted,
                            },
                        )

                if template_id and users and not self.approval_level_id.is_boolean:
                    for user in users:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                            },
                        )

                notifications = []
                if users:
                    for user in users:
                        notifications.append(
                            [
                                self.invoice_user_id.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for %s %s"
                                    )
                                    % (self.journal_id.name, self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)

            if next_line.approve_by == "user":
                self.write(
                    {
                        "level": next_line.level,
                        "user_ids": [(6, 0, next_line.user_ids.ids)],
                        "group_ids": False,
                    }
                )
                if (
                    template_id
                    and next_line.user_ids
                    and self.approval_level_id.is_boolean
                ):
                    for user in next_line.user_ids:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                                "email_cc": self.user_id.email_formatted,
                            },
                        )

                if (
                    template_id
                    and next_line.user_ids
                    and not self.approval_level_id.is_boolean
                ):
                    for user in next_line.user_ids:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email_formatted,
                                "email_to": user.email_formatted,
                            },
                        )

                notifications = []
                if next_line.user_ids:
                    for user in next_line.user_ids:
                        notifications.append(
                            [
                                self.invoice_user_id.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for %s %s"
                                    )
                                    % (self.journal_id.name, self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)

        else:
            template_id = self.env.ref(
                "fs_account_dyanamic_approval.email_template_for_post_account_move"
            )
            if template_id:
                template_id.sudo().send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        "email_from": self.env.user.email_formatted,
                        "email_to": self.user_id.email_formatted,
                    },
                )

            notifications = []
            if self.user_ids:
                notifications.append(
                    [
                        self.invoice_user_id.partner_id,
                        (self._cr.dbname, "res.partner", self.user_id.partner_id.id),
                        {
                            "type": "user_connection",
                            "title": _("Notification"),
                            "message": "Dear User!! your %s %s is posted"
                            % (self.journal_id.name, self.name),
                            "sticky": True,
                            "warning": True,
                        },
                    ]
                )
                self.env["bus.bus"]._sendmany(notifications)

            self.write(
                {
                    "level": False,
                    "group_ids": False,
                    "user_ids": False,
                }
            )
            super(AccountMove, self).action_post()

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
