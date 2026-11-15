"""Convert AMR recordings to a browser-playable stream without changing originals."""
import subprocess
import tempfile
from pathlib import Path

from .kobo import KoboError


def browser_audio(response):
    output = tempfile.TemporaryFile()
    try:
        with tempfile.TemporaryDirectory(prefix="mandi-audio-") as directory:
            source = Path(directory) / "recording.amr"
            try:
                with source.open("wb") as target:
                    for chunk in response.iter_content(chunk_size=65536):
                        target.write(chunk)
            finally:
                response.close()
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-i", str(source),
                 "-vn", "-f", "mp3", "pipe:1"],
                stdout=output, stderr=subprocess.PIPE, check=True, timeout=120,
            )
        output.seek(0)
        return output
    except (OSError, subprocess.SubprocessError) as exc:
        output.close()
        raise KoboError("Could not prepare audio playback. Check that FFmpeg is installed and the recording is valid.") from exc
    except BaseException:
        output.close()
        raise
