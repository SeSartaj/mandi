import io
import shutil
import wave
from unittest import skipUnless
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from apps.integrations.audio import browser_audio
from apps.integrations.kobo import KoboError


class AudioPlaybackTests(SimpleTestCase):
    @skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for playback conversion")
    def test_transcoding_returns_mp3_and_closes_upstream(self):
        recording = io.BytesIO()
        with wave.open(recording, "wb") as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(8000)
            sound.writeframes(b"\x00\x00" * 800)
        upstream = Mock()
        upstream.iter_content.return_value = [recording.getvalue()]
        converted = browser_audio(upstream)
        try:
            self.assertTrue(converted.read().startswith(b"ID3"))
        finally:
            converted.close()
        upstream.close.assert_called_once()

    def test_missing_converter_is_readable_and_closes_upstream(self):
        upstream = Mock()
        upstream.iter_content.return_value = [b"#!AMR\n"]
        with patch("apps.integrations.audio.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(KoboError):
                browser_audio(upstream)
        upstream.close.assert_called_once()

    def test_playback_endpoint_converts_amr_and_original_endpoint_preserves_it(self):
        from types import SimpleNamespace
        from rest_framework.test import APIRequestFactory, force_authenticate
        from config.api.submissions import KoboSubmissionAttachment
        attachment = {"basename": "background.amr", "mimetype": "audio/amr"}
        for playback in (False, True):
            with self.subTest(playback=playback):
                upstream = Mock(headers={})
                upstream.iter_content.return_value = [b"#!AMR\n"]
                request = APIRequestFactory().get("/attachment/", {"playback": "1"} if playback else {})
                force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
                with patch("config.api.submissions.integrations.submission_attachment", return_value=(attachment, upstream)), \
                     patch("apps.integrations.audio.browser_audio", return_value=io.BytesIO(b"ID3 audio")) as converter:
                    response = KoboSubmissionAttachment.as_view()(request, pk=1, index=0)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response["Content-Type"], "audio/mpeg" if playback else "audio/amr")
                    self.assertEqual(converter.call_count, 1 if playback else 0)
                    list(response.streaming_content)
                    response.close()
