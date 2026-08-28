"""Deterministic validator / critic pass.

Takes a (possibly imperfect) LLM-generated scene and repairs it so the renderer
never receives dangling references. It:

* remaps unknown asset types to the closest known asset,
* drops duplicate object/edge ids and self-loops,
* clamps positions inside the canvas,
* removes timeline steps that point at non-existent objects/edges,
* guarantees every object has an ``appear`` step so nothing stays invisible,
* sorts the timeline by start time.

Every repair is recorded in ``scene.warnings`` and surfaced to the UI.
"""
from __future__ import annotations

import math

from app.assets.registry import AssetRegistry
from app.models.scene import ActionType, Scene, TimelineStep

_EDGE_ACTIONS = {ActionType.connect, ActionType.disconnect, ActionType.traffic}
_OBJECT_ACTIONS = {
    ActionType.appear,
    ActionType.disappear,
    ActionType.remove,
    ActionType.move,
    ActionType.highlight,
    ActionType.pulse,
    ActionType.change_state,
}
_TARGETLESS = {ActionType.narrate, ActionType.wait}


def _point_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float):
    """Distance from point P to segment AB, plus the closest point and AB delta."""
    dx, dy = bx - ax, by - ay
    seg_sq = dx * dx + dy * dy
    if seg_sq == 0:
        return math.hypot(px - ax, py - ay), ax, ay, dx, dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_sq))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy), cx, cy, dx, dy


def _relax_layout(objects, edges, canvas):
    """Nudge objects apart and off edges they are not connected to, so nothing
    overlaps another node or sits on top of a connection line."""
    if len(objects) < 2:
        return objects

    margin = 60
    max_x, max_y = canvas.width - margin, canvas.height - margin
    pos = {o.id: [float(o.position.x), float(o.position.y)] for o in objects}
    radius = {o.id: max(o.size.width, o.size.height) / 2 for o in objects}
    ids = list(pos)
    edge_pairs = [(e.from_, e.to) for e in edges if e.from_ in pos and e.to in pos]

    for _ in range(40):
        moved = False
        # object-object separation
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                dx = pos[b][0] - pos[a][0]
                dy = pos[b][1] - pos[a][1]
                dist = math.hypot(dx, dy) or 0.01
                want = radius[a] + radius[b] + 34
                if dist < want:
                    shove = (want - dist) / 2
                    ux, uy = dx / dist, dy / dist
                    pos[a][0] -= ux * shove
                    pos[a][1] -= uy * shove
                    pos[b][0] += ux * shove
                    pos[b][1] += uy * shove
                    moved = True
        # object-edge separation
        for oid in ids:
            for f, t in edge_pairs:
                if oid in (f, t):
                    continue
                px, py = pos[oid]
                dist, cx, cy, dx, dy = _point_segment(px, py, pos[f][0], pos[f][1], pos[t][0], pos[t][1])
                clearance = radius[oid] + 24
                if dist < clearance:
                    nx, ny = px - cx, py - cy
                    nd = math.hypot(nx, ny)
                    if nd < 1e-3:  # object sits exactly on the line
                        seg = math.hypot(dx, dy) or 0.01
                        nx, ny, nd = -dy / seg, dx / seg, 1.0
                    shove = clearance - dist + 6
                    pos[oid][0] += (nx / nd) * shove
                    pos[oid][1] += (ny / nd) * shove
                    moved = True
        for oid in ids:
            pos[oid][0] = min(max(pos[oid][0], margin), max_x)
            pos[oid][1] = min(max(pos[oid][1], margin), max_y)
        if not moved:
            break

    result = []
    for obj in objects:
        x, y = pos[obj.id]
        if abs(x - obj.position.x) > 0.5 or abs(y - obj.position.y) > 0.5:
            obj = obj.model_copy(update={"position": obj.position.model_copy(update={"x": round(x, 1), "y": round(y, 1)})})
        result.append(obj)
    return result


def validate_and_repair(scene: Scene, registry: AssetRegistry) -> Scene:
    warnings: list[str] = list(scene.warnings)
    margin = 60
    max_x = scene.canvas.width - margin
    max_y = scene.canvas.height - margin

    # --- objects: unique ids, known types, clamped positions ---
    seen_ids: set[str] = set()
    objects = []
    for obj in scene.objects:
        if obj.id in seen_ids:
            warnings.append(f"Dropped duplicate object id '{obj.id}'.")
            continue
        seen_ids.add(obj.id)

        resolved = registry.resolve(obj.type)
        if resolved != obj.type:
            warnings.append(f"Asset type '{obj.type}' mapped to '{resolved}'.")
            obj = obj.model_copy(update={"type": resolved})

        x = min(max(obj.position.x, margin), max_x)
        y = min(max(obj.position.y, margin), max_y)
        if (x, y) != (obj.position.x, obj.position.y):
            obj = obj.model_copy(update={"position": obj.position.model_copy(update={"x": x, "y": y})})
        objects.append(obj)
    valid_ids = {o.id for o in objects}

    # --- edges: valid endpoints, unique ids, no self-loops ---
    seen_edges: set[str] = set()
    edges = []
    for edge in scene.edges:
        if edge.from_ not in valid_ids or edge.to not in valid_ids:
            warnings.append(f"Dropped edge '{edge.id}' with a missing endpoint.")
            continue
        if edge.from_ == edge.to:
            warnings.append(f"Dropped self-loop edge '{edge.id}'.")
            continue
        if edge.id in seen_edges:
            warnings.append(f"Dropped duplicate edge id '{edge.id}'.")
            continue
        seen_edges.add(edge.id)
        edges.append(edge)
    valid_edges = {e.id for e in edges}

    # --- relax layout: separate overlapping objects and push them off unrelated edges ---
    objects = _relax_layout(objects, edges, scene.canvas)

    # --- timeline: valid targets, positive durations, sorted ---
    steps: list[TimelineStep] = []
    for step in scene.timeline:
        if step.action in _EDGE_ACTIONS and step.target not in valid_edges:
            warnings.append(f"Dropped '{step.action.value}' step with unknown edge '{step.target}'.")
            continue
        if step.action in _OBJECT_ACTIONS and step.target not in valid_ids:
            warnings.append(f"Dropped '{step.action.value}' step with unknown object '{step.target}'.")
            continue

        duration = step.duration if step.duration and step.duration > 0 else 0.5
        at = max(0.0, step.at)
        if duration != step.duration or at != step.at:
            step = step.model_copy(update={"duration": duration, "at": at})
        steps.append(step)

    # --- guarantee every object becomes visible ---
    appeared = {s.target for s in steps if s.action == ActionType.appear}
    missing = [o.id for o in objects if o.id not in appeared]
    if missing:
        steps = [
            TimelineStep(action=ActionType.appear, target=oid, at=0.0, duration=0.5)
            for oid in missing
        ] + steps
        warnings.append(f"Added appear steps for {len(missing)} object(s) missing from the timeline.")

    steps.sort(key=lambda s: s.at)

    return scene.model_copy(
        update={"objects": objects, "edges": edges, "timeline": steps, "warnings": warnings}
    )
