# Fidobe HR stack — module workflows (single reference)

This document summarises how the main HR-related custom modules fit together and how typical processes flow. You can copy the whole file into Google Docs; headings and lists will paste cleanly.

---

## 1. Purpose of this document

- Give **one place** to understand **what each module does** and **how work moves** between Employee master data, contracts, probation, time off, payroll, documents, and costs.
- Explain **HR Team Manager** access: who sees **only their team** versus **full HR / payroll** roles.
- List **enterprise / regional addons** pulled in by the umbrella **Fidobe HR** application.

---

## 2. Big picture: how modules relate

**Umbrella application**

- **fs_hr (Fidobe HR)** is the Odoo “application” module that installs a bundle: core HR, payroll, Saudi GOSI, UAE WPS, employee updation, gratuity settlement, and **HR Team Manager** security (`fs_hr_team_manager`).

**Custom Fidobe HR addons (typical flow)**

1. **fs_hr_contract** — Contract fields, salary setup (UAE payroll linkage), and security groups such as **Head of HR** and **Contract Finance Approver**.
2. **fs_hr_probation** — Probation lifecycle on contracts (reviews, cron reminders, wizard, transition to running/open).
3. **fs_hr_leave** — Time-off UX/rules extensions (e.g. sick leave attachment logic, approval reminder cron).
4. **fs_payroll_dynamic_approval** — Payroll **batch** workflow (submit → Head of HR → Finance → validate), plus cut-off and contract preview behaviour tied to **fs_hr_contract** / **fs_base**.
5. **fs_hr_document_management** — Document templates, deployments to employees, e-sign flow and audit, portal hooks.
6. **fs_hr_employee_cost** — Employee-level costs and contributions, cost centres, approvals, dashboards linked to employees.

**Security / access**

- **fs_hr_team_manager** — Dedicated group **HR Team Manager**: **read-only** HR/payroll-related data **scoped to the user’s employee record and their reporting hierarchy** (manager chain / subordinates). Must **not** be combined with full **HR Officer** (`Manage all employees`) or users effectively see everyone again.

Dependencies between these addons are defined in each module’s `__manifest__.py`; **fs_hr_team_manager** explicitly depends on **hr**, **hr_contract**, **hr_holidays**, **hr_payroll**, **hr_work_entry_contract_enterprise**, **fs_hr_leave**, **fs_hr_contract**, **fs_hr_document_management**, and **fs_hr_employee_cost** so team-scoped rules apply consistently across those areas.

---

## 3. End-to-end workflow (narrative)

Use this as a storyboard for procedures or training.

### 3.1 Employee and organisation setup

- Standard Odoo **Employees** app: create/update employees, departments, jobs, managers (**Manager** field drives hierarchy used by **HR Team Manager** rules).
- **fs_hr** view extensions may surface regional fields (e.g. UAE labour/salary card, gratuity UI) via bundled enterprise/customisations.

### 3.2 Contract lifecycle

- User creates or updates **contracts** (`hr.contract`). **fs_hr_contract** adds behaviour for UAE payroll linkage, salary rule linkage, and groups (**Head of HR**, **Contract Finance Approver**) used downstream.
- **fs_hr_probation**, where enabled on a contract:
  - Contract can move into **Probation** after approval.
  - **Month-based reviews** (e.g. 3rd / 5th month) are driven by **scheduled jobs** and notifications.
  - **Line manager** uses a **probation review wizard**; on successful final review the contract can move to **Running / Open** (running).
  - Email / confirmation letter flows are defined in that module’s data files.

### 3.3 Time off (holidays)

- Employees submit **time off** in standard **Time Off** app (**hr_holidays**).
- **fs_hr_leave** adds logic such as:
  - **Sick leave**: attachment may be **required** when duration exceeds a threshold on configured leave types.
  - **Approval reminders**: a **cron** can email approvers for requests still pending when the start date is within a short horizon (e.g. next 7 days), with throttling (at most once per day per request).

### 3.4 Payroll batches and approvals

- Payroll runs as **payslip batches** (`hr.payslip.run`) in the Payroll app (Enterprise payroll + work entries).
- **fs_payroll_dynamic_approval** adds:
  - **Submit for approval**, **HR approve**, **Finance approve**, **Reject**, aligned with **Head of HR** and **Contract Finance Approver** groups from **fs_hr_contract**.
  - **Restricts validating** a batch until approvals are complete (per module views/logic).
  - **Cut-off / booking** concepts and **contract previews** (salary payment month, booking month, EOS accrual start, etc.) via settings and contract/payslip extensions.
  - **Locks** certain eligibility fields after payroll is processed where configured.

### 3.5 Documents and acknowledgements

- **fs_hr_document_management**:
  - **Templates** (offer, contract, AML, NDA, policies) with company-specific legal/stamp/signatory setup.
  - **Deployments** targeting all staff or filters (department, location, job, manual selection).
  - **Per-employee lines**: generated PDFs, portal access tokens, states (sent / viewed / signed), reminders for pending signatures.
  - **Signed documents** stored on the employee record for audit.

### 3.6 Employee costs and contributions

- **fs_hr_employee_cost**:
  - HR enters **employee costs** (hiring, renewal, cancellation, medical, etc.) with amount, department, **cost centre**, attachments.
  - **Approvals** follow standard Odoo approval patterns configured on that model.
  - **Contributions** track employer/employee shares linked to employees.
  - **Pivot/graph** views support cost-to-hire style reporting.

---

## 4. Per-module quick reference

| Module | Role in the workflow |
|--------|----------------------|
| **fs_hr** | Installs the **Fidobe HR** application bundle and shared HR UI tweaks; ensures **fs_hr_team_manager** is part of the stack. |
| **fs_hr_team_manager** | **HR Team Manager** group: read-only access filtered to **self + subordinates** on employees, contracts, time off, allocations, payslips/lines/batches (where applicable), document lines/signed docs, employee costs/contributions; extends menus so managers can open those apps without full HR Officer rights. |
| **fs_hr_contract** | Contract customisations, UAE payroll integration point, salary rule data, **Head of HR** / **Finance approver** groups used by payroll approval. |
| **fs_hr_probation** | Probation state, scheduled reviews, manager wizard, emails/letters, transition to running contract. |
| **fs_hr_leave** | Sick-leave attachment rule, time-off **approval reminder** cron for pending requests nearing start date. |
| **fs_payroll_dynamic_approval** | Payroll batch **HR + Finance** approval gates, cut-offs, contract/payslip locking and previews. |
| **fs_hr_document_management** | Templates, deployments, e-sign tracking, employee-linked signed documents. |
| **fs_hr_employee_cost** | Employee costs, contributions, cost centres, dashboards and approvals. |

---

## 5. HR Team Manager — operational checklist

**Goal:** Managers see HR/payroll-related information **only for their team** (themselves plus everyone below them in the employee hierarchy).

**Steps for administrators**

1. Install or upgrade **fs_hr_team_manager** (or upgrade **fs_hr**, which depends on it).
2. For each team manager user:
   - Assign security group **HR Team Manager**.
   - **Remove** **Officer: Manage all employees** if they must not see company-wide HR data.
3. On each user record, set **Related Employee** / HR employee link so `user.employee_id` is correct.
4. Maintain **Manager** on employee forms so the hierarchy (`parent_path`) is accurate.

**Important limits (for documentation / training)**

- Team filtering relies on **employee-linked users** and **reporting hierarchy**. Requests without a normal employee linkage (e.g. some company-wide time-off types) may not match the same filters.
- Document **deployment headers** may remain broadly visible to internal users due to existing access on that model; **lines** and **signed employee documents** are scoped for team managers in **fs_hr_team_manager**.
- Payroll technical models must exist as in standard Enterprise **hr_payroll**; if your database uses different model definitions, access/rule XML IDs may need alignment.

---

## 6. Regional / enterprise modules bundled by fs_hr (reference only)

These are referenced by **fs_hr** so they install together; detailed workflows follow each vendor’s documentation plus any local customisations in your database:

- **ent_saudi_gosi** — Saudi GOSI-related HR/payroll extensions.
- **ent_uae_wps_report** — UAE WPS reporting / employee identifiers as exposed in UI.
- **ent_hr_employee_updation** — Employee master data extensions (identification, passport, etc.).
- **ent_hr_gratuity_settlement** — End-of-service gratuity configuration and settlement flows.

---

## 7. Suggested Google Docs cleanup after paste

- Apply your organisation’s **Heading 1 / Heading 2** styles to the numbered sections.
- Replace this line with your **document title, version, and owner**.
- Add screenshots of Odoo menus (**Employees**, **Time Off**, **Payroll**, **Document Management**, **Employee Costs**) next to section 3 if needed.

---

## 8. Deployment reality for GII

### 8.1 Code layers on the server

The GII environments are not driven by a single addons repository. The effective runtime stack is layered:

- **Odoo Community core** from `/home/odoo/src/odoo`
- **Enterprise** addons from `/home/odoo/src/enterprise`
- **Themes** from `/home/odoo/src/themes`
- **Project / customer addons** from `/home/odoo/src/user`

For the branch environments checked during this investigation, the runtime addons path logged by Odoo was:

- `/home/odoo/src/odoo/odoo/addons`
- `/home/odoo/.local/share/Odoo/addons/17.0`
- `/home/odoo/src/user`
- `/home/odoo/src/odoo/addons`
- `/home/odoo/src/enterprise`
- `/home/odoo/src/themes`
- `/home/odoo/data/addons/17.0`

### 8.2 Repo split: GII vs OpenHR

The **GII** repo (`varun0290/Gii`, mirrored from `giluat.livbuzz.com`) contains the Fidobe/project layer, especially the `fs_*` modules and selected HR / payroll custom modules.

However, the restored databases also expect a second code source:

- **ent_openhr** (Bitbucket)

That separate OpenHR/vendor repo is the source of base modules such as:

- `ent_hr_employee_updation`
- `ent_hr_reward_warning`
- `ent_hr_resignation`
- `ent_hrms_dashboard`

This means:

- **`fs_*` modules are not replacements for the matching `ent_*` modules**
- several `fs_*` modules are **custom layers on top of** missing vendor/base modules

### 8.3 Important example: resignation flow

`fs_ent_hr_resignation` exists in GII, but it depends on:

- `hr`
- `ent_hr_resignation`

So the database can only load resignation features correctly if **both** are present:

1. `ent_hr_resignation` provides the base `hr.resignation` model
2. `fs_ent_hr_resignation` applies Fidobe-specific extensions on top of that base

### 8.4 Important example: dashboard flow

The `hr_dashboard` client action belongs to:

- `ent_hrms_dashboard`

If that module is missing from the runtime addons path, the frontend fails with:

- `KeyNotFoundError: Cannot find hr_dashboard in this registry!`

---

## 9. Live vs UAT side-by-side findings

### 9.1 Database restore targets used

**Live**

- Host: `32132822@varun0290-gii.odoo.com`
- Database: `varun0290-gii-main-32132822`
- Dump restored: `gil_prod_2026-05-13_05-14-39.dump`

**UAT**

- Host: `32135406@varun0290-gii-uat2-32135406.dev.odoo.com`
- Database: `varun0290-gii-uat2-32135406`
- Dump restored: `gil_uat2_2026-05-13_06-46-47.dump`

### 9.2 Shared problem observed after restore

Both environments initially showed the same functional breakage:

- Python-side missing model: `hr.resignation`
- Frontend missing client action registry key: `hr_dashboard`

The reason was the same on both databases:

- the databases had OpenHR modules marked **installed**
- the branch code deployed in `/home/odoo/src/user` only contained the GII repo
- the required OpenHR/vendor module folders were not present on disk

### 9.3 Concrete UAT remediation applied

UAT was used as the first proving ground.

The following missing OpenHR module folders were added to `/home/odoo/src/user` on UAT:

- `ent_hr_employee_updation`
- `ent_hr_reward_warning`
- `ent_hr_resignation`
- `ent_hrms_dashboard`

After that, a targeted module update was run on UAT for:

- `ent_hr_employee_updation`
- `ent_hr_reward_warning`
- `ent_hr_resignation`
- `ent_hrms_dashboard`

### 9.4 Signs the UAT fix succeeded

After the UAT code upload and module update:

- the server log showed `ent_hrms_dashboard` loading successfully
- `hr.resignation` model fields were loaded
- the static dashboard icon route began returning **HTTP 200**
- the original missing-module problem was no longer the active blocker on UAT

### 9.5 Remaining caution

The OpenHR family has more modules than the four listed above. The log still referenced additional missing OpenHR modules such as:

- `ent_hrms_core`
- `ent_hr_reminder`
- `ent_hr_leave_request_aliasing`
- `ent_employee_documents_expiry`
- `ent_ohrms_loan`
- `ent_ohrms_salary_advance`

Those are **not the same issue** as the original `hr_dashboard` / `hr.resignation` failure, but they should be evaluated before any broad production rollout.

---

## 10. Recommended rollout order

1. **Fix and validate on UAT first**.
2. Re-test the exact HR dashboard and resignation flows that were failing.
3. Compare UAT and live installed modules to identify any further OpenHR/vendor gaps.
4. Only after UAT is stable, decide whether to:
   - bring the same missing OpenHR modules into live, or
   - rationalise `fs_*` and `ent_*` usage more broadly.

---

*Generated as a single-source overview for the Fidobe HR custom modules and HR Team Manager behaviour. Update this file when you add or change modules.*
