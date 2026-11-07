# Running the Mandi review build

The initial local review milestone is implemented. KoBo, survey, archive, and licensing are not connected to live systems. The demo command creates synthetic records and source adapters explicitly identify their records as demonstrations.

## Start locally

Run commands from the repository root. Python 3.12+ and Node 24+ are recommended for this setup.

```bash
python3 -m venv .venv
.venv/bin/pip install -r mandi_backend/requirements.txt
cp mandi_backend/.env.example mandi_backend/.env
```

Choose your database password in `mandi_backend/.env`, then start the local PostgreSQL service:

```bash
docker compose --env-file mandi_backend/.env up -d postgres
.venv/bin/python mandi_backend/manage.py migrate
MANDI_DEMO_PASSWORD='choose-your-local-review-password' .venv/bin/python mandi_backend/manage.py seed_demo
.venv/bin/python mandi_backend/manage.py runserver 127.0.0.1:8001
```

In another terminal:

```bash
npm --prefix mandi_frontend ci
npm --prefix mandi_frontend run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5174 and sign in as `reviewer`, using the password supplied to `seed_demo`. Existing account passwords are not reset when seeding again. The frontend API defaults to http://127.0.0.1:8001/api/v1; override it with `mandi_frontend/.env` if needed. The backend loads its `.env` automatically; process environment variables take precedence.

Optional: omit `POSTGRES_DB` from the backend environment to use SQLite for a quick development review. PostgreSQL is required when `DJANGO_DEBUG=0`. No production deployment has been performed.

## Review walkthrough

1. Check the dashboard: distinguish unique establishments from inspection visits, and approved from unapproved entries.
2. Search establishments, create one, edit its details, and inspect its history.
3. Connect a demonstration survey, archive, or licensing record. Its details appear separately. Correct a connection by disconnecting it and selecting another record.
4. Open an unapproved demonstration inspection, inspect its selected results, and approve it.
5. Filter inspections by dates, type, approval, establishment category, province, inspector, and checklist.
6. Open **Checklists**, add a checklist with an `.xls`/`.xlsx` XLSForm, edit it, and download its file.
7. Check coverage reports; date inputs and stored dates use Gregorian values while the UI can display Shamsi or Qamari.
8. Switch between English, Dari, and Pashto/RTL and try the mobile navigation and dark theme.

## Structure and conventions

- `mandi_backend/apps/core/models.py`: `BaseModel` with `created_at`, `updated_at`, `created_by`, and `updated_by`; `Country`, `Province`, and `District` use it.
- `mandi_backend/apps/*/services.py`: domain operations, authorization, transactions, reporting, and integration orchestration.
- Models: persistence and database constraints. API serializers: input/output shape. API views: thin service calls.
- `mandi_backend/config/api.py`: initial REST endpoints and serializers.
- `mandi_frontend/src/features/*`: Mandi screens organized like the CMS features. Pages use the copied CMS `PageSection`, `AppTitle`, `AppTable`, `AppPagination`, `AppFilterPanel`, `AppErrorState`, `AppLoader`, `AppDialog`, form components, and calendar controls.
- `mandi_frontend`: copied CMS build configuration, theme, fonts, dashboard layout/sidebar/header, shared UI/public component set, and supporting shared components, with Mandi screens and API/session adaptation.
- Establishment, source-link, and inspection records are read-only in Django admin so changes cannot bypass services. Checklist add/edit (including XLSForm upload) and inspection add are available as service-backed admin forms; inspection approval remains in the application. `apps/core` provides countries, provinces, districts, and shared abstract model helpers. Account/group administration uses Django's built-in administration. Open `/admin/` on the backend port (`8001`) with a staff/superuser account; create one with `createsuperuser` if needed.
- New employees can be assigned predefined groups in their creation form by an authorized administrator. They are not automatically granted reviewer privileges.

## API contract

The authenticated `GET /api/v1/schema/` endpoint returns an OpenAPI 3 contract generated from the input/output serializers plus endpoint metadata. Lists accept `page` and `page_size` (maximum 100); the copied CMS pagination controls send the selected size. API tokens are sent as `Authorization: Token <token>`. Tokens are held in browser session storage for this local review; production authentication and deployment hardening remain later work.

## Permissions and calendars

See [permissions-and-calendars.md](permissions-and-calendars.md) for migration-installed groups, Can guards, copied form components, and calendar conversion.

## KoBo checklist deployment

The local `kobo-install` stack is expected to be running with nginx on port `80`.
In this environment `kf.kobo.local` resolves through a Host header rather than
DNS, so the backend uses:

```bash
KOBO_BASE_URL=http://127.0.0.1
KOBO_HOST_HEADER=kf.kobo.local
KOBO_API_TOKEN=<token>
KOBO_VERIFY_TLS=0
```

The token belongs to the KoBo superuser. The backend imports the checklist
XLSForm through `/api/v2/imports/`, waits for the import task, then creates or
redeploys the asset through `/api/v2/assets/{uid}/deployment/`.

- `POST /api/v1/checklists/{id}/deploy/` requires
  `inspections.deploy_checklist`.
- Mandi administrators and integration operators receive that permission.
- The checklist stores the KoBo asset UID, deployment status, error message,
  deployer, and deployment time.
- A failed KoBo import or deployment returns the KoBo error in the checklist row
  and shows a failure message in the UI.
- Upload or replace the XLSForm before deploying. Re-deploying updates the
  existing KoBo asset when it still exists.

Restart the backend after changing KoBo environment variables.

## Integration boundary

`GET /api/v1/integrations/establishment-choices/?kind=pharmacy` returns stable Mandi IDs as choice names and readable labels. It is an authenticated JSON export, not yet a deployed KoBo preload/pull integration.

`POST /api/v1/integrations/ingest/` accepts normalized inspection summaries. It requires the inspection-add permission. Provider adapters and actual KoBo field mappings are not implemented yet. The input's mapping version records which mapping produced a result; it does not perform mapping itself.

Submission identity is `(provider, provider_form_id, submission_id)`. An unchanged retry preserves the record and approval. A changed submission updates the existing record, resets approval, and creates an audit entry. This is a conservative provisional rule for review, not a finalized rejection/revision workflow.

Selected summaries currently support overall percentage, named sections with earned/possible scores, and findings with actions/deadlines. Full answers, attachments, sample/quarantine annexes, and laboratory workflows are deferred to actual checklist conversion. No score is automatically derived from unresolved paper-checklist rules.

Source links currently allow one external record per source per establishment, and prevent the same source record from being connected to two Mandi establishments. Review this assumption if source systems represent branches or duplicates differently.

Disable demo source lookup with `DEMO_INTEGRATIONS=0`. Live adapters then report unavailable rather than returning pretend live data.

## Checks

```bash
.venv/bin/python mandi_backend/manage.py check
.venv/bin/python mandi_backend/manage.py makemigrations --check --dry-run
.venv/bin/python mandi_backend/manage.py test tests
npm --prefix mandi_frontend run build
npm --prefix mandi_frontend run lint
npm --prefix mandi_frontend run format:check
```

Tests create and destroy a separate test database. The local PostgreSQL development user can create it. Initial verification includes PostgreSQL service and API tests and browser checks; deployment hardening, backup/restore, actual checklist scoring, live sync, and real data migration remain later work.

## Stop local services

Stop the two development servers with Ctrl-C. To stop PostgreSQL while preserving its data:

```bash
docker compose --env-file mandi_backend/.env stop postgres
```

## Verification recorded on 2026-11-07

- 18 backend workflow/API tests passed against PostgreSQL.
- Django system checks and migration consistency checks passed.
- Frontend production build, lint, and formatting checks passed.
- Browser checks verified establishment creation/editing, demonstration source search/linking, inspection approval, inspection filters, coverage reporting, and English/Dari/Pashto RTL, desktop/mobile, and dark layouts. Browser-created synthetic review records remain available for inspection.

## CMS layout and Pashto follow-up

The custom shell has been replaced with the actual AFDA CMS DashboardLayout, sidebar/header, user dropdown, and theme/language controls. Tables, dialogs, selects, labels, pagination, badges, textareas, and page sections use copied CMS components. The CMS theme replaces the original Mandi theme overrides. Pashto translations cover every Mandi-specific Dari key; shared controls use the CMS Pashto translations. See `mandi_frontend/README.md` for provenance and adaptations.

Copied shared components retain lint warnings present in their implementation (component exports, effect state updates, and a skeleton's random width); no lint errors are introduced.

The follow-up adds the copied CMS calendar selector and custom form wrappers, predefined groups through migrations, and Can guards. Current verification: 24 backend tests and three frontend permission/calendar tests pass.
