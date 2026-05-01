# -*- coding: utf-8 -*-
"""Helpers for first payroll booking vs first salary payment month (join-day cut-offs)."""
from dateutil.relativedelta import relativedelta


def first_month_start_from_join(join_date, day_cutoff):
    """Return the first day of the calendar month where payroll rule applies.

    If join day is on/before *day_cutoff* → that month (1st).
    If join is after *day_cutoff* → first day of the following month.
    """
    if not join_date:
        return False
    if join_date.day <= int(day_cutoff):
        return join_date.replace(day=1)
    return join_date.replace(day=1) + relativedelta(months=1)


def month_label(d):
    if not d:
        return False
    return d.strftime('%B %Y')


def get_join_cutoff(env):
    ICP = env['ir.config_parameter'].sudo()
    v = ICP.get_param('fs_payroll_dynamic_approval.salary_join_cutoff_day')
    if v is not None and str(v).strip() != '':
        return int(v)
    legacy = ICP.get_param('fs_payroll_dynamic_approval.salary_cutoff_day')
    if legacy is not None and str(legacy).strip() != '':
        return int(legacy)
    return 20


def get_booking_cutoff(env):
    ICP = env['ir.config_parameter'].sudo()
    v = ICP.get_param('fs_payroll_dynamic_approval.payroll_booking_cutoff_day')
    if v is not None and str(v).strip() != '':
        return int(v)
    return 25
