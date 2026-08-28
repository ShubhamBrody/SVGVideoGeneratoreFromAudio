"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.assets.registry import get_registry
from app.config import get_settings
from app.llm.gateway import build_gateway
from app.routers import assets, scene, transcribe, ws
from app.scene.generator import SceneGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry = get_registry()
    gateway = await build_gateway(settings, registry)
    app.state.registry = registry
    app.state.gateway = gateway
    app.state.generator = SceneGenerator(gateway, registry)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SVG Video Generator From Audio",
        version=__version__,
        summary="Turn spoken technical concepts into deterministic animated SVG diagrams.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        gateway = getattr(app.state, "gateway", None)
        return {
            "status": "ok",
            "service": "svg-video-generator",
            "version": __version__,
            "provider": gateway.provider_name if gateway else "unknown",
        }

    app.include_router(assets.router)
    app.include_router(scene.router)
    app.include_router(transcribe.router)
    app.include_router(ws.router)
    return app


app = create_app()
