"""Build a short media test XLSForm covering every input type Mandi renders.

Run with the project virtualenv:

    .venv/bin/python checklists/build_media_test_checklist.py

Upload the generated workbook in Mandi (Checklists -> Add checklist -> Deploy)
and open it in KoboCollect or Enketo.
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).with_name("media_test_checklist.xlsx")

SURVEY_HEADERS = [
    "type",
    "name",
    "label::Dari (fa)",
    "label::English (en)",
    "hint::Dari (fa)",
    "hint::English (en)",
    "required",
    "appearance",
    "parameters",
]

CHOICES = [
    ["list_name", "name", "label::Dari (fa)", "label::English (en)"],
    ["yes_no", "yes", "بلی", "Yes"],
    ["yes_no", "no", "نخیر", "No"],
    ["issues", "cleanliness", "پاکی", "Cleanliness"],
    ["issues", "storage", "شرایط نگهداری", "Storage conditions"],
    ["issues", "documents", "اسناد و مجوز", "Documents and licence"],
    ["issues", "staff", "حضور کارمندان", "Staff presence"],
    ["issues", "other", "سایر", "Other"],
]

SETTINGS = [
    ["form_title", "form_id", "version", "default_language"],
    [
        "چک لست آزمایشی انواع ورودی",
        "media_input_test",
        "2026110801",
        "Dari (fa)",
    ],
]

SURVEY = [
    ["start", "start", "", ""],
    ["end", "end", "", ""],
    ["today", "today", "", ""],
    # Records audio for the whole session while the form is open.
    [
        "background-audio",
        "background_audio",
        "صدای پس زمینه بازرسی",
        "Background audio of the inspection",
        "ضبط صدا از آغاز تا ختم فورم ادامه میابد (ضروری نیست).",
        "Recording continues while the form is open (optional).",
        "",
        "",
    ],
    [
        "begin_group",
        "site",
        "۱. معلومات بازدید",
        "1. Visit details",
    ],
    [
        "text",
        "site_name",
        "اسم تأسیسه",
        "Facility name",
        "",
        "",
        "yes",
        "",
    ],
    ["date", "visit_date", "تاریخ بازدید", "Visit date", "", "", "yes", ""],
    ["time", "visit_time", "زمان بازدید", "Visit time", "", "", "", ""],
    [
        "geopoint",
        "location",
        "موقعیت (GPS)",
        "Location (GPS)",
        "نقطه را ثبت کنید یا از GPS استفاده کنید.",
        "Capture the point with the device GPS.",
        "",
        "",
    ],
    ["end_group", "site", "", ""],
    [
        "begin_group",
        "evidence",
        "۲. عکس، صدا و ویدیو",
        "2. Photo, audio and video",
    ],
    [
        "image",
        "facility_photo",
        "عکس تأسیسه",
        "Facility photo",
        "یک عکس از نمای بیرونی بگیرید.",
        "Take one photo of the facility front.",
        "",
        "",
        "max-pixels=1024",
    ],
    [
        "image",
        "signature",
        "امضاء مسئول فنی",
        "Technical manager signature",
        "با انگشت امضاء کنید.",
        "Sign with your finger.",
        "",
        "signature",
        "max-pixels=1024",
    ],
    [
        "audio",
        "voice_note",
        "یادداشت صوتی",
        "Voice note",
        "یک توضیح کوتاه را ضبط کنید.",
        "Record a short explanation.",
        "",
        "",
    ],
    [
        "video",
        "walkthrough_video",
        "ویدیوی بازدید",
        "Walkthrough video",
        "یک ویدیوی کوتاه از محیط بگیرید.",
        "Record a short walkthrough video.",
        "",
        "",
    ],
    [
        "file",
        "document",
        "سند اسکن شده",
        "Scanned document",
        "مجوز یا سند را ضمیمه کنید (PDF، عکس و غیره).",
        "Attach a licence or document (PDF, image, etc.).",
        "",
        "",
    ],
    ["end_group", "evidence", "", ""],
    [
        "begin_group",
        "answers",
        "۳. پرسش ها",
        "3. Questions",
    ],
    [
        "select_one yes_no",
        "standards_met",
        "آیا معیار ها رعایت شده است؟",
        "Are the standards met?",
        "",
        "",
        "yes",
        "horizontal-compact",
    ],
    [
        "select_multiple issues",
        "issues_found",
        "کدام موارد نیاز به اصلاح دارد؟",
        "Which issues need correction?",
        "",
        "",
        "",
        "",
    ],
    [
        "barcode",
        "asset_tag",
        "بارکد یا QR تأسیسه",
        "Facility barcode / QR",
        "بارکد را اسکن کنید.",
        "Scan the facility barcode.",
        "",
        "",
    ],
    [
        "text",
        "comments",
        "ملاحظات",
        "Comments",
        "",
        "",
        "",
        "multiline",
    ],
    ["end_group", "answers", "", ""],
    [
        "note",
        "done",
        "تشکر. این فورم آزمایشی به پایان رسید.",
        "Thank you. This media test form is complete.",
    ],
]


def style_sheet(sheet, widths, freeze="A2"):
    header_fill = PatternFill("solid", fgColor="DDEBF7")
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    sheet.freeze_panes = freeze


def main():
    workbook = Workbook()

    survey = workbook.active
    survey.title = "survey"
    survey.append(SURVEY_HEADERS)
    for row in SURVEY:
        survey.append(row + [""] * (len(SURVEY_HEADERS) - len(row)))
    style_sheet(survey, [22, 24, 46, 42, 44, 42, 10, 20, 20])

    choices = workbook.create_sheet("choices")
    for row in CHOICES:
        choices.append(row)
    style_sheet(choices, [14, 20, 32, 30])

    settings = workbook.create_sheet("settings")
    for row in SETTINGS:
        settings.append(row)
    style_sheet(settings, [46, 24, 14, 16])

    workbook.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
