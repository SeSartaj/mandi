from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from django.core import signing
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.integrations import documents

CONNECTION = dict(
    LICENSING_BASE_URL="http://licensing.test",
    LICENSING_REGISTRATION_API_KEY="secret-key",
    LICENSING_TIMEOUT=3,
    SURVEY_BASE_URL="http://survey.test:8005",
    SURVEY_REGISTRATION_API_KEY="survey-key",
    SURVEY_TIMEOUT=3,
)

PDF = b"%PDF-1.7 data"


def upstream(body=PDF, status=200, headers=None):
    response = Mock(status_code=status, is_redirect=False)
    response.headers = {
        "Content-Type": "application/pdf",
        "Content-Length": str(len(body)),
        **(headers or {}),
    }
    chunks = [body, b""]
    response.raw.read.side_effect = lambda *args, **kwargs: chunks.pop(0)
    return response


def token_of(path):
    return parse_qs(urlsplit(path).query)["token"][0]


@override_settings(**CONNECTION)
class DocumentRewriteTests(SimpleTestCase):
    def test_upstream_documents_become_signed_mandi_links(self):
        detail = {
            "sections": [
                {
                    "title": "Attachments",
                    "fields": [
                        {"label": "License document", "value": "http://licensing.test/media/a.pdf"},
                        {
                            "label": "Extra attachments",
                            "value": ["http://survey.test:8005/media/b.pdf"],
                        },
                        {"label": "Website", "value": "http://elsewhere.test/x.pdf"},
                        {"label": "Name", "value": "Shop"},
                    ],
                }
            ]
        }
        documents.rewrite(detail, "licensing")
        fields = detail["sections"][0]["fields"]
        self.assertTrue(
            fields[0]["value"].startswith("sources/licensing/document/?token=")
        )
        self.assertTrue(
            fields[1]["value"][0].startswith("sources/survey/document/?token=")
        )
        self.assertEqual(fields[2]["value"], "http://elsewhere.test/x.pdf")
        self.assertEqual(fields[3]["value"], "Shop")

    def test_relative_document_uses_the_profile_source(self):
        detail = {
            "sections": [
                {"title": "Attachments", "fields": [{"label": "Stamp", "value": "/media/stamp.png"}]}
            ]
        }
        documents.rewrite(detail, "licensing")
        self.assertIn(
            "sources/licensing/document/", detail["sections"][0]["fields"][0]["value"]
        )

    def test_unconfigured_source_is_left_alone(self):
        detail = {
            "sections": [
                {
                    "title": "Attachments",
                    "fields": [{"label": "Stamp", "value": "http://licensing.test/media/x.png"}],
                }
            ]
        }
        with override_settings(LICENSING_BASE_URL="", LICENSING_REGISTRATION_API_KEY=""):
            documents.rewrite(detail, "archive")
        self.assertEqual(
            detail["sections"][0]["fields"][0]["value"],
            "http://licensing.test/media/x.png",
        )


@override_settings(**CONNECTION)
class DocumentTokenTests(SimpleTestCase):
    def test_signed_link_round_trips(self):
        path = documents.proxy_path("survey", "http://survey.test:8005/media/a.pdf")
        self.assertEqual(
            documents.from_token(token_of(path)),
            ("survey", "http://survey.test:8005/media/a.pdf"),
        )

    def test_nonsense_token_is_rejected(self):
        with self.assertRaises(PermissionDenied):
            documents.from_token("not-a-token")

    def test_expired_token_is_rejected(self):
        payload = {"source": "licensing", "url": "http://licensing.test/media/a.pdf"}
        with patch("django.core.signing.time.time", return_value=1000):
            stale = signing.TimestampSigner(salt=documents.SALT).sign_object(payload)
        with patch("django.core.signing.time.time", return_value=1000 + 7200):
            with self.assertRaises(PermissionDenied):
                documents.from_token(stale)

    def test_unknown_source_in_token_is_rejected(self):
        forged = signing.dumps({"source": "archive", "url": "http://licensing.test/a.pdf"}, salt=documents.SALT)
        with self.assertRaises(PermissionDenied):
            documents.from_token(forged)


@override_settings(**CONNECTION)
class DocumentStreamTests(TestCase):
    def test_key_is_attached_and_file_streamed(self):
        with patch(
            "apps.integrations.documents.requests.get", return_value=upstream()
        ) as get:
            response = documents.response("licensing", "http://licensing.test/media/a.pdf")
            body = b"".join(response.streaming_content)
        self.assertEqual(body, PDF)
        self.assertEqual(get.call_args.args[0], "http://licensing.test/media/a.pdf")
        self.assertEqual(get.call_args.kwargs["headers"], {"X-API-KEY": "secret-key"})
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("inline", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Content-Length"], str(len(PDF)))

    def test_foreign_host_is_refused(self):
        with patch("apps.integrations.documents.requests.get") as get:
            with self.assertRaises(PermissionDenied):
                documents.response("licensing", "http://internal.test/secret.pdf")
        get.assert_not_called()

    def test_relative_path_is_resolved_against_the_source(self):
        with patch(
            "apps.integrations.documents.requests.get", return_value=upstream()
        ) as get:
            documents.response("licensing", "/media/a.pdf")
        self.assertEqual(get.call_args.args[0], "http://licensing.test/media/a.pdf")

    def test_redirect_inside_the_source_is_followed(self):
        redirect = Mock(status_code=302, is_redirect=True)
        redirect.headers = {"Location": "/media/a.pdf"}
        with patch(
            "apps.integrations.documents.requests.get",
            side_effect=[redirect, upstream()],
        ) as get:
            response = documents.response("licensing", "http://licensing.test/media")
            b"".join(response.streaming_content)
        self.assertEqual(get.call_args.args[0], "http://licensing.test/media/a.pdf")

    def test_redirect_off_the_source_is_refused(self):
        redirect = Mock(status_code=302, is_redirect=True)
        redirect.headers = {"Location": "http://elsewhere.test/x.pdf"}
        with patch("apps.integrations.documents.requests.get", return_value=redirect):
            with self.assertRaises(PermissionDenied):
                documents.response("licensing", "http://licensing.test/media/a.pdf")

    def test_rejected_key_is_reported(self):
        with patch("apps.integrations.documents.requests.get", return_value=upstream(status=403)):
            with self.assertRaises(documents.DocumentError) as error:
                documents.response("licensing", "http://licensing.test/media/a.pdf")
        self.assertIn("integration key", str(error.exception))

    def test_missing_document_is_not_found(self):
        with patch("apps.integrations.documents.requests.get", return_value=upstream(status=404)):
            with self.assertRaises(NotFound):
                documents.response("licensing", "http://licensing.test/media/a.pdf")

    def test_oversized_document_is_refused(self):
        with patch("apps.integrations.documents.requests.get", return_value=upstream()):
            with patch.object(documents, "MAX_BYTES", 5):
                with self.assertRaises(documents.DocumentError):
                    documents.response("licensing", "http://licensing.test/media/a.pdf")


@override_settings(**CONNECTION)
class DocumentEndpointTests(TestCase):
    def test_signed_link_streams_without_a_session(self):
        path = "/api/v1/" + documents.proxy_path(
            "licensing", "http://licensing.test/media/a.pdf"
        )
        with patch("apps.integrations.documents.requests.get", return_value=upstream()):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), PDF)

    def test_anonymous_unsigned_request_is_denied(self):
        response = self.client.get(
            "/api/v1/sources/licensing/document/",
            {"url": "http://licensing.test/media/a.pdf"},
        )
        self.assertEqual(response.status_code, 403)

    def test_tampered_token_is_denied(self):
        path = (
            "/api/v1/"
            + documents.proxy_path("licensing", "http://licensing.test/media/a.pdf")
            + "x"
        )
        response = self.client.get(path)
        self.assertEqual(response.status_code, 403)
