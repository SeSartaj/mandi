# Inspection capability demo form

`mandi_inspection_demo.xlsx` is a working XLSForm for showing employees how the
Mandi + ODK Central workflow behaves. Regenerate it with:

```bash
.venv/bin/python checklists/build_inspection_demo.py
```

## What the form demonstrates

- **Establishment lookup** — `establishment_id` is a searchable
  `select_one_from_file establishments.csv` question. Mandi generates the CSV
  from establishments of the checklist's kind.
- **Automatic timestamps** — `start` and `end` are ODK metadata saved with every
  submission, along with `today`, `deviceid`, and `username`.
- **Location** — a required `geopoint` captured with the map placement control.
- **Inspection team** — lead inspector plus two optional team names.
- **Repeatable sections** — add as many section rows as needed. Each row has a
  section name, a `1`/`0` compliant/non-compliant result, findings, and a photo.
- **Repeatable samples** — add one row per sample with brand name, photo, expiry
  date, batch number, and quantity.
- **Photos** — establishment, license, section, sample, and signature photos.
  All image questions use `max-pixels=1024`.
- **Summary** — overall findings, follow-up flag, and signature photo.

The form writes `establishment_id`, `inspected_on`, and `inspection_kind` at the
submission root because Mandi's sync reads those fields there.

## Deploy through Mandi

1. Create or update establishments in **Mandi → Establishments**.
2. Open **Mandi → Checklists**, upload `mandi_inspection_demo.xlsx`, and choose
   the establishment kind (the workbook is set up for `pharmacy`).
3. Deploy the checklist. Mandi keeps the original, prepares the form, attaches
   `establishments.csv`, and publishes it to Central.
4. Add new establishments later, then **redeploy** the checklist and refresh the
   form on devices so the CSV snapshot is current.

## Connect ODK Collect

1. In Mandi, open **Employees → Manage → ODK Collect access**, select the deployed
   checklist, and create a credential.
2. Copy the one-time server URL.
3. In ODK Collect: **Settings → Server → Enter server URL**, paste it, then
   **Get Blank Form** and download the demo form.
4. Fill and submit. Mandi's worker imports submissions every 60 seconds, or use
   **Sync submissions** on the checklist page.

The server URL contains the credential. Mandi does not store it, so save it
before leaving the dialog. Revoke it in Mandi if a device is lost.

### Phone on the same network

ODK Collect only trusts system certificate authorities, so it will reject the
internal development CA used by `https://collect.localhost:8443`. For a phone on
the same LAN, use the optional plain-HTTP route:

```dotenv
BIND_ADDRESS=0.0.0.0
ODK_DOMAIN=10.10.6.25
PUBLIC_COLLECTION_URL=http://10.10.6.25:8080
LAN_HTTP_HOST=10.10.6.25
```

Then apply it:

```bash
./scripts/setup.sh
docker compose up -d --wait
docker compose exec proxy caddy reload --config /etc/caddy/Caddyfile
```

Use `http://10.10.6.25:8080` as the Central server URL. Issue a new collector
credential in Mandi and paste the full `http://10.10.6.25:8080/v1/key/...` URL
into ODK Collect; the old HTTPS URL was built for `collect.localhost`.

This HTTP route is for trusted local demonstrations only: credentials and form
data are not encrypted. For production or untrusted networks, keep
`PUBLIC_COLLECTION_URL` on your public HTTPS domain and leave `LAN_HTTP_HOST`
empty.

For a browser-only demonstration, open the Central form in Enketo/Web Forms or
use **Preview** in the Central form page.

## Verify the connection

The published form's `formList` must return the form:

```bash
curl --cacert deploy/runtime/local-ca.crt \
  -H 'X-OpenRosa-Version: 1.0' \
  '<collector server URL>/formList'
```

The response should include the form ID assigned by Mandi
(`mandi_<checklist id>`) and the demo title:

```xml
<formID>mandi_2</formID>
<name>Mandi Inspection Capability Demo</name>
```

## Pull submissions into Mandi

The sync worker uses the administrator by default. To use the new employee
account, set `MANDI_SYNC_USERNAME` in `.env`. The imported submission creates an
inspection record, maps the Central submitter to the employee holding the
collector credential, and shows the raw record and answers in the checklist
submission viewer.
