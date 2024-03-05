from odoo import models, fields, api

class HrJob(models.Model):
    _inherit = 'hr.job'

    def get_hr_job_status(self):
        return [('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    status = fields.Selection(selection=get_hr_job_status, default='draft')

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_set_to_draft(self):
        self.write({'status': 'draft'})

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args if args else []
        if args:
            args += [("status", '=', 'approved')]
        result = super(HrJob, self).name_search(
            name=name, args=args, operator=operator, limit=limit
        )
        return result

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        job_id = res.get('job_id')
        if isinstance(job_id, int) and job_id > 0:
            job_id = self.env['hr.job'].browse([job_id])
            if job_id and job_id.status != 'approved':
                del res['job_id']
        return res
