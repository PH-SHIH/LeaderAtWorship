from fastapi import APIRouter

from app.api.v1 import audio, flows, projection, songs, subtitles

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(songs.router, prefix="/songs", tags=["songs"])
api_router.include_router(subtitles.router, prefix="/subtitles", tags=["subtitles"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(flows.router, prefix="/flows", tags=["flows"])
api_router.include_router(projection.router, prefix="/projection", tags=["projection"])
