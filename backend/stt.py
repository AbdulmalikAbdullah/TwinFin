"""Speech-to-text for the chat composer: Whisper (tiny, multilingual) on CPU.

Runs faster-whisper's `tiny` model   the multilingual one, so it transcribes both Arabic
and English   with int8 on CPU. faster-whisper decodes the browser's webm/opus blob itself
through bundled PyAV, so there is no system ffmpeg dependency.

Two rules, matching the rest of the backend:

  1. **Load once, lazily.** The model is ~75 MB and takes a few seconds to load the first
     time; we cache it so only the first transcription pays that cost.
  2. **Never surface a stack trace.** Anything that goes wrong raises `STTUnavailable`, which
     the endpoint turns into a friendly message   the user can always fall back to typing.
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache

from config import STT_COMPUTE_TYPE, STT_DEVICE, STT_MODEL

log = logging.getLogger(__name__)

# The languages we force-decode. Whisper-tiny's auto language detection is shaky on short
# clips, and the UI already declares the language, so we pass it through instead of guessing.
SUPPORTED = ("ar", "en")


class STTUnavailable(RuntimeError):
    """Raised when transcription cannot run (package missing, model load failed, bad audio).

    Callers catch this and return a friendly message rather than a 500 with a traceback.
    """


def is_available() -> bool:
    """Whether faster-whisper is importable. Used by /api/health and to hide the mic if not."""
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=1)
def _model():
    """Load and cache the Whisper model. First call downloads it (~75 MB) and loads it."""
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # noqa: BLE001
        raise STTUnavailable("faster-whisper is not installed") from exc

    log.info("Loading Whisper STT model %r on %s (%s)...", STT_MODEL, STT_DEVICE, STT_COMPUTE_TYPE)
    try:
        return WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE_TYPE)
    except Exception as exc:  # noqa: BLE001
        raise STTUnavailable(f"could not load Whisper model {STT_MODEL!r}: {exc}") from exc


def transcribe(audio: bytes, lang: str | None = None) -> str:
    """Transcribe a recorded audio blob to text.

    `audio` is the raw bytes of whatever the browser's MediaRecorder produced (usually
    webm/opus); PyAV inside faster-whisper decodes it. `lang` ("ar"/"en") is forced when
    given, otherwise Whisper auto-detects.
    """
    if not audio:
        raise STTUnavailable("no audio provided")

    model = _model()
    language = lang if lang in SUPPORTED else None

    try:
        segments, _info = model.transcribe(
            io.BytesIO(audio),
            language=language,
            beam_size=1,
            # Silero VAD trims silence so tiny doesn't hallucinate words into quiet gaps.
            vad_filter=True,
        )
        return "".join(segment.text for segment in segments).strip()
    except STTUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        raise STTUnavailable(f"transcription failed: {exc}") from exc
