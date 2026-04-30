# -*- coding: utf-8 -*-
from odoo import api, models, _


def _many2one_id_from_read(val):
    if not val:
        return False
    if isinstance(val, int):
        return val
    if isinstance(val, (list, tuple)) and len(val):
        return val[0]
    return False


def _probation_confirmation_report_values(env, docids, is_with_changes):
    """Build PDF context for hr.contract; never browse missing hr.employee from QWeb."""
    contracts = env['hr.contract'].browse(docids)
    safe_employee_name = {cid: '' for cid in docids}
    for row in contracts.read(['employee_id']):
        cid = row['id']
        eid = _many2one_id_from_read(row.get('employee_id'))
        if not eid:
            continue
        emp = env['hr.employee'].sudo().browse(eid)
        safe_employee_name[cid] = emp.name if emp.exists() else _('(Employee record missing)')
    return {
        'doc_ids': docids,
        'doc_model': 'hr.contract',
        'docs': contracts,
        'safe_employee_name': safe_employee_name,
        'is_with_changes': is_with_changes,
    }


class ReportProbationConfirmedNoChanges(models.AbstractModel):
    # Short name: full ir.model name must map to PG identifier ≤ 63 chars
    _name = 'report.fs_giluat_reports.prob_pdf_nochg'

    @api.model
    def _get_report_values(self, docids, data=None):
        return _probation_confirmation_report_values(self.env, docids, False)


class ReportProbationConfirmedWithChanges(models.AbstractModel):
    _name = 'report.fs_giluat_reports.prob_pdf_wchg'

    @api.model
    def _get_report_values(self, docids, data=None):
        return _probation_confirmation_report_values(self.env, docids, True)
