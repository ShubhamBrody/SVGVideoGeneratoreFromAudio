"""Asset manifest and raw SVG endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.assets.registry import get_registry
from app.models.api import AssetInfo, AssetManifest

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=AssetManifest)
async def list_assets() -> AssetManifest:
    registry = get_registry()
    assets = [
        AssetInfo(
            type=a.type,
            label=a.label,
            category=a.category,
            keywords=a.keywords,
            view_box=a.view_box,
            svg=a.svg,
        )
        for a in registry.all()
    ]
    return AssetManifest(assets=assets, categories=registry.categories())


@router.get("/{asset_type}/svg")
async def get_asset_svg(asset_type: str) -> Response:
    asset = get_registry().get(asset_type)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Unknown asset '{asset_type}'.")
    document = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{asset.view_box}">{asset.svg}</svg>'
    )
    return Response(content=document, media_type="image/svg+xml")
