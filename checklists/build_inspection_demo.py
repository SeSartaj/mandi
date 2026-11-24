"""Build the employee-facing inspection capability demo XLSForm.

Run from the repository root:
    .venv/bin/python checklists/build_inspection_demo.py
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUTPUT = Path(__file__).with_name("mandi_inspection_demo.xlsx")

SURVEY_HEADERS = [
    "type",
    "name",
    "label",
    "hint",
    "required",
    "appearance",
    "default",
    "calculation",
    "parameters",
]

SURVEY = [
    # ODK metadata captured automatically at form start/end.
    ("start", "start", "Start time", "Captured automatically.", "", "", "", ""),
    ("end", "end", "End time", "Captured automatically.", "", "", "", ""),
    ("today", "today", "Today", "Captured automatically.", "", "", "", ""),
    ("deviceid", "deviceid", "Device ID", "Captured automatically.", "", "", "", ""),
    ("username", "username", "ODK username", "Shown when configured on the device.", "", "", "", ""),
    (
        "note",
        "intro",
        "Inspection capability demo. Select an establishment from Mandi, capture the location, "
        "assess repeatable sections, add samples, and attach photos.",
        "",
        "",
        "",
        "",
        "",
    ),
    # These three fields must stay at the submission root: Mandi's sync reads
    # establishment_id, inspected_on, and inspection_kind from the top level.
    ("date", "inspected_on", "Inspection date", "", "yes", "", "today()", ""),
    (
        "select_one inspection_kind",
        "inspection_kind",
        "Inspection type",
        "",
        "yes",
        "minimal",
        "comprehensive",
        "",
    ),
    (
        "select_one_from_file establishments.csv",
        "establishment_id",
        "Establishment",
        "Search by name. The value submitted is the ODK Entity UUID.",
        "yes",
        "search",
        "",
        "",
    ),
    # Visit evidence.
    ("begin_group", "visit", "Visit evidence", "", "", "field-list", "", ""),
    (
        "geopoint",
        "location",
        "Establishment location",
        "Capture GPS at the establishment gate.",
        "yes",
        "placement-map",
        "",
        "",
    ),
    ("image", "establishment_photo", "Establishment photo", "", "yes", "", "", ""),
    ("image", "license_photo", "License / registration photo", "", "", "", "", ""),
    ("end_group", "", "", "", "", "", "", ""),
    # Inspection team.
    ("begin_group", "team", "Inspection team", "", "", "field-list", "", ""),
    ("text", "inspector_name", "Lead inspector name", "", "yes", "", "", ""),
    ("text", "inspector_2_name", "Second inspector name", "", "", "", "", ""),
    ("text", "inspector_3_name", "Third inspector name", "", "", "", "", ""),
    ("end_group", "", "", "", "", "", "", ""),
    # Repeatable sections. Each row is one section with a 0/1 result.
    (
        "begin_repeat",
        "sections",
        "Inspection sections",
        "Add one row for each section you assess.",
        "",
        "",
        "",
        "",
    ),
    ("select_one section_list", "section_name", "Section", "", "yes", "", "", ""),
    (
        "select_one yn",
        "section_result",
        "Result",
        "1 = compliant, 0 = non-compliant.",
        "yes",
        "horizontal",
        "",
        "",
    ),
    ("text", "section_notes", "Findings / required action", "", "", "multiline", "", ""),
    ("image", "section_photo", "Section photo", "", "", "", "", ""),
    ("end_repeat", "", "", "", "", "", "", ""),
    # Repeatable sample list.
    (
        "begin_repeat",
        "samples",
        "Samples collected",
        "Add one row for each sample.",
        "",
        "",
        "",
        "",
    ),
    ("text", "sample_brand_name", "Brand name", "", "yes", "", "", ""),
    ("image", "sample_photo", "Sample photo", "", "", "", "", ""),
    ("date", "sample_expiry_date", "Expiry date", "", "", "", "", ""),
    ("text", "sample_batch_number", "Batch / lot number", "", "", "", "", ""),
    ("integer", "sample_quantity", "Quantity", "", "", "", "", ""),
    ("end_repeat", "", "", "", "", "", "", ""),
    # Summary and sign-off.
    ("begin_group", "summary", "Summary and sign-off", "", "", "field-list", "", ""),
    ("text", "summary_findings", "Overall findings", "", "", "multiline", "", ""),
    (
        "select_one yn",
        "follow_up_required",
        "Follow-up action required?",
        "",
        "yes",
        "horizontal",
        "",
        "",
    ),
    ("image", "signature_photo", "Inspector signature photo", "", "", "", "", ""),
    ("end_group", "", "", "", "", "", "", ""),
]

CHOICES = [
    ("inspection_kind", "comprehensive", "Comprehensive"),
    ("inspection_kind", "brief", "Brief"),
    ("inspection_kind", "follow_up", "Follow-up"),
    ("inspection_kind", "special", "Special"),
    ("section_list", "premises", "Premises and environment"),
    ("section_list", "storage", "Storage and conditions"),
    ("section_list", "documentation", "Documentation and records"),
    ("section_list", "personnel", "Personnel and training"),
    ("section_list", "equipment", "Equipment"),
    ("section_list", "other", "Other"),
    ("yn", "1", "1 — Yes / compliant"),
    ("yn", "0", "0 — No / non-compliant"),
]

SETTINGS = [
    ("form_title", "Mandi Inspection Capability Demo"),
    ("form_id", "mandi_inspection_demo"),
    ("version", "1"),
    ("default_language", "English (en)"),
    ("instance_name", "concat(${inspector_name}, ' / ', ${inspected_on})"),
    # Mandi extension: restrict establishments.csv to this establishment kind.
    ("establishment_kind", "pharmacy"),
]


def style_sheet(sheet):
    header_fill = PatternFill("solid", fgColor="1F2A44")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
    sheet.freeze_panes = "A2"
    for column in sheet.columns:
        letter = column[0].column_letter
        width = max((len(str(cell.value or "")) for cell in column), default=10)
        sheet.column_dimensions[letter].width = min(max(width + 2, 12), 70)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def build():
    workbook = Workbook()
    survey = workbook.active
    survey.title = "survey"
    survey.append(SURVEY_HEADERS)
    for row in SURVEY:
        # Central warns about every image without a size limit and refuses to
        # create the form unless warnings are ignored. Keep photos small.
        survey.append([*row, "max-pixels=1024" if row[0] == "image" else ""])

    choices = workbook.create_sheet("choices")
    choices.append(["list_name", "name", "label"])
    for row in CHOICES:
        choices.append(row)

    settings = workbook.create_sheet("settings")
    settings.append(["form_title", "form_id", "version", "default_language", "instance_name", "establishment_kind"])
    settings.append([value for _, value in SETTINGS])

    for sheet in (survey, choices, settings):
        style_sheet(sheet)

    workbook.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
