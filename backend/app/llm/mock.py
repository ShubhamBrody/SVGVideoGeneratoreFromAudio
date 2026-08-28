"""Offline, rule-based Scene builder.

This is the zero-configuration fallback: it inspects the prompt text, matches
concepts to assets in the registry, lays them out, and produces a reasonable
animated scene. It lets the entire pipeline run without any API keys, and it is
what powers the demo when no LLM is configured.
"""
from __future__ import annotations

import re

from app.assets.registry import AssetRegistry
from app.models.scene import (
    ActionType,
    EdgeStyle,
    ObjectState,
    Position,
    Scene,
    SceneEdge,
    SceneObject,
    TimelineStep,
)

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_FAILURE = (
    "fail", "unhealthy", "down", "crash", "dies", "die", "dead",
    "restart", "replace", "kill", "broken", "outage", "evict",
)
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "how",
    "what", "show", "me", "explain", "when", "then", "is", "are", "does", "do",
    "from", "into", "that", "this", "it", "its", "as", "by", "at", "so", "if",
    "becomes", "between", "sends", "send", "receives", "goes", "through", "via",
}


def _clamp(n: int, lo: int = 1, hi: int = 8) -> int:
    return max(lo, min(hi, n))


def _count_near(low: str, noun: str, default: int = 3) -> int:
    m = re.search(r"(\d+)\s+" + noun, low)
    if m:
        return _clamp(int(m.group(1)))
    for word, value in _NUMBER_WORDS.items():
        if re.search(rf"\b{word}\s+{noun}", low):
            return _clamp(value)
    return default


def _row(n: int, y: float, x0: float = 180, x1: float = 1100) -> list[tuple[float, float]]:
    if n <= 1:
        return [((x0 + x1) / 2, y)]
    step = (x1 - x0) / (n - 1)
    return [(x0 + i * step, y) for i in range(n)]


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _title_from(text: str) -> str:
    t = text.strip().rstrip(".")
    if not t:
        return "Scene"
    t = t[:1].upper() + t[1:]
    return (t[:58] + "\u2026") if len(t) > 60 else t


class MockSceneBuilder:
    def __init__(self, registry: AssetRegistry) -> None:
        self.r = registry

    def build(self, text: str) -> Scene:
        text = (text or "").strip() or "a client sends a request to a server"
        low = text.lower()
        if "kubernetes" in low or "k8s" in low or re.search(r"\bpods?\b", low):
            return self._kubernetes(text, low)
        return self._generic(text, low)

    # -- Kubernetes fan-out template (service -> pods, optional failure) --
    def _kubernetes(self, text: str, low: str) -> Scene:
        n = _count_near(low, r"pods?", default=3)
        failure = any(k in low for k in _FAILURE)
        objects = [
            SceneObject(id="service", type="kubernetes.service", label="Service",
                        position=Position(x=640, y=120))
        ]
        edges: list[SceneEdge] = []
        pods_xy = _row(n, y=440)
        for i, (x, y) in enumerate(pods_xy, 1):
            objects.append(SceneObject(id=f"pod-{i}", type="kubernetes.pod",
                                       label=f"Pod {i}", position=Position(x=x, y=y)))
            edges.append(SceneEdge(id=f"e{i}", from_="service", to=f"pod-{i}",
                                   style=EdgeStyle.traffic))

        tl: list[TimelineStep] = []
        t = 0.0
        tl.append(TimelineStep(action=ActionType.appear, target="service", at=t, duration=0.5))
        t += 0.5
        for i in range(1, n + 1):
            tl.append(TimelineStep(action=ActionType.appear, target=f"pod-{i}", at=t, duration=0.4))
            t += 0.3
        t += 0.2
        for i in range(1, n + 1):
            tl.append(TimelineStep(action=ActionType.connect, target=f"e{i}", at=t, duration=0.4))
            t += 0.15
        traffic_start = t + 0.2
        for i in range(1, n + 1):
            tl.append(TimelineStep(action=ActionType.traffic, target=f"e{i}",
                                   at=traffic_start, duration=1.6))
        tl.append(TimelineStep(action=ActionType.narrate, target="", at=traffic_start,
                               duration=2.0,
                               params={"text": "The Service load-balances traffic across the pods."}))
        t = traffic_start + 1.9

        if failure:
            fail_i = (n + 1) // 2
            fid, feid = f"pod-{fail_i}", f"e{fail_i}"
            tl.append(TimelineStep(action=ActionType.change_state, target=fid, at=t,
                                   duration=0.5, params={"state": "unhealthy"}))
            tl.append(TimelineStep(action=ActionType.pulse, target=fid, at=t, duration=0.6))
            tl.append(TimelineStep(action=ActionType.narrate, target="", at=t, duration=2.0,
                                   params={"text": f"Pod {fail_i} fails its health check."}))
            t += 1.5
            tl.append(TimelineStep(action=ActionType.disconnect, target=feid, at=t, duration=0.4))
            t += 0.4
            tl.append(TimelineStep(action=ActionType.remove, target=fid, at=t, duration=0.5))
            t += 0.7
            rx, ry = pods_xy[fail_i - 1]
            objects.append(SceneObject(id="pod-new", type="kubernetes.pod", label=f"Pod {n + 1}",
                                       position=Position(x=rx, y=min(ry + 150, 630)),
                                       state=ObjectState.healthy))
            edges.append(SceneEdge(id="e-new", from_="service", to="pod-new", style=EdgeStyle.traffic))
            tl.append(TimelineStep(action=ActionType.narrate, target="", at=t, duration=2.0,
                                   params={"text": "Kubernetes schedules a replacement pod."}))
            tl.append(TimelineStep(action=ActionType.appear, target="pod-new", at=t, duration=0.5))
            t += 0.6
            tl.append(TimelineStep(action=ActionType.connect, target="e-new", at=t, duration=0.4))
            t += 0.4
            tl.append(TimelineStep(action=ActionType.traffic, target="e-new", at=t, duration=1.6))

        title = "Kubernetes pod failure" if failure else "Kubernetes service and pods"
        return Scene(title=title, objects=objects, edges=edges, timeline=tl, narration=text)

    # -- Generic left-to-right pipeline for everything else --
    def _generic(self, text: str, low: str) -> Scene:
        matched = _dedupe(self.r.match(text))
        if len(matched) >= 2:
            node_types = [self.r.resolve(t) for t in matched[:6]]
            node_labels = [self.r.get(t).label for t in node_types]  # type: ignore[union-attr]
        else:
            words = [w for w in re.findall(r"[a-z][a-z0-9-]+", low) if w not in _STOP]
            picked = _dedupe(words)[:4] or ["client", "server"]
            node_labels = [w.title() for w in picked]
            node_types = ["generic.box"] * len(node_labels)
            if matched:
                node_types[0] = matched[0]
                node_labels[0] = self.r.get(matched[0]).label  # type: ignore[union-attr]

        n = len(node_types)
        xs = _row(n, y=360)
        objects: list[SceneObject] = []
        edges: list[SceneEdge] = []
        for i, (type_, label, (x, y)) in enumerate(zip(node_types, node_labels, xs), 1):
            oid = f"n{i}"
            objects.append(SceneObject(id=oid, type=type_, label=label, position=Position(x=x, y=y)))
            if i > 1:
                edges.append(SceneEdge(id=f"e{i - 1}", from_=f"n{i - 1}", to=oid, style=EdgeStyle.data))

        tl: list[TimelineStep] = []
        t = 0.0
        for i in range(1, n + 1):
            tl.append(TimelineStep(action=ActionType.appear, target=f"n{i}", at=t, duration=0.45))
            t += 0.35
        t += 0.15
        for i in range(1, n):
            tl.append(TimelineStep(action=ActionType.connect, target=f"e{i}", at=t, duration=0.4))
            t += 0.2
        traffic_start = t + 0.15
        for i in range(1, n):
            tl.append(TimelineStep(action=ActionType.traffic, target=f"e{i}",
                                   at=traffic_start, duration=1.4))
        t = traffic_start + 1.6

        if any(k in low for k in _FAILURE):
            fid = f"n{n}"
            tl.append(TimelineStep(action=ActionType.change_state, target=fid, at=t,
                                   duration=0.5, params={"state": "unhealthy"}))
            tl.append(TimelineStep(action=ActionType.pulse, target=fid, at=t, duration=0.6))
            tl.append(TimelineStep(action=ActionType.narrate, target="", at=t, duration=2.0,
                                   params={"text": f"{node_labels[-1]} fails."}))

        return Scene(title=_title_from(text), objects=objects, edges=edges,
                     timeline=tl, narration=text)
