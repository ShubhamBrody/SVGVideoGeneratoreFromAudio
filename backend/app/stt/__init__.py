"""Speech-to-text."""
from app.stt.whisper_stt import STTUnavailable, openai_transcribe, transcribe_bytes

__all__ = ["STTUnavailable", "transcribe_bytes", "openai_transcribe"]
