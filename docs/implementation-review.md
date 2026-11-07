# Implementation review against the Mandi requirements

Review date: 2026-11-07

This review checks the work that was left in the workspace against the agreed
requirements and records the corrections made before continuing.

## Requirement check

| Requirement | Status |
| --- | --- |
| Set up `mandi_backend` first | Met. Django/DRF backend, authentication, PostgreSQL/SQLite development setup, migrations, and API schema are present. |
| Keep business logic in services | Met after correction. Establishment, inspection, account, integration, and reporting rules live in `apps/*/services.py`. Checklist and audit-event reads were moved out of `config/api.py`. |
| Copy the frontend foundation from `/home/foodev/afdacms/frontend` | Met after correction. The dashboard layout, header, sidebar, theme, fonts, UI primitives, form components, calendar controls, language store, and shared table/pagination/select components come from the CMS. |
| Use the copied CMS UI components instead of new ones | Met after correction. Pages use `PageSection`, `AppTable`, `AppPagination`, `AppFilterPanel`, `AppErrorState`, `AppLoader`, `AppDialog`, `AppTitle`, and the copied form wrappers. The former monolithic `App.tsx` page code was removed. |
| Add Pashto | Met. Pashto is in the language menu, RTL is applied, Vazirmatn is used, and Mandi keys have Pashto values. Missing filter/registry labels were added during this review. |
| Use `Can` for permissions | Met. Routes, navigation, add/edit actions, approvals, and group assignment are guarded. API services remain authoritative. |
| Predefined groups through migrations | Met. `accounts.0002_predefined_groups` installs the six Mandi groups with explicit permissions. |
| Copy the calendar selector and support Qamari, Shamsi, and Gregorian | Met. The CMS calendar selector and date controls are used. Stored and submitted dates remain Gregorian; the backend has no alternate-calendar columns. |
| Copy and use all form components | Met. The CMS custom form components are copied and used by login, establishment, employee, and inspection-filter forms. |
| Backend stores Gregorian dates only | Met. Inspection dates, deadlines, timestamps, and filters are Gregorian. |

## Drift found and corrected

1. **Hand-built page layer.** The previous frontend had the CMS shell but its
   screens were written as a single large `App.tsx` with custom heading, table,
   pagination, error, empty, and modal helpers. This did not follow the request
   to use the CMS components.
   - Pages are now split into `features/auth`, `dashboard`, `establishments`,
     `inspections`, `employees`, and `reports`.
   - Their headings, tables, pagination, filters, errors, loaders, and dialogs
     use the copied CMS components.

2. **Incomplete shared component set.** Several CMS public components were not
   copied (`AppErrorState`, `AppTitle`, `AppFilterPanel`, `AppDialog`,
   `AppBreadcrumb`) and `useDebouncedValue` was missing.
   - They were copied from the CMS and are now used by the Mandi pages.

3. **Pagination contract was only cosmetic.** The CMS pagination offers page-size
   choices, while the backend always returned 25 rows.
   - The backend now accepts `page_size` up to 100 through the shared
     `MandiPagination` class, and all list pages send and display the selected
     size.

4. **Some read workflows lived in the API layer.** Checklist reads were
   performed directly in `config/api.py`.
   - They now call `inspections.list_checklists`.

5. **Translation gaps.** The new page labels "Filters", "Clear all", "Remove
   filter", "Employee directory", "Inspection records", and related keys were
   missing in one or more languages.
   - They were added in English, Dari, and Pashto.

## Deliberately deferred

These items were outside the review milestone and remain unchanged:

- live KoBo, survey, archive, and licensing connections;
- actual checklist conversion and full-response storage;
- final approval/rejection and scoring-credit policies;
- production deployment and hardening.

## Verification

- Backend: `manage.py check`, migration consistency, and 27 tests pass.
- Frontend: production build and three permission/calendar tests pass.
- Browser: dashboard, establishment registry, establishment detail, source
  linking dialog, inspection filters, coverage, and Pashto RTL were checked
  against the local backend.
