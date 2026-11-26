# Survey registration API reference

Survey provides read-only pharmacy and wholesale registration records. Mandi is
a puller; it never writes to Survey.

## Credentials

- Set `REGISTRATION_INTEGRATION_API_KEY` on the Survey backend.
- Store the same secret as `SURVEY_REGISTRATION_API_KEY` in Mandi's server
  environment. Never expose it to browsers.
- Every request sends `X-API-KEY: <key>` and `Accept: application/json`.
- Missing or invalid keys return `403`, including when Survey has no key set.

## Endpoints

| Method | Path |
| --- | --- |
| GET | `/api/applications/pharmacy/registration/list/` |
| GET | `/api/applications/wholesale/registration/list/` |
| GET | `/api/applications/pharmacy/registration/<id>/` |
| GET | `/api/applications/wholesale/registration/<id>/` |

The detail endpoints return the **full registration record**, including all business
fields, address, owner, technical staff, Sharia lawyer, surveyors and attachment
URLs. Unknown IDs, or an ID that belongs to the other registration type, return
`404`.

## Search, filtering and pagination

| Parameter | Meaning |
| --- | --- |
| `search` | Case-insensitive substring match on Survey ID, business name, province, owner first/last name, or owner phone. Omit it to list all visible records. |
| `page` | Page number starting at 1. Defaults to 1. |
| `page_size` | Records per page, 1–100. Defaults to 15. |
| `province`, `district` | Province or district name, or numeric ID. Case-insensitive for names. |
| `village` | Village substring match. |
| `name` | Business-name substring match. |
| `application_status` | `ongoing`, `completed` or `rejected`. |
| `application_step` | Numeric application step. |
| `grade`, `grade_type` | Pharmacy grade and grade type. |
| `is_official`, `has_lawyer`, `has_pharmacist` | Boolean flags (`true`/`false`). |
| `confirmed_by_team_leader`, `confirmed_by_project_coordinator`, `confirmed_by_audit` | Confirmation flags. |
| `tin_number`, `opening_letter_number` | Substring matches. |
| `years_of_activity`, `years_of_activity__gte`, `years_of_activity__lte` | Exact or ranged numeric filters. |
| `owner_first_name`, `owner_last_name`, `owner_father_name`, `owner_phone` | Owner substring filters. |
| `ordering` | `updated_at`, `created_at`, `name`, `application_step`, `application_status`, `grade` or `years_of_activity`; prefix with `-` to reverse. |

Unknown filter parameters are ignored. Invalid choice/boolean/date filters
return `400`. Results are ordered by most recently updated first, then by higher
Survey ID when `ordering` is omitted. There is no `next` link; a page beyond the
last returns an empty `results` array while retaining `count`. Invalid
pagination returns `400`.

## List response

```json
{
  "count": 1,
  "results": [
    {
      "application_id": 123,
      "name": "Example Pharmacy",
      "address": {
        "province": "Herat",
        "province_name": {"id": 1, "name": "Herat"},
        "district_name": {"id": 10, "name": "Injil"},
        "village": "Example Village",
        "exact_address": "Example Road",
        "latitude": "34.35000000",
        "longitude": "62.20000000",
        "point": {"type": "Point", "coordinates": [62.2, 34.35]}
      },
      "applicant": {
        "first_name": "Example",
        "last_name": "Owner",
        "phone_number": null
      },
      "owner": {
        "id": 5,
        "first_name": "Example",
        "last_name": "Owner",
        "father_name": "Father",
        "grand_father": "Grandfather",
        "gender": "male",
        "phone_number": null
      },
      "entity_type": "pharmacy",
      "application_status": "completed",
      "application_step": 8,
      "is_official": true,
      "grade": "1",
      "grade_type": "pharmacy",
      "tin_number": "TIN-123",
      "opening_letter_number": "OL-123",
      "opening_letter_date": "2025-01-01",
      "years_of_activity": 3,
      "current_entity_area": 30,
      "required_entity_area": 25,
      "has_lawyer": true,
      "has_pharmacist": true,
      "technical_staff_count": 1,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-02T00:00:00Z"
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `application_id` | Numeric Survey record ID. Mandi stores it as the external ID. |
| `name` | Business name. |
| `address.province` | Province name, or `null` when there is no address. |
| `address.province_name`, `address.district_name` | Objects with numeric `id` and `name`, or `null`. |
| `address.village`, `address.exact_address` | Address text, or `null`. |
| `address.latitude`, `address.longitude` | Decimal strings with eight fractional digits, or `null`. |
| `address.point` | GeoJSON Point with `[longitude, latitude]`, or `null`. |
| `applicant` | Owner first name, last name and nullable phone, or `null`. |
| `owner` | Owner summary with father/grandfather names and gender. |
| `entity_type` | `pharmacy` or `wholesale`. |
| `application_status`, `application_step` | Workflow state. |
| `is_official`, `grade`, `grade_type` | Registration classification. |
| `tin_number`, `opening_letter_number`, `opening_letter_date` | Registration references. |
| `years_of_activity`, `current_entity_area`, `required_entity_area` | Business metrics. |
| `pharmacy_count_nearby`, `wholesale_count_nearby`, `distance_to_nearest_pharmacy`, `distance_to_nearest_health_center`, `type_of_health_center` | Nearby-business metrics. |
| `has_lawyer`, `has_pharmacist`, `confirmed_by_*`, `rejection_reason`, `is_resent` | Workflow flags. |
| `technical_staff_count` | Number of technical staff records. |
| `created_at`, `updated_at` | Record timestamps. |

A record without an address returns every address field as `null`.

## Detail response

The detail endpoint returns all registration fields plus:

- `address`: full location data.
- `owner`, `technical_staff`, `sharia_lawyer`: full person records, including
  contact, education, technical-card and Sharia-lawyer fields. Personal NID and
  attachment data is included; Mandi hides it unless the viewer has
  `establishments.view_sensitive_source_details`.
- `surveyor`: the Survey users who created/worked on the record.
- `opening_letter`, `form_attachment`, `other_attachments`: file URLs. The
  files are served with the same `X-API-KEY`, so Mandi proxies them through
  `GET /api/v1/sources/survey/document/?token=…` instead of linking directly.
- `confirmed_by_*_user`, `rejected_by`: workflow users.
- `gps_pharmacy_count_nearby`, `gps_distance_to_nearest_pharmacy`:
  PostGIS-derived proximity metrics.
- `created_at`, `updated_at`, `created_by`, `updated_by`.

## Mandi configuration

```dotenv
SURVEY_BASE_URL=https://survey.example.com
SURVEY_REGISTRATION_API_KEY=<integration key>
SURVEY_TIMEOUT=15
SURVEY_SYNC_ENABLED=1
SURVEY_SYNC_INTERVAL=300
SURVEY_SYNC_PAGE_SIZE=50
```

`SURVEY_BASE_URL` is the backend origin without `/api`. Mandi constructs the
registration paths shown above. Automatic sync runs in `registry-worker`
alongside Licensing; use `--source survey` for an explicit run:

```sh
docker compose exec registry-worker python manage.py sync_registries --once --source survey
```

## Identity and overlap with Licensing

- Survey `application_id` is globally unique across pharmacy and wholesale, so
  Mandi uses the bare numeric ID as the external identity.
- Licensing publishes the Survey ID as a secondary `survey` mapping. The Survey
  sync pass sees that existing link and treats the record as already connected;
  it never creates a second establishment.
- If an existing `survey_id` belongs to a different Mandi establishment type,
  the record is skipped as a duplicate/type conflict rather than imported
  again. It is surfaced in the skipped count, not retried as a failure.
- Survey records that Licensing does not know become new establishments with a
  primary `survey` mapping.
- Only pharmacy and wholesale Survey records are imported. Any other Mandi
  establishment type is rejected for this source.
