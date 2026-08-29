"""The Scene DSL — the contract between the AI and the deterministic renderer.

An LLM (or the offline mock) emits a ``Scene``: a set of positioned ``objects``,
``edges`` connecting them, and a ``timeline`` of animation steps. The frontend
compiles the timeline into a GSAP animation. Keeping this schema small and
validated is what makes the output reliable instead of hallucinated SVG.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _sid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class ObjectState(str, Enum):
    normal = "normal"
    healthy = "healthy"
    unhealthy = "unhealthy"
    highlighted = "highlighted"
    dimmed = "dimmed"


class EdgeStyle(str, Enum):
    solid = "solid"
    dashed = "dashed"
    traffic = "traffic"
    data = "data"
    control = "control"
    dependency = "dependency"


class ActionType(str, Enum):
    appear = "appear"
    disappear = "disappear"
    remove = "remove"
    move = "move"
    highlight = "highlight"
    change_state = "change_state"
    connect = "connect"
    disconnect = "disconnect"
    traffic = "traffic"
    pulse = "pulse"
    rotate = "rotate"
    scale = "scale"
    orbit = "orbit"
    travel = "travel"
    emphasize = "emphasize"
    shake = "shake"
    camera = "camera"
    label = "label"
    narrate = "narrate"
    wait = "wait"


class Position(BaseModel):
    x: float
    y: float


class Size(BaseModel):
    width: float = 96.0
    height: float = 96.0


class SceneObject(BaseModel):
    """A single node in the scene, backed by an SVG asset ``type``."""

    id: str
    type: str  # asset type, e.g. "kubernetes.pod"
    label: str = ""
    position: Position
    size: Size = Field(default_factory=Size)
    state: ObjectState = ObjectState.normal
    meta: dict[str, Any] = Field(default_factory=dict)


class SceneEdge(BaseModel):
    """A directed connection between two objects."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: str
    label: str = ""
    style: EdgeStyle = EdgeStyle.solid


class TimelineStep(BaseModel):
    """One animation instruction, resolved by the frontend animation engine."""

    id: str = Field(default_factory=lambda: _sid("step"))
    action: ActionType
    target: str = ""  # object id, edge id, or "" (narrate / wait)
    at: float = 0.0  # start time, seconds
    duration: float = 0.6
    params: dict[str, Any] = Field(default_factory=dict)


class Canvas(BaseModel):
    width: int = 1280
    height: int = 720
    background: str = "#0b1020"


class Scene(BaseModel):
    id: str = Field(default_factory=lambda: _sid("scene"))
    title: str = "Untitled scene"
    canvas: Canvas = Field(default_factory=Canvas)
    objects: list[SceneObject] = Field(default_factory=list)
    edges: list[SceneEdge] = Field(default_factory=list)
    timeline: list[TimelineStep] = Field(default_factory=list)
    narration: str = ""
    warnings: list[str] = Field(default_factory=list)

    def object_ids(self) -> set[str]:
        return {o.id for o in self.objects}

    def edge_ids(self) -> set[str]:
        return {e.id for e in self.edges}
