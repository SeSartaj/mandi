# Running Mandi locally

The initial local review milestone is implemented. KoBo, survey, archive, and licensing are not connected to live systems. The demo command creates synthetic records and source adapters explicitly identify their records as demonstrations.

## Full local stack (Mandi + ODK Central)

Run commands from the repository root. You need Docker Engine with the Compose plugin, Git, and Python 3 for the setup helper. The same `compose.yml` is used locally and in production; only `.env` changes.

```bash
./scripts/setup.sh      # generates secrets and clones the pinned Central release
./scripts/deploy.sh     # builds, migrates, and starts the whole stack
```

Open:

- Mandi: https://mandi.localhost:8443 — sign in as `MANDI_ADMIN_USERNAME` with `MANDI_ADMIN_PASSWORD` from `.env`.
- Central: https://collect.localhost:8443 — sign in as `ODK_ADMIN_EMAIL` with `ODK_ADMIN_PASSWORD` from `.env`.
- ODK Collect server URL: the credential shown once under **Employees → Manage → ODK Collect access**. The device must resolve `collect.localhost` and trust the local CA.

### Phone on the same LAN

ODK Collect trusts only Android system certificate authorities, so it cannot use
the internal CA. To demo on a phone connected to the same network, configure an
HTTP endpoint for Central:

```dotenv
BIND_ADDRESS=0.0.0.0
ODK_DOMAIN=10.10.6.25
PUBLIC_COLLECTION_URL=http://10.10.6.25:8080
LAN_HTTP_HOST=10.10.6.25
```

Then run `./scripts/setup.sh` and `./scripts/deploy.sh`, and issue a new collector
credential. The URL will start with `http://10.10.6.25:8080/v1/key/...`.
`PUBLIC_COLLECTION_URL` is the base URL Central puts in form lists, manifests, and
attachment links; `LAN_HTTP_HOST` controls the optional plain-HTTP Caddy route.
Leave `LAN_HTTP_HOST` empty in production. HTTP is unencrypted and is only for a
trusted local demonstration network.

`*.localhost` resolves to `127.0.0.1` in current browsers. For command-line verification, trust the generated certificate:

```bash
./scripts/local-ca.sh
curl --cacert deploy/runtime/local-ca.crt https://mandi.localhost:8443/api/health/
```

On Ubuntu, `./scripts/local-ca.sh` also prints the `update-ca-certificates` commands. Firefox may need to import the CA under **Settings → Certificates → Authorities**. Do not use the local CA in production.

Stop the stack without deleting data:

```bash
docker compose stop
```

Reset all local data deliberately (this deletes both databases and uploads):

```bash
docker compose down -v
rm -rf deploy/runtime/central backups/*
```

## Backend-only development with SQLite

For quick backend or frontend iteration without Central, use Python and Vite directly. Python 3.12+ and Node 24+ are recommended.

```bash
python3 -m venv .venv
.venv/bin/pip install -r mandi_backend/requirements.txt
cp mandi_backend/.env.example mandi_backend/.env   # omit POSTGRES_DB for SQLite
.venv/bin/python mandi_backend/manage.py migrate
.venv/bin/python mandi_backend/manage.py seed_locations   # 34 provinces + 401 districts
.venv/bin/python mandi_backend/manage.py createsuperuser
.venv/bin/python mandi_backend/manage.py runserver 127.0.0.1:8000
```

In another terminal:

```bash
npm --prefix mandi_frontend ci
npm --prefix mandi_frontend run dev -- --host 127.0.0.1
```

Open http://127.0.0.1:5174 and sign in with the superuser you created. The frontend API defaults to `/api/v1` on the frontend origin. Vite proxies `/api` and `/media` to Django at `127.0.0.1:8000`, so browsers on other devices do not call their own localhost. Override `VITE_API_URL` in `mandi_frontend/.env` for a separate API host; production hosting must forward `/api` and `/media` to Django. The backend loads its `.env` automatically; process environment variables take precedence.

PostgreSQL is required when `DJANGO_DEBUG=0`. The database-only Compose file used by earlier review builds has been removed; use the full stack above for PostgreSQL and ODK collection.

## Database connection refused

If `runserver` passes system checks but reports `connection refused`, the local
PostgreSQL service is stopped or unavailable. The full stack does not publish
PostgreSQL to the host; start the stack with `./scripts/deploy.sh` and use the
containerized backend, or omit `POSTGRES_DB` from `mandi_backend/.env` to use
SQLite for backend-only work.

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
- `mandi_backend/config/api/`: views grouped by domain (`accounts`, `establishments`, `inspections`, `checklists`, `submissions`, `reporting`), shared input/output serializers, and pagination/validation helpers. Views handle HTTP; domain rules and persistence stay in app services.
- `mandi_frontend/src/features/*`: Mandi screens organized like the CMS features. Pages use the copied CMS `PageSection`, `AppTitle`, `AppTable`, `AppPagination`, `AppFilterPanel`, `AppErrorState`, `AppLoader`, `AppDialog`, form components, and calendar controls.
- `mandi_frontend`: copied CMS build configuration, theme, fonts, dashboard layout/sidebar/header, shared UI/public component set, and supporting shared components, with Mandi screens and API/session adaptation.
- Establishment, source-link, and inspection records are read-only in Django admin so changes cannot bypass services. Checklist add/edit (including XLSForm upload) and inspection add are available as service-backed admin forms; inspection approval remains in the application. `apps/core` provides countries, provinces, districts, and shared abstract model helpers. Account/group administration uses Django's built-in administration. Open `/admin/` on the backend port (`8000`) with a staff/superuser account; create one with `createsuperuser` if needed.
- New employees can be assigned predefined groups in their creation form by an authorized administrator. They are not automatically granted reviewer privileges.

## API contract

The authenticated `GET /api/v1/schema/` endpoint returns an OpenAPI 3 contract generated from the input/output serializers plus endpoint metadata. Lists accept `page` and `page_size` (maximum 100); the copied CMS pagination controls send the selected size. API tokens are sent as `Authorization: Token <token>`. Tokens are held in browser session storage for this local review; production authentication and deployment hardening remain later work.

## Permissions and calendars

See [permissions-and-calendars.md](permissions-and-calendars.md) for migration-installed groups, Can guards, copied form components, and calendar conversion.

## Checklist deployment and collection (ODK Central)

Checklists are deployed through the configured collection provider
(`COLLECTION_PROVIDER`, default `odk`). Deployment requires the
`inspections.deploy_checklist` permission, which Mandi administrators and
integration operators receive.

- `POST /api/v1/checklists/{id}/deploy/` prepares the XLSForm, adds a first
  `select_one_from_file establishments.csv` question named `establishment_id`
  when missing, inserts read-only establishment detail rows after it, and
  publishes the form to the provider.
- The detail rows are wrapped in one `field-list` group, so Collect shows the
  whole Licensing profile on a single page instead of one page per field. They
  use `pulldata('establishments', '<column>', 'name', ${establishment_id})`
  calculations plus notes, so collectors see the selected establishment's
  province, district, address, license number/dates, grade, owner, owner
  phone/email, technical manager and phone, technical staff count, and
  activities offline. Empty values are hidden with `relevant`.
- `GET /api/v1/integrations/establishments.csv` downloads the establishment CSV
  used by that question, including those Licensing fields from the stored
  business/contact projection. It requires `inspections.deploy_checklist`
  because it contains owner/technical-manager contact details.
- Adding the detail rows changes the form structure, so an already-published
  form must normally be published under a new checklist code/version rather than
  redeployed in place; Central's structure warning is reported with a hint. The
  deploy dialog also offers **Publish anyway**, which retries with Central's
  `ignoreWarnings=true` after an explicit confirmation; use it only when you
  accept that older submissions may become unreadable.
- `POST /api/v1/integrations/collection/sync/` pulls submissions from deployed
  forms. Pass `{"checklist_id": ...}` or `{"establishment_id": ...}` to limit a
  sync.
- Stored submissions live in `CollectionSubmission`; deployment metadata is in
  `FormDeployment`, and collection access grants are in `CollectorGrant`.

## Browsing checklists and submissions

- `GET /api/v1/checklists/{id}/` returns one checklist with `submission_count`.
- `GET /api/v1/checklists/{id}/collection-submissions/` lists the submissions of
  one checklist. Query parameters: `search`, `establishment_id`, `date_from`,
  `date_to`, plus `page` and `page_size`.
- `GET /api/v1/collection-submissions/{id}/` returns one submission with scores,
  typed answers, and attachments.
- `GET /api/v1/collection-submissions/{id}/attachments/{index}/` streams an
  uploaded file through the backend.
- `form_schema` stores `types`, `paths`, `groups`, and `order`, so answers keep
  their form order and carry their section label and field type. Media questions
  render the matched upload (`_attachments`) inline; geopoints link to
  OpenStreetMap; other files appear as links.
- UI routes: `/checklists/:id` (submission browser with search and filters) and
  `/submissions/:id` (single submission with section scores, grouped answers,
  files, and raw JSON).

## Integration boundary

`GET /api/v1/integrations/establishment-choices/?kind=pharmacy` returns stable Mandi IDs as choice names and readable labels. It is an authenticated JSON export, not a live preload/pull integration.

`POST /api/v1/integrations/ingest/` accepts normalized inspection summaries. It requires the inspection-add permission. Provider adapters and actual field mappings are not implemented yet. The input's mapping version records which mapping produced a result; it does not perform mapping itself.

Submission identity is `(provider, provider_form_id, submission_id)`. An unchanged retry preserves the record and approval. A changed submission updates the existing record, resets approval, and creates an audit entry. This is a conservative provisional rule for review, not a finalized rejection/revision workflow.

Selected summaries currently support overall percentage, named sections with earned/possible scores, and findings with actions/deadlines. Full answers, attachments, sample/quarantine annexes, and laboratory workflows are deferred to actual checklist conversion. No score is automatically derived from unresolved paper-checklist rules.

Source links currently allow one external record per source per establishment, and prevent the same source record from being connected to two Mandi establishments. Review this assumption if source systems represent branches or duplicates differently.

## Licensing registry import

Licensing is configured with `LICENSING_BASE_URL` and
`LICENSING_REGISTRATION_API_KEY`. The `licensing` external system is active and
searchable by default; the catalog reports it as connected when both values are
set.

To import every active Licensing category (`company`, `factory`, `pharmacy`,
`wholesale`) once and link each record as the establishment's primary identity:

```bash
.venv/bin/python mandi_backend/manage.py sync_registries --full --source licensing
```

Explicit `--once`/`--full` runs work even when continuous polling
(`REGISTRATION_SYNC_ENABLED`) is off. The import is idempotent: rerunning it
updates changed identities and reports unchanged records. Because Licensing is
primary, local edits to imported names and locations are blocked; use the
refresh action or rerun the import instead.

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

Stop the two development servers with Ctrl-C. To stop the full container stack
while preserving data:

```bash
docker compose stop
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

### Checklist metadata from XLSForm

When adding a checklist, select its XLSForm first. Mandi previews the workbook through
`POST /api/v1/checklists/metadata/` and fills `name` from `settings.form_title`,
`code` from `settings.form_id`, and `version` from `settings.version`. If no title
is provided, it uses the filename without its extension. Missing code/version
remain editable required fields. Manual edits and existing checklist details are
preserved when a file is selected or replaced.

An optional Mandi-specific `establishment_kind` column in the `settings` sheet
can supply the type: `pharmacy`, `wholesaler`, `importer`, or `factory`. Standard
XLSForms do not specify this business classification; when absent, select it
manually. Previewing does not store a file or create a checklist. Both `.xlsx`
and the existing LibreOffice-based `.xls` conversion are supported.

### User accounts and checklist access

In Django admin (`/admin/`), open **Accounts → Users → Add user** to create a
login and password. Choose the appropriate Mandi role groups. Enable
**Restrict checklist access** and select **Allowed checklists** to limit that
user to specific forms. With the restriction enabled, an empty list grants no
checklist access. Normal role permissions are still required; the allowlist does
not grant editing, deployment, or administration rights. Superusers retain full
access. Existing accounts remain unrestricted unless explicitly changed.

Restrictions apply to checklist and inspection lists/details, related submissions
and attachments, sync/deployment operations, and corresponding admin records.
Coverage counts use the user's visible inspections. A restricted user who has
permission to create a checklist automatically receives access to that new form.

### Background audio playback

AMR recordings are converted to MP3 for browser playback through the authenticated
attachment endpoint using `?playback=1`. Install FFmpeg on the backend host (it is
already available in the development environment). The original attachment is
preserved and remains available through the endpoint without that parameter.
Temporary audio files are removed after conversion; playback streams close when
the response finishes.

### Live Licensing connection

The supplied API contract is saved in [licensing-api-reference.md](licensing-api-reference.md).
Set `LICENSING_BASE_URL`, `LICENSING_REGISTRATION_API_KEY`, and optionally
`LICENSING_TIMEOUT` in `mandi_backend/.env` (and in the root `.env` for Compose).
Production currently points at `http://192.168.1.4:8008`; the key is stored only
in the ignored server environment. Restart the backend after changing
environment settings.

To import every active Licensing category and link each record as the primary
establishment identity:

```bash
.venv/bin/python mandi_backend/manage.py sync_registries --full --source licensing
```

The import is idempotent and works even when continuous polling is off. Because
Licensing is primary, local edits to imported names and locations are blocked;
use refresh or rerun the import instead. Development-only records must not be
mixed with production IDs: clear them before switching origins.

On an establishment detail page, linked Licensing records show a
**Licensing details** section immediately: establishment identity and status,
license number/dates and documents, location with map coordinates, ownership and
applicant contacts, technical staff, and activities/premises. Inspection dates
and checklist questions stay in the collection forms and are not copied from
Licensing. Users with `view_sourcelink` can open **Licensing → Connect** under
Source systems to search and page through applications, then select a record.

Mandi maps importer → company, factory → factory, pharmacy → pharmacy, and
wholesaler → wholesale. Source identities include category and exact application
ID (`company:APP-123`) to avoid cross-category collisions. The detail endpoint is
loaded on demand; Mandi stores only a minimal business/location projection, not
identity documents or the full upstream response. Existing Mandi source-link
permissions are enforced. List requests remain paginated; the client also accepts
a plain array response. No upstream pagination URLs are followed directly.

Verified on 2026-11-21 against production: company 429, factory 73, pharmacy 955,
wholesale 0. List, identity, and detail lookups succeeded for all populated
categories.
