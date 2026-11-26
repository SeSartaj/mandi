# Kabul pharmacy checklist (evidence, scoring, audit trail)

| | |
| --- | --- |
| Form id | `kabul_pharmacy_inspection` |
| Version | `2026112602` |
| Workbook | `checklists/kabul_pharmacy_checklist.xlsx` |
| Builder | `checklists/build_kabul_pharmacy_checklist.py` |
| Languages | Dari (default), Pashto, English – every label, hint and choice |
| Layout | one `field-list` page per section; repeats show one page per item |

A compact field checklist for **pharmacies in Kabul**: automatic location and audit data,
evidence photographs, three scored sections of the national pharmacy checklist,
sampled/quarantined medicines, and the inspecting employees' names with finger
signatures. The collector is never asked for a date or a time.

```bash
.venv/bin/python checklists/build_kabul_pharmacy_checklist.py
```

Upload the workbook in Mandi: **Checklists → Add checklist** (kind *Pharmacy*) → **Deploy**.

## Form sequence

Each section group is `appearance=field-list`, so it is a single screen in KoboCollect and
Enketo. Repeat groups also use `field-list` (one page per item), but a repeat may **not** sit
inside a field-list group – ODK rejects that with *"repeats in field-list groups are not
supported"*. Sections ۶ and ۷ therefore have a plain wrapper group, a short intro screen, and
then one page per repeat item.

| # | Group | Questions |
| --- | --- | --- |
| — | metadata | `start`, `end`, `today`, `username`, `deviceid`, `start-geopoint` |
| ۱ | Pharmacy | `establishment_id` (searchable, pharmacies only), injected establishment details, Kabul scope note |
| ۲ | Location and evidence photographs | `pharmacy_location` (required point at the entrance), `pharmacy_front_photo`, `licence_wall_photo`, `interior_photo_entry`, `interior_photo_shelves`, `interior_photo_storage` |
| ۳ | Licence to operate | `q_license_1..5` – 1 / 0 / not applicable |
| ۴ | Medicine storage conditions | `q_storage_1..5` – 1 / 0 / not applicable |
| ۵ | Cleanliness and general condition | `q_premises_1..5` – 1 / 0 / not applicable |
| ۶ | Samples and quarantined medicines | repeat `sample_items`: action, medicine, batch, expiry, quantity, unit, seal, reason, photo |
| ۷ | Inspecting employees and signatures | repeat `inspector_items`: `inspector_name`, `inspector_signature` only |
| ۸ | Audit trail | automatic user/device/start/location notes and the calculated inspection duration |

There is **no scoring page**: the scores are calculated in the background and never shown to
the person filling the form.

## Automatic location

- `start-geopoint` (`start_location`) is captured by the device when the form opens and
  is stored with the submission. It is not shown as a question, so it cannot be edited.
- `pharmacy_location` is a separate **required** `geopoint` so the submission always has a
  point taken at the pharmacy entrance, even if the background capture fails. The hint asks
  the inspector to use the device GPS and not to place the point by hand on the map.

## Automatic date, time and duration

- XLSForm metadata: `start` / `end` are the form open and finalize timestamps, `today` the
  device date, `username` and `deviceid` the collector identity. None of them is a question,
  so nothing can be edited.
- The form asks for **no** start or end date and **no** start or end time.
- `inspection_duration_minutes` is a `calculate` – `(end − start)` in minutes. While the form
  is still open (`end` empty) it falls back to `now()`, so the value is always available and
  is refreshed on every answer until the form is finalized:

```
if(${end} = '', round((decimal-date-time(now()) - decimal-date-time(${start})) * 1440, 0),
   round((decimal-date-time(${end}) - decimal-date-time(${start})) * 1440, 0))
```

- Section ۸ repeats the automatic values as visible notes (`audit_user`, `audit_device`,
  `audit_started`, `audit_start_point`, `duration_note`) so the audit trail is visible next
  to the answers. `start`, `end` and the KoBo submission time stay in the submission record.

Every value comes from the device clock and GPS. A modified client or a spoofed device can
change them, and the timestamps describe form entry rather than independently verified
arrival and departure.

Every value comes from the device clock and GPS. A modified client or a spoofed device can
change them, and the timestamps describe form entry rather than independently verified
arrival and departure.

## Photographs

All images use `appearance=new` and `parameters=max-pixels=1600`. `new` removes gallery
selection in KoboCollect (documented as KoboCollect-only), so use KoboCollect for this
workflow rather than a desktop browser.

1. `pharmacy_front_photo` – front of the pharmacy and the signboard.
2. `licence_wall_photo` – the licence as affixed to the wall; if it is not displayed,
   photograph the empty wall area.
3. `interior_photo_entry` – inside, facing the entrance door.
4. `interior_photo_shelves` – inside, facing the medicine shelves.
5. `interior_photo_storage` – inside, facing the refrigerator and quarantine area.

## Scoring

Every question is `select_one yn` with three answers, shown as a normal full-width radio
list (no `horizontal-compact` grid, no drop-down, so each option is a large tap target):

| Value | Dari | Pashto | English |
| --- | --- | --- | --- |
| `1` | ۱ – مطابق / تکمیل | ۱ – سم / بشپړ | 1 – Met (1 point) |
| `0` | ۰ – عدم مطابقت | ۰ – نه سم | 0 – Not met (0 points) |
| `2` | ۲ – قابل تطبیق نیست | ۲ – د تطبیق وړ نه دی | 2 – Not applicable |

A *not applicable* answer scores 0 **and** is removed from that section's denominator, so it
neither helps nor penalises the percentage. If every question of a section is marked not
applicable the section percentage is 0 rather than a division by zero.

| Section key | Source in `pharmacy_inspection_checklist_1405.xlsx` | Questions | Max |
| --- | --- | --- | --- |
| `license` | section 2 (licence and technical manager) | 5 | 5 |
| `storage` | section 6 (storage conditions) | 5 | 5 |
| `premises` | section 7 (building and cleanliness) | 5 | 5 |

Calculated fields, following the convention Mandi reads for the submission page:

```
score_<key>   = sum of if(q = '1', 1, 0)
max_<key>     = number of questions - number of "not applicable" answers
pct_<key>     = round(100 * score_<key> div max_<key>, 1)   (0 when max_<key> is 0)
score_total   = sum of score_<key>
max_total     = sum of max_<key>
result_pct    = round(100 * score_total div max_total, 1)
title_<key>, order_<key>  = section label and position used by Mandi
```

The percentages are **not shown in the form**. The calculations run in the background and
are hidden from the collector; Mandi reads them
(`apps/integrations/submissions.py: extract_scores`) for the badge on the submission page and
the section index. An empty `scoring` page would be skipped anyway – it holds no prompts.

## Languages

Every label, hint and choice is present in Dari (`label::Dari (fa)`, the default),
Pashto (`label::Pashto (ps)`) and English (`label::English (en)`). The builder stores the
three texts side by side in the section tables, and Mandi keeps the Dari text as the
question label for the submissions grid.

## Samples and quarantined medicines

Repeat group `sample_items`, one row per medicine. `sample_action` distinguishes
*منونه برداری برای لابراتوار* (sample for laboratory testing) from *قرنطین ادویه*
(quarantine). The reason is required; the photo of the medicine label and expiry date is
optional so a missing camera does not block the record.

## Signatures

`inspector_signature` is an `image` with `appearance=signature` (KoBo stores a PNG). The
repeat group asks for **two things only** – `inspector_name` and the signature – with one
row per employee; add another row for a colleague who joined the visit. There is no phone,
position or date question: the audit trail already records who submitted the form and when.
The owner/technical-manager acknowledgement is not part of this short form; add it from the
national checklist if a countersignature is required.

## Establishment selection

The workbook contains `establishment_id` (`select_one_from_file establishments.csv`) inside
section ۱, with `choice_filter = kind = 'pharmacy'` so only pharmacies of the linked list can
be selected. On deploy Mandi detects the existing question, keeps it in place, and injects the
`mandi_est_details` group (province, district, address, licence number and dates, grade,
owner, technical manager, staff count, activities) directly after it using `pulldata()`.
The project's `establishments` Entity List is linked to the form, so pharmacy changes do not
need a redeploy.

The question sits inside the `visit` group, so Central stores the answer as
`visit/establishment_id`. `OdkProvider.normalize` (`apps/integrations/odk.py`) resolves it
from the top level, from a flat `visit/establishment_id` key and from a nested `visit`
object, which is what links each submission to its pharmacy. Submissions collected before
that fix are relinked by running a normal sync (the **Sync** action on the checklist or
`POST /api/v1/collection/sync/`); the sync updates existing submission rows in place.

The Entity List is project-scoped and is **not** filtered by province (`establishment_kind`
in the settings sheet is ignored, and the CSV has no per-form province filter). Deploy this
checklist in a project whose establishments are the Kabul pharmacies, and confirm the
province/district shown in the details group before continuing. To harden the picker once a
deployment's CSV stores the capital consistently, extend the filter, for example
`kind = 'pharmacy' and (province = 'Kabul' or province = 'کابل')`; check that no Kabul
pharmacy is hidden before relying on it.

## Validation

Compiled with the project virtualenv's pyxform (same converter KoBo runs):

```bash
.venv/bin/python -c "from pyxform.xls2xform import xls2xform_convert; \
  xls2xform_convert('checklists/kabul_pharmacy_checklist.xlsx','/tmp/kabul.xml',validate=False)"
```

The compiled XML contains the three label languages, the hidden `start_location` geopoint,
the metadata preloads, one `field-list` page per section, five required photos, the two
repeats, the duration calculation and the score calculations.
Deploying through Mandi also compiles after the establishment details are injected.
