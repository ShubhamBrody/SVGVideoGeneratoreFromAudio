"""Turns a text prompt into a validated Scene via the LLM gateway."""
from __future__ import annotations

import json
import re

from app.assets.registry import AssetRegistry
from app.llm.gateway import LLMGateway
from app.llm.mock import MockSceneBuilder
from app.llm.prompts import build_director_prompt
from app.models.scene import Scene
from app.scene.director import compile_storyboard, deterministic_storyboard, parse_storyboard
from app.scene.validator import validate_and_repair

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


class SceneGenerationError(RuntimeError):
    pass


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = re.sub(r"^json", "", text.strip(), flags=re.IGNORECASE).strip()
    match = _JSON_BLOCK.search(text)
    return match.group(0) if match else text


class SceneGenerator:
    def __init__(self, gateway: LLMGateway, registry: AssetRegistry) -> None:
        self._gateway = gateway
        self._registry = registry
        self._director_system = build_director_prompt(registry)

    async def generate(self, text: str) -> tuple[Scene, str]:
        text = (text or "").strip()
        if not text:
            raise SceneGenerationError("Prompt text is empty.")
        raw, provider = await self._gateway.complete(self._director_system, text)
        scene = self._build_scene(raw, text)
        scene = validate_and_repair(scene, self._registry)
        return scene, provider

    def _build_scene(self, raw: str, text: str) -> Scene:
        # 1. preferred: storyboard -> speech-paced timeline
        board = parse_storyboard(raw)
        if board is not None:
            try:
                scene = compile_storyboard(board, self._registry, text)
                if scene.objects and scene.timeline:
                    return scene
            except Exception:
                pass

        # 2. tolerate a flat Scene if the model emitted one
        try:
            scene = Scene.model_validate(json.loads(_extract_json(raw)))
            if scene.objects:
                if not scene.narration:
                    scene = scene.model_copy(update={"narration": text})
                return scene
        except Exception:
            pass

        # 3. deterministic fallback — speech-paced storyboard for scripts
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if len(sentences) >= 3:
            try:
                return compile_storyboard(
                    deterministic_storyboard(text, self._registry), self._registry, text
                )
            except Exception:
                pass
        return MockSceneBuilder(self._registry).build(text)
