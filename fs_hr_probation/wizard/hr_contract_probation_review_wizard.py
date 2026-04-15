from odoo import models, fields, api, _

class HrContractProbationReviewWizard(models.TransientModel):
    _name = 'hr.contract.probation.review.wizard'
    _description = 'Probation Review Wizard'

    contract_id = fields.Many2one('hr.contract', string="Contract", required=True)
    review_phase = fields.Selection([
        ('3', '3rd Month'),
        ('5', '5th Month')
    ], string="Review Phase", required=True)
    
    feedback = fields.Text(string="Feedback", required=True)
    decision = fields.Selection([
        ('approve', 'Approve as Full Time'),
        ('reject', 'Reject')
    ], string="Final Decision")

    def action_submit_review(self):
        self.ensure_one()
        vals = {}
        if self.review_phase == '3':
            vals.update({
                'probation_review_3_feedback': self.feedback,
                'probation_review_3_done': True,
            })
        else:
            vals.update({
                'probation_review_5_feedback': self.feedback,
                'probation_final_decision': self.decision,
                'probation_review_5_done': True,
            })
        
        self.contract_id.with_context(skip_hr_contract_lock=True).write(vals)
        
        # If approved in 5th month, automatically advance to Running (Open)
        if self.review_phase == '5' and self.decision == 'approve':
            self.contract_id.action_confirm_full_time()
        
        return {'type': 'ir.actions.act_window_close'}
