"""Request/response models for the HTTP + WebSocket API."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.scene import Scene


class GenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The concept to visualize.")
    scene_id: str | None = Field(
        default=None,
        description="Existing scene id for conversational edits (reserved for future use).",
    )


class GenerateResponse(BaseModel):
    scene: Scene
    provider: str
    warnings: list[str] = Field(default_factory=list)


class TranscriptionResponse(BaseModel):
    text: str
    duration: float | None = None
    language: str | None = None


class AssetInfo(BaseModel):
    type: str
    label: str
    category: str
    keywords: list[str] = Field(default_factory=list)
    view_box: str = "0 0 100 100"
    svg: str = ""  # inner markup of the asset


class AssetManifest(BaseModel):
    assets: list[AssetInfo]
    categories: list[str]
