from . import models


def post_init_hook(env):
    """Backfill resigned/fired flags for employees archived via departure reason only."""
    env['hr.employee']._bootstrap_resign_flags_from_departure_reason()
