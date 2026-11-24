# Establishment ownership and external registries

Mandi keeps a small identity record locally so it can list establishments, issue XLSForms and report during upstream outages. Native records are editable. An establishment with a primary source mapping gets identity updates through that source's adapter; ordinary PATCH requests cannot overwrite it. Secondary mappings support on-demand lookups without becoming authoritative.

`EstablishmentType` and `ExternalSystem` are configurable catalogs in Django admin (`/admin/`). Codes are stable: disable entries instead of deleting or renaming codes in use. Seeded types include pharmacies, wholesalers, importers, factories, hospitals and clinics. Add a type in admin and it becomes available in the Mandi forms and XLSForm metadata. Type-specific local attributes are a JSON object; external mappings remain separate relational rows with unique `(source, external_id)` and `(establishment, source)` constraints. The database also permits only one primary mapping per establishment.

An external system catalog entry selects an adapter from `apps/integrations/registry.py`. Implement `search(kind, search, page, page_size)`, `identity(kind, external_id)` and `details(kind, external_id)` there. Credentials belong in backend environment settings. Never place them in a catalog entry or frontend bundle. Adapter identity projections expose business identity/location only. Real source links cache only the display name and synchronization time, not full profiles. New systems require code for their actual API contract; adding a catalog entry alone cannot connect an arbitrary API.

The contract a new source system must implement is documented in [external source integration contract](integration-contract.md).

The Licensing adapter implements the four-category Licensing API contract supplied with the project: company → importer, factory → factory, pharmacy → pharmacy, wholesale → wholesaler. It is the single external application registry; archive and survey references are derived from it. No upstream writes are performed. Configure the origin with `LICENSING_BASE_URL` and the key with `LICENSING_REGISTRATION_API_KEY`; the same connection powers manual search/connect and automatic sync. Survey/archive support demonstration records only when `DEMO_INTEGRATIONS=1`; configure actual adapters for real use.

## Automatic licensing sync

The single Compose stack includes a dedicated `registry-worker`, separate from ODK collection sync. With a Licensing origin/key configured, it automatically creates establishments and primary source mappings, then refreshes those identities on subsequent passes. Existing secondary mappings and ownership transfers to Mandi are respected; sync never adopts them implicitly. Missing upstream records are retained locally. No names are used for automatic merging.

Server-only configuration:

```dotenv
LICENSING_BASE_URL=http://192.168.1.4:8008
LICENSING_REGISTRATION_API_KEY=<read-only key>
LICENSING_TIMEOUT=15
LICENSING_SYNC_ENABLED=1
LICENSING_SYNC_INTERVAL=60
LICENSING_SYNC_PAGE_SIZE=50
```

Use the backend **origin**, without `/api` appended: the client constructs `/api/applications/{category}/registration/list/` and its detail routes. The actual key is stored only in ignored environment files, not this document.

The deployed Licensing origin is `http://192.168.1.4:8008`. An older backup contains `http://10.10.0.125:8001`, a previous developer-local instance; do not use it. The Licensing frontend's own `.env.local` describes its browser API and is not Mandi's configuration.

Each batch fetches one page per active supported type, ordered by `created_at`, then fetches details for complete identity/location/status. Page size is capped at 100. Page cursors survive worker restarts. The last page wraps to page one so all records are revisited; 60 seconds is the pause between batches, not a promise that every establishment refreshes every minute. Per-record failures are retried on the next full pass; page failures retain their cursor, and invalid later-page 404s reset to page one. A PostgreSQL advisory lock prevents overlapping batches from separate workers/manual commands. Error/status records contain no API keys, raw profiles or upstream response bodies.

View progress/errors under **Establishments → Automatic licensing sync** or `GET /api/v1/registry/sync/`. The UI refresh button reloads status. Trigger one bounded batch with:

```sh
docker compose exec registry-worker python manage.py sync_registries --once
```

It will report `busy` if the worker is already running a batch. Configure `MANDI_SYNC_USERNAME` to choose an existing active Mandi user with view/add/change establishment and view/change source-link permissions; the bootstrap administrator is the default. Set `LICENSING_SYNC_ENABLED=0` to pause automatic registry ingestion while Mandi and ODK continue operating.

## External systems page

**Establishments → External systems** (`/external-systems`) lists every active catalog entry with its connection state, last successful sync, and two actions:

- **Sync now** runs one bounded batch for that system and reports created/updated/failed counts; a second press while a batch runs reports that it is busy.
- **Complete sync** queues one complete pass. The request is executed by `registry-worker`, which may take several minutes, so the HTTP call returns immediately and the page polls for `pending` / `running` / `done` state.

- `GET /api/v1/registry/systems/` returns the same state, including `configured`, `syncable`, `can_sync`, per-category cursors, and the latest `full_sync` request.
- `POST /api/v1/registry/systems/{code}/sync/` accepts an optional `page_size` (1–100) and runs one batch.
- `POST /api/v1/registry/systems/{code}/full-sync/` queues a complete pass (202) or reports the active request (200).
- Licensing is directly syncable. Archive and Survey are delivered through Licensing, so their buttons stay disabled and their status reads **Derived from Licensing**.
- Viewing the page needs `establishments.view_establishment`; triggering either sync additionally needs view/add/change establishment and change source-link permissions.

## Workflow

1. Create local establishments with **Add establishment**, or choose **Import from registry**. Import uses exact external IDs and returns the existing local record on repeat; names are never used for automatic merging.
2. Connect secondary records in the establishment's source panels. Open their detail pages to read current upstream information.
3. **Use [source] as primary registry** transfers ownership to a connected source and refreshes its identity atomically. A failed refresh rolls back the transfer. **Refresh registry identity** updates the local identity; an outage leaves the last successful local identity available.
4. **Transfer ownership to Mandi** makes the local record editable while retaining the external mapping. The primary source must be relinquished before disconnecting/replacing its mapping.
5. New submissions capture the identity and mapped external IDs known when Mandi first receives them. Registry refreshes and unchanged submission resyncs preserve that snapshot. A corrected establishment assignment captures the corrected establishment identity. Earlier records with no snapshot are explicitly shown as having no captured identity; they are not backfilled with invented history.
6. Open a linked source to read its current upstream profile. Mandi fetches details on demand and stores only the minimal business/location projection for the primary link.

Snapshot times describe ingestion or detail retrieval, not the time an offline inspector observed the registry. Submission lists and details use the captured establishment identity when available.

## Local and server deployment

Use the existing single Compose deployment:

```sh
./scripts/deploy.sh
```

The script builds the inactive Mandi slot, backs up its database, applies migrations, checks health, switches the proxy, and updates both workers. Routine Mandi deployments leave Central running. These migrations add tables/fields and relax old hardcoded choices, allowing the previous slot to remain up during deployment. See `docs/deployment.md` for server/domain configuration and rollback limits. The Licensing origin is private: the Ubuntu server/container must have a route to its network.

## Acceptance tests

- Create a native pharmacy with attributes such as `{"cold_storage":true}`. Edit it and verify the values persist. Add a `laboratory` type in admin; reload and verify it is offered for establishments and checklists.
- With `DEMO_INTEGRATIONS=1`, import a Survey demonstration pharmacy. Import the same ID again; verify there is only one establishment. Try editing its identity: the UI disables editing and the API rejects changes.
- Refresh the imported identity. Transfer ownership to Mandi, edit the name, then transfer it back to the connected registry. Verify the source controls identity again. Try disconnecting a primary mapping; it must fail until ownership is transferred.
- Ingest a test submission through the ODK flow. Change the current native establishment name, then resync the unchanged submission. The stored submission and its establishment snapshot must remain unchanged.
- Connect a Survey demo source to that establishment and open its detail page. Verify missing fields and unavailable upstream services produce readable messages without breaking the local establishment page. Disconnect the secondary source and verify the local establishment remains.
- For a configured live adapter, make the source unavailable. Source search/detail/refresh should give a readable error; local establishment listing/detail and submissions must still work.
- A user lacking add/change/source-link permissions must not import or transfer ownership. Existing checklist scope restrictions still apply to source detail access.
- For automatic sync, point the origin at a server exposing the documented API. Verify all four categories appear, repeat a sync and confirm no duplicates, change one upstream name/address/status, and verify its local primary identity updates while old submission snapshots stay fixed. Transfer ownership to Mandi and verify later syncs skip it.
- If the registry cannot be reached, expect visible per-category sync errors and retained local records until connectivity is restored.

Automated verification from the repository root:

```sh
POSTGRES_DB='' DJANGO_DEBUG=1 .venv/bin/python mandi_backend/manage.py test tests --noinput
cd mandi_frontend
npm test
npm run build
```

Tests use an isolated test database. Use a temporary `MEDIA_ROOT` when running against a populated checkout to keep uploaded test files separate.


## Licensing, archive and survey detail pages

The Licensing origin supplies the four application categories and the archive/survey references embedded in its records. Imported records are linked during creation, without a manual Connect step. The previous `registration` source was merged into `licensing` by migration, so existing mappings remain valid.

License detail responses supply `archive_id`/`survey_id` and embedded profiles. Import, identity refresh and automatic sync maintain those relational mappings, including unchanged identities. Automatically managed mappings follow changed/removed references. Manual mappings are preserved; conflicting references fail visibly rather than overwriting someone else's mapping. Existing imports can be backfilled with one complete pass:

```sh
docker compose exec registry-worker python manage.py sync_registries --full
```

A complete pass holds the registry lock, visits every supported category/page once and exits; the normal worker resumes afterward. If another batch holds the lock, the command reports `busy`; retry after the current batch finishes. Page errors end that category's pass, while normal polling retries later.

Establishment detail displays Licensing, Archive and Survey as separate sections. Archive/Survey sections state that their profiles are supplied through Licensing; no independent archive/survey API is assumed. Mandi checks the mapped ID before displaying a nested profile. The page uses a curated inspection profile: establishment information, readable location, owner/co-owner contacts, technical staff, legal representative, license, and activities/premises. Internal IDs, repeated multilingual lookup objects, personal identity documents, birth information, fingerprints, tax numbers and raw workflow/finance data are omitted. Reference names display once using the selected UI language, and profile labels are translated into Dari and Pashto. The sidebar lists all configured establishment types and opens the corresponding filtered list. Unknown upstream province values remain empty instead of preventing an otherwise valid import.

Non-privileged users see the operational projection of source details; users with `view_sensitive_source_details` may see the additional fields the Licensing API exposes.
