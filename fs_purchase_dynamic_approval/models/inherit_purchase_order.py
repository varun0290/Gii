from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    approval_level_id = fields.Many2one(
        "sh.purchase.approval.config",
        string="Approval Level",
        compute="compute_approval_level",
    )
    state = fields.Selection(
        selection_add=[
            ("to_review", "To Review"),
            ("waiting_for_approval", "Waiting for Approval"),
            ("reject", "Reject"),
            ("purchase",),
        ]
    )
    level = fields.Integer(
        string="Next Approval Level",
        readonly=True,
        copy=False,
    )
    review_level = fields.Integer(
        string="Next Reviewer Level",
        readonly=True,
        copy=False,
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Users",
        readonly=True,
        copy=False,
    )
    reviewer_user_ids = fields.Many2many(
        "res.users",
        "rel_reviewer_res_users",
        string="Reviewer",
        copy=False,
    )
    group_ids = fields.Many2many(
        "res.groups",
        string="Groups",
        readonly=True,
        copy=False,
    )
    is_boolean = fields.Boolean(
        string="Boolean",
        compute="compute_is_boolean",
        search="_search_is_boolean",
    )
    is_skip_boolean = fields.Boolean(
        string="Boolean",
        compute="compute_is_skip_boolean",
        search="_search_is_skip_boolean",
    )
    is_reviewer = fields.Boolean(
        string="Reviewer",
        compute="compute_is_reviewer",
        search="_search_is_reviewer",
    )
    approval_info_line = fields.One2many(
        "sh.approval.info",
        "purchase_order_id",
        readonly=True,
    )
    reviewer_info_line = fields.One2many(
        "purchase.reviewer",
        "review_purchase_id",
        string="Reviewer Info",
    )
    rejection_date = fields.Datetime(
        string="Reject Date",
        readonly=True,
    )
    reject_by = fields.Many2one(
        "res.users",
        string="Reject By",
        readonly=True,
    )
    reject_reason = fields.Char(
        string="Reject Reason",
        readonly=True,
    )
    department_ids = fields.Many2many(
        "hr.department",
        related="user_id.department_ids",
        string="Departments",
    )

    def compute_is_skip_boolean(self):
        line = self.approval_level_id.purchase_approval_line
        if line and self.env.user.id in line[0].user_ids.ids:
            self.is_skip_boolean = True
        else:
            self.is_skip_boolean = False

    def _search_is_skip_boolean(self, operator, value):
        results = []
        if value:
            po_ids = self.env["purchase.order"].search([])
            if po_ids:
                for po in po_ids:
                    line = po.approval_level_id.purchase_approval_line
                    if self.env.user.id in line[0].user_ids.ids:
                        results.append(po.id)
        return [("id", "in", results)]

    def compute_is_reviewer(self):
        if self.env.user.id in self.reviewer_user_ids.ids:
            self.is_reviewer = True
        else:
            self.is_reviewer = False

    def _search_is_reviewer(self, operator, value):
        results = []
        if value:
            po_ids = self.env["purchase.order"].search([])
            if po_ids:
                for po in po_ids:
                    if self.env.user.id in po.reviewer_user_ids.ids:
                        results.append(po.id)
        return [("id", "in", results)]

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
            po_ids = self.env["purchase.order"].search([])
            if po_ids:
                for po in po_ids:
                    if self.env.user.id in po.user_ids.ids or any(
                        item in self.env.user.groups_id.ids for item in po.group_ids.ids
                    ):
                        results.append(po.id)
        return [("id", "in", results)]

    def action_review_done(self):
        template_id = self.env.ref(
            "fs_purchase_dynamic_approval.email_template_for_review_purchase_order"
        )

        info = self.reviewer_info_line.filtered(lambda x: x.level == self.review_level)

        if info:
            info.status = True
            info.reviewed_date = datetime.now()
            info.reviewed_by = self.env.user

        line_id = self.env["purchase.reviewer"].search(
            [
                ("level", "=", self.review_level),
                ("review_purchase_id", "=", self.id),
            ],
            limit=1,
        )

        next_line = self.env["purchase.reviewer"].search(
            [
                ("level", ">", line_id.level),
                ("review_purchase_id", "=", self.id),
            ],
            limit=1,
        )

        if next_line:
            self.write(
                {
                    "review_level": next_line.level,
                    "reviewer_user_ids": [(6, 0, next_line.user_ids.ids)],
                }
            )

            if template_id and next_line.user_ids:
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
                                    "You have review notification for purchase"
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
            self.action_send_approval()

    def action_skip_reviewer(self):
        line_id = self.env["purchase.reviewer"].search(
            [
                ("level", "=", self.review_level),
                ("review_purchase_id", "=", self.id),
            ],
            limit=1,
        )

        next_line = self.env["purchase.reviewer"].search(
            [
                ("level", ">", line_id.level),
                ("review_purchase_id", "=", self.id),
            ],
            limit=1,
        )
        if next_line:
            self.write(
                {
                    "review_level": next_line.level,
                    "reviewer_user_ids": [(6, 0, next_line.user_ids.ids)],
                }
            )
        else:
            self.action_send_approval()

    def button_confirm(self):
        template_id = self.env.ref(
            "fs_purchase_dynamic_approval.email_template_for_review_purchase_order"
        )

        if self.reviewer_info_line:
            self.write({"state": "to_review"})
            lines = self.reviewer_info_line
            if lines:
                self.write(
                    {
                        "review_level": lines[0].level,
                        "reviewer_user_ids": [(6, 0, lines[0].user_ids.ids)],
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
                                        "You have review notification for purchase"
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
            self.action_send_approval()

    def action_send_approval(self):
        template_id = self.env.ref(
            "fs_purchase_dynamic_approval.email_template_for_approve_purchase_order"
        )

        if self.approval_level_id.purchase_approval_line:
            self.write({"state": "waiting_for_approval"})
            lines = self.approval_level_id.purchase_approval_line

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
        else:
            for order in self:
                order.order_line._validate_analytic_distribution()
                order._add_supplier_to_product()
                # Deal with double validation process
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({"state": "to approve"})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])

    @api.depends("amount_untaxed", "amount_total")
    def compute_approval_level(self):
        if self.company_id.approval_based_on:
            if self.company_id.approval_based_on == "untaxed_amount":
                purchase_approvals = self.env["sh.purchase.approval.config"].search(
                    [
                        ("min_amount", "<=", self.amount_untaxed),
                        ("company_ids.id", "in", [self.env.company.id]),
                        ("department_ids", "in", self.user_id.department_ids.ids),
                    ]
                )

                listt = []
                for purchase_approval in purchase_approvals:
                    listt.append(purchase_approval.min_amount)

                if listt:
                    purchase_approval = purchase_approvals.filtered(
                        lambda x: x.min_amount == max(listt)
                    )

                    self.update({"approval_level_id": purchase_approval[0].id})
                else:
                    self.approval_level_id = False

            if self.company_id.approval_based_on == "total":
                purchase_approvals = self.env["sh.purchase.approval.config"].search(
                    [
                        ("min_amount", "<=", self.amount_total),
                        ("company_ids.id", "in", [self.env.company.id]),
                        ("department_ids", "in", self.user_id.department_ids.ids),
                    ]
                )

                listt = []
                for purchase_approval in purchase_approvals:
                    listt.append(purchase_approval.min_amount)

                if listt:
                    purchase_approval = purchase_approvals.filtered(
                        lambda x: x.min_amount == max(listt)
                    )

                    self.update({"approval_level_id": purchase_approval[0].id})
                else:
                    self.approval_level_id = False

        else:
            self.approval_level_id = False

    def action_approve_order(self):
        template_id = self.env.ref(
            "fs_purchase_dynamic_approval.email_template_for_approve_purchase_order"
        )

        info = self.approval_info_line.filtered(lambda x: x.level == self.level)

        if info:
            info.status = True
            info.approval_date = datetime.now()
            info.approved_by = self.env.user

        line_id = self.env["sh.purchase.approval.line"].search(
            [
                ("purchase_approval_config_id", "=", self.approval_level_id.id),
                ("level", "=", self.level),
            ]
        )

        next_line = self.env["sh.purchase.approval.line"].search(
            [
                ("purchase_approval_config_id", "=", self.approval_level_id.id),
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

        else:
            template_id = self.env.ref(
                "fs_purchase_dynamic_approval.email_template_for_confirm_purchase_order"
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
                            "message": "Dear User!! your Purchase order %s is confirmed"
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
            for order in self:
                order.order_line._validate_analytic_distribution()
                order._add_supplier_to_product()
                # Deal with double validation process
                if order._approval_allowed():
                    order.button_approve()
                else:
                    order.write({"state": "to approve"})
                if order.partner_id not in order.message_partner_ids:
                    order.message_subscribe([order.partner_id.id])

    def action_reset_to_draft(self):
        self.write({"state": "draft"})


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Account Analytic",
    )
    project_id = fields.Many2one("project.project", string="Project")

    @api.depends("product_id", "order_id.partner_id", "analytic_account_id")
    def _compute_analytic_distribution(self):
        super(PurchaseOrderLine, self)._compute_analytic_distribution()
        for rec in self:
            if rec.analytic_account_id:
                analytic_account_id = str(rec.analytic_account_id.id)
                rec.analytic_distribution = {analytic_account_id: 100}

    def _prepare_account_move_line(self, move=False):
        results = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        results.update(
            {
                "analytic_account_id": self.analytic_account_id.id,
                "analytic_distribution": {str(self.analytic_account_id.id): 100},
            }
        )
        return results

    @api.constrains("analytic_account_id", "price_subtotal", "state")
    def _check_analytic_account_budget(self):
        for record in self:
            if not record.analytic_account_id:
                continue
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
                raise ValidationError(
                    _(
                        "Transaction exceeds project budget (%s %s)"
                        % (
                            crossovered_budget_line[0].planned_amount,
                            record.currency_id.name,
                        )
                    )
                )
