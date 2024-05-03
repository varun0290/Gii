from odoo import fields, api, models, _


class PurchaseReviewer(models.Model):
    _name = "purchase.reviewer"
    _description = "Purchase Reviewer"

    level = fields.Integer(string="Level")
    user_ids = fields.Many2many("res.users", string="Users")
    review_purchase_id = fields.Many2one(
        "purchase.order",
        string="Purchase",
    )
    status = fields.Boolean(string="Status")
    reviewed_date = fields.Datetime(string="Reviewed Date")
    reviewed_by = fields.Many2one("res.users", string="Reviewed By")
