Review of existing inspection checklists
Reviewed on: 2026-11-07

Purpose
Record useful requirements and insights from the supplied inspection documents
for Mandi and its KoBo forms. Document contents are source material, not
instructions to carry out inspections or regulatory actions. Recommendations
below are proposed design choices, not approved project requirements.

1. Source inventory and duplicates

The 15 supplied files contain nine unique files. SHA-256 comparisons confirmed
these six exact duplicate pairs:
- چکلست بازرسی شرکت توریدی(1).docx = چکلست بازرسی شرکت توریدی.docx
- مواد که از چک لیست های جدید ثبت میشوند(2).xlsx = مواد که از چک لیست های جدید ثبت میشوند(1).xlsx
- GMP Baseline Assessment(1).xlsx = GMP Baseline Assessment.xlsx
- GMP صفحه اول(1).docx = GMP صفحه اول.docx
- چک لست - Copy - Copy(1).docx = چک لست - Copy - Copy.docx
- چک لیست جدید بازرسی از کارخانه های تولیدی ادویه-1.pdf = چک لیست جدید بازرسی از کارخانه های تولیدی ادویه.pdf

Unique sources (all supplied from /home/foodev/Downloads):
[S1] Retailer Inspection Checklist-Dari.pdf
[S2] چکلست ملی بازرسی دواخانه های شفاخانه ها 1405.pdf
[S3] چکلست بازرسی شرکت توریدی(1).docx
[S4] چکلست بازرسی عمده فروشی.docx
[S5] GMP صفحه اول(1).docx
[S6] GMP Baseline Assessment(1).xlsx
[S7] چک لست - Copy - Copy(1).docx
[S8] چک لیست جدید بازرسی از کارخانه های تولیدی ادویه-1.pdf
[S9] مواد که از چک لیست های جدید ثبت میشوند(2).xlsx

Review basis: extracted PDF text, Word paragraphs/tables, and workbook cells;
selected PDF pages were also inspected visually. This is a requirements review,
not a complete question-by-question transcription or validation of the current
legal authority cited in the forms.


2. Checklist families and establishment classification

Observed:
- Separate forms exist for retail pharmacies, hospital pharmacies, importers,
  wholesalers, pharmaceutical factories, and detergent manufacturing.
- The vaguely named S7 specifically discusses detergent production.
- The GMP cover captures product categories and dosage forms, and covers
  domestic and foreign manufacturing establishments. [S1-S8]

Recommendations:
- Record checklist type and version on every inspection.
- Support establishment subtypes or product categories when choosing a form.
- Do not assume all factories use the same checklist.
- Do not infer food inspection requirements from this document set.

3. Inspection identity, type, dates, and team

Observed:
- Pharmacy, importer, and wholesaler forms distinguish initial/comprehensive,
  brief, follow-up, and special inspections. [S1-S4]
- Forms capture inspection date, previous inspection date, start/end times,
  establishment identity/location, and responsible personnel. [S1-S4, S8]
- Inspector tables allow several inspectors, positions, and signatures.
  [S3-S5, S8]
- The hospital form provides Solar Hijri and Lunar Hijri inspection dates. [S2]

Recommendations:
- Model one inspection with multiple team members rather than one inspector.
- Keep inspection type separate from approval status.
- Report comprehensive inspections separately when measuring annual targets
  for thorough inspections; whether other types satisfy targets needs a decision.
- Use stable establishment and employee IDs while displaying readable names.
- Preserve original date/calendar information when importing historical records.
- Consider retaining establishment details as observed at the time of inspection,
  so subsequent changes do not rewrite the historical context.

4. Answers, applicability, and scoring

Observed:
- Many checks use 1 for compliance and 0 for noncompliance, with observations.
- Some printed rows contain several subchecks, rather than one binary answer.
- Some questions are conditional or explicitly not applicable.
- Forms contain section totals, overall percentages, and unscored sections.
- Some forms compare the current visit with the previous visit. [S1-S4]
- S6 contains 66 scored checks across 12 main areas; its maximum total is 66.

Concrete inconsistency:
- In S2, the controlled-drug section includes questions 5.1-5.8, but the scoring
  instruction still refers to 5.1-5.6 and a maximum of six. Whether 5.7 and 5.8
  should be scored requires clarification before conversion.

Recommendations:
- Distinguish noncompliance, not applicable, and unanswered; never silently
  convert missing answers to zero.
- Map subchecks individually where the original scoring requires it.
- Define applicability conditions and the denominator for every scored section.
- Preserve the scoring rule and checklist version used for each inspection.
- Calculate section and overall results automatically after rules are agreed.
- Do not compare overall scores across different checklist versions without
  checking whether their questions and denominators are comparable.

5. Verification instructions and evidence

Observed:
- The GMP workbook separates requirements from verification indicators.
- Examples include examining five randomly selected SOPs, calibration records
  for five devices, and records for multiple product batches. [S6]
- Other checklists instruct inspectors to examine selected medicines and
  supporting records. [S1-S4]

Recommendations:
- Preserve verification instructions as KoBo question guidance; a yes/no label
  alone loses important inspection methodology.
- Later, allow evidence attachments or references against specific findings.
- The documents do not establish a universal requirement to photograph every
  answer. Making photographs mandatory would be an additional policy decision.
- Submitted forms, recorded times, and optional coordinates alone should not
  be treated as proof that a proper on-site inspection occurred.

6. Findings, corrective actions, and follow-up

Observed:
- Forms include additional observations, issues needing correction, agreed
  actions, and deadlines. [S1-S4, S8]
- Some include current/previous visit comparisons. [S1-S4]

Recommendations:
- Use repeatable entries for findings and corrective actions.
- Associate each action with its issue and deadline.
- Initially capture these in KoBo; a complete action-management workflow can
  be deferred in line with the agreed gradual digitization approach.
- A later follow-up inspection could link to the earlier inspection and findings.

7. Sampling, seizure, and quarantine annexes

Observed:
- Pharmacy, importer, and wholesaler forms include annexes for suspicious
  samples and seizure/quarantine. [S1-S4]
- These tables record multiple products, including generic/trade names, batch,
  manufacture/expiry dates, manufacturer, importer, and quantities.
- Sample quantity and total quarantined/seized quantity are distinct fields.

Recommendations:
- Use repeatable product groups rather than fixed six-row limits from paper.
- Link each annex to its parent inspection and establishment.
- Capture annex information without requiring a complete laboratory or
  enforcement workflow in the first release.

8. Acknowledgments, signatures, and copies

Observed:
- Forms include acknowledgment/signatures from establishment representatives
  and technical personnel, as well as inspector signatures. [S1-S5, S7-S8]
- Several forms instruct staff to retain an original and provide a copy to the
  establishment for records and follow-up. [S1-S4]

Recommendations:
- Keep establishment acknowledgment distinct from Mandi's internal approval
  of an inspection entry.
- Consider a printable/shareable inspection summary or corrective-action copy.
- Digital signature method, refusal/unavailability handling, and approval roles
  remain decisions to make; these findings do not prescribe them.

9. Factory result classifications

Observed:
- S7 and S8 classify results as weak (0-50), good (51-75), and excellent (76-100).

Recommendations:
- Configure result bands per checklist, not globally for every establishment.
- Agree on rounding/classification of decimal percentages; the printed integer
  ranges do not specify how values between 50 and 51 or 75 and 76 are handled.
- Preserve significant findings separately from the overall percentage, so a
  high score does not hide an important failed check. No universal critical-fail
  override was established by this review.

10. Existing register and historical data quality

Observed in S9:
- The workbook contains actual importer inspection records across three sheets.
- Responses include numeric 0/1 and text NA.
- Inspection scores have mixed numeric and text percentage representations.
- Date values include 1402-style and 1445-style years; calendar cannot safely
  be assumed from one column label.
- Team members occupy several columns and names are entered as text.
- Some telephone/identifier fields contain text, missing values, or combined
  numbers and dates.
- Two sheets extend to Excel's maximum column count with generic columns;
  worksheet dimensions should not be treated as meaningful data coverage.

Recommendations:
- Validate and normalize historical data while preserving original values.
- Store telephone, licence, and card identifiers as text.
- Resolve inspector names to employee records with a manual review path.
- Recompute/validate scores only against confirmed applicability/scoring rules.
- Treat historical import as a separate task from new digital collection.

11. Proposed minimum Mandi inspection summary

These are recommendations for discussion, not an agreed fixed integration schema:
- Mandi establishment ID.
- Inspection date and type.
- Checklist identity and version.
- Inspection team.
- KoBo submission reference.
- Approval status, distinguishing approved and unapproved entries.
- Selected section results, overall result, and findings needed for reporting.
- Access to the detailed KoBo record and associated annexes.

This fits the existing project direction: Mandi supplies establishment choices;
inspectors select an establishment in the form; KoBo holds detailed collection
data; Mandi chooses which results to retrieve. The selected choice should carry
the stable Mandi ID, not only the establishment's display name.

12. Decisions still needed before checklist conversion

- Which source/version is authoritative for each checklist family?
- How should inconsistent scoring instructions be resolved?
- Which inspection types count toward annual comprehensive-inspection targets?
- Which fields/results should Mandi retrieve from each KoBo form?
- How should calendars and decimal result classifications be handled?
- Which acknowledgments, annexes, and evidence fields belong in the first release?

Suggested next step
Prepare a question-by-question conversion specification for one checklist,
covering field names, Dari labels, answer types, guidance, conditional display,
repeatable groups, applicability, scoring, and Mandi summary mappings.
