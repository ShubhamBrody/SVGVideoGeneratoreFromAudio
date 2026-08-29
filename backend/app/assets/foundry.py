"""Asset Foundry: acquire the icons a topic needs, on demand.

The built-in library only covers infrastructure. For anything else (a king, a
dragon, a chessboard, a neuron...) this module:

1. asks the LLM to plan a *manifest* of concrete visual subjects the script needs,
2. tries to fetch a real icon for each from the open Iconify library, and
3. falls back to an LLM-drawn SVG when nothing fits,

then normalizes each into the house 100x100 "card" style and writes it under
``assets/generated/`` where the registry picks it up automatically. Everything is
sanitized before it is written, because these SVGs are inlined into the browser.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from app.assets.registry import AssetRegistry
from app.config import Settings
from app.llm.gateway import LLMGateway
from app.llm.prompts import build_asset_manifest_prompt, build_svg_prompt

# Icon sets to prefer, best-looking / most-recognizable first. Colorful emoji and
# game-icons shine for non-technical subjects; the rest are clean flat icon sets.
_PREFERRED = (
    "noto", "openmoji", "twemoji", "fluent-emoji", "fluent-emoji-flat", "emojione",
    "game-icons", "material-symbols", "mdi", "ph", "tabler", "fa6-solid",
    "streamline", "carbon", "ic",
)

_SVG_TAG = re.compile(r"<svg\b[^>]*>(.*)</svg>", re.DOTALL | re.IGNORECASE)
_VIEWBOX = re.compile(r'viewBox="([^"]+)"', re.IGNORECASE)
_ARRAY = re.compile(r"\[.*\]", re.DOTALL)
_BAD_TAGS = re.compile(
    r"<\s*(script|foreignObject|image|use|text|a|animate\w*)\b[^>]*>.*?<\s*/\s*\1\s*>"
    r"|<\s*(script|image|use|animate\w*)\b[^>]*/?>",
    re.DOTALL | re.IGNORECASE,
)
_ON_ATTR = re.compile(r"\s+on\w+\s*=\s*(\"[^\"]*\"|'[^']*')", re.IGNORECASE)
_JS_URI = re.compile(r"javascript:", re.IGNORECASE)


class AssetSpec(BaseModel):
    name: str
    label: str = ""
    query: str = ""
    keywords: list[str] = Field(default_factory=list)


# Generic library types a forged icon should replace, and abstract words that are NOT
# drawable objects (algorithm parts, qualities) — we refuse to forge these.
_GENERIC_TYPES = {"generic.box", "generic.cache", "generic.database", "generic.cloud"}
_ABSTRACT = {
    "backtracking", "backtrack", "recursion", "recursive", "iteration", "iterate",
    "loop", "complexity", "algorithm", "process", "procedure", "logic", "condition",
    "constraint", "comparison", "evaluation", "decision", "step", "phase", "stage",
    "state", "function", "method", "variable", "index", "pointer", "row", "column",
    "diagonal", "cell", "case", "solution", "approach", "concept", "idea", "rule",
    "order", "sequence", "count", "sum", "total", "result", "output", "input",
    "data", "value", "element", "item", "flow", "event", "task",
}


def _is_abstract(spec: AssetSpec) -> bool:
    words = re.findall(r"[a-z]+", f"{spec.name} {spec.label}".lower())
    return bool(words) and all(w in _ABSTRACT for w in words)


# ------------------------------- parsing / io --------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")[:40]


def parse_manifest(raw: str) -> list[AssetSpec]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip().strip("`").strip()
    match = _ARRAY.search(text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except Exception:
        return []
    specs: list[AssetSpec] = []
    for item in data if isinstance(data, list) else []:
        try:
            spec = AssetSpec.model_validate(item)
        except Exception:
            continue
        if _slug(spec.name):
            specs.append(spec)
    return specs


def _sanitize_svg(text: str) -> tuple[str, str] | None:
    """Return ``(view_box, inner_markup)`` from an SVG string, stripped of anything
    unsafe or unsupported. Returns ``None`` if there is no usable shape content."""
    if not text:
        return None
    match = _SVG_TAG.search(text)
    if not match:
        return None
    view_box_match = _VIEWBOX.search(match.group(0))
    view_box = view_box_match.group(1) if view_box_match else "0 0 100 100"
    inner = match.group(1)
    inner = _BAD_TAGS.sub("", inner)
    inner = _ON_ATTR.sub("", inner)
    inner = _JS_URI.sub("", inner).strip()
    # need at least one real shape element
    if not re.search(r"<(path|rect|circle|ellipse|polygon|polyline|line|g)\b", inner, re.IGNORECASE):
        return None
    return view_box, inner


def _house_card(view_box: str, inner: str) -> tuple[str, str]:
    """Wrap a bare glyph in the app's rounded-card style at viewBox 0 0 100 100."""
    card = (
        '<rect x="6" y="6" width="88" height="88" rx="18" fill="#334155"/>'
        f'<svg x="20" y="20" width="60" height="60" viewBox="{view_box}" '
        'preserveAspectRatio="xMidYMid meet">'
        f"{inner}</svg>"
    )
    return "0 0 100 100", card


def _generated_dir(settings: Settings) -> Path:
    path = Path(settings.generated_assets_dir)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / settings.generated_assets_dir
    return path


# ------------------------------ acquisition ----------------------------------

def _prefer(icons: list[str]) -> str:
    for pref in _PREFERRED:
        for icon in icons:
            if icon.startswith(pref + ":"):
                return icon
    return icons[0]


async def _from_iconify(client: httpx.AsyncClient, base: str, query: str) -> tuple[str, str] | None:
    try:
        resp = await client.get(f"{base}/search", params={"query": query, "limit": 32})
        resp.raise_for_status()
        icons = resp.json().get("icons") or []
    except Exception:
        return None
    if not icons:
        return None
    prefix, _, name = _prefer(icons).partition(":")
    if not prefix or not name:
        return None
    try:
        resp = await client.get(f"{base}/{prefix}/{name}.svg", params={"color": "#e2e8f0", "height": 96})
        resp.raise_for_status()
        parsed = _sanitize_svg(resp.text)
    except Exception:
        return None
    if parsed is None:
        return None
    return _house_card(*parsed)


async def _from_llm(gateway: LLMGateway, spec: AssetSpec) -> tuple[str, str] | None:
    subject = spec.label or spec.name
    try:
        raw, _ = await gateway.complete(build_svg_prompt(subject, spec.query), subject)
    except Exception:
        return None
    return _sanitize_svg(raw)


async def _acquire(
    client: httpx.AsyncClient, gateway: LLMGateway, spec: AssetSpec, settings: Settings
) -> tuple[str, str] | None:
    query = spec.query or spec.label or spec.name
    found = await _from_iconify(client, settings.iconify_base, query)
    if found is not None:
        return found
    return await _from_llm(gateway, spec)


# --------------------------------- public ------------------------------------

async def _forge_specs(
    specs: list[AssetSpec], gateway: LLMGateway, registry: AssetRegistry, settings: Settings
) -> list[str]:
    """Acquire an icon for each concrete spec; skip abstract or already-present ones."""
    specs = [s for s in specs if _slug(s.name) and not _is_abstract(s)][: settings.asset_forge_max]
    if not specs:
        return []
    gen_dir = _generated_dir(settings)
    gen_dir.mkdir(parents=True, exist_ok=True)
    new_types: list[str] = []
    async with httpx.AsyncClient(
        timeout=settings.asset_forge_timeout, follow_redirects=True
    ) as client:
        for spec in specs:
            slug = _slug(spec.name)
            type_ = f"generated.{slug}"
            path = gen_dir / f"{slug}.svg"
            if registry.has(type_) or path.exists():
                continue
            acquired = await _acquire(client, gateway, spec, settings)
            if acquired is None:
                continue
            view_box, inner = acquired
            path.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">\n{inner}\n</svg>\n',
                encoding="utf-8",
            )
            new_types.append(type_)
    return new_types


async def forge_assets(
    gateway: LLMGateway, script: str, registry: AssetRegistry, settings: Settings
) -> list[str]:
    """Plan (via LLM) and acquire the concrete icons a ``script`` needs.

    Never raises on network/LLM failure — returns whatever it managed to create.
    """
    if not settings.enable_asset_forge:
        return []
    existing = [a.label for a in registry.all()]
    try:
        raw, _ = await gateway.complete(build_asset_manifest_prompt(script, existing), script)
        specs = parse_manifest(raw)
    except Exception:
        specs = []
    return await _forge_specs(specs, gateway, registry, settings)


async def forge_for_cast(
    cast, gateway: LLMGateway, registry: AssetRegistry, settings: Settings
) -> list[str]:
    """Forge scene-accurate icons for director cast members still on a generic asset.

    Runs AFTER the director, so visuals match exactly what the scene shows (each
    object's label becomes the search query) instead of a pre-guessed manifest.
    """
    if not settings.enable_asset_forge:
        return []
    specs: list[AssetSpec] = []
    seen: set[str] = set()
    for obj in cast:
        label = (getattr(obj, "label", "") or "").strip()
        if not label:
            continue
        # already have a good (non-generic) icon for what this object is?
        if any(m not in _GENERIC_TYPES for m in registry.match(label)):
            continue
        slug = _slug(label)
        if slug and slug not in seen and not registry.has(f"generated.{slug}"):
            seen.add(slug)
            specs.append(AssetSpec(name=slug, label=label, query=label))
    return await _forge_specs(specs, gateway, registry, settings)
