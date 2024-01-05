from odoo import api, fields, tools, models, _


class SaleApprovalInfo(models.Model):
    _name = "sh.sale.approval.info"
    _description = "Sale Approval Information"

    level = fields.Integer(string="Approval Level")
    user_ids = fields.Many2many("res.users", string="Users")
    group_ids = fields.Many2many("res.groups", string="Groups")
    status = fields.Boolean(string="Status")
    approval_date = fields.Datetime(string="Approved Date")
    approved_by = fields.Many2one("res.users", string="Approved By")
    sale_order_id = fields.Many2one("sale.order")
