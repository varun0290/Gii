# fs_hr_team_manager

## Purpose

Adds an **HR Team Manager** security group so managers can **view** HR data only for **their own employee record and their reporting hierarchy** (subordinates via `hr.employee` manager chain / `parent_path`).

Access is **read-only** for the covered models. Users with this group must **not** also have **Officer: Manage all employees** (`hr.group_hr_user`), or they will see company-wide data again.

## What this module provides

| Area | Details |
|------|---------|
| Group | `group_fs_hr_team_manager` — category: Human Resources / Employees |
| Record rules | Filter employees, contracts, contract history, time off, allocations, payslips (and related lines/batches/inputs/worked days), document deployment lines, signed employee documents, employee costs, contributions |
| Access rights | Read-only ACLs on the above models plus supporting reads (departments, jobs, calendars, document templates/versions/deployments, cost centres) |
| Menus | Extends HR Employees payroll section, Contracts, Time Off management/reporting, and Payroll root so team managers can reach those apps |

## Dependencies

`hr`, `hr_contract`, `hr_holidays`, `hr_payroll`, `hr_work_entry_contract_enterprise`, `fs_hr_leave`, `fs_hr_contract`, `fs_hr_document_management`, `fs_hr_employee_cost`

## Setup

1. Upgrade/install the module after deploying code.
2. Assign **HR Team Manager** to users who should see only their team.
3. Remove **Officer: Manage all employees** from those users if present.
4. Ensure each user has **Employee** linked (**Preferences / HR Settings**).

## Files

- `security/fs_hr_team_manager_groups.xml` — group definition  
- `security/ir.model.access.csv` — model access  
- `security/fs_hr_team_manager_rules.xml` — `ir.rule` domains  
- `views/fs_hr_team_manager_menus.xml` — menu `groups_id` extensions  

## Caveats

- Team scope uses `user.employee_id` and `child_of` on `hr.employee`; leaves without `employee_id` (e.g. some company/department requests) are not covered by the same rule shape.
- Deployment **headers** (`hr.document.deployment`) follow existing broad internal-user access from `fs_hr_document_management`; lines and signed documents are team-filtered here.
- Payroll model XML IDs assume standard Enterprise `hr_payroll`; adjust CSV/rules if your build differs.
