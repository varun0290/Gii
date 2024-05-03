from odoo import fields, api, models, _


class PurchaseReviewer(models.Model):
    _name = "purchase.reviewer"
    _description = "Purchase Reviewer"

    level = fields.Integer(string="Level")
    review_purchase_id = fields.Many2one(
        "purchase.order",
        string="Purchase",
    )
    department_ids = fields.Many2many(
        "hr.department",
        related="review_purchase_id.department_ids",
        string="Departments",
    )
    user_ids = fields.Many2many(
        "res.users",
        string="Users",
        domain="[('department_ids', 'in', department_ids)]",
    )
    status = fields.Boolean(string="Status")
    reviewed_date = fields.Datetime(string="Reviewed Date")
    reviewed_by = fields.Many2one("res.users", string="Reviewed By")
