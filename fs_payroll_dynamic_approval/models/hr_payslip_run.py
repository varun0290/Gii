# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection(
        selection_add=[
            ('wait_hr', 'Waiting HR'),
            ('wait_finance', 'Waiting Finance'),
        ],
        ondelete={'wait_hr': 'set default', 'wait_finance': 'set default'},
    )

    approval_done = fields.Boolean(
        string="Payroll approvals completed",
        default=False,
        copy=False,
        help="Set when Finance completes batch approval so Confirmed payroll can be processed.",
    )

    def _compute_state_change(self):
        """Delay auto-move to Confirmed until approval workflows have finished."""
        for payslip_run in self:
            if payslip_run.state in ('wait_hr', 'wait_finance'):
                continue
            if payslip_run.state == 'draft' and payslip_run.slip_ids:
                payslip_run.update({'state': 'verify', 'approval_done': False})

    def action_submit_for_approval(self):
        for record in self:
            if not record.slip_ids:
                raise UserError(_("Generate payslips before submitting for approval."))
            record.write({'state': 'wait_hr', 'approval_done': False})

    def action_approve_hr(self):
        if not self.env.user.has_group('fs_hr_contract.group_head_of_hr') and not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only Head of HR can approve."))
        for record in self:
            record.write({'state': 'wait_finance'})

    def action_approve_finance(self):
        if not self.env.user.has_group('fs_hr_contract.group_vp_finance') and not self.env.user.has_group('base.group_system'):
            raise UserError(_("Only Contract Finance Approver (VP Finance) can approve."))
        for record in self:
            record.write({'state': 'verify', 'approval_done': True})

    def action_reject(self):
        if not (self.env.user.has_group('fs_hr_contract.group_head_of_hr') or
                self.env.user.has_group('fs_hr_contract.group_vp_finance') or
                self.env.user.has_group('base.group_system')):
            raise UserError(_("You are not authorized to reject."))
        for record in self:
            record.write({'state': 'verify', 'approval_done': False})

    def action_validate(self):
        not_approved = self.filtered(lambda r: r.state not in ('verify', 'close', 'paid'))
        if not_approved:
            raise UserError(_(
                "Payroll batch must be submitted and approved before processing. "
                "Use Submit for Approval and complete Finance approval."
            ))
        unready = self.filtered(lambda r: r.state == 'verify' and not r.approval_done)
        if unready:
            raise UserError(_(
                "This batch is not cleared for payroll processing yet. Complete HR/Finance approvals first."
            ))
        return super().action_validate()

    def action_draft(self):
        res = super().action_draft()
        self.write({'approval_done': False})
        return res
