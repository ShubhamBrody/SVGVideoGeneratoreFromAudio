"""Camera agent: a deterministic cinematographer.

After the scene is compiled, this pass adds ``camera`` timeline steps that frame
whatever the narration is talking about — it zooms/pans to the object(s) each beat
acts on, holds (rests) while they are discussed, and pulls back to establish the
whole picture at transitions and at the end. Focusing the viewer's eye is what
turns a busy diagram into an *explanation*.
"""
from __future__ import annotations

from app.models.scene import ActionType, Scene, TimelineStep

_ZOOM_MAX = 1.75
_PAD = 170.0  # breathing room (px) around the framed objects
_SETTLE = 0.9  # how long a camera move takes before it rests
_MOVE_ACTIONS = {
    ActionType.appear, ActionType.emphasize, ActionType.highlight, ActionType.pulse,
    ActionType.change_state, ActionType.move, ActionType.rotate, ActionType.scale,
    ActionType.orbit, ActionType.travel, ActionType.remove, ActionType.disappear,
}


def add_camera_moves(scene: Scene) -> Scene:
    objects = scene.objects
    if len(objects) < 2:
        return scene

    w, h = scene.canvas.width, scene.canvas.height
    pos = {
        o.id: (o.position.x, o.position.y, max(o.size.width, o.size.height) / 2)
        for o in objects
    }

    narrates = sorted(
        (s for s in scene.timeline if s.action == ActionType.narrate), key=lambda s: s.at
    )
    movers = [s for s in scene.timeline if s.action in _MOVE_ACTIONS and s.target in pos]
    total = max((s.at + s.duration for s in scene.timeline), default=0.0)
    if not narrates:
        return scene

    def framing(ids: set[str]) -> tuple[float, float, float]:
        if not ids:
            return w / 2, h / 2, 1.0
        min_x = min(pos[i][0] - pos[i][2] for i in ids)
        max_x = max(pos[i][0] + pos[i][2] for i in ids)
        min_y = min(pos[i][1] - pos[i][2] for i in ids)
        max_y = max(pos[i][1] + pos[i][2] for i in ids)
        zoom = min(w / (max_x - min_x + 2 * _PAD), h / (max_y - min_y + 2 * _PAD))
        zoom = max(1.0, min(_ZOOM_MAX, zoom))
        return (min_x + max_x) / 2, (min_y + max_y) / 2, zoom

    cam: list[TimelineStep] = []
    last_key: tuple | None = None
    for i, beat in enumerate(narrates):
        start = beat.at
        end = narrates[i + 1].at if i + 1 < len(narrates) else total
        focus = {s.target for s in movers if start - 0.05 <= s.at < end - 0.05}
        cx, cy, zoom = framing(focus)
        key = (round(zoom, 1), round(cx / 40), round(cy / 40))
        if key == last_key:  # same subject as the last beat -> let the camera rest
            continue
        last_key = key
        cam.append(
            TimelineStep(
                action=ActionType.camera,
                target="",
                at=round(start, 2),
                duration=round(min(_SETTLE, max(0.4, (end - start) * 0.5)), 2),
                params={"zoom": round(zoom, 3), "cx": round(cx, 1), "cy": round(cy, 1)},
            )
        )

    # establish the whole picture at the very start and pull back to it at the end
    cam.insert(0, TimelineStep(action=ActionType.camera, target="", at=0.0, duration=0.6,
                               params={"zoom": 1.0, "cx": w / 2, "cy": h / 2}))
    if total > 2.0:
        cam.append(TimelineStep(action=ActionType.camera, target="", at=round(total - 1.4, 2),
                                duration=1.2, params={"zoom": 1.0, "cx": w / 2, "cy": h / 2}))

    timeline = sorted([*scene.timeline, *cam], key=lambda s: s.at)
    return scene.model_copy(update={"timeline": timeline})
