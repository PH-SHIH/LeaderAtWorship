# LeaderAtWorship 系統架構文件

> 版本：1.2 | 更新日期：2026-03-09

## 1. 系統概覽

LeaderAtWorship 採用 **單體式 Web 應用** 架構，以 FastAPI 為核心，整合音頻處理管線、WebSocket 即時投影、與 Server-Side Rendering 前端。

```
┌─────────────────────────────────────────────────────────┐
│                      Client Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Dashboard │  │  Player  │  │ Flow Ed. │  │Projctn │  │
│  │  (HTML)   │  │  (HTML)  │  │  (HTML)  │  │(WS+HTML)│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
├─────────────────────────────────────────────────────────┤
│                     Server Layer                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │              FastAPI Application                │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │    │
│  │  │ REST API │  │WebSocket │  │  Templates   │  │    │
│  │  │  v1/*    │  │  /ws/*   │  │  (Jinja2)    │  │    │
│  │  └────┬─────┘  └────┬─────┘  └──────────────┘  │    │
│  │       │              │                          │    │
│  │  ┌────┴──────────────┴──────────────────────┐   │    │
│  │  │            Service Layer                 │   │    │
│  │  │  YouTube │ Separator │ Transcriber       │   │    │
│  │  │  LyricsFetcher │ Aligner │ SubtitleGen   │   │    │
│  │  │  ProjectionManager │ FlowService         │   │    │
│  │  └─────────────────┬────────────────────────┘   │    │
│  │                    │                            │    │
│  │  ┌─────────────────┴────────────────────────┐   │    │
│  │  │          Data Access Layer               │   │    │
│  │  │  SQLAlchemy 2.0 (async) + aiosqlite      │   │    │
│  │  └─────────────────┬────────────────────────┘   │    │
│  └────────────────────│────────────────────────────┘    │
│                       │                                 │
│  ┌────────────────────┴────────────────────────┐        │
│  │              Storage Layer                  │        │
│  │  SQLite DB │ Audio Files │ SRT Exports      │        │
│  └─────────────────────────────────────────────┘        │
├─────────────────────────────────────────────────────────┤
│                  External Dependencies                  │
│  yt-dlp │ Demucs │ mlx-whisper │ syncedlyrics           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 分層架構

### 2.1 各層職責

| 層次 | 職責 | 技術 |
|------|------|------|
| **Presentation** | HTML 頁面渲染、前端互動 | Jinja2 + Vanilla JS |
| **API** | REST endpoints、WebSocket 端點 | FastAPI Router |
| **Service** | 業務邏輯、音頻處理、投影管理 | Python async |
| **Data Access** | ORM 對應、資料庫查詢 | SQLAlchemy 2.0 async |
| **Storage** | 資料持久化 | SQLite + 檔案系統 |

### 2.2 依賴方向

```
Presentation → API → Service → Data Access → Storage
                                    ↓
                            External Services
                     (yt-dlp, Demucs, mlx-whisper)
```

所有依賴單向流動，下層不依賴上層。

---

## 3. 元件架構

### 3.1 REST API 元件

```
app/api/v1/
├── router.py          # 彙總路由器 (/api/v1 prefix)
├── songs.py           # /songs — 歌曲 CRUD
├── subtitles.py       # /subtitles — 字幕管理 + 行編輯
├── audio.py           # /audio — 音頻處理 + 串流
├── flows.py           # /flows — 敬拜流程 CRUD
└── projection.py      # /projection — 投影 Session 管理
```

### 3.2 WebSocket 元件

```
app/api/ws/
└── projection.py      # /ws/projection/{session_id} — 即時投影通訊
```

**WebSocket 通訊架構：**

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   Control    │ ──cmd──▶│                  │──state──▶│   Display    │
│    Panel     │◀─state──│   Projection     │         │   Screen     │
│  (原始頁面)   │         │   Manager        │         │  (新視窗)     │
│              │         │  (in-memory)     │         │              │
│ ┌──────────┐ │         └──────────────────┘         │ ┌──────────┐ │
│ │Audio     │ │                │                     │ │ 5-line   │ │
│ │Player    │ │         ┌──────┴───────┐             │ │ Lyrics   │ │
│ │(3-track) │ │         │ Flow Data    │             │ │ Context  │ │
│ └──────────┘ │         │ (preloaded)  │             │ └──────────┘ │
└──────────────┘         └──────────────┘             └──────────────┘
```

### 3.3 音頻處理管線

```
                    ┌──────────────────────────────────────────┐
                    │  asyncio.Semaphore(max_concurrent=1)     │
                    │                                          │
┌─────────┐  queue  │ ┌─────────┐  ┌──────────┐  ┌──────────┐ │
│  POST   │───────▶ │ │ YouTube │─▶│  Demucs  │─▶│ Whisper  │ │
│/extract │  (N件)  │ │Download │  │Separation│  │Transcribe│ │
└─────────┘         │ └─────────┘  └──────────┘  └────┬─────┘ │
                    │                                  │       │
                    │ ┌─────────┐  ┌──────────┐  ┌────┴─────┐ │
                    │ │   DB    │◀─│   SRT    │◀─│ Aligner  │ │
                    │ │ Persist │  │Generator │  │+ Fetcher │ │
                    │ └─────────┘  └──────────┘  └──────────┘ │
                    └──────────────────────────────────────────┘

狀態流轉：pending → queued → downloading → separating → transcribing
        → aligning → generating → saving → completed / failed
```

批次提交多個 URL 時，Semaphore 確保同一時間只有一條管線執行（Demucs + mlx-whisper 記憶體密集），其餘任務以 `queued` 狀態等候。

### 3.4 資料模型關聯

```
Song ──────────┬──────── SongLyrics ──── LyricsLine
  │            │
  │            └──────── SubtitleFile ── SubtitleLine
  │
  └── FlowItem ──────── WorshipFlow
                              │
                    ProjectionSession
```

---

## 4. 技術棧

### 4.1 後端

| 元件 | 技術 | 版本 | 用途 |
|------|------|------|------|
| Web Framework | FastAPI | ≥0.115 | 非同步 REST API + WebSocket |
| ASGI Server | Uvicorn | ≥0.32 | HTTP/WS 伺服器 |
| ORM | SQLAlchemy | 2.0+ | 非同步資料庫操作 |
| Database | SQLite | 3.x | 嵌入式資料庫（via aiosqlite） |
| Migration | Alembic | ≥1.14 | 資料庫 Schema 版本管理 |
| Template | Jinja2 | ≥3.1 | Server-Side Rendering |
| Config | pydantic-settings | ≥2.7 | 環境變數管理 |

### 4.2 音頻處理

| 元件 | 技術 | 用途 |
|------|------|------|
| YouTube 下載 | yt-dlp | 影片音頻擷取 |
| 人聲分離 | Demucs (htdemucs) | 分離人聲與伴奏 |
| 語音辨識 | mlx-whisper | Apple Silicon 最佳化的 Whisper |
| 歌詞搜尋 | syncedlyrics | 線上同步歌詞搜尋 |
| 文字匹配 | rapidfuzz | 模糊字串比對 |
| 中文轉換 | hanziconv / opencc | 簡繁轉換 |

### 4.3 前端

| 元件 | 技術 | 用途 |
|------|------|------|
| JavaScript | Vanilla JS (ES6+) | 前端互動邏輯 |
| CSS | 原生 CSS | 樣式設計 |
| WebSocket | 原生 WebSocket API | 即時投影通訊 |
| 拖曳排序 | HTML5 Drag & Drop API | 流程項目排序 |
| Audio API | HTMLAudioElement + timeupdate | 音頻播放與字幕同步 |

---

## 5. 部署架構

### 5.1 單機部署（目前）

```
┌──────────────────────────────────────┐
│          macOS Apple Silicon         │
│                                      │
│  ┌──────────────────────────────┐    │
│  │      Python Virtual Env      │    │
│  │  ┌────────────────────────┐  │    │
│  │  │    Uvicorn (port 8000) │  │    │
│  │  │    ┌────────────────┐  │  │    │
│  │  │    │  FastAPI App   │  │  │    │
│  │  │    └────────────────┘  │  │    │
│  │  └────────────────────────┘  │    │
│  └──────────────────────────────┘    │
│                                      │
│  ┌────────────┐  ┌───────────────┐   │
│  │  SQLite DB │  │  data/audio/  │   │
│  └────────────┘  └───────────────┘   │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  ML Models (on-device)         │  │
│  │  mlx-whisper │ Demucs          │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
        │
    LAN Network
        │
┌───────┴────────┐
│  投影機 / 螢幕  │
│  (瀏覽器全螢幕)  │
└────────────────┘
```

### 5.2 LAN 使用場景

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  操作員電腦   │     │ 投影機螢幕   │     │  主領平板    │
│  (Server)    │     │  (Display)   │     │ (Control)   │
│  port 8000   │◀───▶│ /display/1   │     │ /control/1  │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                                       │
       └───────────────────────────────────────┘
                    WebSocket 連線
```

---

## 6. 資料流

### 6.1 音頻處理流程

```
使用者輸入 YouTube URL
        │
        ▼
POST /api/v1/audio/extract
        │
        ▼
┌─ Semaphore Gate (max_concurrent_pipelines) ──┐
│  如已有管線執行 → status = "queued" 等待      │
│  取得鎖後開始執行：                            │
│  1. yt-dlp download → data/audio/{id}.wav    │
│  2. Demucs separate → vocals.wav + accomp.wav│
│  3. mlx-whisper transcribe → segments[]      │
│  4. syncedlyrics fetch → LRC lyrics          │
│  5. anchor_align(whisper, lyrics) → aligned  │
│  6. generate_srt(aligned) → .srt file        │
│  7. DB: Song + SubtitleFile + SubtitleLine[]  │
└──────────────────────────────────────────────┘
        │
        ▼
GET /api/v1/audio/tasks/{id} (polling)
        │
        ▼
歌曲詳情頁（播放器 + 同步字幕）
```

### 6.2 投影控制流程

```
敬拜流程編輯器
        │
   「啟動投影」按鈕（立即預開空白視窗避免彈窗封鎖）
        │
        ▼
POST /api/v1/projection/sessions
  body: { flow_id: N }
        │
  ┌─────┴──────────────────────────────┐
  │ Server:                            │
  │ 1. 建立 ProjectionSession          │
  │ 2. 載入 Flow → Items → Songs       │
  │ 3. 查詢每首歌的最新 SubtitleFile    │
  │ 4. 建構 FlowItemData[] 記憶體結構   │
  │ 5. 初始化 ProjectionState          │
  │    (含 current_song_id, start_ms)  │
  └────────────────────────────────────┘
        │
        ▼
  回傳 session_id
        │
  ┌─────┴──────────────┐
  ▼                    ▼
Display              Control
(新視窗)             (當前頁面導航)
  │                    │
  └─────┬──────────────┘
        │
  WebSocket /ws/projection/{session_id}
        │
  ┌─────┴─────────────────────────────┐
  │ Control 送出指令:                  │
  │   next_line / prev_line           │
  │   next_item / prev_item           │
  │   goto_item / goto_line           │
  │   toggle_blank / set_text         │
  │                                    │
  │ Control 音頻播放 timeupdate:       │
  │   自動計算 currentMs vs start_ms   │
  │   → goto_line 自動推進字幕行       │
  │                                    │
  │ Server 更新 State，廣播到所有 Client│
  │                                    │
  │ Display 接收 State，渲染 5 行歌詞   │
  │  (前2行 + 當前高亮行 + 後2行)       │
  └────────────────────────────────────┘
```

---

## 7. 目錄結構

```
LeaderAtWorship/
├── app/                         # 應用程式主目錄
│   ├── main.py                  # FastAPI 應用工廠
│   ├── config.py                # 環境設定（pydantic-settings）
│   ├── database.py              # SQLAlchemy 引擎 & Session
│   ├── api/                     # API 層
│   │   ├── deps.py              # 依賴注入（db session）
│   │   ├── v1/                  # REST API v1
│   │   └── ws/                  # WebSocket 端點
│   ├── models/                  # ORM 模型
│   ├── schemas/                 # Pydantic 驗證模型
│   ├── services/                # 業務邏輯層
│   ├── tasks/                   # 背景任務
│   ├── utils/                   # 工具函式
│   ├── templates/               # Jinja2 HTML 模板
│   └── static/                  # 靜態資源 (CSS/JS)
├── alembic/                     # 資料庫遷移
├── data/                        # 運行時資料
│   ├── db/                      # SQLite 資料庫
│   ├── audio/                   # 下載的音頻
│   ├── separated/               # 分離後的音軌
│   └── exports/                 # 產生的字幕檔
├── tests/                       # 測試
├── docs/                        # 文件
├── pyproject.toml               # 專案設定 & 依賴
├── setup.sh                     # 一鍵安裝腳本
├── alembic.ini                  # Alembic 設定
├── .env                         # 環境變數
└── .env.example                 # 環境變數範本
```

---

## 8. 關鍵設計決策

### 8.1 為什麼選擇 SQLite？
- 單機部署，不需要資料庫伺服器
- 零設定，安裝即用
- 透過 aiosqlite 實現非同步存取
- 足以應對教會場景的資料量

### 8.2 為什麼選擇 mlx-whisper 而非 OpenAI Whisper？
- Apple Silicon 原生加速，速度快 3-5 倍
- 無需 GPU（使用 Neural Engine / ANE）
- 模型品質相同（使用 large-v3-turbo）

### 8.3 為什麼用 Vanilla JS 而非 React/Vue？
- 降低部署複雜度（不需 Node.js 建置流程）
- 頁面數量少（< 10 頁），Jinja2 SSR 足夠
- 減少依賴，簡化維護

### 8.4 為什麼用 WebSocket 而非 SSE？
- 投影控制需要雙向通訊（Controller → Server → Display）
- SSE 只支援單向推送
- WebSocket 延遲更低，適合即時投影場景

### 8.5 為什麼用 In-Memory Task Store 而非 Celery？
- 單機部署，不需要 Redis/RabbitMQ
- 背景任務數量少，使用 `asyncio.create_task` 即可
- `asyncio.Semaphore` 提供輕量級並行控制，序列化 ML 重載任務
- 簡化部署流程
