# Mandi frontend

See [development instructions](../docs/development.md) for startup, review flows, and limitations.

The frontend uses components copied from `/home/foodev/afdacms/frontend/src`:

- `components/dashboardLayout`: the CMS DashboardLayout, header, collapsible/mobile sidebar, navigation, AFDA identity, and user dropdown.
- `components/ui`: the complete top-level UI component set, including sidebar, sheet, dialog, table, select, card, badge, input, label, textarea, pagination, dropdown, and tooltip primitives.
- `components/public`: the CMS shared page components, including `AppTable`, `AppPagination`, `AppSelect`, `AppTitle`, `AppFilterPanel`, `AppErrorState`, `AppDialog`, `AppLoader`, and breadcrumb support.
- Supporting CMS PageSection, hooks, fonts, logo, language configuration, theme store, translation wrappers, theme/language controls, and calendar selector.

Mandi screens live in `src/features` (`auth`, `dashboard`, `establishments`,
`inspections`, `checklists`, `employees`, and `reports`). They are composed
from the copied CMS components rather than new page primitives. The Checklists
screen lets administrators upload or replace `.xls`/`.xlsx` XLSForms, download
them, and deploy them to KoBo. The Deploy action is guarded by
`inspections.deploy_checklist` and displays the KoBo deployment status or error. Routes, permissions, user identity, and logout are
bound to those components. Breadcrumb labels and
accessible control labels have been localized. The CMS active-position switcher
and password dialog are omitted because those account APIs do not exist in
Mandi. The header includes the CMS calendar selector, with Gregorian, Shamsi,
and Qamari input/display while API values remain Gregorian.

The original CMS theme is used directly. Mandi CSS only arranges page content; the earlier custom application shell and theme overrides have been removed. Vite/TypeScript and lint/format configurations also come from the CMS. Dependencies are installed independently and locked; no CMS credentials or business records were copied.

The CMS language menu offers Pashto, Dari, and English. Pashto and Dari use RTL layouts and Vazirmatn. Theme selection uses the CMS light/dark/system menu. The selected language persists across reloads.

Source-system and inspection fixture data remain demonstrations. Live integration work follows user review.

The copied `Can` component guards routes, navigation, and actions. All CMS custom form components have been copied, and active forms use their React Hook Form wrappers. See [permissions and calendar notes](../docs/permissions-and-calendars.md) for group definitions, adaptations, and verification.

Run `npm test` for permission/calendar checks.
