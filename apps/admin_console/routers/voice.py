# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# https://www.apache.org/licenses/LICENSE-2.0

"""Same-origin browser voice controls and audio proxies."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from apps.admin_console.schemas.voice_schema import SpeechRequest, VoiceSettings
from apps.admin_console.services.voice_service import MAX_AUDIO_BYTES, voice_service
from apps.admin_console.database.connection import db_session
from apps.admin_console.database.repositories.session_repository import session_repo
from apps.admin_console.core.state import state
from artemis.runtime import trace_store


router = APIRouter(tags=["voice"])
ASSETS = Path(__file__).resolve().parent.parent / "voice"


@router.get("/voice", include_in_schema=False)
async def voice_page():
    return FileResponse(ASSETS / "index.html", headers={"Cache-Control": "no-store"})


@router.get("/voice/{asset}", include_in_schema=False)
async def voice_asset(asset: str):
    if asset not in {"voice.js", "audio.js", "capture-worklet.js", "style.css"}:
        raise HTTPException(404, "Unknown voice asset")
    return FileResponse(ASSETS / asset, headers={"Cache-Control": "no-store"})


@router.get("/api/voice/settings")
async def get_settings():
    return await asyncio.to_thread(voice_service.load)


@router.put("/api/voice/settings")
async def save_settings(settings: VoiceSettings):
    return await asyncio.to_thread(voice_service.save, settings)


@router.post("/api/voice/transcribe")
async def transcribe(file: UploadFile = File(...)):
    try:
        audio = await file.read(MAX_AUDIO_BYTES + 1)
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(413, "音频超过 12 MiB 限制")
        return {"text": await voice_service.transcribe(audio, "voice.wav")}
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        await file.close()


@router.post("/api/voice/speech")
async def speech(request: SpeechRequest):
    try:
        audio = await voice_service.synthesize(request.text)
        return Response(audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc


def read_final_report(session_id: str) -> dict:
    with db_session() as connection:
        rows = connection.execute(
            "SELECT action_taken FROM steps WHERE session_id = ? ORDER BY step_number DESC LIMIT 5",
            (session_id,),
        ).fetchall()
    for row in rows:
        try:
            action = json.loads(row["action_taken"] or "{}")
        except (ValueError, TypeError):
            continue
        if isinstance(action, dict) and action.get("action") == "report_task_status":
            args = action.get("args")
            if isinstance(args, dict):
                return args
    return {}


def task_details(session_id: str) -> dict:
    row = session_repo.get_session_by_id(session_id)
    if not row:
        queued = next(
            (item for item in state.queue_items if item.get("session_id") == session_id), None
        )
        if queued:
            return {
                "session_id": session_id,
                "status": queued.get("status", "pending"),
                "message": "",
            }
        raise HTTPException(404, "语音任务尚未创建或不存在")
    status = row.get("status", "unknown")
    message = ""
    if status in {"completed", "success", "failed", "cancelled", "stopped"}:
        report = read_final_report(session_id)
        message = report.get("explanation") or report.get("details") or report.get("summary") or ""
        if not message:
            trace = trace_store.read_status(session_id) or {}
            message = trace.get("error") or ""
        if status in {"completed", "success"} and report.get("status") == "failed":
            status = "failed"
    return {"session_id": session_id, "status": status, "message": str(message)[:2000]}


@router.get("/api/voice/tasks/{session_id}")
async def voice_task(session_id: str):
    return await asyncio.to_thread(task_details, session_id)
