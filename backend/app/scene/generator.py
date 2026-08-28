"""Turns a text prompt into a validated Scene via the LLM gateway."""
from __future__ import annotations

import json
import re

from app.assets.registry import AssetRegistry
from app.llm.gateway import LLMGateway
from app.llm.mock import MockSceneBuilder
from app.llm.prompts import build_system_prompt
from app.models.scene import Scene
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
        self._system = build_system_prompt(registry)

    async def generate(self, text: str) -> tuple[Scene, str]:
        text = (text or "").strip()
        if not text:
            raise SceneGenerationError("Prompt text is empty.")
        raw, provider = await self._gateway.complete(self._system, text)
        scene = self._parse(raw, text)
        scene = validate_and_repair(scene, self._registry)
        return scene, provider

    def _parse(self, raw: str, text: str) -> Scene:
        try:
            data = json.loads(_extract_json(raw))
            scene = Scene.model_validate(data)
            if not scene.objects:
                raise ValueError("scene has no objects")
            if not scene.narration:
                scene = scene.model_copy(update={"narration": text})
            return scene
        except Exception:
            # The model returned unusable JSON — fall back to the deterministic builder.
            return MockSceneBuilder(self._registry).build(text)
