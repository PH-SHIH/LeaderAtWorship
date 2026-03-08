from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.router import api_router
from app.api.ws.projection import router as ws_router
from app.database import init_db
from app.utils.file_helpers import ensure_data_dirs

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_dirs()
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LeaderAtWorship",
        version="0.1.0",
        description="敬拜字幕生成與即時投影控制工具",
        lifespan=lifespan,
    )

    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/")
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/projection/display/{session_id}")
    async def projection_display(request: Request, session_id: int):
        return templates.TemplateResponse(
            "projection/display.html",
            {"request": request, "session_id": session_id},
        )

    @app.get("/projection/control/{session_id}")
    async def projection_control(request: Request, session_id: int):
        return templates.TemplateResponse(
            "projection/control.html",
            {"request": request, "session_id": session_id},
        )

    @app.get("/songs")
    async def songs_page(request: Request):
        return templates.TemplateResponse("songs/list.html", {"request": request})

    @app.get("/flows")
    async def flows_page(request: Request):
        return templates.TemplateResponse("flows/editor.html", {"request": request})

    @app.get("/audio")
    async def audio_page(request: Request):
        return templates.TemplateResponse("audio/process.html", {"request": request})

    return app


app = create_app()
