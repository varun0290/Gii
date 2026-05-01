from datetime import timedelta

from markupsafe import Markup

from odoo import models, fields, api, _
from odoo.tools import format_date


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    attachment_required = fields.Boolean(compute="_compute_attachment_required")
    timeoff_reminder_last_send_date = fields.Date(
        string='Last approval reminder sent on',
        copy=False,
        readonly=True,
        groups='hr_holidays.group_hr_holidays_user',
        help='Automatic reminder emails to approvers are sent at most once per day per request.',
    )

    @api.depends('number_of_days_display')
    def _compute_attachment_required(self):
        for leave in self:
            leave.attachment_required = False
            if leave.holiday_status_id.is_sick_leave and leave.number_of_days_display > 3:
                leave.attachment_required = True

    @api.model
    def _cron_time_off_approval_reminder(self):
        """Email approvers when time off is still pending and starts within 7 days."""
        today = fields.Date.today()
        horizon = today + timedelta(days=7)
        domain = [
            ('state', 'in', ('confirm', 'validate1')),
            ('holiday_type', '=', 'employee'),
            ('active', '=', True),
            ('holiday_status_id.leave_validation_type', '!=', 'no_validation'),
            ('request_date_from', '<=', horizon),
            ('request_date_from', '>=', today),
            '|', ('timeoff_reminder_last_send_date', '=', False),
            ('timeoff_reminder_last_send_date', '<', today),
        ]
        leaves = self.sudo().search(domain, order='request_date_from, id')
        for leave in leaves:
            approvers = leave._get_responsible_for_approval()
            partners = approvers.mapped('partner_id').filtered('email')
            if not partners:
                continue
            leave._send_time_off_approval_reminder_email(partners)
            leave.timeoff_reminder_last_send_date = today

    def _send_time_off_approval_reminder_email(self, partner_records):
        self.ensure_one()
        env = self.env
        date_from = format_date(env, self.request_date_from)
        date_to = format_date(env, self.request_date_to)
        base_url = self.get_base_url()
        link = f'{base_url}/web#id={self.id}&model=hr.leave&view_type=form'
        state_label = dict(self._fields['state'].selection).get(self.state, self.state)
        body = Markup(
            '<p>%s</p>'
            '<ul>'
            '<li><strong>%s</strong> %s</li>'
            '<li><strong>%s</strong> %s</li>'
            '<li><strong>%s</strong> %s — %s</li>'
            '<li><strong>%s</strong> %s</li>'
            '</ul>'
            '<p><a href="%s">%s</a></p>'
        ) % (
            _('This time off request is still awaiting approval and the start date is within the next 7 days.'),
            _('Employee:'),
            self.employee_id.name or '',
            _('Time off type:'),
            self.holiday_status_id.name or '',
            _('Dates:'),
            date_from,
            date_to,
            _('Status:'),
            state_label,
            link,
            _('Open request in Odoo'),
        )
        self.message_notify(
            subject=_(
                'Reminder: %(employee)s — time off pending approval (%(dates)s)',
                employee=self.employee_id.name or '',
                dates=date_from,
            ),
            body=body,
            partner_ids=partner_records.ids,
            email_layout_xmlid='mail.mail_notification_light',
            record_name=self.display_name,
        )
