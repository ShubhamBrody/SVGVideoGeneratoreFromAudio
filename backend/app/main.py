"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup and shutdown hooks are wired here as subsystems come online
    # (asset registry, LLM gateway, STT engine).
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
        return {
            "status": "ok",
            "service": "svg-video-generator",
            "version": __version__,
        }

    return app


app = create_app()
