# LeaderAtWorship 詳細設計文件

> 版本：1.2 | 更新日期：2026-03-09

## 1. 資料庫設計

### 1.1 ER Diagram

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│    Song      │ 1───N │  SongLyrics  │ 1───N │ LyricsLine  │
│─────────────│       │──────────────│       │─────────────│
│ id (PK)     │       │ id (PK)      │       │ id (PK)     │
│ title       │       │ song_id (FK) │       │ lyrics_id(FK│
│ artist      │       │ language     │       │ line_number │
│ key_signatr │       │ content      │       │ text        │
│ tempo_bpm   │       │ is_primary   │       │ section_labl│
│ tags        │       └──────────────┘       └─────────────┘
│ audio_path  │
│ vocals_path │       ┌──────────────┐       ┌─────────────┐
│ accomp_path │ 1───N │ SubtitleFile │ 1───N │SubtitleLine │
│ created_at  │       │──────────────│       │─────────────│
│ updated_at  │       │ id (PK)      │       │ id (PK)     │
└──────┬──────┘       │ song_id (FK) │       │ sub_file_id │
       │              │ filename     │       │ index       │
       │              │ format       │       │ start_ms    │
       │              │ source       │       │ end_ms      │
       │              │ file_path    │       │ text        │
       │              │ align_source │       │ text_second │
       │              │ align_conf   │       │ confidence  │
       │              │ align_matched│       │ source_type │
       │              │ align_total  │       └─────────────┘
       │              │ align_algo   │
       │              │ created_at   │
       │              └──────────────┘
       │
┌──────┴──────┐       ┌──────────────┐
│  FlowItem   │ N───1 │ WorshipFlow  │
│─────────────│       │──────────────│
│ id (PK)     │       │ id (PK)      │
│ flow_id (FK)│       │ name         │
│ song_id (FK)│       │ date         │
│ position    │       │ notes        │
│ item_type   │       │ created_at   │
│ label       │       └──────┬───────┘
│ trans_note  │              │
│ duration_s  │       ┌──────┴───────┐
└─────────────┘       │ Projection   │
                      │ Session      │
                      │──────────────│
                      │ id (PK)      │
                      │ flow_id (FK) │
                      │ cur_item_idx │
                      │ cur_line_idx │
                      │ is_live      │
                      │ is_blank     │
                      │ started_at   │
                      │ ended_at     │
                      └──────────────┘
```

### 1.2 表定義

#### Song

| 欄位 | 型態 | 限制 | 說明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主鍵 |
| title | VARCHAR(255) | NOT NULL, INDEX | 歌曲名稱 |
| artist | VARCHAR(255) | | 藝人/團隊 |
| key_signature | VARCHAR(10) | | 調性（C, Am, etc.） |
| tempo_bpm | INTEGER | | BPM |
| tags | TEXT | | 標籤（逗號分隔） |
| audio_path | VARCHAR(500) | | 原始音頻路徑 |
| vocals_path | VARCHAR(500) | | 人聲音軌路徑 |
| accompaniment_path | VARCHAR(500) | | 伴奏音軌路徑 |
| created_at | DATETIME | DEFAULT NOW | 建立時間 |
| updated_at | DATETIME | ON UPDATE NOW | 更新時間 |

#### SubtitleFile

| 欄位 | 型態 | 限制 | 說明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主鍵 |
| song_id | INTEGER | FK → Song | 所屬歌曲 |
| filename | VARCHAR(255) | NOT NULL | 檔名 |
| format | VARCHAR(10) | NOT NULL | srt/vtt/lrc/txt |
| source | VARCHAR(50) | | 來源：whisper, whisper+aligned, imported |
| file_path | VARCHAR(500) | | SRT 檔案路徑 |
| alignment_source | VARCHAR(50) | | 歌詞來源（syncedlyrics 等） |
| alignment_confidence | FLOAT | | 平均對齊信心度 [0.0-1.0] |
| alignment_matched | INTEGER | | 成功對齊行數 |
| alignment_total | INTEGER | | GT 歌詞總行數 |
| alignment_algorithm | VARCHAR(20) | | anchor / greedy_fallback |
| created_at | DATETIME | DEFAULT NOW | 建立時間 |

#### SubtitleLine

| 欄位 | 型態 | 限制 | 說明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主鍵 |
| subtitle_file_id | INTEGER | FK → SubtitleFile | 所屬字幕檔 |
| index | INTEGER | NOT NULL | 行號（1-based） |
| start_ms | INTEGER | NOT NULL | 開始時間（毫秒） |
| end_ms | INTEGER | NOT NULL | 結束時間（毫秒） |
| text | TEXT | NOT NULL | 主要文字 |
| text_secondary | TEXT | | 次要文字（雙語） |
| confidence | FLOAT | | 對齊信心度 |
| source_type | VARCHAR(20) | | anchor/interpolated/extrapolated/phantom/greedy |

#### WorshipFlow

| 欄位 | 型態 | 限制 | 說明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主鍵 |
| name | VARCHAR(255) | NOT NULL | 流程名稱 |
| date | DATE | | 敬拜日期 |
| notes | TEXT | | 備註 |
| created_at | DATETIME | DEFAULT NOW | 建立時間 |

#### FlowItem

| 欄位 | 型態 | 限制 | 說明 |
|------|------|------|------|
| id | INTEGER | PK, AUTO | 主鍵 |
| flow_id | INTEGER | FK → WorshipFlow | 所屬流程 |
| song_id | INTEGER | FK → Song, NULL | 關聯歌曲 |
| position | INTEGER | NOT NULL | 排序位置 |
| item_type | VARCHAR(50) | NOT NULL | song/prayer/reading/announcement |
| label | VARCHAR(255) | | 顯示名稱 |
| transition_note | TEXT | | 銜接備註 |
| duration_seconds | INTEGER | | 預估時長 |

---

## 2. API 設計

### 2.1 REST API 端點

#### Songs API

```
GET    /api/v1/songs                    # 列表（?q=搜尋）
POST   /api/v1/songs                    # 新增
GET    /api/v1/songs/{song_id}          # 詳情
PUT    /api/v1/songs/{song_id}          # 更新
DELETE /api/v1/songs/{song_id}          # 刪除
POST   /api/v1/songs/{song_id}/lyrics   # 新增歌詞
```

#### Subtitles API

```
GET    /api/v1/subtitles                      # 列表
GET    /api/v1/subtitles/{subtitle_id}        # 詳情（含所有行）
GET    /api/v1/subtitles/by-song/{song_id}    # 依歌曲查詢
PATCH  /api/v1/subtitles/lines/{line_id}      # 更新單行
POST   /api/v1/subtitles/{subtitle_id}/lines  # 插入新行
DELETE /api/v1/subtitles/lines/{line_id}      # 刪除行
```

#### Audio API

```
POST   /api/v1/audio/extract                  # 提交 YouTube URL
GET    /api/v1/audio/tasks                    # 任務列表
GET    /api/v1/audio/tasks/{task_id}          # 任務狀態
GET    /api/v1/audio/tasks/{task_id}/download  # 下載 SRT
GET    /api/v1/audio/stream/{song_id}         # 音頻串流（?track=original|vocals|accompaniment）
```

#### Flows API

```
GET    /api/v1/flows                    # 列表
POST   /api/v1/flows                    # 新增
GET    /api/v1/flows/{flow_id}          # 詳情（含 song_title）
PUT    /api/v1/flows/{flow_id}          # 更新（replace-all 策略）
DELETE /api/v1/flows/{flow_id}          # 刪除
```

#### Projection API

```
POST   /api/v1/projection/sessions     # 建立投影 Session
```

### 2.2 WebSocket 協議

**端點：** `ws://host:port/ws/projection/{session_id}?role=display|controller`

#### 訊息格式

**Server → Client（狀態同步）：**
```json
{
  "type": "state_sync",
  "data": {
    "session_id": 1,
    "flow_id": 2,
    "current_item_index": 0,
    "current_line_index": 3,
    "is_blank": false,
    "current_text": "主要字幕文字",
    "current_text_secondary": "",
    "current_song_id": 5,
    "items": [
      {"label": "讚美之泉", "item_type": "song", "song_id": 5, "line_count": 25}
    ],
    "total_items": 3,
    "total_lines": 25,
    "current_item_label": "讚美之泉",
    "current_item_lines": [
      {"text": "第一行歌詞", "text_secondary": "", "start_ms": 15230}
    ]
  }
}
```

**Client → Server（控制指令）：**
```json
{"action": "next_line"}
{"action": "prev_line"}
{"action": "goto_line", "index": 5}
{"action": "next_item"}
{"action": "prev_item"}
{"action": "goto_item", "index": 2}
{"action": "toggle_blank"}
{"action": "set_text", "text": "自訂文字", "text_secondary": ""}
```

---

## 3. 核心演算法設計

### 3.1 錨點式歌詞對齊演算法

**目標：** 將線上搜尋到的歌詞（Ground Truth）與 Whisper 轉錄結果精準對齊，取得正確的時間戳。

**演算法流程：**

```
Phase 1: 文字正規化
  ├── 繁體→簡體轉換
  ├── Unicode NFKC 正規化
  ├── 移除標點符號
  └── 全形→半形

Phase 2: 錨點提取（Dynamic Programming）
  ├── 計算 Whisper segment 與 GT line 的相似度矩陣
  │   └── 使用 rapidfuzz.fuzz.ratio (≥ anchor_threshold)
  ├── 篩選高品質匹配（logprob ≥ logprob_threshold）
  └── DP 求解最大權重單調子序列
      └── dp[i] = max weight of monotonic subsequence ending at match i

Phase 3: 時間軸扭曲
  ├── 錨點行：直接使用 Whisper segment 的時間戳
  ├── 插值行（兩錨點之間）：線性插值
  │   └── t = t_prev + (t_next - t_prev) * k / (n + 1)
  └── 外插行（首/尾錨點之外）：依比例外推

Phase 4: 幽靈行偵測
  ├── 檢查每行 GT 周圍是否有 Whisper 證據
  │   └── phantom_threshold_ms 時間窗口內無 segment → phantom
  └── 標記為 "phantom" source_type

Fallback: 貪婪匹配
  └── 當錨點數量不足時，退化為逐行貪婪匹配
```

**品質指標：**
- `confidence`：每行的對齊信心度 [0.0 - 1.0]
- `match_ratio`：成功匹配行數 / GT 總行數
- `algorithm`：使用的演算法（"anchor" 或 "greedy_fallback"）

### 3.2 投影狀態機

```
┌──────────┐   next_item   ┌──────────┐   next_item   ┌──────────┐
│  Item 0  │──────────────▶│  Item 1  │──────────────▶│  Item 2  │
│  Line 0  │  prev_item    │  Line 0  │  prev_item    │  Line 0  │
│  Line 1  │◀──────────────│  Line 1  │◀──────────────│  Line 1  │
│  Line 2  │               │  ...     │               │  ...     │
│  ...     │               │  Line N  │               │  Line M  │
└──────────┘               └──────────┘               └──────────┘

狀態：
  current_item_index: 目前歌曲索引
  current_line_index: 目前字幕行索引
  is_blank: 是否黑幕
  current_text: 主要顯示文字
  current_text_secondary: 次要顯示文字
  current_song_id: 目前歌曲 ID（用於音頻串流）
  current_item_lines[].start_ms: 每行開始時間（用於音頻同步）

導航規則：
  next_line: line_index + 1（超過當前歌曲行數則不動）
  prev_line: line_index - 1（< 0 則不動）
  next_item: item_index + 1, line_index = 0
  prev_item: item_index - 1, line_index = 0
  goto_item(n): item_index = n, line_index = 0
  goto_line(n): line_index = n

音頻同步機制：
  控制端播放音頻時，timeupdate 事件觸發：
  1. 取得 currentTime (ms)
  2. 反向遍歷 cachedLineTimings 找到 start_ms ≤ currentMs 的最大 index
  3. 若 targetLine ≠ currentLineIndex → 送出 goto_line 指令
  4. Server 廣播新狀態，Display 更新 5 行歌詞視窗
```

### 3.3 音頻串流設計

```
Client 請求:
  GET /api/v1/audio/stream/{song_id}?track=vocals
  Range: bytes=1048576-2097151

Server 處理:
  1. 根據 track 參數選擇音頻檔案
     - original → song.audio_path
     - vocals → song.vocals_path
     - accompaniment → song.accompaniment_path
  2. 讀取檔案大小
  3. 解析 Range header
  4. 回傳 206 Partial Content
     Content-Range: bytes 1048576-2097151/10485760
     Content-Type: audio/wav
```

---

## 4. 服務模組設計

### 4.1 YouTube 下載服務（youtube.py）

```python
class DownloadResult:
    audio_path: Path      # WAV 檔案路徑
    title: str            # 影片標題
    artist: str           # 頻道/藝人
    duration_seconds: int # 音頻時長
    video_id: str         # YouTube ID

async def download_audio(url: str) -> DownloadResult:
    # 使用 yt-dlp 下載
    # 輸出格式：WAV 16kHz mono
    # 儲存至 data/audio/{video_id}.wav
```

### 4.2 人聲分離服務（separator.py）

```python
async def separate(audio_path: Path) -> tuple[Path, Path]:
    # 使用 Demucs (htdemucs) 分離
    # 輸出：(vocals.wav, no_vocals.wav)
    # 快取機制：已分離的檔案不重複處理
    # 設定：device, shifts, segment, overlap, jobs
```

### 4.3 語音辨識服務（transcriber.py）

```python
async def transcribe(audio_path: Path) -> list[dict]:
    # 使用 mlx-whisper 辨識
    # 輸出：[{start_ms, end_ms, text, avg_logprob}, ...]
    # 模型：mlx-community/whisper-large-v3-turbo
    # 語言：auto / zh / en
```

### 4.4 歌詞搜尋服務（lyrics_fetcher.py）

```python
class FetchResult:
    lines: list[LrcLine]   # 解析後的歌詞行
    provider: str           # 來源提供者
    raw_lrc: str            # 原始 LRC 文字
    has_timestamps: bool    # 是否有時間戳

async def fetch_lyrics(title: str, artist: str | None) -> FetchResult | None:
    # 智慧搜尋策略：
    # 1. "{title} {artist}"
    # 2. "{title}" (不含藝人)
    # 3. 簡體中文版本
    # 4. 移除括號內容
```

### 4.5 歌詞對齊服務（lyrics_aligner.py）

```python
class AlignmentResult:
    segments: list[dict]    # 對齊後的 segments
    stats: dict             # 統計資料
    algorithm: str          # anchor / greedy_fallback

def align(
    whisper_segments: list[dict],
    gt_lines: list,
    anchor_threshold: float = 0.55,
    logprob_threshold: float = -0.7,
    phantom_threshold_ms: int = 3000,
    output_traditional: bool = True,
    bpm_snap: bool = False,
) -> AlignmentResult:
```

### 4.6 投影管理服務（projection_manager.py）

```python
@dataclass
class SubtitleLineData:
    text: str = ""
    text_secondary: str = ""
    start_ms: int = 0           # 用於音頻同步

@dataclass
class ProjectionState:
    session_id: int
    flow_id: int | None
    current_item_index: int
    current_line_index: int
    is_blank: bool
    current_text: str
    current_text_secondary: str
    current_song_id: int | None  # 用於音頻串流 URL
    items: list[dict]            # 項目元資料 (含 song_id)
    total_items: int
    total_lines: int
    current_item_label: str
    current_item_lines: list     # [{text, text_secondary, start_ms}, ...]

class ProjectionManager:
    def connect(session_id, websocket, role): ...
    def disconnect(session_id, websocket): ...
    def load_flow_data(session_id, flow_id, items): ...
    async def handle_command(session_id, command): ...
    async def broadcast(session_id, message): ...
```

---

## 5. 前端設計

### 5.1 頁面結構

| 頁面 | URL | 模板 | 功能 |
|------|-----|------|------|
| 首頁 | `/` | index.html | 快速操作、導覽 |
| 歌曲列表 | `/songs` | songs/list.html | 歌曲庫瀏覽 |
| 歌曲詳情 | `/songs/{id}` | songs/detail.html | 播放器 + 字幕 |
| 音頻處理 | `/audio` | audio/process.html | 進度追蹤 |
| 流程編輯 | `/flows` | flows/editor.html | 流程管理 |
| 投影顯示 | `/projection/display/{sid}` | projection/display.html | 字幕投影 |
| 投影控制 | `/projection/control/{sid}` | projection/control.html | 操作面板 |

### 5.2 JavaScript 模組

| 模組 | 檔案 | 職責 |
|------|------|------|
| WebSocket Client | ws-client.js | 連線管理、自動重連、訊息分發 |
| Projection Display | projection.js | 接收狀態、渲染五行歌詞上下文視窗 |
| Projection Controller | controller.js | 發送指令、渲染流程導航、音頻播放與字幕同步 |
| Audio Player | player.js | 歌曲詳情頁音頻播放、字幕同步、音軌切換 |

### 5.3 投影顯示畫面規格（五行歌詞上下文）

```
┌─────────────────────────────────────┐
│              (全黑背景)              │
│                                     │
│       前第二行歌詞 (淡灰 2.8vw)       │
│       前第一行歌詞 (半透明 2.8vw)     │
│       ▶ 當前歌詞行 (白色粗體 4vw) ◀  │
│       後第一行歌詞 (半透明 2.8vw)     │
│       後第二行歌詞 (淡灰 2.8vw)       │
│                                     │
└─────────────────────────────────────┘

CSS 樣式層級：
  .lyric-line        → 2.8vw, rgba(255,255,255,0.35)
  .lyric-line.near   → 2.8vw, rgba(255,255,255,0.55)
  .lyric-line.active → 4vw, #fff, font-weight:700, text-shadow

邊界處理：
  若索引 < 0 或 ≥ 總行數 → 顯示 &nbsp; 占位符保持佈局穩定
```

### 5.4 控制面板佈局

```
┌─────────────────────────────────────┐
│  目前字幕文字預覽                     │
│  [位置資訊: 歌曲 1/3, 行 5/25]        │
├─────────────────────────────────────┤
│  [◀上一首] [◀上一行] [下一行▶] [下一首▶] [黑幕] │
├─────────────────────────────────────┤
│  音頻播放器（歌曲音頻 + 播放時自動同步字幕）│
│  [▶播放] ═══════════○═════ 2:35/4:12  │
│  (○原聲) (○人聲) (○伴奏)              │
├──────────────┬──────────────────────┤
│  流程項目列表  │  字幕行列表           │
│  ┌──────────┐│  ┌──────────────────┐│
│  │▶讚美之泉 ││  │  1. 第一行歌詞   ││
│  │ Amazing  ││  │  2. 第二行歌詞   ││
│  │ 十架     ││  │▶ 3. 第三行歌詞   ││
│  └──────────┘│  │  4. 第四行歌詞   ││
│              │  └──────────────────┘│
├──────────────┴──────────────────────┤
│  [手動輸入文字]  [送出]               │
└─────────────────────────────────────┘
```

---

## 6. 錯誤處理策略

### 6.1 管線並行控制

批次提交多個 YouTube 連結時，所有任務共用一個 `asyncio.Semaphore`，確保同一時間只有 `max_concurrent_pipelines`（預設 1）條管線在執行：

```python
# app/tasks/audio_pipeline.py
_pipeline_semaphore: asyncio.Semaphore | None = None  # Lazy-init

async def run_audio_pipeline(task_id, youtube_url, whisper_model=None):
    sem = _get_semaphore()
    if sem.locked():
        task_store[task_id].update({"status": "queued", "detail": "等待其他任務完成..."})
    async with sem:
        await _run_audio_pipeline_inner(task_id, youtube_url, whisper_model)
```

**任務狀態流轉：**
```
pending → queued（等待 Semaphore）→ downloading → separating
→ transcribing → aligning → generating → saving → completed / failed
```

設計考量：
- Demucs 使用 `demucs_jobs` 個 CPU 線程，mlx-whisper 佔用大量 Apple Silicon 統一記憶體
- 並行執行多條管線會導致 OOM 或 SQLite 寫入鎖定
- Semaphore 在 asyncio event loop 層級運作，不需額外基礎設施

### 6.2 管線錯誤處理

| 步驟 | 失敗情境 | 處理方式 |
|------|---------|---------|
| YouTube 下載 | URL 無效 / 網路錯誤 | 任務標記 failed，回傳錯誤訊息 |
| 人聲分離 | Demucs 未安裝 | 跳過分離，使用原始音頻繼續 |
| 語音辨識 | mlx-whisper 未安裝 | 任務失敗（核心步驟） |
| 歌詞搜尋 | 找不到歌詞 | 跳過對齊，使用 Whisper 原始結果 |
| 歌詞對齊 | 品質不達標 | 回退使用 Whisper 原始結果 |

### 6.3 WebSocket 錯誤處理

- 連線斷開：Client 自動重連（ws-client.js 內建）
- Session 不存在：回傳錯誤訊息並關閉連線
- 無效指令：忽略並記錄 warning

---

## 7. 設定系統

所有設定透過環境變數管理，prefix `LAW_`：

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LAW_")

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/db/leader_at_worship.db"

    # Whisper
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    whisper_language: str = "auto"

    # Demucs
    demucs_model: str = "htdemucs"
    demucs_device: str = "cpu"
    demucs_shifts: int = 1
    demucs_segment: int = 7
    demucs_overlap: float = 0.1
    demucs_jobs: int = 8

    # Alignment
    alignment_enabled: bool = True
    alignment_anchor_threshold: float = 0.55
    alignment_min_confidence: float = 0.5
    alignment_min_match_ratio: float = 0.4
    alignment_output_traditional: bool = True

    # Pipeline concurrency
    max_concurrent_pipelines: int = 1  # Serialize heavy ML tasks to avoid OOM

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
```
