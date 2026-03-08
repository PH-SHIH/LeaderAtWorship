# LeaderAtWorship 開發者文件

> 版本：1.0 | 更新日期：2026-03-08

## 1. 開發環境設定

### 1.1 前置需求

```bash
# macOS Apple Silicon
brew install ffmpeg python@3.12
```

### 1.2 專案設定

```bash
git clone <repo-url>
cd LeaderAtWorship

# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝所有依賴（含 ML + 開發工具）
pip install -e ".[ml,dev]"

# 環境設定
cp .env.example .env

# 初始化資料庫
mkdir -p data/db data/audio data/exports data/models
alembic upgrade head
```

### 1.3 啟動開發伺服器

```bash
uvicorn app.main:app --reload --port 8000
```

`--reload` 會自動偵測程式碼變更並重啟。

### 1.4 依賴分組

`pyproject.toml` 定義了三組依賴：

| 分組 | 安裝指令 | 內容 |
|------|---------|------|
| 核心 | `pip install -e .` | FastAPI, SQLAlchemy, yt-dlp 等 |
| ML | `pip install -e ".[ml]"` | mlx-whisper, demucs, torch |
| Dev | `pip install -e ".[dev]"` | pytest, ruff |

---

## 2. 專案結構

```
app/
├── main.py              # 應用程式進入點 (create_app)
├── config.py            # 環境設定 (Settings class)
├── database.py          # SQLAlchemy 引擎 & async session
├── api/
│   ├── deps.py          # 依賴注入 (get_db)
│   ├── v1/
│   │   ├── router.py    # API 路由彙總
│   │   ├── songs.py     # 歌曲 CRUD
│   │   ├── subtitles.py # 字幕管理 + 行編輯
│   │   ├── audio.py     # 音頻處理 + 串流
│   │   ├── flows.py     # 敬拜流程
│   │   └── projection.py # 投影 Session
│   └── ws/
│       └── projection.py # WebSocket 端點
├── models/              # SQLAlchemy ORM 模型
│   ├── song.py          # Song, SongLyrics, LyricsLine
│   ├── subtitle.py      # SubtitleFile, SubtitleLine
│   ├── worship_flow.py  # WorshipFlow, FlowItem
│   └── session.py       # ProjectionSession
├── schemas/             # Pydantic 請求/回應模型
├── services/            # 業務邏輯
│   ├── youtube.py       # YouTube 下載
│   ├── separator.py     # Demucs 人聲分離
│   ├── transcriber.py   # mlx-whisper 語音辨識
│   ├── lyrics_fetcher.py    # 線上歌詞搜尋
│   ├── lyrics_aligner.py   # 錨點式對齊
│   ├── subtitle_generator.py # SRT/VTT 產生
│   └── projection_manager.py # 投影狀態管理
├── tasks/
│   ├── audio_pipeline.py # 音頻處理管線編排
│   └── task_store.py    # In-memory 任務追蹤
├── utils/               # 工具函式
├── templates/           # Jinja2 HTML 模板
└── static/              # CSS / JS 靜態資源
```

---

## 3. 核心模式與慣例

### 3.1 非同步資料庫操作

所有 DB 操作使用 `async/await`，透過依賴注入取得 session：

```python
from app.api.deps import get_db

@router.get("/songs")
async def list_songs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Song).order_by(Song.created_at.desc()))
    songs = result.scalars().all()
    return songs
```

### 3.2 Eager Loading

使用 `selectinload` 預載入關聯資料，避免 N+1 問題：

```python
from sqlalchemy.orm import selectinload

stmt = (
    select(WorshipFlow)
    .options(selectinload(WorshipFlow.items).selectinload(FlowItem.song))
    .where(WorshipFlow.id == flow_id)
)
result = await db.execute(stmt)
flow = result.scalar_one_or_none()
```

### 3.3 背景任務

使用 FastAPI 的 `BackgroundTasks` 或 `asyncio.create_task`：

```python
@router.post("/audio/extract")
async def extract_audio(req: AudioExtractRequest):
    task_id = str(uuid4())
    task_store[task_id] = {"status": "pending", "progress": 0}
    asyncio.create_task(run_audio_pipeline(task_id, req.url))
    return {"task_id": task_id}
```

### 3.4 Pydantic Schema 慣例

```python
# Request schema (Create)
class SongCreate(BaseModel):
    title: str
    artist: str = ""

# Response schema
class SongResponse(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)

# Update schema (all fields optional)
class SongUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
```

### 3.5 環境設定存取

```python
from app.config import settings

model = settings.whisper_model
device = settings.demucs_device
```

---

## 4. 資料庫遷移

### 4.1 建立新遷移

```bash
# 修改 models 後自動產生遷移腳本
alembic revision --autogenerate -m "描述改動"

# 檢查產生的遷移腳本
cat alembic/versions/xxxx_*.py
```

### 4.2 套用遷移

```bash
# 升級到最新版本
alembic upgrade head

# 降級一個版本
alembic downgrade -1

# 查看目前版本
alembic current
```

### 4.3 遷移注意事項

- SQLite 不支援 `ALTER COLUMN` — 需要使用 `batch_alter_table`
- 新增 nullable 欄位不需要預設值
- 新增 NOT NULL 欄位需要提供 `server_default`

```python
# SQLite 相容的 batch migration
with op.batch_alter_table('songs') as batch_op:
    batch_op.add_column(sa.Column('accompaniment_path', sa.String(500)))
```

---

## 5. 新增功能指南

### 5.1 新增 API 端點

1. **建立 schema**（`app/schemas/`）：

```python
# app/schemas/new_feature.py
class NewFeatureCreate(BaseModel):
    name: str

class NewFeatureResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
```

2. **建立 API 路由**（`app/api/v1/`）：

```python
# app/api/v1/new_feature.py
router = APIRouter(prefix="/new-feature", tags=["new-feature"])

@router.post("/", status_code=201)
async def create(data: NewFeatureCreate, db: AsyncSession = Depends(get_db)):
    ...
```

3. **註冊路由**（`app/api/v1/router.py`）：

```python
from app.api.v1.new_feature import router as new_feature_router
api_router.include_router(new_feature_router)
```

### 5.2 新增 ORM 模型

1. 在 `app/models/` 建立模型檔案
2. 在 `app/database.py` 確認 Base metadata 會載入
3. 執行 `alembic revision --autogenerate -m "add new_feature table"`
4. 檢查並套用遷移

### 5.3 新增頁面

1. 建立模板（`app/templates/new_feature/page.html`）
2. 在 `app/main.py` 加入頁面路由：

```python
@app.get("/new-feature")
async def new_feature_page(request: Request):
    return templates.TemplateResponse("new_feature/page.html", {"request": request})
```

---

## 6. 音頻處理管線擴充

### 6.1 管線架構

`app/tasks/audio_pipeline.py` 中的 `run_audio_pipeline()` 是主編排函式：

```python
async def run_audio_pipeline(task_id, youtube_url, whisper_model=None):
    try:
        # Step 1: Download (10-25%)
        dl_result = await youtube.download_audio(youtube_url)

        # Step 2: Separate (30-55%)
        vocals_path, accompaniment_path = await separator.separate(dl_result.audio_path)

        # Step 3: Transcribe (60-85%)
        segments = await transcriber.transcribe(vocals_path)

        # Step 4: Align (85-90%) — optional
        if settings.alignment_enabled:
            lyrics = await lyrics_fetcher.fetch_lyrics(title, artist)
            if lyrics:
                result = lyrics_aligner.align(segments, lyrics.lines)
                # Apply alignment if quality passes

        # Step 5: Generate SRT (90%)
        srt_content = subtitle_generator.generate_srt(final_segments)

        # Step 6: Persist to DB (95-100%)
        # Create Song, SubtitleFile, SubtitleLine records
    except Exception as e:
        task_store[task_id]["status"] = "failed"
        task_store[task_id]["error"] = str(e)
```

### 6.2 新增處理步驟

在管線中加入新步驟：

1. 建立服務模組（`app/services/new_step.py`）
2. 在 `audio_pipeline.py` 的適當位置呼叫
3. 更新進度百分比

---

## 7. WebSocket 開發

### 7.1 ProjectionManager

`app/services/projection_manager.py` 管理所有投影 Session 的狀態：

```python
# 全域單例
projection_manager = ProjectionManager()

# 連線管理
projection_manager.connect(session_id, websocket, role="controller")

# 處理指令
await projection_manager.handle_command(session_id, {"action": "next_line"})

# 廣播狀態
await projection_manager.broadcast(session_id, {
    "type": "state_update",
    "data": state.to_dict()
})
```

### 7.2 新增指令

在 `handle_command()` 中加入新的 action 處理：

```python
async def handle_command(self, session_id: int, command: dict):
    action = command.get("action")
    state = self._state[session_id]

    if action == "new_action":
        # 處理新指令
        ...

    # 更新文字
    self._resolve_text(session_id, state)
    # 廣播
    await self.broadcast(session_id, {"type": "state_update", "data": ...})
```

---

## 8. 測試

### 8.1 執行測試

```bash
# 全部測試
pytest

# 特定測試
pytest tests/test_api/test_songs.py

# 顯示詳細輸出
pytest -v

# 包含覆蓋率
pytest --cov=app
```

### 8.2 測試結構

```
tests/
├── test_api/
│   └── test_songs.py     # API 端點測試
└── test_services/         # 服務層測試
```

### 8.3 測試 async 端點

```python
import pytest
from httpx import AsyncClient
from app.main import create_app

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_list_songs(client):
    resp = await client.get("/api/v1/songs")
    assert resp.status_code == 200
```

---

## 9. 程式碼品質

### 9.1 Linter

```bash
# 檢查
ruff check app/

# 自動修復
ruff check app/ --fix

# 格式化
ruff format app/
```

### 9.2 型別標註

專案使用 Python 3.10+ 型別語法：

```python
# 使用 | None 而非 Optional
def get_song(song_id: int) -> Song | None: ...

# 使用 list[] 而非 List[]
def get_lines() -> list[SubtitleLine]: ...
```

---

## 10. API 文件

FastAPI 自動產生 API 文件：

| 格式 | URL |
|------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

---

## 11. 部署

### 11.1 生產模式

```bash
# 關閉 debug
LAW_DEBUG=false

# 多 worker（注意：WebSocket 不相容多 worker）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 11.2 LAN 存取

預設綁定 `0.0.0.0`，同網路的裝置可透過伺服器 IP 存取：

```bash
# 查看 IP
ifconfig | grep "inet " | grep -v 127.0.0.1
```

其他裝置訪問 `http://{IP}:8000`。

### 11.3 注意事項

- WebSocket 不相容多 worker 模式（in-memory state）
- SQLite 不適合高並發寫入
- ML 模型首次使用會自動下載（約 3GB）
- 確保 `data/` 目錄有足夠磁碟空間

---

## 12. 疑難排解

### 12.1 mlx-whisper 安裝失敗

```bash
# 確認 Apple Silicon
uname -m  # 應顯示 arm64

# 嘗試單獨安裝
pip install mlx-whisper
```

### 12.2 Demucs 記憶體不足

```bash
# 減少 segment 大小
LAW_DEMUCS_SEGMENT=5

# 減少 shifts
LAW_DEMUCS_SHIFTS=1
```

### 12.3 資料庫遷移衝突

```bash
# 查看目前版本
alembic current

# 重建資料庫（開發用）
rm data/db/leader_at_worship.db
alembic upgrade head
```

### 12.4 yt-dlp 下載失敗

```bash
# 更新 yt-dlp
pip install -U yt-dlp

# 檢查 ffmpeg
ffmpeg -version
```
