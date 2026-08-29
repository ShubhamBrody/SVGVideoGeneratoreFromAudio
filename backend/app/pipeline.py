"""End-to-end generation pipeline.

    topic/script -> LLM script -> director storyboard -> per-beat TTS
                 -> audio-synced scene + narration.mp3 -> (record MP4) -> (upload)

Run:  python -m app.pipeline "How a load balancer spreads traffic across servers"
Add   --record   to also render an MP4 (needs Playwright, see app/recorder.py).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

import httpx

from app import tts
from app.assets.foundry import forge_assets, forge_for_cast
from app.assets.registry import get_registry
from app.config import Settings, get_settings
from app.llm.gateway import build_gateway
from app.llm.prompts import build_director_prompt, build_script_prompt
from app.llm.providers import OllamaProvider, OpenAIProvider
from app.scene.camera import add_camera_moves
from app.scene.director import compile_storyboard, deterministic_storyboard, parse_storyboard
from app.scene.validator import validate_and_repair


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


async def _text_provider(settings: Settings):
    """A provider for plain-text (script) generation, honoring LLM_PROVIDER."""
    choice = (settings.llm_provider or "auto").lower()
    if choice != "openai":  # prefer local Ollama unless explicitly openai
        ollama = OllamaProvider(settings)
        if await ollama.available():
            return ollama
    if choice != "ollama" and settings.openai_api_key:
        try:
            provider = OpenAIProvider(settings)
            if await provider.available():
                return provider
        except Exception:
            pass
    return None


def _fallback_script(topic: str) -> str:
    subject = topic.strip().rstrip(".")
    return (f"Let's understand {subject}. First we set up the main components. "
            f"Then we see how they work together to serve a request. "
            f"A key event puts the system under pressure. "
            f"The system reacts and recovers, returning to a healthy state.")


async def generate_script(settings: Settings, topic: str) -> str:
    provider = await _text_provider(settings)
    if provider is None:
        return _fallback_script(topic)
    try:
        raw = await provider.complete("You are a technical explainer scriptwriter.", build_script_prompt(topic))
    except Exception:
        return _fallback_script(topic)
    script = raw.strip().strip('"').strip()
    return script or _fallback_script(topic)


async def _storyboard(gateway, registry, script: str, max_tokens: int | None = None):
    raw, provider = await gateway.complete(build_director_prompt(registry), script, max_tokens)
    board = parse_storyboard(raw)
    if board is None or not board.cast or not board.beats:
        board = deterministic_storyboard(script, registry)
        provider = f"{provider}->deterministic"
    return board, provider


async def build(
    topic_or_script: str,
    out_dir: str = "output",
    voice: str = tts.DEFAULT_VOICE,
    record: bool = False,
    upload: bool = False,
    title: str | None = None,
) -> dict:
    settings = get_settings()
    registry = get_registry()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. script
    if len(_sentences(topic_or_script)) >= 3:
        script = topic_or_script.strip()
        print("[1/6] using the provided script")
    else:
        print(f"[1/6] writing a script for: {topic_or_script!r}")
        script = await generate_script(settings, topic_or_script)
    (out / "script.txt").write_text(script, encoding="utf-8")
    print(f"      script -> {len(_sentences(script))} sentences")

    gateway = await build_gateway(settings, registry)

    # 2. forge any visuals the topic needs that the built-in library lacks
    print("[2/6] forging any missing visuals...")
    new_types = await forge_assets(gateway, script, registry, settings)
    if new_types:
        registry.load()  # refresh so the director can pick the new icons
    print(f"      +{len(new_types)} new assets" + (f": {', '.join(new_types)}" if new_types else ""))

    # 3. storyboard (director)
    print("[3/6] directing the scene...")
    board, provider = await _storyboard(gateway, registry, script, settings.director_max_tokens)
    cast_new = await forge_for_cast(board.cast, gateway, registry, settings)
    if cast_new:
        registry.load()  # scene-accurate icons for cast still on a generic asset
    beat_texts = [b.narration.strip() for b in board.beats if b.narration.strip()]
    print(
        f"      {len(board.cast)} objects, {len(beat_texts)} beats (provider: {provider})"
        + (f", +{len(cast_new)} cast icons" if cast_new else "")
    )

    # 3. one continuous, natural voiceover; beat timings come from word boundaries
    print(f"[4/6] synthesizing a continuous voiceover ({voice})...")
    narration, durations, speech_total = await tts.synthesize_narration(
        beat_texts, out / "narration.mp3", voice
    )
    print(f"      {len(durations)} beats, {speech_total:.1f}s of flowing narration")

    # 4. audio-synced scene (beat timing = real speech timing, no artificial gaps)
    scene = add_camera_moves(
        validate_and_repair(
            compile_storyboard(
                board, registry, script, beat_durations=durations, beat_pad=0.0, min_beat=0.4
            ),
            registry,
        )
    )
    (out / "scene.json").write_text(scene.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    video_seconds = max((s.at + s.duration for s in scene.timeline), default=0.0)
    print(f"      scene {video_seconds:.1f}s | narration {tts.audio_duration(narration):.1f}s (synced)")

    result = {
        "script": str(out / "script.txt"),
        "scene": str(out / "scene.json"),
        "narration": str(narration),
        "video_seconds": round(video_seconds, 1),
        "title": title or scene.title,
    }

    # 5. record + upload (optional)
    if record:
        from app.recorder import record_scene

        try:  # ensure the running backend serves any forged icons (new or cached)
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post("http://localhost:5173/api/assets/reload")
        except Exception:
            pass
        print("[5/6] recording the animation to MP4...")
        mp4 = await record_scene(scene, str(narration), out / "video.mp4")
        result["video"] = str(mp4)
        print(f"      video -> {mp4}")
        if upload:
            from app.youtube import upload_video

            print("[6/6] uploading to YouTube...")
            result["youtube"] = upload_video(mp4, title=result["title"], description=script)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a narrated explainer video from a topic.")
    parser.add_argument("topic", help="a topic (auto-scripted) or a full narration script")
    parser.add_argument("--out", default="output")
    parser.add_argument("--voice", default=tts.DEFAULT_VOICE)
    parser.add_argument("--record", action="store_true", help="also render an MP4 (needs Playwright)")
    parser.add_argument("--upload", action="store_true", help="upload the MP4 to YouTube")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()
    result = asyncio.run(
        build(args.topic, args.out, args.voice, record=args.record, upload=args.upload, title=args.title)
    )
    print("\nDONE:\n" + json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
