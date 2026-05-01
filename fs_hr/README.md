# fs_hr

## Purpose

**Fidobe HR** umbrella application module: bundles core HR, payroll, and regional extensions (see `__manifest__.py` `depends`).

## Change documented here

**HR Team Manager integration**

- Added dependency on **`fs_hr_team_manager`** so installing/upgrading **Fidobe HR** pulls in the team-scoped security group and rules.
- Behaviour and setup for team managers are documented in [`fs_hr_team_manager/README.md`](../fs_hr_team_manager/README.md).

No other files under `fs_hr/` were changed for that feature (only `__manifest__.py`).

## Related addons

Other HR-related custom modules (contracts, leave, probation, payroll approval, etc.) are separate repositories folders in this project; document changes in each module’s own README when you modify them.
