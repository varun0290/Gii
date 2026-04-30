from . import models


def post_init_hook(cr, registry):
    """Backfill resigned/fired flags for employees archived via departure reason only."""
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['hr.employee']._bootstrap_resign_flags_from_departure_reason()
