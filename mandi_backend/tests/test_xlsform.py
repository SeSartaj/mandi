from io import BytesIO

from django.test import SimpleTestCase
from openpyxl import Workbook, load_workbook

from apps.integrations.xlsform import XlsFormError, add_establishment_question


def make_workbook(headers, rows, sheet_name="survey"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def read_survey(content):
    workbook = load_workbook(BytesIO(content))
    sheet = workbook["survey"]
    headers = [cell.value for cell in sheet[1]]
    return [dict(zip(headers, row)) for row in sheet.iter_rows(min_row=2, values_only=True)]


class AddEstablishmentQuestionTests(SimpleTestCase):
    def test_english_form_gets_english_label(self):
        content = make_workbook(
            ["type", "name", "label"],
            [["text", "respondent_name", "Respondent name"]],
        )

        updated, filename = add_establishment_question("form.xlsx", content)

        self.assertEqual(filename, "form.xlsx")
        first = read_survey(updated)[0]
        self.assertEqual(first["type"], "select_one_from_file establishments.csv")
        self.assertEqual(first["name"], "establishment_id")
        self.assertEqual(first["label"], "Establishment")
        self.assertEqual(first["appearance"], "search")
        self.assertEqual(first["required"], "yes")

    def test_multilingual_form_gets_label_in_its_label_column(self):
        content = make_workbook(
            ["type", "name", "label::Dari (fa)", "label::English (en)"],
            [["text", "pharmacy_name", "اسم دواخانه", "Pharmacy name"]],
        )

        updated, _ = add_establishment_question("form.xlsx", content)

        first = read_survey(updated)[0]
        self.assertEqual(first["name"], "establishment_id")
        self.assertEqual(first["label::Dari (fa)"], "تأسیسات")
        self.assertIsNone(first["label::English (en)"])

    def test_existing_establishment_question_is_not_duplicated(self):
        content = make_workbook(
            ["type", "name", "label"],
            [
                ["select_one_from_file establishments.csv", "establishment_id", "Establishment"],
                ["text", "respondent_name", "Respondent name"],
            ],
        )

        updated, _ = add_establishment_question("form.xlsx", content)

        names = [row["name"] for row in read_survey(updated)]
        self.assertEqual(names.count("establishment_id"), 1)
        self.assertEqual(updated, content)

    def test_missing_survey_sheet_is_rejected(self):
        content = make_workbook(["type", "name", "label"], [], sheet_name="Sheet1")

        with self.assertRaises(XlsFormError):
            add_establishment_question("form.xlsx", content)
