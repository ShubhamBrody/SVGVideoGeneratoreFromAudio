"""Regression suite: every speech in the corpus must produce a valid, consistent,
speech-paced scene through the deterministic director (no LLM required)."""
from __future__ import annotations

import re

import pytest

from app.assets.registry import get_registry
from app.models.scene import ActionType
from app.scene.director import compile_storyboard, deterministic_storyboard
from app.scene.validator import validate_and_repair
from tests.speeches import SPEECHES

_REGISTRY = get_registry()
_EDGE_ACTIONS = {ActionType.connect, ActionType.disconnect, ActionType.traffic}
_OBJECT_ACTIONS = {
    ActionType.appear, ActionType.disappear, ActionType.remove, ActionType.move,
    ActionType.highlight, ActionType.pulse, ActionType.change_state,
}


def _sentence_count(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


@pytest.mark.parametrize(
    "speech",
    SPEECHES,
    ids=[f"{s['domain']}-{i}" for i, s in enumerate(SPEECHES)],
)
def test_speech_produces_valid_paced_scene(speech: dict) -> None:
    text = speech["text"]
    scene = compile_storyboard(deterministic_storyboard(text, _REGISTRY), _REGISTRY, text)
    scene = validate_and_repair(scene, _REGISTRY)

    object_ids = {o.id for o in scene.objects}
    edge_ids = {e.id for e in scene.edges}

    assert scene.objects, "scene has no objects"
    assert scene.timeline, "scene has no timeline"

    # every reference resolves and the timeline is ordered
    for edge in scene.edges:
        assert edge.from_ in object_ids and edge.to in object_ids
    ats = [s.at for s in scene.timeline]
    assert ats == sorted(ats)
    for step in scene.timeline:
        if step.action in _EDGE_ACTIONS:
            assert step.target in edge_ids
        elif step.action in _OBJECT_ACTIONS:
            assert step.target in object_ids

    # pacing: one narration beat per sentence, video length scales with the speech
    sentences = _sentence_count(text)
    beats = sum(1 for s in scene.timeline if s.action == ActionType.narrate)
    assert abs(beats - sentences) <= 1
    video = max((s.at + s.duration for s in scene.timeline), default=0.0)
    assert video >= sentences * 2.0


def test_corpus_is_large_and_diverse() -> None:
    assert len(SPEECHES) >= 100
    assert len({s["domain"] for s in SPEECHES}) >= 10
