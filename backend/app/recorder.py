"""Records the animated scene to an MP4 with narration, using a headless browser.

Loads the frontend in render mode (chrome-free), injects the scene so it autoplays,
records the page, then trims the lead-in and muxes the narration track with ffmpeg.
Requires the frontend to be reachable (default http://localhost:5173) and Playwright
Chromium installed (`playwright install chromium`).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app import media, tts


async def record_scene(
    scene,
    narration_path: str,
    out_mp4,
    base_url: str = "http://localhost:5173",
    width: int = 1280,
    height: int = 720,
):
    from playwright.async_api import async_playwright

    video_seconds = max((s.at + s.duration for s in scene.timeline), default=0.0)
    scene_json = json.loads(scene.model_dump_json(by_alias=True))
    rec_dir = Path(tempfile.mkdtemp(prefix="svgrec_"))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(rec_dir),
            record_video_size={"width": width, "height": height},
        )
        page = await context.new_page()
        await page.goto(f"{base_url}/?render", wait_until="load")
        await page.wait_for_function(
            "window.__sceneStore && window.__sceneStore.getState().assetsLoaded === true",
            timeout=20000,
        )
        await page.evaluate("(s) => window.__sceneStore.getState().applyScene(s, 'render')", scene_json)
        await page.wait_for_function(
            "window.__sceneStore.getState().progress >= 0.995",
            timeout=int((video_seconds + 25) * 1000),
        )
        await page.wait_for_timeout(250)
        video = page.video
        await context.close()  # flushes the recording to disk
        webm = Path(await video.path()) if video else None
        await browser.close()

    if not webm or not webm.exists():
        raise RuntimeError("recording failed: no video was produced")

    # The animation ends right as we close, so the last `video_seconds` of the
    # recording is the animation; trim the lead-in and mux the narration.
    total = tts.audio_duration(webm)
    head = max(0.0, total - video_seconds - 0.15)
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    media._run([
        "ffmpeg", "-y", "-ss", f"{head:.3f}", "-i", str(webm),
        "-i", str(narration_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(out_mp4),
    ])
    return out_mp4
