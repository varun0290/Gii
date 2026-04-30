from odoo import models, fields, api, _
from odoo.exceptions import MissingError, UserError
from dateutil.relativedelta import relativedelta


def _many2one_id_from_read(val):
    """read(load=False) Many2one is int OR (id, name); older paths use only tuple."""
    if not val:
        return False
    if isinstance(val, int):
        return val
    if isinstance(val, (list, tuple)) and len(val):
        return val[0]
    return False


class HrContract(models.Model):
    _inherit = 'hr.contract'

    state = fields.Selection(
        selection_add=[
            ('probation', 'Probation'),
        ],
        ondelete={'probation': 'cascade'},
    )

    probation_review_3_feedback = fields.Text(string="3rd Month Feedback", tracking=True)
    probation_review_5_feedback = fields.Text(string="5th Month Feedback", tracking=True)
    probation_final_decision = fields.Selection([
        ('approve', 'Approve as Full Time'),
        ('reject', 'Reject')
    ], string="Final Decision", tracking=True)
    
    probation_review_3_done = fields.Boolean(string="3rd Month Review Done", copy=False)
    probation_review_5_done = fields.Boolean(string="5th Month Review Done", copy=False)

    def action_approve_finance(self):
        """Override to move to probation instead of open."""
        res = super(HrContract, self).action_approve_finance()
        for record in self:
            record.with_context(skip_hr_contract_lock=True).write({'state': 'probation'})
        return res

    def action_probation_review(self):
        self.ensure_one()

        # Determine current review phase
        today = fields.Date.today()
        phase = '3'
        if self.date_start:
            months_passed = relativedelta(today, self.date_start).months + (relativedelta(today, self.date_start).years * 12)
            if months_passed >= 5:
                phase = '5'
            elif months_passed >= 3:
                phase = '3'

        # Copy env context but strip stale RPC keys: another screen's active_id or
        # default_* values (e.g. employee 361) were bleeding into the wizard create.
        # Also set res_id=False so the web client does not reopen an old transient
        # row (which ignores defaults and keeps a wrong contract_id).
        wizard_context = dict(self.env.context)
        for k in ('active_id', 'active_ids', 'active_model', 'active_domain'):
            wizard_context.pop(k, None)
        for k in list(wizard_context.keys()):
            if k.startswith('default_'):
                wizard_context.pop(k, None)
        wizard_context.update({
            'default_contract_id': self.id,
            'default_review_phase': phase,
        })

        return {
            'name': _('Probation Review'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.contract.probation.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': False,
            'context': wizard_context,
        }

    @api.model
    def _cron_probation_review_notification(self):
        """Scheduled action to check for due probation reviews."""
        today = fields.Date.today()
        
        # Check for 3rd month reviews
        contracts_3 = self.search([
            ('state', '=', 'probation'),
            ('probation_review_3_done', '=', False),
        ])
        for contract in contracts_3:
            if contract.date_start:
                due_date = contract.date_start + relativedelta(months=3)
                if today >= due_date:
                    contract._send_probation_notification(3)

        # Check for 5th month reviews
        contracts_5 = self.search([
            ('state', '=', 'probation'),
            ('probation_review_5_done', '=', False),
        ])
        for contract in contracts_5:
            if contract.date_start:
                due_date = contract.date_start + relativedelta(months=5)
                if today >= due_date:
                    contract._send_probation_notification(5)

    def _send_probation_notification(self, month):
        self.ensure_one()
        template = self.env.ref('fs_hr_probation.mail_template_probation_review_notice', raise_if_not_found=False)
        if template:
            template.with_context(review_month=month).send_mail(self.id, force_send=True)
        self.message_post(body=_("Probation review for month %d is now due.") % month)

    def action_confirm_full_time(self):
        """Advance contract state to Running (Open) after successful probation."""
        for record in self:
            if record.probation_final_decision != 'approve':
                raise UserError(_("Cannot confirm as full time unless the decision is 'Approve'."))
            
            if 'is_approve' in record._fields:
                record.with_context(skip_hr_contract_lock=True).write({'is_approve': True})
            
            record.with_context(skip_hr_contract_lock=True).write({
                'state': 'open',
            })
            
            if 'is_approve' in record._fields:
                record.with_context(skip_hr_contract_lock=True).write({'is_approve': False})
            # Trigger communication
            record._send_confirmation_email_and_letter()

    def _probation_confirmation_report_lang(self):
        """Partner language for mail/PDF; avoids QWeb traversing missing hr.employee rows."""
        self.ensure_one()
        row = self.read(['employee_id'], load=False)[0]
        eid = _many2one_id_from_read(row.get('employee_id'))
        if not eid:
            return False
        emp = self.env['hr.employee'].sudo().browse(eid)
        if not emp.exists():
            return False
        user = emp.user_id
        if not user or not user.exists() or not user.partner_id:
            return False
        return user.partner_id.lang or False

    def _send_confirmation_email_and_letter(self):
        """Send HR confirmation email and release the official letter."""
        self.ensure_one()
        template = self.env.ref('fs_hr_probation.mail_template_full_time_confirmation', raise_if_not_found=False)
        if not template:
            self.message_post(body=_("Employee confirmed as full-time. No confirmation email (missing template)."))
            return
        row = self.read(['employee_id'], load=False)[0]
        if not _many2one_id_from_read(row.get('employee_id')):
            self.message_post(body=_("Employee confirmed as full-time. No confirmation email (no employee on contract)."))
            return
        lang = self._probation_confirmation_report_lang() or self.env.lang
        try:
            # Template + report are hr.contract; res_id must be contract id. Context lang skips fragile QWeb on employees.
            template.with_context(lang=lang).send_mail(self.id, force_send=True)
        except MissingError as err:
            self.message_post(
                body=_("Employee confirmed as full-time, but the confirmation email/PDF failed: %s") % err
            )
            return
        self.message_post(body=_("Employee confirmed as full-time. Confirmation email and letter sent."))
