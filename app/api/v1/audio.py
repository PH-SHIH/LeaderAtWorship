from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.schemas.projection import AudioExtractRequest, TaskResponse
from app.tasks.audio_pipeline import run_audio_pipeline
from app.tasks.task_store import task_store

router = APIRouter()


@router.post("/extract", response_model=TaskResponse)
async def extract_audio(
    request: AudioExtractRequest,
    background_tasks: BackgroundTasks,
):
    """Submit a YouTube URL for audio extraction and transcription."""
    task_id = str(uuid4())
    task_store[task_id] = {"status": "pending", "progress": 0}

    background_tasks.add_task(
        run_audio_pipeline, task_id, request.url, request.whisper_model
    )

    return TaskResponse(task_id=task_id, status="pending")


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks():
    """List all in-memory tasks (most recent first)."""
    return [
        TaskResponse(
            task_id=tid,
            status=t["status"],
            progress=t.get("progress", 0),
            error=t.get("error"),
            result_id=t.get("result_id"),
            song_id=t.get("song_id"),
            video_title=t.get("video_title"),
            detail=t.get("detail"),
        )
        for tid, t in reversed(list(task_store.items()))
    ]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """Poll the status of a specific task."""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress", 0),
        error=task.get("error"),
        result_id=task.get("result_id"),
        song_id=task.get("song_id"),
        video_title=task.get("video_title"),
        detail=task.get("detail"),
    )


@router.get("/tasks/{task_id}/download")
async def download_result(task_id: str):
    """Download the generated SRT file for a completed task."""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not yet completed")

    result_id = task.get("result_id")
    if not result_id:
        raise HTTPException(status_code=404, detail="No result file")

    from app.database import async_session_factory
    from app.models.subtitle import SubtitleFile

    async with async_session_factory() as session:
        subtitle_file = await session.get(SubtitleFile, result_id)
        if not subtitle_file:
            raise HTTPException(status_code=404, detail="Subtitle file not found")

        file_path = Path(subtitle_file.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(
            path=file_path,
            filename=subtitle_file.filename,
            media_type="text/plain",
        )


@router.get("/stream/{song_id}")
async def stream_audio(song_id: int, track: str = "original", request: Request = None):
    """Stream audio file with HTTP Range request support for seeking."""
    from app.database import async_session_factory
    from app.models.song import Song

    async with async_session_factory() as session:
        song = await session.get(Song, song_id)
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        # Copy values before session closes
        if track == "vocals" and song.vocals_path:
            audio_path_str = song.vocals_path
        elif track == "accompaniment" and song.accompaniment_path:
            audio_path_str = song.accompaniment_path
        else:
            audio_path_str = song.audio_path
        if not audio_path_str:
            raise HTTPException(status_code=404, detail="No audio file for this song")

    file_path = Path(audio_path_str)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range") if request else None

    if range_header:
        # Parse "bytes=start-end"
        range_spec = range_header.replace("bytes=", "")
        range_parts = range_spec.split("-")
        start = int(range_parts[0]) if range_parts[0] else 0
        end = int(range_parts[1]) if range_parts[1] else file_size - 1
        content_length = end - start + 1

        async def stream_range():
            async with aiofiles.open(file_path, "rb") as f:
                await f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    data = await f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            stream_range(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": "audio/wav",
            },
        )
    else:
        return FileResponse(
            path=file_path,
            media_type="audio/wav",
            headers={"Accept-Ranges": "bytes"},
        )
