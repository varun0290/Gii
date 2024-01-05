from odoo import api, fields, tools, models, _


class AccountApprovalInfo(models.Model):
    _name = "account.sh.approval.info"
    _description = "Account Approval Information"

    level = fields.Integer(string="Approval Level")
    user_ids = fields.Many2many("res.users", string="Users")
    group_ids = fields.Many2many("res.groups", string="Groups")
    status = fields.Boolean(string="Status")
    approval_date = fields.Datetime(string="Approved Date")
    approved_by = fields.Many2one("res.users", string="Approved By")
    account_move_id = fields.Many2one("account.move")
