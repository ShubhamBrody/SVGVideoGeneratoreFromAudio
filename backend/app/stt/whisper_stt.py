"""Whisper transcription with a graceful OpenAI-API fallback.

Primary path uses ``faster-whisper`` (install via requirements-whisper.txt). If it
is not available, we fall back to OpenAI's hosted transcription when an API key is
configured. Otherwise a clear ``STTUnavailable`` is raised so the API can return a
helpful 503.
"""
from __future__ import annotations

import io
import os
import tempfile
from functools import lru_cache

from app.config import get_settings


class STTUnavailable(RuntimeError):
    """Raised when no speech-to-text backend is available."""


@lru_cache
def _load_model():
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:  # not installed / no wheel
        raise STTUnavailable(
            "Whisper is not installed. Run: pip install -r requirements-whisper.txt "
            "(or set OPENAI_API_KEY to use hosted transcription)."
        ) from exc

    settings = get_settings()
    device = settings.whisper_device
    if device == "auto":
        device = "cpu"
    return WhisperModel(
        settings.whisper_model,
        device=device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe_bytes(data: bytes, suffix: str = ".webm") -> tuple[str, float | None, str | None]:
    """Transcribe audio bytes with faster-whisper. Blocking — call in a thread."""
    model = _load_model()
    tmp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(data)
        tmp_path = handle.name
    try:
        segments, info = model.transcribe(tmp_path, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text, getattr(info, "duration", None), getattr(info, "language", None)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def openai_transcribe(data: bytes, filename: str) -> tuple[str, float | None, str | None]:
    """Fallback transcription through the OpenAI audio API."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise STTUnavailable("No local Whisper and no OPENAI_API_KEY configured.")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        timeout=settings.llm_timeout,
    )
    stream = io.BytesIO(data)
    stream.name = filename or "audio.webm"
    try:
        resp = await client.audio.transcriptions.create(model="whisper-1", file=stream)
    except Exception as exc:
        raise STTUnavailable(f"OpenAI transcription failed: {exc}") from exc
    return (getattr(resp, "text", "") or "").strip(), None, None
