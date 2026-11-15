# Short pharmacy inspection with evidence

Form: `pharmacy_brief_evidence`, version `2026111101`.
Workbook: `outputs/short-pharmacy-20261111/pharmacy_brief_evidence.xlsx`.

This short screening form is adapted from `pharmacy_inspection_checklist_1405.xlsx`:

| Short check | Original checklist |
| --- | --- |
| Licence available, valid and displayed | Section 2, opening letter availability/display |
| Technical manager present with valid card | Sections 2 and 8 |
| Five medicines: legible labels and valid expiry dates | Section 4 |
| Label-appropriate storage, thermometer and cold storage when applicable | Section 6 |
| Cleanliness and separation of expired/returned stock | Sections 6 and 7 |

These are condensed screening questions, with no percentage score or automatic approval.
The full source is a hospital-pharmacy checklist; this adaptation uses general pharmacy wording.

## Collection sequence

1. Required live photograph of the pharmacy front and signboard.
2. Select the pharmacy from Mandi's `establishments.csv`.
3. Required GPS capture at the pharmacy entrance, without manual map placement.
4. Five short checks with answers: verified yes, problem found, or not verified.
5. Required photographs of the licence (or its missing location), one sampled medicine's label/expiry, and the storage area.
6. If any check is negative or unverified: required findings/action text and an additional evidence photograph.
7. Optional additional observations.

Dari is the default language. All visible questions, hints and choices also have Pashto translations.
Automatic metadata records start/end date and time, today's date, device ID, configured username,
and a background GPS point at form start. The required explicit GPS question provides a location
even if background capture does not succeed. The device clock supplies timestamps; reopening a
saved form can affect its end time. These values describe form entry, not independently verified
physical arrival and departure.

Every image uses `appearance=new` to remove gallery selection in KoboCollect Android.
This restriction is [documented as KoboCollect-only](https://support.kobotoolbox.org/appearances_xls.html),
so use KoboCollect rather than a browser for this workflow. A form cannot prevent a modified client
or spoofed device GPS/clock. No Android device acceptance test has been performed.

The workbook intentionally includes `establishment_id` after the front photograph. Mandi's deployer
detects the existing question and therefore does not prepend another establishment question.
Mandi attaches the current establishments CSV during deployment. Direct KoBo upload needs that
CSV attached separately.

Validated with the connected KoBo container's pyxform converter. Verified compiled XML contains
both languages, automatic metadata, conditional evidence requirements, camera-only uploads,
and the front image as the first visible question. Spreadsheet preview rendering stalled and
was stopped; the workbook was inspected programmatically instead. Created in local Mandi as checklist 13 and
deployed to the connected local KoBo instance as asset `av9zro55AHQynwBYEBBgiA`.
