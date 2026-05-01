# -*- coding: utf-8 -*-

from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_contracts(self, date_from, date_to, states=None, kanban_state=False):
        """Include probation contracts wherever running (open) contracts are requested."""
        if states is None:
            states = ['open', 'probation']
        else:
            states = list(states)
            if 'probation' not in states and 'open' in states:
                states.append('probation')
        return super()._get_contracts(date_from, date_to, states=states, kanban_state=kanban_state)
