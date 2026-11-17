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

    def test_reads_title_id_version_and_explicit_kind(self):
        self.assertEqual(self.metadata([
            ["form_title", "form_id", "version", "establishment_kind"],
            ["بازرسی", "inspection", 20261110, "importer"],
        ]), {"name": "بازرسی", "code": "inspection", "version": "20261110", "establishment_kind": "importer"})

    def test_missing_settings_uses_filename_without_guessing_type_or_version(self):
        self.assertEqual(self.metadata(), {"name": "Checklist", "code": "", "version": ""})

    def test_empty_settings_and_invalid_kind(self):
        self.assertEqual(self.metadata([])["name"], "Checklist")
        self.assertNotIn("establishment_kind", self.metadata([
            ["form_title", "establishment_kind"], ["Title", "invalid type!"],
        ]))

    def test_custom_type_metadata_is_supported(self):
        self.assertEqual(self.metadata([["establishment_kind"], ["laboratory"]])["establishment_kind"], "laboratory")

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

    def test_new_and_existing_deployments_use_saved_name_in_every_upload(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from apps.integrations.kobo import deploy_checklist_to_kobo

        original = make_workbook(["type", "name", "label"], [["text", "name", "Name"]])
        for existing in (False, True):
            with self.subTest(existing=existing):
                checklist = SimpleNamespace(
                    name="User chosen title", kobo_asset_uid="asset" if existing else "",
                    xlsform=SimpleNamespace(name="template.xlsx", open=lambda mode: BytesIO(original)),
                )
                asset = {"uid": "asset", "version_id": "v1"}
                with patch("apps.integrations.kobo.get_asset", return_value=asset), \
                     patch("apps.integrations.kobo.import_xlsform", return_value="asset") as importer, \
                     patch("apps.integrations.kobo._request") as request, \
                     patch("apps.integrations.kobo.deploy_asset", return_value={"deployment_status": "deployed"}):
                    deploy_checklist_to_kobo(checklist)
                    self.assertEqual(importer.call_count, 1 if existing else 2)
                    for call in importer.call_args_list:
                        workbook = load_workbook(BytesIO(call.args[0].getvalue()))
                        self.assertEqual(workbook["settings"]["A2"].value, checklist.name)
                        self.assertEqual(call.args[2], checklist.name)
                    request.assert_called_once_with("PATCH", "/api/v2/assets/asset/", json={"name": checklist.name})
