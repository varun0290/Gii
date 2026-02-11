
import logging
import pytz

from collections import defaultdict
from datetime import date, datetime, time

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date, frozendict
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    is_sick_leave = fields.Boolean(string="Supporting Document Mandatory")
    hide_carry_forward_on_dashboard = fields.Boolean(string="Hide Carry Forward on Dashboard")

    def get_allocation_data(self, employees, target_date=None):
        allocation_data = defaultdict(list)
        if target_date and isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date).date()
        elif target_date and isinstance(target_date, datetime):
            target_date = target_date.date()
        elif not target_date:
            target_date = fields.Date.today()

        allocations_leaves_consumed, extra_data = employees.with_context(
            ignored_leave_ids=self.env.context.get('ignored_leave_ids')
        )._get_consumed_leaves(self, target_date)
        leave_type_requires_allocation = self.filtered(lambda lt: lt.requires_allocation == 'yes')

        for employee in employees:
            for leave_type in leave_type_requires_allocation:
                if len(allocations_leaves_consumed[employee][leave_type]) == 0:
                    continue
                lt_info = (
                    leave_type.name,
                    {
                        'remaining_leaves': 0,
                        'virtual_remaining_leaves': 0,
                        'max_leaves': 0,
                        'accrual_bonus': 0,
                        'leaves_taken': 0,
                        'virtual_leaves_taken': 0,
                        'leaves_requested': 0,
                        'leaves_approved': 0,
                        'closest_allocation_remaining': 0,
                        'closest_allocation_expire': False,
                        'holds_changes': False,
                        'total_virtual_excess': 0,
                        'virtual_excess_data': {},
                        'exceeding_duration': extra_data[employee][leave_type]['exceeding_duration'],
                        'request_unit': leave_type.request_unit,
                        'icon': leave_type.sudo().icon_id.url,
                        'allows_negative': leave_type.allows_negative,
                        'max_allowed_negative': leave_type.max_allowed_negative,
                    },
                    leave_type.requires_allocation,
                    leave_type.id)
                for excess_date, excess_days in extra_data[employee][leave_type]['excess_days'].items():
                    amount = excess_days['amount']
                    lt_info[1]['virtual_excess_data'].update({
                        excess_date.strftime('%Y-%m-%d'): excess_days
                    }),
                    lt_info[1]['total_virtual_excess'] += amount
                    if not leave_type.allows_negative:
                        continue
                    lt_info[1]['virtual_leaves_taken'] += amount
                    lt_info[1]['virtual_remaining_leaves'] -= amount
                    if excess_days['is_virtual']:
                        lt_info[1]['leaves_requested'] += amount
                    else:
                        lt_info[1]['leaves_approved'] += amount
                        lt_info[1]['leaves_taken'] += amount
                        lt_info[1]['remaining_leaves'] -= amount
                allocations_now = self.env['hr.leave.allocation']
                allocations_date = self.env['hr.leave.allocation']
                allocations_with_remaining_leaves = self.env['hr.leave.allocation']
                for allocation, data in allocations_leaves_consumed[employee][leave_type].items():
                    # We only need the allocation that are valid at the given date
                    if allocation and allocation.is_carry_forward and leave_type.hide_carry_forward_on_dashboard:
                        continue
                    if allocation:
                        today = fields.Date.today()
                        if allocation.date_from <= today and (not allocation.date_to or allocation.date_to >= today):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_now |= allocation
                        if allocation.date_from <= target_date and (not allocation.date_to or allocation.date_to >= target_date):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_date |= allocation
                        if allocation.date_from > target_date:
                            continue
                        if allocation.date_to and allocation.date_to < target_date:
                            continue
                    lt_info[1]['remaining_leaves'] += data['remaining_leaves']
                    lt_info[1]['virtual_remaining_leaves'] += data['virtual_remaining_leaves']
                    lt_info[1]['max_leaves'] += data['max_leaves']
                    lt_info[1]['accrual_bonus'] += data['accrual_bonus']
                    lt_info[1]['leaves_taken'] += data['leaves_taken']
                    lt_info[1]['virtual_leaves_taken'] += data['virtual_leaves_taken']
                    lt_info[1]['leaves_requested'] += data['virtual_leaves_taken'] - data['leaves_taken']
                    lt_info[1]['leaves_approved'] += data['leaves_taken']
                    if data['virtual_remaining_leaves'] > 0:
                        allocations_with_remaining_leaves |= allocation
                closest_allocation = allocations_with_remaining_leaves[0] if allocations_with_remaining_leaves else self.env['hr.leave.allocation']
                closest_allocations = allocations_with_remaining_leaves.filtered(lambda a: a.date_to == closest_allocation.date_to)
                closest_allocation_remaining = 0
                for closest_allocation in closest_allocations:
                    closest_allocation_remaining += allocations_leaves_consumed[employee][leave_type][closest_allocation]['virtual_remaining_leaves']
                if closest_allocation.date_to:
                    closest_allocation_expire = format_date(self.env, closest_allocation.date_to)
                    calendar = employee.resource_calendar_id\
                               or employee.company_id.resource_calendar_id
                    # closest_allocation_duration corresponds to the time remaining before the allocation expires
                    closest_allocation_duration =\
                        calendar._attendance_intervals_batch(
                            datetime.combine(closest_allocation.date_to, time.min).replace(tzinfo=pytz.UTC),
                            datetime.combine(target_date, time.max).replace(tzinfo=pytz.UTC))\
                        if leave_type.request_unit in ['hour']\
                        else (closest_allocation.date_to - target_date).days + 1
                else:
                    closest_allocation_expire = False
                    closest_allocation_duration = False
                # the allocations are assumed to be different from today's allocations if there is any
                # accrual days granted or if there is any difference between allocations now and on the selected date
                holds_changes = (lt_info[1]['accrual_bonus'] > 0
                    or bool(allocations_date - allocations_now)
                    or bool(allocations_now - allocations_date))\
                    and target_date != fields.Date.today()
                lt_info[1].update({
                    'closest_allocation_remaining': closest_allocation_remaining,
                    'closest_allocation_expire': closest_allocation_expire,
                    'closest_allocation_duration': closest_allocation_duration,
                    'holds_changes': holds_changes,
                })
                if not self.env.context.get('from_dashboard', False) or lt_info[1]['max_leaves']:
                    allocation_data[employee].append(lt_info)
        for employee in allocation_data:
            for leave_type_data in allocation_data[employee]:
                for key, value in leave_type_data[1].items():
                    if isinstance(value, float):
                        leave_type_data[1][key] = round(value, 2)
        return allocation_data