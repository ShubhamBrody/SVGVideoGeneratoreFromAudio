"""Scene Director: turns a full narration/script into a paced, beat-by-beat scene.

The LLM acts as a *director*. Instead of one flat scene it produces a STORYBOARD:
the ``cast`` of objects, their ``connections``, and an ordered list of ``beats`` —
one per sentence/idea — each with its narration text and the visual ``actions`` for
that moment, but WITHOUT any timing.

A deterministic compiler then joins the beats into a single timeline, sizing each
beat's on-screen time from its narration length (~natural reading rate), so the
video's pacing follows the speech and a long script yields a correspondingly long
video.
"""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field

from app.assets.registry import AssetRegistry
from app.models.scene import (
    ActionType,
    EdgeStyle,
    Position,
    Scene,
    SceneEdge,
    SceneObject,
    TimelineStep,
)

# pacing: ~175 wpm speech ≈ 0.34 s/word, with padding and sensible bounds
_SEC_PER_WORD = 0.34
_MIN_BEAT = 2.8
_MAX_BEAT = 9.0
_STAGGER = 0.28

_ACTION_VALUES = {a.value for a in ActionType}
_EDGE_STYLE_VALUES = {e.value for e in EdgeStyle}
_EDGE_ACTIONS = {"connect", "disconnect", "traffic"}
_OBJECT_ACTIONS = {
    "appear", "disappear", "remove", "move", "highlight", "pulse", "change_state",
}
_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)

# heuristics for the deterministic (no-LLM) director
_FAILURE_WORDS = (
    "fail", "fails", "failed", "unhealthy", "crash", "crashes", "crashed", "down",
    "dies", "die", "dead", "kill", "broken", "outage", "evict", "stops sending",
    "timeout expires", "missing heartbeat", "no longer",
)
_RECOVER_WORDS = (
    "healthy", "recover", "recovers", "resumes", "completes", "restored",
    "returns to a healthy", "back to normal", "stabil",
)
_FLOW_WORDS = (
    "read", "reads", "reading", "stream", "streams", "streaming", "send", "sends",
    "sending", "route", "routes", "flow", "flows", "consume", "consumes",
    "process", "processes", "processing", "handle", "handles", "handling", "fetch",
)
_SOURCE_TYPES = {
    "kafka", "topic", "service", "broker", "kafka_broker", "load_balancer",
    "api_gateway", "coordinator", "producer", "user", "client",
}
_GENERIC_TYPES = {"generic.box", "generic.cache", "generic.database"}



# ----------------------------- storyboard models -----------------------------

class StoryAction(BaseModel):
    action: str
    target: str = ""
    params: dict = Field(default_factory=dict)


class StoryBeat(BaseModel):
    narration: str = ""
    actions: list[StoryAction] = Field(default_factory=list)


class StoryObject(BaseModel):
    id: str
    type: str
    label: str = ""
    position: Position | None = None


class StoryConnection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: str
    label: str = ""
    style: str = "data"


class Storyboard(BaseModel):
    title: str = "Scene"
    cast: list[StoryObject] = Field(default_factory=list)
    connections: list[StoryConnection] = Field(default_factory=list)
    beats: list[StoryBeat] = Field(default_factory=list)


def parse_storyboard(raw: str) -> Storyboard | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip().strip("`").strip()
    match = _JSON_BLOCK.search(text)
    if not match:
        return None
    try:
        board = Storyboard.model_validate(json.loads(match.group(0)))
    except Exception:
        return None
    return board if board.cast and board.beats else None


# ------------------------------- the compiler --------------------------------

def _beat_seconds(narration: str) -> float:
    words = len(narration.split())
    return max(_MIN_BEAT, min(_MAX_BEAT, words * _SEC_PER_WORD + 1.2))


def _action_duration(action: str, beat_dur: float) -> float:
    if action in {"traffic", "pulse"}:
        return max(1.2, beat_dur * 0.7)
    if action == "move":
        return 0.8
    return 0.5


def _auto_pos(index: int, total: int) -> Position:
    cols = 4 if total > 6 else max(1, min(total, 4))
    row, col = divmod(index, cols)
    x = 640.0 if cols == 1 else 200 + col * (880 / (cols - 1))
    y = 170 + row * 175
    return Position(x=min(1180, max(90, x)), y=min(640, max(90, y)))


def compile_storyboard(
    board: Storyboard,
    registry: AssetRegistry,
    text: str,
    beat_durations: list[float] | None = None,
) -> Scene:
    """Join storyboard beats into one speech-paced Scene.

    If ``beat_durations`` (real TTS clip lengths) are given, each beat lasts that
    long plus a short pause, so the animation syncs to the actual voiceover.
    Otherwise beat length is estimated from the narration word count.
    """
    objects: list[SceneObject] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(board.cast):
        if not item.id or item.id in seen_ids:
            continue
        seen_ids.add(item.id)
        resolved = registry.resolve(item.type)
        # If the model chose a generic icon, upgrade it from the label when possible
        # (e.g. label "Vector DB" / "Redis" -> ai.vector_db / databases.redis).
        if resolved in _GENERIC_TYPES and item.label:
            for match in registry.match(item.label):
                if match not in _GENERIC_TYPES:
                    resolved = match
                    break
        objects.append(
            SceneObject(
                id=item.id,
                type=resolved,
                label=item.label or item.id,
                position=item.position or _auto_pos(i, len(board.cast)),
            )
        )
    object_ids = {o.id for o in objects}

    edges: list[SceneEdge] = []
    edge_ids: set[str] = set()
    for conn in board.connections:
        if conn.from_ in object_ids and conn.to in object_ids and conn.id not in edge_ids:
            edge_ids.add(conn.id)
            style = conn.style if conn.style in _EDGE_STYLE_VALUES else "data"
            edges.append(
                SceneEdge(id=conn.id, from_=conn.from_, to=conn.to, label=conn.label, style=EdgeStyle(style))
            )

    timeline: list[TimelineStep] = []
    appeared: set[str] = set()
    connected: set[str] = set()
    t = 0.0

    for beat_index, beat in enumerate(board.beats):
        narration = beat.narration.strip()
        if beat_durations and beat_index < len(beat_durations) and beat_durations[beat_index] > 0:
            dur = max(_MIN_BEAT, beat_durations[beat_index] + 0.6)  # voiceover + short pause
        else:
            dur = _beat_seconds(narration)
        if narration:
            timeline.append(
                TimelineStep(action=ActionType.narrate, target="", at=round(t, 2),
                             duration=round(dur, 2), params={"text": narration})
            )
        offset = 0.2
        for act in beat.actions:
            name = act.action.lower().strip()
            if name in {"narrate", "wait"} or name not in _ACTION_VALUES:
                continue
            target = act.target

            if name in _EDGE_ACTIONS:
                if target not in edge_ids:
                    continue
                if name == "traffic" and target not in connected:
                    timeline.append(TimelineStep(action=ActionType.connect, target=target,
                                                 at=round(t + offset, 2), duration=0.4))
                    connected.add(target)
                    offset += _STAGGER
                if name == "connect":
                    connected.add(target)
            elif name in _OBJECT_ACTIONS:
                if target not in object_ids:
                    continue
                if name != "appear" and target not in appeared:
                    timeline.append(TimelineStep(action=ActionType.appear, target=target,
                                                 at=round(t + offset, 2), duration=0.5))
                    appeared.add(target)
                    offset += _STAGGER
                if name == "appear":
                    appeared.add(target)

            timeline.append(
                TimelineStep(action=ActionType(name), target=target, at=round(t + offset, 2),
                             duration=round(_action_duration(name, dur), 2), params=act.params or {})
            )
            offset += _STAGGER

        t += dur

    scene = Scene(
        title=board.title or "Scene",
        objects=objects,
        edges=edges,
        timeline=timeline,
        narration=text,
    )
    return scene


# ------------------- deterministic director (no LLM needed) ------------------

def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if s.strip()]


def _title_from(text: str) -> str:
    first = _sentences(text)
    if not first:
        return "Scene"
    t = first[0].rstrip(".!?")
    return (t[:58] + "\u2026") if len(t) > 60 else t


def deterministic_storyboard(text: str, registry: AssetRegistry) -> Storyboard:
    """Build a speech-paced storyboard from the text alone, without any LLM.

    One beat per sentence guarantees the video length tracks the narration. Cast
    objects are detected by keyword; each appears when first mentioned, failure
    sentences mark an entity unhealthy, recovery marks it healthy, and flow verbs
    animate traffic. This is the reliable baseline behind the LLM director.
    """
    sentences = _sentences(text) or [text.strip() or "Scene"]

    matched: list[str] = []
    for type_ in registry.match(text):
        if type_ not in matched:
            matched.append(type_)
    matched = matched[:8] or ["generic.box"]

    cast: list[StoryObject] = []
    for i, type_ in enumerate(matched):
        asset = registry.get(type_)
        cast.append(StoryObject(id=f"n{i + 1}", type=type_,
                                label=asset.label if asset else type_,
                                position=_auto_pos(i, len(matched))))

    connections: list[StoryConnection] = []
    first_kind = cast[0].type.split(".")[-1] if cast else ""
    if len(cast) >= 3 and first_kind in _SOURCE_TYPES:
        for i in range(1, len(cast)):
            connections.append(StoryConnection.model_validate(
                {"id": f"e{i}", "from": cast[0].id, "to": cast[i].id, "style": "data"}))
    else:
        for i in range(len(cast) - 1):
            connections.append(StoryConnection.model_validate(
                {"id": f"e{i + 1}", "from": cast[i].id, "to": cast[i + 1].id, "style": "data"}))

    keyword_index = [(c, registry.get(c.type).keywords if registry.get(c.type) else []) for c in cast]
    beats: list[StoryBeat] = []
    appeared: set[str] = set()

    for sentence in sentences:
        low = sentence.lower()
        actions: list[StoryAction] = []

        for cast_obj, keywords in keyword_index:
            if cast_obj.id not in appeared and any(kw in low for kw in keywords):
                actions.append(StoryAction(action="appear", target=cast_obj.id))
                appeared.add(cast_obj.id)
        if not appeared and cast:
            actions.append(StoryAction(action="appear", target=cast[0].id))
            appeared.add(cast[0].id)

        if any(w in low for w in _FAILURE_WORDS):
            target = next((c.id for c, _ in reversed(keyword_index) if c.id in appeared), None)
            if target:
                actions.append(StoryAction(action="change_state", target=target,
                                           params={"state": "unhealthy"}))
                actions.append(StoryAction(action="pulse", target=target))
        elif any(w in low for w in _RECOVER_WORDS):
            target = next((c.id for c, _ in keyword_index if c.id in appeared), None)
            if target:
                actions.append(StoryAction(action="change_state", target=target,
                                           params={"state": "healthy"}))
        elif any(w in low for w in _FLOW_WORDS):
            for conn in connections:
                if conn.from_ in appeared and conn.to in appeared:
                    actions.append(StoryAction(action="traffic", target=conn.id))

        beats.append(StoryBeat(narration=sentence, actions=actions))

    return Storyboard(title=_title_from(text), cast=cast, connections=connections, beats=beats)

