"""Text-to-speech for narration.

Primary backend is ``edge-tts`` (Microsoft's free neural voices, no API key).
Falls back to Windows SAPI if edge-tts is unavailable/offline. Durations are
probed with ffprobe so the animation can be paced to the real voiceover length.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

DEFAULT_VOICE = "en-US-AriaNeural"


class TTSUnavailable(RuntimeError):
    pass


async def synthesize(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """Return MP3 audio bytes for ``text``."""
    text = (text or "").strip()
    if not text:
        return b""
    try:
        import edge_tts
    except Exception as exc:  # pragma: no cover
        raise TTSUnavailable("edge-tts not installed (pip install edge-tts)") from exc

    audio = bytearray()
    try:
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
    except Exception as exc:
        raise TTSUnavailable(f"edge-tts synthesis failed: {exc}") from exc
    return bytes(audio)


async def synthesize_to_file(text: str, path: str | Path, voice: str = DEFAULT_VOICE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(await synthesize(text, voice))
    return path


def audio_duration(path: str | Path) -> float:
    """Duration of an audio file in seconds, via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


async def synthesize_beats(
    texts: list[str], out_dir: str | Path, voice: str = DEFAULT_VOICE
) -> list[tuple[Path, float]]:
    """Synthesize each beat to its own MP3; return (path, duration) per beat."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[Path, float]] = []
    for i, text in enumerate(texts):
        clip = out_dir / f"beat_{i:03d}.mp3"
        await synthesize_to_file(text, clip, voice)
        results.append((clip, audio_duration(clip)))
    return results


async def list_voices(prefix: str = "en-") -> list[str]:
    try:
        import edge_tts

        voices = await edge_tts.list_voices()
    except Exception as exc:
        raise TTSUnavailable(str(exc)) from exc
    return sorted(v["ShortName"] for v in voices if v["ShortName"].startswith(prefix))


if __name__ == "__main__":  # quick manual check
    async def _demo() -> None:
        tmp = Path(tempfile.gettempdir()) / "tts_demo.mp3"
        await synthesize_to_file("A Kafka topic feeds three consumers.", tmp)
        print(tmp, f"{audio_duration(tmp):.2f}s", f"{tmp.stat().st_size} bytes")

    asyncio.run(_demo())
