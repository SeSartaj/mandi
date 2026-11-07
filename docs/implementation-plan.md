# Mandi implementation plan

Status on 2026-11-07: the initial backend/frontend review milestone is implemented and running locally. See [development.md](development.md) for startup, verification, provisional rules, and integration limitations. The next step is user review and corrections; live integrations and actual checklist conversion remain deferred.

The frontend was re-checked against the requirement to reuse the AFDA CMS foundation. Screens were moved out of the former monolithic page file into CMS-style feature folders and now use the copied table, pagination, filter, dialog, error, loader, form, and calendar components. The audit and remaining deferrals are recorded in [implementation-review.md](implementation-review.md).

Build the Django backend first, then add a frontend based on `/home/foodev/afdacms/frontend`. Deliver a working local system for review, incorporate corrections, and then proceed with live integrations and checklist conversion.

This document is a plan, not an implementation. The README contains the agreed product direction; [checklist-review-findings.txt](checklist-review-findings.txt) records document observations and recommendations. Recommendations in that review remain proposals unless explicitly included here as provisional implementation choices.

## 1. Set up mandi_backend

### Project foundation

- Create `mandi_backend/` with Django, Django REST Framework, and PostgreSQL.
- Set up environment-based configuration, local development settings, an environment example, dependency management, migrations, and development commands.
- Configure authentication, API permissions, pagination, filtering, consistent errors, CORS, logging, and API schema documentation.
- Start with a custom user model and minimal employee records; avoid implementing the full government organization hierarchy before its access requirements are settled.
- Provide Django admin for supporting administration. Domain-changing admin actions must call services too.
- Provide a repeatable development setup and a command to load clearly identified demonstration data. Keep credentials out of source control.

### Put all business logic in services

Organize each domain app around models, services, and an API layer:

```text
mandi_backend/
  config/
  apps/
    accounts/
    establishments/
    inspections/
    reporting/
    integrations/
  tests/
```

- Models define persistence, relationships, and database constraints.
- Services own business validation, authorization rules, transactions, state changes, reporting calculations, and orchestration of integrations.
- Serializers parse and validate input shape and serialize output; views authenticate requests and delegate to services.
- Commands, admin actions, and later background jobs use the same services. Do not hide business workflows in signals, model `save()` overrides, or frontend code.
- External clients handle transport and response parsing; integration services decide how external data affects Mandi.
- Service operations accept the acting user where relevant and enforce permissions so alternate entry points cannot bypass them.
- Add focused tests for meaningful rules, permissions, transitions, reporting, and integration behavior.

### Establishment registry

- Create establishments with stable IDs, names, types, optional subtypes/product categories, location, and contact details.
- Initially support pharmacies, wholesalers, importers, and factories; allow pharmacy subtypes such as hospital pharmacy. Detailed food establishment requirements remain open.
- Provide searchable, paginated list/detail/create/update APIs.
- Represent links to survey, archive, and licensing records using source system and external record ID.
- Linking is an explicit employee action. Show external details under their source, preserving conflicting values rather than automatically merging them into the Mandi record.
- Record who created or changed a link. Provide a controlled correction/unlink operation.
- Introduce a source-adapter interface and demonstration adapters for the review build. Actual source endpoints and authentication are still unknown.

### Inspection records

- Store establishment, inspection date, inspection type, checklist/version, inspection team, data-collection provider, and provider submission reference.
- Support comprehensive, brief, follow-up, and special inspection types, with applicability varying by checklist.
- Separate inspection type from approval status. Show both approved and unapproved entries as inspections, with an explicit distinction in reporting.
- For the review build, use a minimal approval action restricted by a Django permission; record approver and time. Final approval roles, rejection, and revision policies remain for later decisions.
- Store selected results using a versioned mapping: section scores, earned/possible scores where available, overall result, and selected findings. Do not require a single universal scoring formula across all forms.
- Retain a reference to detailed collection data; KoBo remains the main home for full responses and annexes.
- Preserve original calendar information where necessary and distinguish the inspection date from submission/synchronization timestamps.
- Record history for approval and other material changes. Review-build entries are demonstration records, not a new production manual-entry workflow.

### Reporting services

- Report inspected and uninspected establishments for a selected period, inspection history, inspection team, and approved/unapproved counts.
- Count distinct establishments separately from inspection visits to avoid double-counting coverage.
- Provide filters for establishment type, location, inspection type, checklist, inspector, date range, and approval status.
- Report comprehensive visits separately from other visits and display approval breakdowns without inventing a final credit policy.
- Keep score comparisons tied to compatible checklists and versions.

### Integration foundation

- Define a provider boundary so inspection results are not permanently coupled to KoBo.
- Define a form-specific establishment-choice export containing stable Mandi IDs and readable labels. Exact pull/preload delivery will be selected during KoBo integration.
- Define configurable mapping from provider fields to Mandi summary fields. Mandi decides what to retrieve for each form.
- Design ingestion to identify submissions by provider, form, and submission ID, making retries safe and detecting updates without duplicating inspections.
- Use fixtures to demonstrate ingestion and external record linking. Missing live credentials must not prevent local review.
- Defer live synchronization schedules and job infrastructure until an actual integration requires them.

### Backend completion checks

- A fresh local database can migrate and load demonstration data using documented commands.
- API schema describes the endpoints the frontend will use.
- Tests cover service authorization, manual source links, approval, repeat ingestion, and coverage calculations.
- Reports distinguish approved/unapproved entries and visits/establishments correctly.
- Authentication and protected endpoints work without relying on frontend checks.

## 2. Copy the frontend setup from ~/afdacms and add mandi_frontend

### Reuse the existing foundation

Create `mandi_frontend/` using the inspected CMS frontend as the starting point:

- React, TypeScript, Vite, Tailwind, reusable UI components, icons, and styling.
- Layout/sidebar, routing conventions, themes, and responsive behavior.
- React Query, Axios/error handling, forms, and relevant state utilities.
- Localization, right-to-left presentation, fonts, and appropriate date utilities.
- Build, lint, formatting, and relevant test configuration.

Copy configuration and reusable components with their required assets and dependencies, then prune unused packages and features. Do not copy `node_modules`, build output, real environment files, tokens, customer data, or CMS business modules. Leave the source project unchanged.

Adapt authentication to Mandi's API contract. In particular, the CMS API client uses an active-position header (`X-Active-Bast`) and CMS account state; remove or replace those dependencies rather than requiring Mandi to reproduce them. Use Mandi branding, environment variables, and a development port that can coexist with the CMS.

### Build the review screens

1. Login and authenticated application layout.
2. Dashboard showing inspection coverage and approved/unapproved counts.
3. Establishment list with search, filters, and create/edit forms.
4. Establishment detail with its Mandi details and inspection history.
5. Separate survey, archive, and licensing panels. Unlinked panels offer search/select/connect; demonstration sources are visibly identified.
6. Inspection list and detail with checklist/version, inspection type, team, selected results, provider reference, and approval state/action.
7. Basic employee administration needed to associate inspectors with visits.
8. Coverage report with clear period, inspection-type, and approval filters.

Connect screens to the real local backend and seeded demonstration records. Include loading, empty, validation, permission, and integration-unavailable states. Keep business calculations and permission decisions in backend services.

### Frontend completion checks

- Build, lint, and appropriate focused interaction checks pass.
- Verify login, establishment creation/editing, source linking, inspection review/approval, and reporting in the browser.
- Verify Dari/RTL layout, tables, forms, date presentation, and mobile-width navigation.
- Check that unauthorized actions are rejected by the API and that the UI responds correctly.
- Confirm no CMS navigation, branding, account assumptions, or external connections remain unintentionally.

## 3. Deliver the system for review and corrections

- Document exact commands to run both applications, prepare the database, and seed sample records.
- Supply demonstration cases: an establishment with no inspections, one with an unapproved inspection, one with an approved inspection, repeated visits, and linked/unlinked external sources.
- Clearly identify fixture-backed integrations and any incomplete production behavior.
- Review the complete flow: create establishment, connect an external record, inspect its history/results, approve an entry, and observe report changes.
- Let the user review terminology, fields, screens, workflows, and reporting behavior. Record requested corrections and apply them before expanding scope.

This is the stopping point for the initial implementation milestone. The next phase starts after the user's review and corrections, as requested.

## 4. Move forward after review

- Resolve authoritative checklist versions and scoring ambiguities with the user.
- Prepare one question-by-question KoBo conversion specification, then implement and validate that form.
- Validate establishment choice selection using stable IDs with the actual KoBo form and chosen pull/preload method.
- Connect actual KoBo submissions using an agreed field mapping and test repeat imports, updates, unmapped establishments, and failures.
- Implement survey/archive/licensing adapters as their access details become available.
- Convert the remaining checklists incrementally.
- Decide final approval/rejection rules, evidence requirements, and historical imports separately.
- Plan production deployment, backup/restore verification, and operational monitoring once the reviewed workflows and live integrations are ready.

Automatic establishment matching, inspection recommendations, team planning, full laboratory/enforcement workflows, and mandatory evidence policies are outside the first milestone.
