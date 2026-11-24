# Pharmacy inspection XLSForm

`pharmacy_inspection_checklist_1405.xlsx` is an XLSForm version of the AFDA / MoPH
national checklist **«چک لست ملی بازرسی دواخانه های شفاخانه ها – سال ۱۴۰۵»**.

Upload it in Mandi: **Checklists → Add checklist → chose the `.xlsx` → Deploy**.

## What it contains

| Workbook sheet | Purpose |
| --- | --- |
| `survey` | All questions, grouped per checklist section |
| `choices` | `yn` (1 / 0 / تطبیق نشد), `yes_no`, `grade`, `inspection_type`, `freq` lists |
| `settings` | `form_title`, `form_id = pharmacy_inspection_1405`, `version`, `default_language = Dari (fa)` |

Labels are bilingual (`label::Dari (fa)` and `label::English (en)`). Dari is the
default language, so KoboCollect and Enketo show Dari first.

Sections follow the paper checklist:

1. معلومات عمومی (general details, licence numbers, location, GPS, owner, technical manager)
2. جواز فعالیت – scored, max 5
3. بازرسی عمومی و قانونی بودن ادویه – scored, max 5
4. آزمایش لیبل ادویه – scored, max 4
5. مدیریت ادویه مخدر و تحت کنترول – scored, max 6 (5.7 and 5.8 are recorded but not scored)
6. شرایط نگهداری – scored, max 7, plus two "how often is the temperature recorded" sub-questions
7. وضعیت عمومی ساختمان – scored, max 8
8. کارمندان و خدمات – scored, max 5
9. موجودیت کتب ماخذ – yes/no, not scored
10. نمره دهی – calculated automatically (`result_pct` note shows the final score)
11. سایر مشاهدات – free text
12. هدایات تیم بازرسی – repeat group of issues and agreed actions
13. تعهد مالک و مسئول فنی – confirmation
14/15. وقت ختم کار و بازرسی کنندگان – repeat group of inspectors
- ضمیمه ۱ – repeat group for suspected-medicine samples (Annex 1 sampling form)

## Scoring rules copied from the paper form

- Each scored question is `select_one yn`: `1` = met (1 point), `0` = not met (0 points),
  `2` = تطبیق نشد / not observed (0 points).
- Denominators match the printed maxima, with the same exceptions:
  - section 2 → 4 instead of 5 when 2.5 is "تطبیق نشد";
  - section 5 → 5 instead of 6 when the narcotics register (5.4) is not available;
  - section 8 → minus one for each of 8.3, 8.4, 8.5 answered "تطبیق نشد".
- The final index is `score_total / max_total × 100`, rounded to one decimal.

> The printed page 3 text says "questions 3.1 to 3.6" with a range of 0–6, but only
> 3.1–3.5 are printed. The XLSForm scores 5 questions for section 3; confirm with
> the AFDA review team if a sixth requirement was intended.

## Establishment selection

Do **not** add an establishment question to the workbook. When a checklist is
deployed, Mandi injects, as the first question:

```
type: select_one_from_file establishments.csv
name: establishment_id
label: تأسیسات            (or "Establishment" for non-Dari forms)
appearance: search
required: yes
```

and links the project's `establishments` Entity List to that attachment. Forms
select a live Entity, so establishment changes do not require redeploying the
form. Submissions are matched to establishments through the selected Entity
UUID.

## Regenerating the workbook

```bash
.venv/bin/python checklists/build_pharmacy_checklist.py
```

The script is the source of truth; edit it rather than the spreadsheet.

Validate a change with pyxform (KoBo runs the same converter):

```bash
docker cp checklists/pharmacy_inspection_checklist_1405.xlsx kobofe-kpi-1:/tmp/pharm.xlsx
docker exec kobofe-kpi-1 python -c "from pyxform.xls2xform import xls2xform_convert; print(xls2xform_convert('/tmp/pharm.xlsx','/tmp/pharm.xml'))"
```
