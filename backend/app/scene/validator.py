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
