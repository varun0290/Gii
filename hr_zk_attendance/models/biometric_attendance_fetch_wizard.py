# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BiometricAttendanceFetchWizard(models.TransientModel):
    """Manual Web API attendance pull between two calendar dates."""

    _name = "biometric.attendance.fetch.wizard"
    _description = "Fetch biometric attendance by date range"

    device_id = fields.Many2one(
        "biometric.device.details",
        string="Biometric integration",
        required=True,
        ondelete="cascade",
    )
    date_from = fields.Date(
        required=True,
        string="From date",
        help="Maps to FromDate sent to GetDeviceLogs (YYYY-MM-DD).",
    )
    date_to = fields.Date(
        required=True,
        string="To date",
        help="Maps to ToDate sent to GetDeviceLogs (inclusive).",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        vals.setdefault("date_to", fields.Date.today())
        vals.setdefault(
            "date_from", fields.Date.today() - relativedelta(days=7)
        )
        return vals

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for wiz in self:
            if wiz.date_from and wiz.date_to and wiz.date_from > wiz.date_to:
                raise ValidationError(_("From date cannot be after To date."))

    def action_fetch_attendance(self):
        self.ensure_one()
        device = self.device_id
        if device.connection_mode != "web_api":
            raise UserError(
                _("Date-range fetch applies only when Integration is Web API.")
            )
        stats = device._sync_web_api_date_range(self.date_from, self.date_to)
        msg = _(
            "Fetched %(raw)s punch rows from the device API; consolidated into "
            "%(day)s employee-day attendances in Odoo."
        ) % {
            "raw": stats["raw_logs"],
            "day": stats["daily_rows"],
        }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": msg,
                "type": "success",
                "sticky": False,
            },
        }
