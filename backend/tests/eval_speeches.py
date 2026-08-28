"""Evaluation harness for the speech corpus.

Runs every speech in tests/speeches.py through the SceneGenerator and reports, per
domain and overall: validity, pacing (beats vs sentences, video length), and
ASSET COVERAGE (share of objects that map to a real icon vs a generic fallback).
Coverage is the key signal for "does it mold to any topic, or fall back to boxes?".

Usage (from backend/):
    python -m tests.eval_speeches mock            # full suite, offline/deterministic
    python -m tests.eval_speeches ollama 12       # first 12 through the local LLM
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from collections import Counter, defaultdict

_MODE = sys.argv[1] if len(sys.argv) > 1 else "mock"
_SEL = sys.argv[2] if len(sys.argv) > 2 else None
os.environ["LLM_PROVIDER"] = _MODE
if _MODE == "mock":
    os.environ["OPENAI_API_KEY"] = ""

from app.assets.registry import get_registry  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.llm.gateway import build_gateway  # noqa: E402
from app.scene.generator import SceneGenerator  # noqa: E402
from tests.speeches import SPEECHES  # noqa: E402

_GENERIC = {"generic.box", "generic.database", "generic.cache"}


def _sentences(text: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()])


def _metrics(scene, text: str, provider: str, gen_s: float) -> dict:
    obj_ids = {o.id for o in scene.objects}
    edge_ids = {e.id for e in scene.edges}
    n_obj = len(scene.objects)
    generic = [o for o in scene.objects if o.type in _GENERIC]
    coverage = (n_obj - len(generic)) / n_obj if n_obj else 0.0
    narrate = [s for s in scene.timeline if s.action.value == "narrate"]
    video = max((s.at + s.duration for s in scene.timeline), default=0.0)
    edges_ok = all(e.from_ in obj_ids and e.to in obj_ids for e in scene.edges)
    ats = [s.at for s in scene.timeline]
    return {
        "valid": n_obj > 0 and len(scene.timeline) > 0,
        "real_llm": provider == "ollama" or provider == "openai",
        "objects": n_obj,
        "edges": len(scene.edges),
        "steps": len(scene.timeline),
        "beats": len(narrate),
        "sentences": _sentences(text),
        "video": video,
        "warnings": len(scene.warnings),
        "coverage": coverage,
        "gen_s": gen_s,
        "consistent": edges_ok and ats == sorted(ats),
        "generic_labels": [o.label for o in generic],
    }


async def main() -> None:
    settings = get_settings()
    registry = get_registry()
    gateway = await build_gateway(settings, registry)
    generator = SceneGenerator(gateway, registry)

    speeches = SPEECHES
    if _SEL == "diverse":  # one speech per domain
        seen: set[str] = set()
        speeches = [s for s in SPEECHES if not (s["domain"] in seen or seen.add(s["domain"]))]
    elif _SEL:
        speeches = SPEECHES[: int(_SEL)]
    print(f"Running {len(speeches)} speeches | provider={gateway.provider_name} "
          f"| model={settings.ollama_model}\n")

    by_domain: dict[str, list[dict]] = defaultdict(list)
    generic_counter: Counter = Counter()
    t0 = time.perf_counter()

    for i, item in enumerate(speeches, 1):
        start = time.perf_counter()
        scene, provider = await generator.generate(item["text"])
        m = _metrics(scene, item["text"], provider, time.perf_counter() - start)
        by_domain[item["domain"]].append(m)
        generic_counter.update(m["generic_labels"])
        if _MODE != "mock":
            print(f"  [{i:3}/{len(speeches)}] {item['domain']:12} "
                  f"obj={m['objects']} beats={m['beats']} video={m['video']:.0f}s "
                  f"cov={m['coverage']*100:.0f}% {m['gen_s']:.1f}s")

    total_s = time.perf_counter() - t0

    def avg(rows, key):
        return sum(r[key] for r in rows) / len(rows) if rows else 0.0

    print(f"\n{'domain':14} {'n':>3} {'valid':>6} {'obj':>5} {'beats':>6} "
          f"{'video':>6} {'cover':>6} {'consist':>8}")
    print("-" * 62)
    all_rows: list[dict] = []
    for domain in sorted(by_domain):
        rows = by_domain[domain]
        all_rows.extend(rows)
        print(f"{domain:14} {len(rows):>3} "
              f"{sum(r['valid'] for r in rows) / len(rows) * 100:>5.0f}% "
              f"{avg(rows, 'objects'):>5.1f} {avg(rows, 'beats'):>6.1f} "
              f"{avg(rows, 'video'):>5.0f}s {avg(rows, 'coverage') * 100:>5.0f}% "
              f"{sum(r['consistent'] for r in rows) / len(rows) * 100:>7.0f}%")

    print("-" * 62)
    print(f"{'OVERALL':14} {len(all_rows):>3} "
          f"{sum(r['valid'] for r in all_rows) / len(all_rows) * 100:>5.0f}% "
          f"{avg(all_rows, 'objects'):>5.1f} {avg(all_rows, 'beats'):>6.1f} "
          f"{avg(all_rows, 'video'):>5.0f}s {avg(all_rows, 'coverage') * 100:>5.0f}% "
          f"{sum(r['consistent'] for r in all_rows) / len(all_rows) * 100:>7.0f}%")

    real = sum(r["real_llm"] for r in all_rows)
    print(f"\nreal-LLM scenes: {real}/{len(all_rows)} | "
          f"beats~=sentences: {sum(1 for r in all_rows if abs(r['beats'] - r['sentences']) <= 2)}"
          f"/{len(all_rows)} | avg gen {avg(all_rows, 'gen_s'):.2f}s | wall {total_s:.1f}s")
    print("\nTop concepts falling back to a generic icon (add assets for these):")
    for label, count in generic_counter.most_common(18):
        print(f"  {count:>3}  {label}")


if __name__ == "__main__":
    asyncio.run(main())
