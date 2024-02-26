from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = "sale.order"

    approval_level_id = fields.Many2one(
        "sh.sale.approval.config",
        string="Approval Level",
        compute="compute_approval_level",
    )
    state = fields.Selection(
        selection_add=[
            ("waiting_for_approval", "Waiting for Approval"),
            ("reject", "Reject"),
            ("sale",),
        ]
    )
    level = fields.Integer(string="Next Approval Level", readonly=True)
    user_ids = fields.Many2many("res.users", string="Users", readonly=True)
    group_ids = fields.Many2many("res.groups", string="Groups", readonly=True)
    is_boolean = fields.Boolean(
        string="Boolean", compute="compute_is_boolean", search="_search_is_boolean"
    )
    approval_info_line = fields.One2many(
        "sh.sale.approval.info", "sale_order_id", readonly=True
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
            so_ids = self.env["sale.order"].search([])
            if so_ids:
                for so in so_ids:
                    if self.env.user.id in so.user_ids.ids or any(
                        item in self.env.user.groups_id.ids for item in so.group_ids.ids
                    ):
                        results.append(so.id)
        return [("id", "in", results)]

    def action_confirm(self):
        template_id = self.env.ref(
            "fs_sale_dynamic_approval.email_template_for_approve_sale_order"
        )

        if self.approval_level_id.sale_approval_line:
            self.write({"state": "waiting_for_approval"})
            lines = self.approval_level_id.sale_approval_line

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
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                            },
                        )

                notifications = []
                if users:
                    for user in users:
                        notifications.append(
                            [
                                user.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for Purchase"
                                        " order %s"
                                    )
                                    % (self.name),
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
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                            },
                        )

                notifications = []
                if lines[0].user_ids:
                    for user in lines[0].user_ids:
                        notifications.append(
                            [
                                user.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for Sale"
                                        " order %s"
                                    )
                                    % (self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)

        else:
            super(SaleOrder, self).action_confirm()

    @api.depends("amount_untaxed", "amount_total")
    def compute_approval_level(self):
        if self.company_id.sale_approval_based_on:
            if self.company_id.sale_approval_based_on == "untaxed_amount":
                sale_approvals = self.env["sh.sale.approval.config"].search(
                    [
                        ("min_amount", "<=", self.amount_untaxed),
                        ("company_ids.id", "in", [self.env.company.id]),
                    ]
                )

                listt = []
                for sale_approval in sale_approvals:
                    listt.append(sale_approval.min_amount)

                if listt:
                    sale_approval = sale_approvals.filtered(
                        lambda x: x.min_amount == max(listt)
                    )

                    self.update({"approval_level_id": sale_approval[0].id})
                else:
                    self.approval_level_id = False

            if self.company_id.sale_approval_based_on == "total":
                sale_approvals = self.env["sh.sale.approval.config"].search(
                    [
                        ("min_amount", "<=", self.amount_total),
                        ("company_ids.id", "in", [self.env.company.id]),
                    ]
                )

                listt = []
                for sale_approval in sale_approvals:
                    listt.append(purchase_approval.min_amount)

                if listt:
                    sale_approval = sale_approvals.filtered(
                        lambda x: x.min_amount == max(listt)
                    )

                    self.update({"approval_level_id": sale_approval[0].id})
                else:
                    self.approval_level_id = False

        else:
            self.approval_level_id = False

    def action_approve_order(self):
        template_id = self.env.ref(
            "fs_sale_dynamic_approval.email_template_for_approve_sale_order"
        )

        info = self.approval_info_line.filtered(lambda x: x.level == self.level)

        if info:
            info.status = True
            info.approval_date = datetime.now()
            info.approved_by = self.env.user

        line_id = self.env["sh.sale.approval.line"].search(
            [
                ("sale_approval_config_id", "=", self.approval_level_id.id),
                ("level", "=", self.level),
            ]
        )

        next_line = self.env["sh.sale.approval.line"].search(
            [
                ("sale_approval_config_id", "=", self.approval_level_id.id),
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
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                                "email_cc": self.user_id.email,
                            },
                        )

                if template_id and users and not self.approval_level_id.is_boolean:
                    for user in users:
                        template_id.sudo().send_mail(
                            self.id,
                            force_send=True,
                            email_values={
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                            },
                        )

                notifications = []
                if users:
                    for user in users:
                        notifications.append(
                            [
                                user.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for Sale"
                                        " order %s"
                                    )
                                    % (self.name),
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
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                                "email_cc": self.user_id.email,
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
                                "email_from": self.env.user.email,
                                "email_to": user.email,
                            },
                        )

                notifications = []
                if next_line.user_ids:
                    for user in next_line.user_ids:
                        notifications.append(
                            [
                                user.partner_id,
                                (self._cr.dbname, "res.partner", user.partner_id.id),
                                {
                                    "type": "user_connection",
                                    "title": _("Notification"),
                                    "message": (
                                        "You have approval notification for Sale"
                                        " order %s"
                                    )
                                    % (self.name),
                                    "sticky": True,
                                    "warning": True,
                                },
                            ]
                        )
                    self.env["bus.bus"]._sendmany(notifications)

        else:
            template_id = self.env.ref(
                "fs_sale_dynamic_approval.email_template_for_confirm_sale_order"
            )
            if template_id:
                template_id.sudo().send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        "email_from": self.env.user.email,
                        "email_to": self.user_id.email,
                    },
                )

            notifications = []
            if self.user_ids:
                notifications.append(
                    [
                        self.user_id.partner_id,
                        (self._cr.dbname, "res.partner", self.user_id.partner_id.id),
                        {
                            "type": "user_connection",
                            "title": _("Notification"),
                            "message": "Dear User!! your Sale order %s is confirmed"
                            % (self.name),
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
            super(SaleOrder, self).action_confirm()

    def _can_be_confirmed(self):
        return True

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_invoice_line(self, **optional_values):
        results = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.order_id.analytic_account_id:
            results.update(
                {
                    "analytic_account_id": self.order_id.analytic_account_id.id,
                }
            )
        return results
