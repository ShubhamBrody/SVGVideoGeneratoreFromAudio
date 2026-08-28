from fastapi.testclient import TestClient

from app.assets.registry import get_registry
from app.llm.mock import MockSceneBuilder
from app.main import app
from app.models.scene import (
    ActionType,
    Position,
    Scene,
    SceneEdge,
    SceneObject,
    TimelineStep,
)
from app.scene.validator import validate_and_repair


def _scene_is_consistent(scene: Scene) -> None:
    object_ids = {o.id for o in scene.objects}
    edge_ids = {e.id for e in scene.edges}
    for edge in scene.edges:
        assert edge.from_ in object_ids
        assert edge.to in object_ids
    ats = [s.at for s in scene.timeline]
    assert ats == sorted(ats)
    for step in scene.timeline:
        if step.action in {ActionType.connect, ActionType.disconnect, ActionType.traffic}:
            assert step.target in edge_ids
        elif step.action in {
            ActionType.appear,
            ActionType.remove,
            ActionType.change_state,
            ActionType.highlight,
            ActionType.pulse,
            ActionType.move,
            ActionType.disappear,
        }:
            assert step.target in object_ids


# ---------------- API ----------------

def test_health():
    with TestClient(app) as client:
        body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"


def test_assets_manifest():
    with TestClient(app) as client:
        body = client.get("/api/assets").json()
    assert len(body["assets"]) >= 20
    assert "kubernetes" in body["categories"]
    assert all(a["svg"] for a in body["assets"])


def test_asset_svg_and_404():
    with TestClient(app) as client:
        ok = client.get("/api/assets/kubernetes.pod/svg")
        missing = client.get("/api/assets/does.not.exist/svg")
    assert ok.status_code == 200
    assert ok.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in ok.text
    assert missing.status_code == 404


def test_generate_kubernetes():
    with TestClient(app) as client:
        res = client.post(
            "/api/generate",
            json={"text": "A Kubernetes service routes traffic to five pods, then pod 3 fails and is replaced"},
        ).json()
    scene = Scene.model_validate(res["scene"])
    assert scene.objects and scene.edges and scene.timeline
    _scene_is_consistent(scene)
    # the "from" alias must round-trip in the API payload
    assert "from" in res["scene"]["edges"][0]


def test_generate_generic_pipeline():
    with TestClient(app) as client:
        res = client.post(
            "/api/generate",
            json={"text": "A user calls an API gateway that talks to a server and a postgres database"},
        ).json()
    scene = Scene.model_validate(res["scene"])
    assert len(scene.objects) >= 3
    _scene_is_consistent(scene)


def test_generate_empty_is_rejected():
    with TestClient(app) as client:
        empty = client.post("/api/generate", json={"text": ""})
        whitespace = client.post("/api/generate", json={"text": "   "})
    assert empty.status_code == 422  # fails min_length validation
    assert whitespace.status_code == 400  # rejected by the generator


# ---------------- mock builder ----------------

def test_mock_builder_kafka():
    scene = MockSceneBuilder(get_registry()).build("Explain how Kafka handles a consumer failure")
    assert scene.objects
    assert any(s.action == ActionType.change_state for s in scene.timeline)


# ---------------- validator ----------------

def test_validator_repairs_bad_scene():
    registry = get_registry()
    scene = Scene(
        title="broken",
        objects=[
            SceneObject(id="a", type="unknown.thing", label="A", position=Position(x=-80, y=100)),
            SceneObject(id="a", type="kubernetes.pod", label="dup", position=Position(x=100, y=100)),
            SceneObject(id="b", type="kubernetes.pod", label="B", position=Position(x=200, y=200)),
        ],
        edges=[
            SceneEdge(id="e1", from_="a", to="b"),
            SceneEdge(id="e2", from_="a", to="ghost"),
            SceneEdge(id="e3", from_="a", to="a"),
        ],
        timeline=[
            TimelineStep(action=ActionType.appear, target="a", at=1.0, duration=0.5),
            TimelineStep(action=ActionType.traffic, target="ghost-edge", at=0.5, duration=1.0),
            TimelineStep(action=ActionType.connect, target="e1", at=0.5, duration=0.4),
        ],
    )
    repaired = validate_and_repair(scene, registry)

    assert {o.id for o in repaired.objects} == {"a", "b"}  # duplicate dropped
    repaired_a = next(o for o in repaired.objects if o.id == "a")
    assert registry.has(repaired_a.type)  # unknown type remapped
    assert repaired_a.position.x >= 0  # clamped
    assert {e.id for e in repaired.edges} == {"e1"}  # dangling + self-loop dropped
    assert any(s.action == ActionType.appear and s.target == "b" for s in repaired.timeline)
    _scene_is_consistent(repaired)
    assert repaired.warnings
