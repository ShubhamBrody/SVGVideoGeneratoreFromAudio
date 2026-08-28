"""Scene generation endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models.api import GenerateRequest, GenerateResponse
from app.scene.generator import SceneGenerationError, SceneGenerator

router = APIRouter(prefix="/api", tags=["scene"])


def _generator(request: Request) -> SceneGenerator:
    return request.app.state.generator


@router.post("/generate", response_model=GenerateResponse)
async def generate_scene(payload: GenerateRequest, request: Request) -> GenerateResponse:
    try:
        scene, provider = await _generator(request).generate(payload.text)
    except SceneGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GenerateResponse(scene=scene, provider=provider, warnings=scene.warnings)
