# External source integration contract

This is the contract an external registry must satisfy so Mandi can ingest its
records. Two systems implement it directly today: the Licensing API
(`docs/licensing-api-reference.md`) for company, factory, pharmacy and
wholesale records, and the Survey API (`docs/survey-api-reference.md`) for
pharmacy and wholesale registrations. Archive references still arrive as
metadata inside Licensing records.

Mandi is a **read-only consumer**. It never creates, updates, or deletes data in
the source system. All credentials stay on Mandi's server.

## 1. How Mandi receives records

Mandi uses two paths:

| Path | Trigger | What it does |
| --- | --- | --- |
| Automatic registry sync | `registry-worker` (`sync_registries`), every source's sync interval | Pages through the list endpoints, fetches each record's detail, creates new establishments, refreshes changed identities |
| On demand | `Import from registry`, connect a source, open a source profile, "Refresh registry identity" | Searches the list endpoint, fetches a chosen record's detail |

New records are discovered when the list page returns an `application_id` that
Mandi has never linked before. Changes are discovered on later passes: the
worker re-reads the list and fetches each detail, then compares the identity
fields. Mandi does **not** need a webhook, push notification, or write access.

## 2. Identity and categories

- Every record must have a stable `application_id` that is never reused.
- Mandi's identity is `{category}:{application_id}` (for example
  `pharmacy:EXAMPLE-000001`), because the same ID can exist in another category.
- The `application_id` must be usable in a URL path segment; Mandi URL-encodes it.
- Category → Mandi establishment type:

| Category | Mandi kind |
| --- | --- |
| `company` | `importer` |
| `factory` | `factory` |
| `pharmacy` | `pharmacy` |
| `wholesale` | `wholesaler` |

Additional Mandi establishment types (hospital, clinic, …) can exist locally but
are not populated by the Licensing contract.

The Survey adapter supports only pharmacies and wholesalers:

| Survey category | Mandi kind |
| --- | --- |
| `pharmacy` | `pharmacy` |
| `wholesale` | `wholesaler` |

Survey `application_id` values are numeric and globally unique across pharmacy
and wholesale. Mandi uses the bare `application_id` as the external ID. An
existing `survey_id` link means the record is already connected: sync never
creates a second establishment. If the existing link belongs to a different
Mandi establishment type, the record is counted as skipped (a duplicate or
upstream type conflict) instead of being imported again.

## 3. Transport

- Base URL: an origin only, without `/api` (configured in Mandi's environment).
- All calls are `GET`, `Accept: application/json`, with a trailing slash.
- Authentication: `X-API-KEY: <key>` on every request. The key is issued to
  Mandi's backend and must not be exposed to browsers.
- HTTPS is recommended. Mandi refuses redirects.
- Mandi's timeout is configurable (`LICENSING_TIMEOUT`, default 15s).
- Documents behind the key: when stored files are protected by the same
  `X-API-KEY` (Licensing and Survey both are), the profile may return absolute
  file URLs. Mandi never exposes them to a browser: it replaces each one with a
  signed, one-hour link to `GET /api/v1/sources/{source}/document/?token=…`, and
  that gateway re-requests the file with the key and streams it back as
  `inline` with `Cache-Control: private, no-store`. Only URLs on the configured
  source origin are fetched, redirects off that origin are refused, and files
  over 40 MB are rejected.

## 4. Required endpoints

At minimum, each category must expose a list and a detail endpoint. The current
Licensing shape is:

```
/api/applications/{category}/registration/list/
/api/applications/{category}/registration/{application_id}/
```

`category` is singular and one of `company`, `factory`, `pharmacy`, `wholesale`.
A different URL layout is acceptable only with a Mandi adapter that maps it.

Survey exposes two categories:

```
/api/applications/pharmacy/registration/list/
/api/applications/pharmacy/registration/{application_id}/
/api/applications/wholesale/registration/list/
/api/applications/wholesale/registration/{application_id}/
```

Survey uses the same `X-API-KEY` header but has no `next` link; Mandi derives the
next page from `count`. It accepts `search`, `page`, `page_size` (1–100, default
15), the list filters (`province`, `district`, `village`, `name`,
`application_status`, `application_step`, `grade`, `grade_type`, `is_official`,
`has_lawyer`, `has_pharmacist`, `confirmed_by_*`, `tin_number`,
`opening_letter_number`, `years_of_activity*`, `owner_*`) and `ordering`.
Survey detail responses return the full registration record, including owner,
technical staff, Sharia lawyer, surveyors, attachments and workflow users;
Mandi uses the same response for its source profile.

## 5. List endpoint

Required:

- `application_id` on every record (the only field Mandi needs to discover and
  address a record).
- Pagination via `page` and `page_size`. Mandi requests pages of 50 (maximum
  100) and follows `next`. Either shape is accepted:
  - `{"count": 967, "next": "...", "previous": null, "results": [...]}`
  - a plain array when `paginate=false`
- Ordering support for `created_at` (Mandi requests `ordering=created_at`
  ascending) so new records are eventually reached without gaps.

Recommended:

- `updated_at` on every list item.
- An `updated_since` / `updated_after` filter and descending `-updated_at`
  ordering. This lets a future Mandi adapter poll only records changed after the
  last successful pass instead of re-reading every page.
- A total `count` that reflects the current filter.

Optional filters already understood by Mandi's Licensing adapter: `search`,
`application_id`, `application_type`, `application_status`,
`address_province_name_en`, `address_district_name_en`.

Example list item:

```json
{
  "application_id": "EXAMPLE-000001",
  "name": "Local business name",
  "name_en": "English business name",
  "address": {
    "province": {"name_en": "Kabul", "name_fa": "کابل", "name_ps": "کابل"},
    "latitude": null,
    "longitude": null
  }
}
```

## 6. Detail endpoint

The detail response is a single object (no `results` wrapper). Mandi uses it for
identity, location, and source profiles.

Required for creation:

| Field | Notes |
| --- | --- |
| `application_id` | Must equal the requested ID |
| `name` or `name_en` | At least one non-empty; otherwise the record is rejected |

Read and stored when present:

| Field | Use |
| --- | --- |
| `address.province` | Province name object (`name_en`/`name_fa`/`name_ps`) or string; matched against Mandi's province list |
| `address.district` | District name, matched under the province |
| `address.address` | Free-text address (house/street/landmark) |
| `address.latitude`, `address.longitude` | Numeric coordinates; enable map and nearby features |
| `aisa_license_number` | License number shown in the source panel |
| `license_issue_date` / `issue_date` / `aisa_license_issue_date` | License issue date |
| `license_expiry_date` / `expiry_date` / `aisa_license_expire_date` | License expiry date |
| `grade`, `pharmacy_type` | Pharmacy attributes |
| `activity_domain` | Business activities |
| `applicant`, `technical_staff`, `is_owner_and_technical_same` | Owner/manager contact projection |
| `application_status` | Current workflow status |
| `survey_id`, `archive_id` (or nested `survey.id`, `archive.id`) | Derived Survey/Archive mappings |
| `created_at`, `updated_at` | Audit and optional delta polling |

Fields Mandi treats as personal/private (national ID, passport, date of birth,
salary, photos) are not stored in the establishment identity or list views.
Mandi's own user permissions decide who can see sensitive source details.

Unknown province/district names are stored as blank rather than inventing a
mapping. Missing optional fields are tolerated.

Example minimal detail:

```json
{
  "application_id": "EXAMPLE-000001",
  "name": "English business name",
  "name_en": "English business name",
  "application_status": "completed",
  "address": {
    "province": {"name_en": "Kabul", "name_fa": "کابل", "name_ps": "کابل"},
    "district": {"name_en": "District 5"},
    "address": {"house_number": "12", "street": "Market Road"},
    "latitude": 34.501,
    "longitude": 69.2
  },
  "applicant": {"first_name_en": "Ahmad", "last_name_en": "Ahmadi", "phone_number": "0700000000"},
  "survey_id": "10",
  "archive_id": "20",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-11-20T10:00:00Z"
}
```

## 7. How Mandi applies changes

For each record:

1. No local mapping for `(source, application_id)` → create a Mandi establishment
   and a primary source link.
2. Existing primary mapping → compare `name`, `address`, `latitude`,
   `longitude`, `province`, `district`.
   - identical → `unchanged` (no establishment write);
   - different → `updated`.
3. Existing mapping that is secondary, or whose ownership was transferred to
   Mandi → `skipped`; sync never takes ownership implicitly.
4. Survey/Archive IDs in the detail are maintained as derived links. A manual
   mapping that conflicts with an upstream reference fails visibly instead of
   being overwritten.
5. A record that disappears upstream is retained locally. Mandi does not delete
   establishments based on absence.

Sync is idempotent and restartable; unique constraints prevent duplicates.

## 8. Errors and reliability

| Status | Mandi behavior |
| --- | --- |
| `400` | Treated as a rejected filter; the page fails and is retried |
| `401` / `403` | Configuration error; retried, logged without secrets |
| `404` | Detail not found; record/page skipped/retried |
| `5xx`, timeout, connection error | Page retried on the next pass |

Requests must return JSON. Do not redirect. Do not include secrets in error
bodies or logs.

## 9. Performance expectations

A full pass over the current registry is about 1,500 list+detail reads. Mandi
uses bounded pages and a single worker, but the source must handle:

- list latency small enough for 50 records per page;
- one detail request per record;
- sequential requests (no burst);
- occasional full passes after configuration changes.

## 10. Recommended additions for delta sync

The current Licensing API has no changed-since filter, so Mandi must re-read all
pages to find changes. If a source can add these, Mandi can poll incrementally:

- `updated_at` on list items;
- `updated_since=<ISO-8601>` filter;
- `ordering=-updated_at`;
- optional tombstones or a `deleted` flag (Mandi still does not auto-delete).

## 11. Conformance checklist

- [ ] Stable, URL-safe `application_id` per category
- [ ] List endpoint with `page`/`page_size`, `count`, `next`
- [ ] `ordering=created_at` support and `created_at` in list records
- [ ] Detail endpoint keyed by `application_id`
- [ ] `name` or `name_en` in detail
- [ ] Province, district, address, latitude, longitude when available
- [ ] `X-API-KEY` authentication
- [ ] JSON responses, no redirects
- [ ] `400`/`401`/`403`/`404`/`5xx` semantics
- [ ] Optional: `updated_at` + `updated_since` for incremental polling

## 12. Adding a new source in Mandi

A catalog row alone is not enough. To support a different API, add an adapter in
`mandi_backend/apps/integrations/registry.py` that implements:

- `search(kind, search, page, page_size)`
- `identity(kind, external_id)`
- `details(kind, external_id, include_sensitive=False)`
- `list_page(kind, page, page_size)` (for automatic sync)

Then add an `ExternalSystem` catalog entry whose `adapter` matches, configure
its credentials in server-side settings, and enable it in the External systems
page. Existing contracts (Licensing) need no code change.
