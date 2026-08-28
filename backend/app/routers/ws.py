"""Real-time scene generation over WebSocket.

The client sends ``{ "text": "..." }`` and receives a ``status`` message followed
by a ``scene`` message (or an ``error``). This mirrors the REST ``/api/generate``
endpoint but keeps the connection open for the conversational, real-time feel.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.scene.generator import SceneGenerationError, SceneGenerator

router = APIRouter()


@router.websocket("/ws")
async def scene_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    generator: SceneGenerator = websocket.app.state.generator
    try:
        while True:
            message = await websocket.receive_json()
            text = (message or {}).get("text", "").strip()
            if not text:
                await websocket.send_json({"type": "error", "message": "Empty text."})
                continue

            await websocket.send_json({"type": "status", "message": "Generating scene\u2026"})
            try:
                scene, provider = await generator.generate(text)
            except SceneGenerationError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            await websocket.send_json(
                {
                    "type": "scene",
                    "provider": provider,
                    "scene": scene.model_dump(by_alias=True),
                }
            )
    except WebSocketDisconnect:
        return
