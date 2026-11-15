# Media input test checklist

`media_test_checklist.xlsx` is a short form that exercises every input type Mandi
renders, so the KoBo → Mandi media pipeline can be tested end to end.

Upload it in Mandi (**Checklists → Add checklist**, kind *Pharmacy*, version `1`),
click **Deploy**, then download the blank form on KoboCollect.

## Questions

| # | Type | Name | Purpose |
|---|---|---|---|
| 1 | `select_one_from_file` | `establishment_id` | injected by Mandi on deploy (not in the workbook) |
| 2 | `background-audio` | `background_audio` | audio recorded for the whole session |
| 3 | `text` | `site_name` | required text |
| 4 | `date` / `time` | `visit_date`, `visit_time` | Gregorian date and time |
| 5 | `geopoint` | `location` | GPS → coordinates + OpenStreetMap link in Mandi |
| 6 | `image` | `facility_photo` | camera photo (`max-pixels=1024`) |
| 7 | `image` + `signature` | `signature` | finger signature |
| 8 | `audio` | `voice_note` | audio recording answer |
| 9 | `video` | `walkthrough_video` | video recording answer |
| 10 | `file` | `document` | any upload (PDF, image, …) |
| 11 | `select_one` | `standards_met` | yes/no list |
| 12 | `select_multiple` | `issues_found` | multi-select list |
| 13 | `barcode` | `asset_tag` | barcode / QR scan |
| 14 | `text` | `comments` | multiline note |

Bilingual labels: `label::Dari (fa)` (default) and `label::English (en)`.

## What to expect in Mandi

Open **Checklists → this form → submission**, or the establishment page:

- `image` → thumbnail, click for full size
- `signature` → image (KoBo stores signatures as PNG)
- `audio` / `video` → inline player
- `file` → download link with mimetype
- `geopoint` → `lat, lon` linking to OpenStreetMap
- `background-audio` → appears under **Files** (it is not tied to a question)

Files are streamed through
`GET /api/v1/kobo-submissions/{id}/attachments/{index}/`, so the browser never
needs the KoBo token.

## Device support

- **KoboCollect (Android)**: supports every type above.
- **Enketo (web)**: supports image/audio/video/file/geopoint; `barcode` and
  `background-audio` are Android-only, so test those on a device.

## Regenerating

```bash
.venv/bin/python checklists/build_media_test_checklist.py
```

Validate with pyxform (same converter KoBo uses):

```bash
docker cp checklists/media_test_checklist.xlsx kobofe-kpi-1:/tmp/media.xlsx
docker exec kobofe-kpi-1 python -c "from pyxform.xls2xform import xls2xform_convert; print(xls2xform_convert('/tmp/media.xlsx','/tmp/media.xml'))"
```
