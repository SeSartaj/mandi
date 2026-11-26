from django.test import SimpleTestCase

from apps.integrations.submissions import (
    extract_scores,
    form_schema,
    submission_answers,
)

ASSET = {
    "content": {
        "survey": [
            {
                "name": "establishment_id",
                "type": "select_one_from_file",
                "label": ["تأسیسات", "Establishment"],
            },
            {"name": "q2_1", "type": "select_one yn", "label": ["جواز موجود است؟"]},
            {"name": "q2_2", "type": "select_one yn", "label": ["مکتوب نصب است؟"]},
            {"name": "notes", "type": "text", "label": ["ملاحظات"]},
            {"name": "score_license", "type": "calculate"},
            {"name": "title_license", "type": "calculate"},
        ],
        "choices": [
            {"list_name": "yn", "name": "1", "label": ["۱ – تکمیل"]},
            {"list_name": "yn", "name": "0", "label": ["۰ – نخیر"]},
            {"list_name": "yn", "name": "2", "label": ["تطبیق نشد"]},
        ],
    }
}

SUBMISSION = {
    "_id": 9,
    "_submission_time": "2026-11-08T09:00:00",
    "establishment_id": "4f6a2f6e-0000-0000-0000-000000000000",
    "q2_1": "1",
    "q2_2": "2",
    "notes": "یادداشت",
    "score_license": "1",
    "max_license": "4",
    "pct_license": "25.0",
    "title_license": "۲. جواز فعالیت",
    "score_total": "1",
    "max_total": "4",
    "result_pct": "25.0",
}


class EstablishmentLinkTests(SimpleTestCase):
    """A submission must find its establishment whether the question is
    top level or inside a group (``visit/establishment_id``)."""

    def normalize(self, answers):
        from apps.integrations.odk import OdkProvider

        return OdkProvider.normalize(
            {
                "__id": "sub-1",
                "__system": {"submissionDate": "2026-11-26T08:00:00.000Z"},
                **answers,
            }
        )

    def test_top_level_question_resolves(self):
        remote = self.normalize({"establishment_id": "uuid-top"})
        self.assertEqual(remote.establishment_id, "uuid-top")

    def test_grouped_question_resolves(self):
        remote = self.normalize({"visit": {"establishment_id": "uuid-grouped"}})
        self.assertEqual(remote.establishment_id, "uuid-grouped")

    def test_missing_question_returns_empty(self):
        self.assertEqual(self.normalize({"visit": {"other": "1"}}).establishment_id, "")


class FormSchemaTests(SimpleTestCase):
    def test_labels_and_choices_use_the_default_translation(self):
        schema = form_schema(ASSET)

        self.assertEqual(schema["labels"]["establishment_id"], "تأسیسات")
        self.assertEqual(schema["labels"]["q2_1"], "جواز موجود است؟")
        self.assertEqual(schema["choices"]["q2_1"]["1"], "۱ – تکمیل")

    def test_missing_asset_returns_empty_schema(self):
        self.assertEqual(
            form_schema(None),
            {
                "labels": {},
                "choices": {},
                "types": {},
                "paths": {},
                "groups": {},
                "order": [],
            },
        )

    def test_deployed_select_nodes_use_select_from_list_name(self):
        asset = {
            "content": {
                "survey": [
                    {
                        "name": "q2_1",
                        "type": "select_one",
                        "select_from_list_name": "yn",
                        "label": ["سوال"],
                        "$xpath": "sec2/q2_1",
                    }
                ],
                "choices": [{"list_name": "yn", "name": "1", "label": ["۱ – تکمیل"]}],
            }
        }

        schema = form_schema(asset)

        self.assertEqual(schema["choices"]["q2_1"], {"1": "۱ – تکمیل"})


class ExtractScoresTests(SimpleTestCase):
    def test_sections_use_the_form_title_and_percentages(self):
        scores = extract_scores(SUBMISSION)

        self.assertEqual(len(scores["sections"]), 1)
        section = scores["sections"][0]
        self.assertEqual(section["key"], "license")
        self.assertEqual(section["label"], "۲. جواز فعالیت")
        self.assertEqual(section["score"], 1.0)
        self.assertEqual(section["max"], 4.0)
        self.assertEqual(section["percent"], 25.0)
        self.assertEqual(scores["percent"], 25.0)
        self.assertEqual(scores["score"], 1.0)
        self.assertEqual(scores["max"], 4.0)

    def test_percentage_is_calculated_when_absent(self):
        data = {"score_label": "3", "max_label": "4"}

        section = extract_scores(data)["sections"][0]

        self.assertEqual(section["percent"], 75.0)
        self.assertEqual(section["label"], "لیبل ادویه")

    def test_unknown_sections_fall_back_to_humanized_keys(self):
        data = {"score_custom_area": "2", "max_custom_area": "4"}

        section = extract_scores(data)["sections"][0]

        self.assertEqual(section["label"], "Custom area")

    def test_submission_without_calculations_has_no_sections(self):
        self.assertEqual(extract_scores({"_id": 1})["sections"], [])

    def test_sections_follow_form_order_not_json_order(self):
        data = {
            "scoring/score_staff": "5",
            "scoring/score_license": "4",
            "scoring/score_legality": "3",
            "scoring/score_label": "2",
            "scoring/max_staff": "5",
            "scoring/max_license": "5",
            "scoring/max_legality": "5",
            "scoring/max_label": "4",
        }

        keys = [section["key"] for section in extract_scores(data)["sections"]]

        self.assertEqual(keys, ["license", "legality", "label", "staff"])

    def test_explicit_order_and_numbered_titles_win(self):
        data = {
            "scoring/score_alpha": "1",
            "scoring/score_beta": "1",
            "scoring/max_alpha": "2",
            "scoring/max_beta": "2",
            "scoring/order_beta": "2",
            "scoring/order_alpha": "3",
            "scoring/title_beta": "۲. بخش دوم",
            "scoring/title_alpha": "۳. بخش سوم",
        }

        sections = extract_scores(data)["sections"]

        self.assertEqual([s["label"] for s in sections], ["۲. بخش دوم", "۳. بخش سوم"])


class SubmissionAnswersTests(SimpleTestCase):
    def test_answers_are_labelled_and_choices_translated(self):
        answers = submission_answers(SUBMISSION, form_schema(ASSET))

        by_name = {answer["name"]: answer for answer in answers}
        self.assertNotIn("_id", by_name)
        self.assertNotIn("establishment_id", by_name)
        self.assertNotIn("score_license", by_name)
        self.assertNotIn("title_license", by_name)
        self.assertNotIn("max_license", by_name)
        self.assertNotIn("result_pct", by_name)
        self.assertNotIn("score_total", by_name)
        self.assertEqual(by_name["q2_1"]["label"], "جواز موجود است؟")
        self.assertEqual(by_name["q2_1"]["display"], "۱ – تکمیل")
        self.assertEqual(by_name["q2_2"]["display"], "تطبیق نشد")
        self.assertEqual(by_name["notes"]["display"], "یادداشت")

    def test_answers_without_schema_are_humanized(self):
        answers = submission_answers({"some_question": "yes"}, {})

        self.assertEqual(answers[0]["label"], "Some question")
        self.assertEqual(answers[0]["display"], "yes")

    def test_grouped_and_repeated_paths_are_normalized(self):
        data = {
            "general/pharmacy_name": "دواخانه نمونه",
            "sec2/q2_1": "1",
            "scoring/score_license": "3",
            "scoring/max_license": "5",
            "scoring/pct_license": "60",
            "scoring/title_license": "۲. جواز فعالیت",
            "scoring/score_total": "3",
            "scoring/max_total": "5",
            "scoring/result_pct": "60",
            "samples[1]/sample_trade_name": "Paracetamol",
        }

        answers = submission_answers(data, form_schema(ASSET))
        scores = extract_scores(data)

        by_name = {answer["name"]: answer for answer in answers}
        self.assertEqual(by_name["q2_1"]["display"], "۱ – تکمیل")
        self.assertEqual(by_name["pharmacy_name"]["display"], "دواخانه نمونه")
        self.assertEqual(by_name["sample_trade_name"]["display"], "Paracetamol")
        self.assertNotIn("score_license", by_name)
        self.assertEqual(scores["sections"][0]["label"], "۲. جواز فعالیت")
        self.assertEqual(scores["percent"], 60.0)
