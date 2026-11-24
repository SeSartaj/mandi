"""Build filtered XLSForm scenarios for establishment selection tests.

Run:
    .venv/bin/python checklists/build_scenario_checklists.py

Each form uses the project's ODK Entity List (``establishments.csv``) and a
constant ``choice_filter`` so only the intended establishments are selectable:

- pharmacy_scenario_a       : kind = pharmacy
- pharmacy_scenario_b       : kind = pharmacy
- factory_scenario          : kind = factory
- pharmacy_grade_2_scenario : kind = pharmacy and grade = 2
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUTPUT_DIR = Path(__file__).with_name("scenarios")

SURVEY_HEADERS = [
    "type",
    "name",
    "label::Dari (fa)",
    "label::English (en)",
    "hint::Dari (fa)",
    "hint::English (en)",
    "required",
    "appearance",
    "relevant",
    "calculation",
    "choice_filter",
]
CHOICE_HEADERS = ["list_name", "name", "label::Dari (fa)", "label::English (en)"]

CHOICES = [
    ["score", "0", "۰ – عدم مطابقت", "0 - Not met"],
    ["score", "1", "۱ – تا حدی مطابقت", "1 - Partially met"],
    ["score", "2", "۲ – مطابقت", "2 - Met"],
]


def survey_rows(choice_filter):
    return [
        ("start", "start", "", "", "", "", "", "", "", "", ""),
        ("end", "end", "", "", "", "", "", "", "", "", ""),
        ("deviceid", "deviceid", "", "", "", "", "", "", "", "", ""),
        (
            "select_one_from_file establishments.csv",
            "establishment_id",
            "تأسیس",
            "Establishment",
            "فقط تأسیسات مجاز این فورم نمایش داده می‌شود",
            "Only establishments allowed by this form are shown",
            "yes",
            "search",
            "",
            "",
            choice_filter,
        ),
        (
            "calculate",
            "establishment_name",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "jr:choice-name(${establishment_id}, '${establishment_id}')",
            "",
        ),
        (
            "note",
            "selected_establishment",
            "انتخاب شده: ${establishment_name}",
            "Selected: ${establishment_name}",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ),
        ("date", "inspection_date", "تاریخ بازرسی", "Inspection date", "", "", "yes", "", "", "today()", ""),
        (
            "begin_group",
            "section_a",
            "بخش الف – اسناد و جواز",
            "Section A – Documentation and licensing",
            "",
            "",
            "",
            "field-list",
            "",
            "",
            "",
        ),
        (
            "select_one score",
            "a1",
            "آیا جواز فعالیت معتبر و قابل دید است؟",
            "Is a valid licence available and displayed?",
            "",
            "",
            "yes",
            "",
            "",
            "",
            "",
        ),
        (
            "select_one score",
            "a2",
            "آیا مسئول فنی حاضر و کارت معتبر دارد؟",
            "Is the technical manager present with a valid card?",
            "",
            "",
            "yes",
            "",
            "",
            "",
            "",
        ),
        (
            "select_one score",
            "a3",
            "آیا اسناد و ثبت‌ها به‌روز هستند؟",
            "Are records and documentation up to date?",
            "",
            "",
            "yes",
            "",
            "",
            "",
            "",
        ),
        ("calculate", "score_a", "", "", "", "", "", "", "", "number(${a1}) + number(${a2}) + number(${a3})", ""),
        ("calculate", "max_a", "", "", "", "", "", "", "", "6", ""),
        ("calculate", "pct_a", "", "", "", "", "", "", "", "round((${score_a} div ${max_a}) * 100)", ""),
        ("calculate", "title_a", "", "", "", "", "", "", "", "'Section A – Documentation and licensing'", ""),
        ("end_group", "section_a_end", "", "", "", "", "", "", "", "", ""),
        (
            "begin_group",
            "section_b",
            "بخش ب – محل و ذخیره‌سازی",
            "Section B – Premises and storage",
            "",
            "",
            "",
            "field-list",
            "",
            "",
            "",
        ),
        (
            "select_one score",
            "b1",
            "آیا محل پاک و منظم است؟",
            "Are the premises clean and organised?",
            "",
            "",
            "yes",
            "",
            "",
            "",
            "",
        ),
        (
            "select_one score",
            "b2",
            "آیا ادویه در شرایط مناسب (حرارت و تاریخ انقضا) ذخیره شده است؟",
            "Are medicines stored correctly (temperature and expiry)?",
            "",
            "",
            "yes",
            "",
            "",
            "",
            "",
        ),
        ("calculate", "score_b", "", "", "", "", "", "", "", "number(${b1}) + number(${b2})", ""),
        ("calculate", "max_b", "", "", "", "", "", "", "", "4", ""),
        ("calculate", "pct_b", "", "", "", "", "", "", "", "round((${score_b} div ${max_b}) * 100)", ""),
        ("calculate", "title_b", "", "", "", "", "", "", "", "'Section B – Premises and storage'", ""),
        ("end_group", "section_b_end", "", "", "", "", "", "", "", "", ""),
        ("calculate", "score_total", "", "", "", "", "", "", "", "${score_a} + ${score_b}", ""),
        ("calculate", "max_total", "", "", "", "", "", "", "", "${max_a} + ${max_b}", ""),
        ("calculate", "result_pct", "", "", "", "", "", "", "", "round((${score_total} div ${max_total}) * 100)", ""),
        (
            "note",
            "summary",
            "امتیاز مجموعی: ${score_total} از ${max_total} (${result_pct}%)",
            "Total score: ${score_total} of ${max_total} (${result_pct}%)",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ),
        (
            "text",
            "notes",
            "مشاهدات و یادداشت‌ها",
            "Observations and notes",
            "",
            "",
            "",
            "multiline",
            "",
            "",
            "",
        ),
    ]


def build_checklist(filename, title, form_id, choice_filter):
    workbook = Workbook()
    survey = workbook.active
    survey.title = "survey"
    survey.append(SURVEY_HEADERS)
    for row in survey_rows(choice_filter):
        survey.append(row)

    choices = workbook.create_sheet("choices")
    choices.append(CHOICE_HEADERS)
    for row in CHOICES:
        choices.append(row)

    settings = workbook.create_sheet("settings")
    settings.append(["form_title", "form_id", "version", "default_language"])
    settings.append([title, form_id, "2026112301", "Dari (fa)"])

    for sheet in (survey, choices, settings):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9E2F3")
        for column in sheet.columns:
            width = max(len(str(cell.value or "")) for cell in column) + 2
            sheet.column_dimensions[column[0].column_letter].width = min(width, 70)
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    workbook.save(path)
    workbook.close()
    return path


SCENARIOS = [
    (
        "pharmacy_scenario_a.xlsx",
        "Pharmacy Scenario A – Establishment Filter",
        "scenario_pharmacy_a",
        "kind = 'pharmacy'",
    ),
    (
        "pharmacy_scenario_b.xlsx",
        "Pharmacy Scenario B – Establishment Filter",
        "scenario_pharmacy_b",
        "kind = 'pharmacy'",
    ),
    (
        "factory_scenario.xlsx",
        "Factory Scenario – Establishment Filter",
        "scenario_factory",
        "kind = 'factory'",
    ),
    (
        "pharmacy_grade_2_scenario.xlsx",
        "Pharmacy Grade 2 Scenario – Establishment Filter",
        "scenario_pharmacy_grade_2",
        "kind = 'pharmacy' and grade = '2'",
    ),
]


if __name__ == "__main__":
    for filename, title, form_id, choice_filter in SCENARIOS:
        path = build_checklist(filename, title, form_id, choice_filter)
        print(f"{path}  [{choice_filter}]")
