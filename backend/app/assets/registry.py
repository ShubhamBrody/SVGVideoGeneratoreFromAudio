"""Loads the SVG asset library from disk and exposes it to the rest of the app.

Each ``.svg`` file under ``assets/<category>/<name>.svg`` becomes an asset with
type ``<category>.<name>``. The registry provides:

* the list of available types (fed to the LLM prompt so it only picks real assets),
* keyword matching (used by the offline mock generator),
* the raw inner SVG markup + viewBox (served to the frontend for inline rendering).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

# Keyword hints per asset type: used by the offline matcher and shown to the LLM.
KEYWORDS: dict[str, list[str]] = {
    "kubernetes.pod": ["pod", "pods"],
    "kubernetes.service": ["kubernetes service", "k8s service", "service"],
    "kubernetes.node": ["worker node", "k8s node", "node"],
    "kubernetes.kubelet": ["kubelet"],
    "kubernetes.deployment": ["deployment", "replicaset", "replica set"],
    "networking.client": ["client", "browser", "frontend", "web app"],
    "networking.server": ["web server", "app server", "backend server", "server", "backend"],
    "networking.load_balancer": ["load balancer", "load-balancer", "nginx", "haproxy", "lb"],
    "networking.api_gateway": ["api gateway", "api-gateway", "gateway", "ingress"],
    "networking.user": ["user", "customer", "person", "actor", "passenger", "driver", "client app"],
    "databases.postgres": ["postgres", "postgresql"],
    "databases.mysql": ["mysql", "mariadb"],
    "databases.mongodb": ["mongodb", "mongo", "document db"],
    "databases.redis": ["redis"],
    "messaging.kafka": ["kafka cluster", "kafka", "event stream", "event streaming"],
    "messaging.kafka_broker": ["kafka broker", "broker", "brokers"],
    "messaging.topic": ["kafka topic", "topic", "log"],
    "messaging.partition": ["partition", "partitions"],
    "messaging.coordinator": ["group coordinator", "coordinator", "controller"],
    "messaging.queue": ["message queue", "rabbitmq", "sqs", "queue", "mq"],
    "messaging.producer": ["producer", "publisher"],
    "messaging.consumer": ["consumer group", "consumer", "subscriber"],
    "cloud.s3": ["s3", "object storage", "blob storage", "bucket"],
    "cloud.lambda": ["lambda", "serverless", "cloud function"],
    "cloud.ec2": ["ec2", "virtual machine", "compute instance", "vm"],
    "generic.box": ["component", "module", "subsystem", "box"],
    "generic.database": ["database", "datastore", "db", "storage"],
    "generic.cache": ["cache", "caching layer"],
    "generic.cloud": ["cloud", "the internet"],
    "ai.model": ["neural network", "neural net", "language model", "transformer", "ml model", "llm", "the model", "model", "inference"],
    "ai.gpu": ["gpu", "graphics card"],
    "ai.dataset": ["dataset", "training data", "training set", "data set", "labeled data", "batch"],
    "ai.agent": ["agent"],
    "ai.embedding": ["embedding", "embeddings", "embed", "embeds", "vectors", "vector space"],
    "ai.vector_db": ["vector database", "vector store", "vector db"],
    "ai.retriever": ["retriever", "retrieval", "reranker", "rerank", "nearest neighbor", "nearest-neighbor"],
    "ai.document": ["document", "documents", "chunk", "chunks", "passage", "passages", "knowledge base"],
    "security.lock": ["encryption", "encrypt", "encrypted", "tls", "cipher", "ciphertext", "padlock"],
    "security.key": ["private key", "public key", "api key", "secret", "credential", "credentials"],
    "security.shield": ["zero-trust", "zero trust", "shield", "authorization server", "multi-factor", "guardrail"],
    "security.firewall": ["firewall", "web application firewall", "waf"],
    "networking.cdn": ["cdn", "edge server", "edge location", "content delivery", "edge"],
}

LABEL_OVERRIDES: dict[str, str] = {
    "networking.api_gateway": "API Gateway",
    "networking.load_balancer": "Load Balancer",
    "networking.cdn": "CDN",
    "cloud.s3": "S3",
    "cloud.ec2": "EC2",
    "cloud.lambda": "Lambda",
    "ai.gpu": "GPU",
    "ai.model": "Model",
    "ai.vector_db": "Vector DB",
    "databases.mysql": "MySQL",
    "databases.postgres": "PostgreSQL",
    "databases.mongodb": "MongoDB",
    "databases.redis": "Redis",
    "kubernetes.kubelet": "Kubelet",
    "messaging.kafka": "Kafka",
    "messaging.kafka_broker": "Kafka Broker",
}

_VIEWBOX_RE = re.compile(r'viewBox="([^"]+)"')


@dataclass(frozen=True)
class Asset:
    type: str
    label: str
    category: str
    keywords: list[str]
    view_box: str
    svg: str  # inner markup (children of the <svg> root)


def _default_label(name: str) -> str:
    return name.replace("_", " ").title()


def _parse_svg(text: str) -> tuple[str, str]:
    """Return ``(view_box, inner_markup)`` for an SVG document."""
    match = _VIEWBOX_RE.search(text)
    view_box = match.group(1) if match else "0 0 100 100"
    open_end = text.find(">", text.find("<svg"))
    close = text.rfind("</svg>")
    if open_end == -1 or close == -1:
        return view_box, text
    return view_box, text[open_end + 1 : close].strip()


class AssetRegistry:
    def __init__(self, assets_dir: Path) -> None:
        self._dir = assets_dir
        self._assets: dict[str, Asset] = {}

    def load(self) -> AssetRegistry:
        self._assets.clear()
        if not self._dir.exists():
            return self
        for svg_path in sorted(self._dir.glob("*/*.svg")):
            category = svg_path.parent.name
            name = svg_path.stem
            type_ = f"{category}.{name}"
            view_box, inner = _parse_svg(svg_path.read_text(encoding="utf-8"))
            self._assets[type_] = Asset(
                type=type_,
                label=LABEL_OVERRIDES.get(type_, _default_label(name)),
                category=category,
                keywords=KEYWORDS.get(type_, [name.replace("_", " ")]),
                view_box=view_box,
                svg=inner,
            )
        return self

    def all(self) -> list[Asset]:
        return list(self._assets.values())

    def types(self) -> list[str]:
        return list(self._assets.keys())

    def categories(self) -> list[str]:
        return sorted({a.category for a in self._assets.values()})

    def get(self, type_: str) -> Asset | None:
        return self._assets.get(type_)

    def has(self, type_: str) -> bool:
        return type_ in self._assets

    def match(self, text: str) -> list[str]:
        """Return asset types whose keywords occur in ``text``, ordered by position."""
        text_l = text.lower()
        hits: list[tuple[int, str]] = []
        for type_, asset in self._assets.items():
            for kw in asset.keywords:
                idx = text_l.find(kw)
                if idx != -1:
                    hits.append((idx, type_))
                    break
        hits.sort()
        return [t for _, t in hits]

    def resolve(self, type_: str) -> str:
        """Map an arbitrary/unknown asset type to the closest known one."""
        if type_ in self._assets:
            return type_
        t = (type_ or "").lower().strip().replace("/", ".")
        for known in self._assets:
            if known == t or known.split(".", 1)[1] == t:
                return known
        for known, asset in self._assets.items():
            if any(kw in t or t in kw for kw in asset.keywords):
                return known
        return "generic.box"


@lru_cache
def get_registry() -> AssetRegistry:
    settings = get_settings()
    base = Path(settings.assets_dir)
    if not base.is_absolute():
        base = Path(__file__).resolve().parents[2] / settings.assets_dir
    return AssetRegistry(base).load()
