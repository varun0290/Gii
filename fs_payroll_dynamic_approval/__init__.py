# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """Allow existing payroll batches to keep processing (skip new approval gate)."""
    stale = env['hr.payslip.run'].search([
        ('state', 'in', ('verify', 'close', 'paid')),
        ('approval_done', '=', False),
    ])
    if stale:
        stale.write({'approval_done': True})
