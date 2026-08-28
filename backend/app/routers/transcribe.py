"""Audio transcription endpoint."""
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.api import TranscriptionResponse
from app.stt import whisper_stt

router = APIRouter(prefix="/api", tags=["transcribe"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(file: UploadFile = File(...)) -> TranscriptionResponse:
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Audio exceeds {settings.max_upload_mb} MB limit.",
        )

    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    try:
        text, duration, language = await asyncio.to_thread(
            whisper_stt.transcribe_bytes, data, suffix
        )
    except whisper_stt.STTUnavailable:
        try:
            text, duration, language = await whisper_stt.openai_transcribe(
                data, file.filename or f"audio{suffix}"
            )
        except whisper_stt.STTUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return TranscriptionResponse(text=text, duration=duration, language=language)
