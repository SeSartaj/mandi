import io
from pathlib import Path
import subprocess
import tempfile

from openpyxl import load_workbook


class XlsFormError(Exception):
    pass


_DARI_LABEL_TOKENS = ("dari", "persian", "farsi", "pashto", "::fa", "::ps", "(fa)", "(ps)")

# Fields shown to the collector after selecting an establishment. They are
# pulled from establishments.csv with pulldata(), so no API call is needed
# while collecting offline.
ESTABLISHMENT_DETAIL_FIELDS = (
    ("province", "Province", "ولایت"),
    ("district", "District", "ولسوالی"),
    ("address", "Address", "آدرس"),
    ("license_number", "License number", "شماره جواز"),
    ("license_issue_date", "License issue date", "تاریخ صدور جواز"),
    ("license_expiry_date", "License expiry date", "تاریخ انقضای جواز"),
    ("grade", "Grade", "درجه"),
    ("owner", "Owner", "مالک"),
    ("owner_phone", "Owner phone", "شماره تلفن مالک"),
    ("owner_email", "Owner email", "آدرس الکترونیکی مالک"),
    ("technical_manager", "Technical manager", "مسئول فنی"),
    ("technical_manager_phone", "Technical manager phone", "شماره تلفن مسئول فنی"),
    ("technical_staff_count", "Technical staff count", "تعداد کارمندان فنی"),
    ("activities", "Activities", "فعالیت‌ها"),
)


def _establishment_label(label_header):
    """Pick the establishment question label that matches the form language."""
    normalized = label_header.lower()
    if any(token in normalized for token in _DARI_LABEL_TOKENS):
        return "تأسیسات"
    return "Establishment"


def _as_xlsx(filename, content):
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        return content, f"{Path(filename).stem}.xlsx"
    if suffix != ".xls":
        raise XlsFormError("Upload an .xls or .xlsx XLSForm.")

    with tempfile.TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "input.xls"
        source.write_bytes(content)
        try:
            subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    "xlsx",
                    "--outdir",
                    temp_dir,
                    str(source),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise XlsFormError(
                "Could not convert the .xls XLSForm to .xlsx. Upload an .xlsx file."
            ) from exc
        converted = Path(temp_dir) / "input.xlsx"
        if not converted.exists():
            raise XlsFormError(
                "Could not convert the .xls XLSForm to .xlsx. Upload an .xlsx file."
            )
        return converted.read_bytes(), f"{Path(filename).stem}.xlsx"


def _ensure_column(survey, header_row, columns, name):
    if name in columns:
        return columns[name]
    column = survey.max_column + 1
    survey.cell(row=header_row, column=column, value=name)
    columns[name] = column
    return column


def add_establishment_question(filename, content):
    """Ensure the survey selects a Mandi establishment and shows its details."""
    xlsx_content, xlsx_name = _as_xlsx(filename, content)
    workbook = load_workbook(io.BytesIO(xlsx_content))
    if "survey" not in workbook.sheetnames:
        raise XlsFormError("The XLSForm has no 'survey' sheet.")

    survey = workbook["survey"]
    header_row = None
    columns = {}
    for row in range(1, min(survey.max_row, 10) + 1):
        values = {
            str(survey.cell(row=row, column=column).value).strip().lower(): column
            for column in range(1, survey.max_column + 1)
            if survey.cell(row=row, column=column).value
        }
        if "type" in values and "name" in values:
            header_row = row
            columns = values
            break
    if header_row is None:
        raise XlsFormError("The XLSForm survey sheet has no type/name header row.")

    label_column = columns.get("label")
    if label_column is None:
        label_column = next(
            (column for name, column in columns.items() if name.startswith("label")),
            None,
        )
    if label_column is None:
        raise XlsFormError("The XLSForm survey sheet has no label column.")
    label_header = str(survey.cell(row=header_row, column=label_column).value or "")
    dari = any(token in label_header.lower() for token in _DARI_LABEL_TOKENS)

    name_column = columns["name"]
    establishment_row = None
    details_present = False
    for row in range(header_row + 1, survey.max_row + 1):
        value = survey.cell(row=row, column=name_column).value
        if value == "establishment_id":
            establishment_row = row
        elif isinstance(value, str) and value.startswith("mandi_est_"):
            details_present = True

    appearance = _ensure_column(survey, header_row, columns, "appearance")
    required = _ensure_column(survey, header_row, columns, "required")
    calculation = _ensure_column(survey, header_row, columns, "calculation")
    relevant = _ensure_column(survey, header_row, columns, "relevant")

    if establishment_row is None:
        survey.insert_rows(header_row + 1)
        establishment_row = header_row + 1
        added_establishment = True
        values = {
            "type": "select_one_from_file establishments.csv",
            "name": "establishment_id",
            "label": _establishment_label(label_header),
            "appearance": "search",
            "required": "yes",
        }
        for key, value in values.items():
            column = label_column if key == "label" else columns.get(key)
            if column is not None:
                survey.cell(row=establishment_row, column=column, value=value)
    else:
        added_establishment = False

    if details_present:
        if not added_establishment:
            return xlsx_content, xlsx_name
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue(), xlsx_name

    detail_rows = [
        {
            "type": "begin_group",
            "name": "mandi_est_details",
            "label": "معلومات تأسیسات" if dari else "Establishment details",
            "appearance": "field-list",
        }
    ]
    for key, english, dari_label in ESTABLISHMENT_DETAIL_FIELDS:
        calculate_name = f"mandi_est_{key}"
        detail_rows.append(
            {
                "type": "calculate",
                "name": calculate_name,
                "calculation": f"pulldata('establishments', '{key}', 'name', ${{establishment_id}})",
            }
        )
        detail_rows.append(
            {
                "type": "note",
                "name": f"{calculate_name}_note",
                "label": f"{dari_label if dari else english}: ${{{calculate_name}}}",
                "relevant": f"string-length(${{{calculate_name}}}) > 0",
            }
        )
    detail_rows.append({"type": "end_group"})
    survey.insert_rows(establishment_row + 1, amount=len(detail_rows))
    for offset, values in enumerate(detail_rows, start=1):
        for key, value in values.items():
            column = label_column if key == "label" else columns.get(key)
            if column is not None:
                survey.cell(row=establishment_row + offset, column=column, value=value)

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue(), xlsx_name


def read_checklist_metadata(filename, content):
    """Read checklist defaults without executing formulas or changing the file."""
    from zipfile import BadZipFile

    xlsx_content, _ = _as_xlsx(filename, content)
    try:
        workbook = load_workbook(io.BytesIO(xlsx_content), read_only=True, data_only=True)
    except (BadZipFile, ValueError, OSError) as exc:
        raise XlsFormError("Could not read the XLSForm workbook.") from exc
    try:
        if "survey" not in workbook.sheetnames:
            raise XlsFormError("The XLSForm has no 'survey' sheet.")
        metadata = {}
        if "settings" in workbook.sheetnames:
            rows = workbook["settings"].iter_rows(values_only=True)
            headers = None
            for row in rows:
                if any(value is not None for value in row):
                    headers = [str(value or "").strip().lower() for value in row]
                    break
            if headers:
                for row in rows:
                    if any(value is not None for value in row):
                        metadata = {
                            key: str(value).strip()
                            for key, value in zip(headers, row)
                            if key and value is not None
                        }
                        break
        result = {
            "name": metadata.get("form_title") or Path(filename).stem,
            "code": metadata.get("form_id", ""),
        }
        # Establishment type is a Mandi extension, not a standard XLSForm setting.
        kind = metadata.get("establishment_kind", "").lower()
        if kind and len(kind) <= 20 and all(char.isascii() and (char.isalnum() or char in "-_") for char in kind):
            result["establishment_kind"] = kind
        return result
    finally:
        workbook.close()


def uses_establishment_type_filter(workbook):
    """True when the survey filters its establishment choice by a type question."""
    if "survey" not in workbook.sheetnames:
        return False
    survey = workbook["survey"]
    header_row = None
    columns = {}
    for row in range(1, min(survey.max_row, 10) + 1):
        values = {
            str(survey.cell(row=row, column=column).value).strip().lower(): column
            for column in range(1, survey.max_column + 1)
            if survey.cell(row=row, column=column).value
        }
        if "type" in values and "name" in values:
            header_row = row
            columns = values
            break
    if header_row is None or "choice_filter" not in columns:
        return False
    filter_column = columns["choice_filter"]
    for row in range(header_row + 1, survey.max_row + 1):
        value = survey.cell(row=row, column=filter_column).value
        if value and "establishment_type" in str(value):
            return True
    return False


def set_form_title(content, title):
    """Set the deployment copy's title while preserving other form settings."""
    workbook = load_workbook(io.BytesIO(content))
    try:
        sheet = workbook["settings"] if "settings" in workbook.sheetnames else workbook.create_sheet("settings")
        header_row = next((row for row in range(1, sheet.max_row + 1)
                           if any(cell.value is not None for cell in sheet[row])), 1)
        title_column = next((cell.column for cell in sheet[header_row]
                             if str(cell.value or "").strip().lower() == "form_title"), None)
        if title_column is None:
            title_column = sheet.max_column + 1 if any(cell.value is not None for cell in sheet[header_row]) else 1
            sheet.cell(header_row, title_column, "form_title")
        value_row = next((row for row in range(header_row + 1, sheet.max_row + 1)
                          if any(cell.value is not None for cell in sheet[row])), header_row + 1)
        cell = sheet.cell(value_row, title_column)
        cell.value = title
        cell.data_type = "s"
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()
    finally:
        workbook.close()
