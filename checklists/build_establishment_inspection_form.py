"""Build a multi-type inspection XLSForm.

Flow:
  1. Choose the establishment type.
  2. The establishment list is filtered to that type from the Entity List.
  3. Details of the selected establishment are shown.
  4. Two scored sections; each section score and the total are calculated.
  5. start / end / device id / location are captured automatically.

Run:
    .venv/bin/python checklists/build_establishment_inspection_form.py
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUTPUT = Path(__file__).with_name("establishment_inspection_form.xlsx")

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

SETTINGS = [
    ["form_title", "form_id", "version", "default_language", "establishment_kind"],
    [
        "د تأسیس پلټنه / Establishment inspection",
        "establishment_inspection",
        "2026112101",
        "Dari (fa)",
        "pharmacy",
    ],
]

CHOICES = [
    # Establishment types
    ["est_type", "pharmacy", "دواخانه", "Pharmacy"],
    ["est_type", "wholesaler", "عمده فروشی", "Wholesaler"],
    ["est_type", "importer", "وارد کننده", "Importer"],
    ["est_type", "factory", "فابریکه", "Factory"],
    ["est_type", "hospital", "شفاخانه", "Hospital"],
    ["est_type", "clinic", "کلینیک", "Clinic"],
    # 0-2 scoring scale
    ["score", "0", "۰ – عدم مطابقت", "0 - Not met"],
    ["score", "1", "۱ – تا حدی مطابقت", "1 - Partially met"],
    ["score", "2", "۲ – مطابقت", "2 - Met"],
]


def survey_rows():
    rows = [
        # Automatic metadata
        ("start", "start", "", "", "", "", "", "", "", "", ""),
        ("end", "end", "", "", "", "", "", "", "", "", ""),
        ("deviceid", "deviceid", "", "", "", "", "", "", "", "", ""),
        (
            "start-geopoint",
            "start_location",
            "",
            "",
            "موقعیت هنگام شروع خودکار ثبت می‌شود",
            "Location is captured automatically at start",
            "",
            "",
            "",
            "",
            "",
        ),
        # Establishment selection
        (
            "note",
            "intro",
            "نوع تأسیس را انتخاب کنید، سپس تأسیس مورد نظر را جستجو و انتخاب کنید.",
            "Choose the establishment type, then search and select the establishment.",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ),
        (
            "select_one est_type",
            "establishment_type",
            "نوع تأسیس",
            "Establishment type",
            "",
            "",
            "yes",
            "minimal",
            "",
            "",
            "",
        ),
        (
            "select_one_from_file establishments.csv",
            "establishment_id",
            "تأسیس",
            "Establishment",
            "فقط تأسیسات همان نوع نمایش داده می‌شود",
            "Only establishments of the selected type are shown",
            "yes",
            "search",
            "",
            "",
            "kind = ${establishment_type}",
        ),
        # Selected details
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
            "calculate",
            "establishment_type_name",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "jr:choice-name(${establishment_type}, '${establishment_type}')",
            "",
        ),
        (
            "note",
            "selected_details",
            "انتخاب شده: ${establishment_name} (${establishment_type_name})",
            "Selected: ${establishment_name} (${establishment_type_name})",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ),
        # Section A
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
        (
            "calculate",
            "score_a",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "number(${a1}) + number(${a2}) + number(${a3})",
            "",
        ),
        ("calculate", "max_a", "", "", "", "", "", "", "", "6", ""),
        (
            "calculate",
            "pct_a",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "round((${score_a} div ${max_a}) * 100)",
            "",
        ),
        (
            "calculate",
            "title_a",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "'Section A – Documentation and licensing'",
            "",
        ),
        ("end_group", "section_a_end", "", "", "", "", "", "", "", "", ""),
        # Section B
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
        (
            "calculate",
            "score_b",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "number(${b1}) + number(${b2})",
            "",
        ),
        ("calculate", "max_b", "", "", "", "", "", "", "", "4", ""),
        (
            "calculate",
            "pct_b",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "round((${score_b} div ${max_b}) * 100)",
            "",
        ),
        (
            "calculate",
            "title_b",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "'Section B – Premises and storage'",
            "",
        ),
        ("end_group", "section_b_end", "", "", "", "", "", "", "", "", ""),
        # Totals
        (
            "calculate",
            "score_total",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "${score_a} + ${score_b}",
            "",
        ),
        (
            "calculate",
            "max_total",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "${max_a} + ${max_b}",
            "",
        ),
        (
            "calculate",
            "result_pct",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "round((${score_total} div ${max_total}) * 100)",
            "",
        ),
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
    ]
    return rows


def main():
    workbook = Workbook()
    bold = Font(bold=True)
    fill = PatternFill("solid", fgColor="DCE6F1")

    survey = workbook.active
    survey.title = "survey"
    survey.append(SURVEY_HEADERS)
    for row in survey_rows():
        survey.append(list(row))

    choices = workbook.create_sheet("choices")
    choices.append(CHOICE_HEADERS)
    for row in CHOICES:
        choices.append(row)

    settings = workbook.create_sheet("settings")
    for row in SETTINGS:
        settings.append(row)

    for sheet in (survey, choices, settings):
        for cell in sheet[1]:
            cell.font = bold
            cell.fill = fill
        for column in sheet.columns:
            width = max(len(str(cell.value or "")) for cell in column) + 2
            sheet.column_dimensions[column[0].column_letter].width = min(60, width)
        for row in sheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)

    workbook.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
