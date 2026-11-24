# Acceptance testing the current Mandi + ODK setup

Checked on 2026-11-17. Run commands from `/home/foodev/afda/mandi`.

## What is installed now

- One Compose project (`mandi`) and one stack definition (`compose.yml`).
- Mandi uses PostgreSQL 17.7, Django/Gunicorn, two frontend/API slots, and one sync worker.
- Central 2026.3.1 uses its own PostgreSQL 14.24, nginx, Enketo, pyxform, Redis, mail, and secrets.
- Caddy provides routing and local HTTPS. No database ports are published.
- Active Mandi slot: blue. Green is retained for rollback.
- Mandi: https://mandi.localhost:8443
- Central / phone collection: http://10.10.6.25:8080
- Current mode is **local/LAN**, listening on all host interfaces. Central's LAN URL uses unencrypted HTTP; production must use HTTPS and disable the LAN route.

Current checks passed: Compose configuration, Mandi database migration check,
Mandi health/login-page requests, Central LAN frontend, integration-account
authentication, and access to Central project 1. The live backend Python files
match the checkout. The isolated automated test run passed 103 backend and
orchestration tests and 14 frontend tests; it did not change the running databases.

The live baseline is 3 establishments, 2 deployed checklists, 1 imported
submission, 1 approved inspection, and 1 active collector credential. Worker logs
show repeated imports without extra inspection records or unmapped inspectors.

**Open issue:** `https://10.10.6.25:8443` failed its TLS handshake during this
check. The working collection URL is the HTTP LAN endpoint above. Test Central's
HTTPS route separately before treating HTTPS as verified. Do not use the older
`collect.localhost` URL from the generic development instructions with this configuration.

## 1. Check access and health

```bash
docker compose ps -a
curl --fail --cacert deploy/runtime/local-ca.crt \
  https://mandi.localhost:8443/api/health/
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' \
  http://10.10.6.25:8080/
```

Expected: Mandi returns `{"status":"ok","service":"mandi"}`; Central returns
200. Long-running services stay up, and services with health checks are healthy.
`mandi-init`, `central-secrets`, and `public-ca` exiting with code 0 is normal:
these are initialization jobs. A stopped legacy `mandi-postgres-1` container is
not used by the current stack.

Open Mandi in your browser. Use `MANDI_ADMIN_USERNAME` and `MANDI_ADMIN_PASSWORD`
from `.env`. Central has a separate administrator, configured with
`ODK_ADMIN_EMAIL` and `ODK_ADMIN_PASSWORD`; Mandi login credentials are not SSO.
Keep passwords and collector URLs private.

If Mandi's browser certificate is untrusted, run `./scripts/local-ca.sh` and
follow the trust instructions it prints. On a phone, `localhost` means the
phone itself: use `10.10.6.25`, with the phone connected to the same LAN.

## 2. Test a complete inspection through the phone

Use records with a `QA-` prefix so test data is easy to identify.

1. In Mandi, create a pharmacy named `QA-Pharmacy-1`. Record its ID or detail-page URL.
2. Upload a test XLSForm as a new checklist, choosing **pharmacy** as its kind.
   A small form is easiest: include a notes question, an ISO `inspected_on` date,
   an `inspection_kind` choice, and a numeric `result_pct` field if testing scores.
   Optionally include a photo or audio question.
3. Deploy it in Mandi. Expected: status becomes **deployed**, the Central form
   exists, and Mandi can still download the original workbook.
4. Create employee `qa.inspector`, assign **Mandi inspectors**, and save.
5. Open **Employees → Manage → ODK Collect access**, select that checklist, and
   create a Collect credential. Save the server URL while it is displayed.
   It should start with `http://10.10.6.25:8080/v1/key/`.
6. Add an ODK Collect project using that server URL. Download the form. Expected:
   this credential exposes its assigned forms, and the establishment selector
   contains `QA-Pharmacy-1`.
7. Fill the form, selecting that pharmacy. Use distinctive notes and a known
   percentage such as 80 if the form has `result_pct`. Take a photo if applicable.
   Finalize and send the submission.
8. Wait about 60 seconds, or use **Sync submissions** on Mandi's checklist page.
9. Check Mandi's checklist submissions, the pharmacy's history, and inspections.
   Expected: one new submission and one new **unapproved** inspection, the right
   establishment and checklist, `qa.inspector` as the inspector, the expected
   date, and the expected percentage. Check all answer labels and media.

Submit as the **Mandi-provisioned collector**. A submission made as the Central
administrator can appear as raw data without becoming an inspection, because
that Central actor has no Mandi employee mapping.

Mapping defaults: if `inspected_on` is absent, Mandi uses Central's submission
date; if `inspection_kind` is absent, it uses `comprehensive`. Valid explicit
kinds are `comprehensive`, `brief`, `follow_up`, and `special`.

## 3. Test offline collection

Download the form and establishment list while online. Turn off both Wi-Fi and
mobile data, fill and finalize a second inspection, then reconnect Wi-Fi and
send it. Expected: it is retained on the phone while offline and appears once
in Central and Mandi after sending. Check that it still references the correct
Mandi establishment.

## 4. Test approval and repeated synchronization

1. Open the new inspection as an administrator or **Mandi inspection reviewers**
   user and approve it.
2. Run **Sync submissions** twice, then wait for another automatic sync.
3. Expected: the submission/inspection counts do not increase, its ID stays the
   same, and approval remains intact.
4. If your Central workflow permits editing the same submission, change a real
   answer and resync. Expected: the same inspection is updated and becomes
   unapproved. Sending a new form creates a different submission and is not an
   edit test.
5. Check coverage reports. A first inspection increases the number of inspected
   establishments by one. A second inspection of the same establishment adds a
   visit without counting another unique establishment. Approval changes the
   approved/unapproved split.

## 5. Test permissions and collector revocation

Create another checklist and a second test employee. In **Manage**, enable
**Restrict checklist access** and allow only the first checklist.

- Sign in as that employee: only permitted checklists and their submissions should
  be visible. Paste a disallowed checklist/submission URL directly: it should be
  denied or not found, not expose data. Test attachment links too.
- A **Mandi viewers** account must not create users, deploy forms, or approve
  inspections. A reviewer should be able to approve but should not gain user
  administration rights.
- With the inspector's Collect credential still active, try deactivating that
  employee. Expected: Mandi requires revoking collection access first.
- Revoke the credential, then deactivate the employee. Expected: Mandi login is
  rejected and the old Collect credential cannot download forms or submit new
  data. Downloaded offline copies may remain on the device.
- Reset another test employee's password. Expected: their old password and old
  Mandi login token stop working; the new password works.

Use a second administrator to change the current administrator's own access;
self-deactivation/access removal is deliberately blocked.

## 6. Test establishment-list refresh and form updates

Create another QA pharmacy and a QA factory. Redeploy the pharmacy checklist,
then refresh/download it on the device. Expected: both QA pharmacies are
available; the factory is absent from the pharmacy list. The list is a snapshot,
so creating establishments alone does not update previously downloaded forms.

Change a harmless label in the workbook and redeploy. Expected: the Central form
ID stays the same, its published version changes, and earlier submissions remain
available. An incompatible field-type change should report an error and preserve
the previously published form; test this only with the QA checklist.

## 7. Test independence during a Central outage

Do this when nobody else is collecting. In a second terminal, keep Mandi's
health endpoint open or repeat its health request.

```bash
docker compose stop central-service
# Check Mandi login, establishments, stored inspections, and reports.
docker compose start central-service
```

Expected: Mandi remains usable. New sync/deployment attempts report a connection
problem rather than losing existing records. Once Central is healthy again,
the worker resumes and does not duplicate inspections.

Inspect diagnostics with:

```bash
docker compose logs --since=10m --tail=80 worker central-service
```

Worker counts should normally show `skipped: 0` and `unmapped_inspectors: 0` for
these tests. A nonzero unmapped count usually means a Central-created collector
or web user was used instead of a Mandi-provisioned employee.

## 8. Test deployment, rollback, and persistence

In one terminal, monitor health:

```bash
while sleep 1; do
  curl --silent --show-error --max-time 5 \
    --cacert deploy/runtime/local-ca.crt \
    --output /dev/null --write-out '%{http_code}\n' \
    https://mandi.localhost:8443/api/health/
done
```

In another terminal:

```bash
./scripts/deploy.sh
cat deploy/runtime/active
./scripts/rollback.sh
cat deploy/runtime/active
```

Expected: the active slot alternates and then returns; health checks keep
returning 200; Central is not restarted by a normal Mandi release; users,
checklists, submissions, approvals, and media remain intact. Rollback changes
application images, not database migrations.

Then test `docker compose stop` followed by `docker compose up -d --wait`.
Expected: all records remain and initialization does not reset passwords or
create duplicate administrators/projects.

## 9. Test backups separately from restoration

Run `./scripts/backup.sh`. Expected: a new private directory contains Mandi and
Central database dumps, Mandi uploads, Central secrets, environment settings,
and release state. Check that the database archives can be listed and the tar
archives can be opened.

A backup is only fully verified after restoration. Restore to a **separate test
VM** and confirm login, forms, submissions, and attachments there. The Compose
file gives volumes fixed names: changing only `docker compose -p` does **not**
isolate the data volumes. Do not perform a restore experiment against this
running stack, and do not use `docker compose down -v` to stop it normally.

## Recording results

For each scenario, record pass/fail, the checklist and inspection IDs, submission
ID, user role, phone/Collect version, and any relevant error. Do not record
passwords or the secret `/v1/key/...` collector URL in shared screenshots/logs.
Production acceptance still needs real-domain HTTPS, collection on the intended
network, and a backup restoration test.
