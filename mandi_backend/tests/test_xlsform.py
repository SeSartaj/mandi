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

    def test_existing_establishment_question_gets_detail_rows_without_duplication(self):
        content = make_workbook(
            ["type", "name", "label"],
            [
                ["select_one_from_file establishments.csv", "establishment_id", "Establishment"],
                ["text", "respondent_name", "Respondent name"],
            ],
        )

        updated, _ = add_establishment_question("form.xlsx", content)

        rows = read_survey(updated)
        names = [row["name"] for row in rows]
        self.assertEqual(names.count("establishment_id"), 1)
        self.assertIn("mandi_est_province", names)
        self.assertIn("mandi_est_owner", names)
        self.assertNotEqual(updated, content)

    def test_detail_rows_use_pulldata_and_hide_empty_values(self):
        content = make_workbook(
            ["type", "name", "label"],
            [["text", "respondent_name", "Respondent name"]],
        )

        updated, _ = add_establishment_question("form.xlsx", content)
        rows = {row["name"]: row for row in read_survey(updated)}

        self.assertEqual(rows["mandi_est_details"]["type"], "begin_group")
        self.assertEqual(rows["mandi_est_details"]["appearance"], "field-list")
        calculate = rows["mandi_est_license_number"]
        self.assertEqual(calculate["type"], "calculate")
        self.assertIn("pulldata('establishments', 'license_number', 'name'", calculate["calculation"])
        note = rows["mandi_est_license_number_note"]
        self.assertEqual(note["type"], "note")
        self.assertIn("${mandi_est_license_number}", note["label"])
        self.assertIn("string-length(${mandi_est_license_number}) > 0", note["relevant"])

    def test_missing_survey_sheet_is_rejected(self):
        content = make_workbook(["type", "name", "label"], [], sheet_name="Sheet1")

        with self.assertRaises(XlsFormError):
            add_establishment_question("form.xlsx", content)

    def survey_names(self, content):
        return [row["name"] for row in read_survey(content)]

    def with_settings(self, value):
        workbook = load_workbook(BytesIO(make_workbook(
            ["type", "name", "label"], [["text", "respondent_name", "Name"]]
        )))
        settings = workbook.create_sheet("settings")
        settings.append(["form_id", "mandi_establishment"])
        settings.append(["test", value])
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_none_mode_skips_establishment_and_details(self):
        updated, _ = add_establishment_question("form.xlsx", self.with_settings("none"))
        names = self.survey_names(updated)
        self.assertNotIn("establishment_id", names)
        self.assertNotIn("mandi_est_details", names)

    def test_optional_mode_does_not_require_establishment(self):
        updated, _ = add_establishment_question("form.xlsx", self.with_settings("optional"))
        rows = {row["name"]: row for row in read_survey(updated)}
        self.assertIn("establishment_id", rows)
        self.assertIn(rows["establishment_id"]["required"], (None, ""))


class ChecklistMetadataTests(SimpleTestCase):
    def metadata(self, settings_rows=None):
        from apps.integrations.xlsform import read_checklist_metadata
        workbook = Workbook()
        workbook.active.title = "survey"
        workbook.active.append(["type", "name", "label"])
        if settings_rows is not None:
            sheet = workbook.create_sheet("settings")
            for row in settings_rows:
                sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        return read_checklist_metadata("Checklist.xlsx", output.getvalue())

    def test_reads_title_and_form_id(self):
        self.assertEqual(self.metadata([
            ["form_title", "form_id", "version", "establishment_kind"],
            ["بازرسی", "inspection", 20261110, "importer"],
        ]), {"name": "بازرسی", "code": "inspection"})

    def test_missing_settings_uses_filename_without_guessing_type_or_version(self):
        self.assertEqual(self.metadata(), {"name": "Checklist", "code": ""})

    def test_establishment_kind_metadata_is_ignored(self):
        self.assertEqual(self.metadata([])["name"], "Checklist")
        self.assertNotIn("establishment_kind", self.metadata([
            ["form_title", "establishment_kind"], ["Title", "invalid type!"],
        ]))
        self.assertNotIn("establishment_kind", self.metadata([["establishment_kind"], ["laboratory"]]))

    def test_invalid_file_is_a_readable_error(self):
        from apps.integrations.xlsform import read_checklist_metadata
        with self.assertRaises(XlsFormError):
            read_checklist_metadata("broken.xlsx", b"not a workbook")


class ChecklistMetadataApiTests(SimpleTestCase):
    def test_upload_returns_metadata_without_creating_a_checklist(self):
        from types import SimpleNamespace
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.test import APIRequestFactory, force_authenticate
        from config.api.checklists import ChecklistMetadata

        upload = SimpleUploadedFile("example.xlsx", make_workbook(
            ["type", "name", "label"], [["text", "name", "Name"]],
        ))
        request = APIRequestFactory().post("/api/v1/checklists/metadata/", {"xlsform": upload})
        user = SimpleNamespace(is_authenticated=True, is_active=True, has_perm=lambda permission: True)
        force_authenticate(request, user=user)
        response = ChecklistMetadata.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "example")

    def test_reader_cannot_use_metadata_upload(self):
        from types import SimpleNamespace
        from rest_framework.test import APIRequestFactory, force_authenticate
        from config.api.checklists import ChecklistMetadata

        request = APIRequestFactory().post("/api/v1/checklists/metadata/", {})
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True, is_active=True, has_perm=lambda permission: False))
        self.assertEqual(ChecklistMetadata.as_view()(request).status_code, 403)


class DeploymentTitleTests(SimpleTestCase):
    def test_saved_name_overrides_template_title_and_preserves_settings(self):
        from apps.integrations.xlsform import set_form_title
        workbook = Workbook()
        workbook.active.title = "survey"
        settings = workbook.create_sheet("settings")
        settings.append(["form_title", "form_id", "version"])
        settings.append(["Template title", "stable_id", "20261110"])
        original = BytesIO()
        workbook.save(original)
        updated = load_workbook(BytesIO(set_form_title(original.getvalue(), "نام جدید")))
        self.assertEqual(list(updated["settings"].values), [
            ("form_title", "form_id", "version"), ("نام جدید", "stable_id", "20261110"),
        ])
        unchanged = load_workbook(BytesIO(original.getvalue()))
        self.assertEqual(unchanged["settings"]["A2"].value, "Template title")

    def test_missing_settings_get_title(self):
        from apps.integrations.xlsform import set_form_title
        original = make_workbook(["type", "name", "label"], [["text", "name", "Name"]])
        workbook = load_workbook(BytesIO(set_form_title(original, "Saved title")))
        self.assertEqual(list(workbook["settings"].values), [("form_title",), ("Saved title",)])
