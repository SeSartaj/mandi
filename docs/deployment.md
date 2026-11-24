# Deploy Mandi and ODK Central on Ubuntu

Mandi owns employee accounts, permissions, establishments, XLSForm originals,
checklist metadata, submission history, and external source mappings. Central owns
form execution, offline collection credentials, raw submissions, and attachments.
They communicate only over Central's authenticated HTTP API. Neither application
reads the other's database. An outage of Central does not prevent Mandi login or
access to stored records.

`compose.yml` is the only stack definition. It runs both applications in one
Compose project: Mandi (PostgreSQL, Django, React, collection and registry sync workers, Caddy)
and ODK Central (PostgreSQL 14, service, nginx, Enketo, pyxform, mail, Redis,
secrets). Caddy terminates HTTPS for both hostnames. Only Caddy publishes ports.

Central keeps its own database, volumes, and runtime configuration. Mandi talks
to it exclusively through Central's authenticated HTTP API, so either side can
be replaced or upgraded without changing the other's database.

Central is built from a local, pinned upstream checkout in
`deploy/runtime/central`. `scripts/setup.sh` clones `v2026.3.1` (commit
`7d6de621955c5bb6a68e098ca10c9cbb92285cdf`) and its `server` submodule. A
remote Git build cannot work because that submodule is not fetched. Both values
are stored in `.env` as `CENTRAL_VERSION` and `CENTRAL_COMMIT`.

## First deployment

Use Ubuntu with Docker Engine, the Docker Compose plugin **2.24 or newer**, Git,
Python 3, curl, and flock. Install Docker using its
[official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
Allow enough disk/RAM for two Mandi releases and Central's build; 4 CPU / 8 GB RAM
and 40 GB free disk is a sensible initial allocation, to be measured under load.
The first build downloads Node dependencies, a prebuilt Central frontend, and
LibreOffice/ffmpeg for Mandi, so it takes longer than later code deployments.

1. Clone this repository onto the server and enter it.
2. Point two DNS names to the server, e.g. `mandi.your-domain.org` and
   `collect.your-domain.org`. Allow TCP ports 80/443 and optionally UDP 443.
   Remove conflicting published services from these ports. PostgreSQL, Django,
   Central's service, and Redis have no published host ports.
3. Generate configuration and the pinned Central checkout:

   ```bash
   ./scripts/setup.sh --production
   nano .env
   ```

   Set `MANDI_DOMAIN`, `ODK_DOMAIN`, `PUBLIC_COLLECTION_URL`
   (`https://ODK_DOMAIN`), `SYSADMIN_EMAIL`, `MANDI_ADMIN_EMAIL`,
   `ODK_ADMIN_EMAIL`, and `ODK_EMAIL` to your real domains and email addresses.
   Leave `LAN_HTTP_HOST` empty in production. Keep the generated passwords/secret.
   Use distinct addresses for the Central administrator and integration user.
   Keep generated values unquoted; these deployment scripts intentionally treat
   `.env` as data and never execute it. Do not put shell code or dollar
   interpolation in this file.
4. Deploy everything with one command:

   ```bash
   ./scripts/deploy.sh
   ```

   The first run builds Central's upstream services and Mandi, starts PostgreSQL
   and Redis, runs both databases' migrations, obtains HTTPS certificates,
   bootstraps a Central administrator, a project-scoped integration account and
   the inspections project, creates the initial Mandi administrator, and starts
   periodic submission sync. No demo records are created and no existing volumes
   are deleted.
5. Open `https://MANDI_DOMAIN`. Log in with `MANDI_ADMIN_EMAIL` and the generated
   `MANDI_ADMIN_PASSWORD` from `.env`. Central's own administrator logs in at
   `https://ODK_DOMAIN` with `ODK_ADMIN_EMAIL` / `ODK_ADMIN_PASSWORD`.

Central is pinned to `v2026.3.1` (commit
`7d6de621955c5bb6a68e098ca10c9cbb92285cdf`). The service account has the **manager**
role only on `ODK_PROJECT_ID`; it has no site administrator role. Its password
stays on the server. Mandi and Central employee passwords are independent; this
is not SSO. Only administrators who operate Central need Central web accounts.

If initial setup is interrupted, rerun the same command. It preserves existing
accounts/passwords, detects existing users/projects, and retries initialization.
If the chosen project ID does not match the ID Central allocates, the bootstrap
prints the ID; set `ODK_PROJECT_ID` accordingly and rerun. Authentication failures
are surfaced rather than resetting passwords silently.

## Routine deployment and rollback

Update the checkout to the revision you intend to release, then run one command:

```bash
./scripts/deploy.sh
```

This does not upgrade, rebuild, or restart Central, and it does not take the old
Mandi web service down for image builds. It alternates the `backend`/`web`
services between blue and green slots inside the same Compose project, backs up
Mandi’s database/uploads before migrations, applies migrations, starts the
candidate, and verifies frontend → API → PostgreSQL before Caddy switches the
route from the old slot. A public HTTPS health check must then pass. Route
failures restore the previous route. The old web/API remain running for immediate
rollback; only the new worker polls submissions. A file lock prevents concurrent
deployments. Interrupted candidates can be replaced by rerunning deployment.

Central upgrades are explicit:

```bash
# After changing CENTRAL_VERSION and CENTRAL_COMMIT in .env
./scripts/deploy.sh --with-central
```

This rebuilds and restarts only Central's services around the new checkout. It
may require a maintenance window because Central can run its own database
migrations. For a first installation, plain `./scripts/deploy.sh` already builds
Central; no flag is needed.

```bash
./scripts/rollback.sh
```

Rollback changes application traffic and the worker to the previous image. It
**does not reverse database migrations or restore data**. Keep release migrations
backward compatible with the previous release: add before removing/renaming,
backfill separately, then remove in a later release. Destructive migrations or
major Central/database upgrades may require a planned maintenance window.
This is minimal-downtime deployment, not a guarantee of zero downtime: schema
locks, initial TLS issuance, or incompatible application/database changes can
interrupt requests. Long in-flight requests on the old instance can complete.

Release state is in ignored `deploy/runtime/active` and `previous`. Keep `.env`,
Docker volumes, and this runtime directory across deployments. Do not run
`docker compose down -v`. Old images are intentionally retained; prune unused
images only after verifying backups and which releases you want to retain.

## Forms and employees

1. Create establishments in Mandi.
2. Upload an `.xlsx` or `.xls` XLSForm in **Checklists** and deploy. Mandi keeps
   the original and sends Central a prepared copy. Each checklist gets a stable
   `mandi_<checklist-id>` Central form ID and each publish gets a unique XLSForm
   version. Changing field types may require a new checklist, because Central
   enforces compatibility with previously published forms.
3. Mandi inserts a required root `establishment_id` selector if missing, creates
   or reconciles the project's `establishments` Entity List, and links it to the
   form before publishing. Keep the Entity List current with the entity sync
   worker; changes reach devices on their next form update without redeploying
   the form. Existing custom `establishment_id` questions are preserved; ensure
   they submit the ODK Entity UUID, not an establishment name.
4. Create an employee, assign Mandi permission groups, and use **Manage** to edit
   their name/position, reset passwords, change groups, deactivate accounts, and
   limit access to selected checklists.
5. In **Manage → ODK Collect access**, select one or more deployed checklists and
   create a credential. Checklists in the same ODK project share one credential;
   selecting checklists from different projects creates one credential per
   project. Copy each private server URL into ODK Collect's server settings.
   Credentials are displayed once and are not stored by Mandi. Forms can be
   downloaded for offline collection and submitted when online.
6. Revoke credentials in Mandi before deactivating an employee or narrowing their
   checklist access. Failed revocation leaves the grant active and reports the
   error so it can be retried. This avoids claiming a disabled Mandi account has
   lost Central access while its device credential still works. Password resets
   terminate the employee's Mandi API token. Existing downloaded device copies
   cannot be remotely erased by revoking server access.

The sync worker uses the initial Mandi administrator by default. Set
`MANDI_SYNC_USERNAME` to an active employee with the required checklist and
establishment permissions to use a separate account.

The sync worker retries outages every `COLLECTION_SYNC_INTERVAL` seconds
(default 60). **Sync submissions** also imports immediately. Imported records are
deduplicated by provider deployment and submission ID; an unchanged retry keeps
the existing record, and changed content updates it. Attachments are fetched on
demand through Mandi's authenticated endpoint, never public media URLs.

Mapping contract: `establishment_id` is the ODK Entity UUID selected from the
project's Entity List. Mandi resolves it through the project-scoped
`EntityBinding`, so the same establishment can be used in multiple Central
projects without UUID collisions. Existing `score_*`, `max_*`, `pct_*`, and
`title_*` calculations render in the submission viewer. Central-created
collectors should be provisioned through Mandi so their checklist access is
managed in one place. Encrypted submissions and repeat-table OData expansion are
not yet mapped; their original records remain in Central.

An interrupted deployment claim can be retried after 15 minutes. Publishing uses
Central's draft → attachment → publish sequence, so a failed upload does not
replace the published form with an incomplete draft. Forms with other required
media files need those files supplied in Central before publishing; Mandi
currently manages the workbook and the `establishments.csv` Entity List link.

## Provider boundary

`apps/integrations/providers.py` defines normalized submissions and the adapter
registry. `odk.py` implements deploy, submission pagination/normalization,
attachment streaming, form links, collector provisioning, and revocation. `collection.py` owns the
Mandi workflows. `FormDeployment`, `CollectionSubmission`, and `CollectorGrant`
store remote references independently of the checklist and Mandi user models.
To add another XLSForm service, implement/register an adapter in `COLLECTION_ADAPTERS`, provide its
configuration, and map its submission metadata to the normalized submission
contract. Core establishments, users, and submissions do not change.

Provider selection is an adapter choice, not automatic migration between
providers.

## Backups and recovery

```bash
./scripts/backup.sh
```

Creates a dated private directory under `backups/` containing custom-format
PostgreSQL dumps for Mandi and Central, Mandi media, Central encryption secrets,
and environment configuration. Central's default binary storage lives in its
database. Copy backups to independent off-server storage and test restoration.
The script is not a recurring backup scheduler. For strictly coordinated
snapshots across uploads and databases, pause writes/collectors during backup;
the routine live backup is a database-consistent dump plus a separate media copy.
External S3 storage, if later configured, requires its own backup policy.

For recovery, stop the application slots/worker and the Central services that
write data, keep PostgreSQL running, restore each dump to a **clean** matching
PostgreSQL database with `pg_restore --clean --if-exists --no-owner`, restore media
to the `mandi-media` volume, Central secrets to `mandi-central-secrets`, and
restore `.env`. Start the same pinned releases and verify login, downloads,
submission sync, and attachments before allowing new submissions. Do not restore
an old database behind a newer schema without matching application versions.

## Central upgrades and operations

Normal Mandi deployments never change Central. For a deliberate Central upgrade,
take a backup first, read ODK's release/upgrade notes, then set the tested
`CENTRAL_VERSION` and `CENTRAL_COMMIT` in `.env` and run
`./scripts/deploy.sh --with-central`. `setup.sh`/`deploy.sh` fetch the matching
tag and verify the commit before building. A checkout with local changes is
never overwritten. Follow upstream instructions for PostgreSQL major upgrades;
changing an image tag alone is not a database upgrade.

Inspect the stack with the normal Compose commands:

```bash
docker compose ps
docker compose logs --tail=100 proxy central-service central-web backend-blue backend-green worker
```

To read the active Mandi slot:

```bash
read -r SLOT RELEASE < deploy/runtime/active
printf 'active %s (%s)\n' "$RELEASE" "$SLOT"
docker compose logs --tail=100 "backend-$SLOT" "web-$SLOT"
```

References: [ODK installation](https://docs.getodk.org/central-install/),
[ODK form API](https://docs.getodk.org/central-api-form-management/),
[ODK account API](https://docs.getodk.org/central-api-accounts-and-users/),
[ODK upgrades](https://docs.getodk.org/central-upgrade/).

## Validation scope

The single-stack version was checked with 102 backend/orchestration tests,
14 frontend tests, and a production frontend build. All Mandi and Central images
were built locally from the pinned checkout. The full stack started with one
Compose project; Central's administrator, integration account, and project were
bootstrapped; both HTTPS routes returned 200; the Mandi administrator logged in;
an XLSForm was published to Central and a collector credential provisioned;
the blue/green deployment and rollback scripts switched traffic and health
checks passed; and Mandi-only plus full backups were produced. Public DNS/TLS
issuance on a real server and collection from a physical device still need an
acceptance run. Django's optional HSTS subdomain/preload advisories remain;
deployment checks fail on errors, without requiring either policy.

See [registry configuration and testing](registry-and-evidence.md) to enable automatic establishment creation and identity refresh from the Licensing API. Both workers are included in the same Compose project and updated by `scripts/deploy.sh`.
