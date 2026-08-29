"""ffmpeg helpers: build the narration track and mux audio onto the recorded video."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True)


def make_silence(seconds: float, path: str | Path) -> Path:
    path = Path(path)
    _run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{max(0.05, seconds):.3f}", "-b:a", "48k", str(path),
    ])
    return path


def concat_narration(clips: list[str | Path], out: str | Path, pause: float = 0.6) -> Path:
    """Concatenate beat clips with a pause after each, so the track aligns with
    the animation's beat slots (each beat = audio + pause)."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    silence = out.parent / "_silence.mp3"
    make_silence(pause, silence)

    list_file = out.parent / "_concat.txt"
    lines: list[str] = []
    for clip in clips:
        lines.append(f"file '{Path(clip).resolve().as_posix()}'")
        lines.append(f"file '{silence.resolve().as_posix()}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:a", "libmp3lame", "-ar", "24000", "-ac", "1", str(out),
    ])
    return out


def mux(video: str | Path, audio: str | Path, out: str | Path) -> Path:
    """Combine a (silent) video with a narration track into an H.264/AAC MP4."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(out),
    ])
    return out
