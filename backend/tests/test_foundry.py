"""Unit tests for the Asset Foundry (pure functions — no network or LLM)."""
from __future__ import annotations

from app.assets.foundry import (
    _house_card,
    _prefer,
    _sanitize_svg,
    _slug,
    parse_manifest,
)


def test_slug_normalizes():
    assert _slug("King Arthur!") == "king_arthur"
    assert _slug("  Vector-DB  ") == "vector_db"
    assert _slug("???") == ""


def test_parse_manifest_extracts_specs():
    raw = """Here you go:
    [
      {"name": "king", "label": "King", "query": "king crown", "keywords": ["king"]},
      {"name": "dragon", "label": "Dragon", "query": "fire dragon"}
    ]"""
    specs = parse_manifest(raw)
    assert [s.name for s in specs] == ["king", "dragon"]
    assert specs[0].query == "king crown"


def test_parse_manifest_handles_garbage():
    assert parse_manifest("no json here") == []
    assert parse_manifest("") == []


def test_prefer_picks_preferred_set():
    icons = ["random:thing", "mdi:crown", "noto:crown"]
    assert _prefer(icons) == "noto:crown"  # noto ranks above mdi
    assert _prefer(["random:thing"]) == "random:thing"


def test_sanitize_strips_scripts_and_handlers():
    dirty = (
        '<svg viewBox="0 0 24 24">'
        '<script>alert(1)</script>'
        '<rect x="1" y="1" width="10" height="10" onclick="steal()"/>'
        '<image href="http://evil/x.png"/>'
        "</svg>"
    )
    result = _sanitize_svg(dirty)
    assert result is not None
    view_box, inner = result
    assert view_box == "0 0 24 24"
    assert "script" not in inner.lower()
    assert "onclick" not in inner.lower()
    assert "<image" not in inner.lower()
    assert "<rect" in inner.lower()


def test_sanitize_rejects_empty():
    assert _sanitize_svg("<svg></svg>") is None
    assert _sanitize_svg("not svg at all") is None


def test_house_card_wraps_glyph():
    view_box, inner = _house_card("0 0 24 24", '<path d="M0 0h24v24H0z"/>')
    assert view_box == "0 0 100 100"
    assert "rounded" not in inner  # sanity: it's markup, not prose
    assert 'viewBox="0 0 24 24"' in inner
    assert "<rect" in inner and "<path" in inner
