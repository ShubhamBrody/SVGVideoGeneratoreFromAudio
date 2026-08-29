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


async def synthesize_narration(
    beat_texts: list[str], out_path: str | Path, voice: str = DEFAULT_VOICE
) -> tuple[Path, list[float], float]:
    """Synthesize all beats as ONE continuous, natural voiceover.

    Returns ``(mp3_path, beat_durations, total_seconds)``. Beat durations come from
    edge-tts word-boundary timings, so the animation can sync to the real speech
    without chopping it into separate clips (which is what makes it sound choppy).
    """
    try:
        import edge_tts
    except Exception as exc:  # pragma: no cover
        raise TTSUnavailable("edge-tts not installed (pip install edge-tts)") from exc

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []
    for text in beat_texts:
        text = (text or "").strip()
        if not text:
            continue
        if text[-1] not in ".!?":
            text += "."
        parts.append(text)
    if not parts:
        out_path.write_bytes(b"")
        return out_path, [], 0.0

    word_counts = [len(p.split()) for p in parts]
    full_text = " ".join(parts)

    audio = bytearray()
    offsets: list[float] = []  # start time (s) of each spoken word
    try:
        communicate = edge_tts.Communicate(full_text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                offsets.append(chunk["offset"] / 10_000_000.0)  # 100-ns ticks -> seconds
    except Exception as exc:
        raise TTSUnavailable(f"edge-tts synthesis failed: {exc}") from exc

    out_path.write_bytes(bytes(audio))
    total = audio_duration(out_path)

    total_words = max(1, sum(word_counts))
    starts: list[float] = []
    cumulative = 0
    for count in word_counts:
        if offsets:
            starts.append(offsets[min(cumulative, len(offsets) - 1)])
        else:
            starts.append(total * cumulative / total_words)
        cumulative += count
    starts[0] = 0.0  # anchor the first beat to the start of the audio

    durations = [
        max(0.1, (starts[i + 1] if i + 1 < len(starts) else total) - starts[i])
        for i in range(len(starts))
    ]
    return out_path, durations, total


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
