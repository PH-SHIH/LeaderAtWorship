# LeaderAtWorship

敬拜字幕生成與即時投影控制工具，專為 Apple Silicon Mac 優化。

## Features

- **YouTube 音頻處理** — 貼上連結即自動下載、人聲分離、語音轉錄
- **智慧歌詞對齊** — 錨點式動態規劃演算法，將線上歌詞與 Whisper 轉錄精準對齊
- **字幕生成** — 自動產生 SRT/VTT 時間軸字幕，支援雙語顯示
- **即時投影** — WebSocket 即時同步，五行歌詞上下文顯示（前二行 + 高亮當前行 + 後二行）
- **音頻同步投影** — 控制端播放音頻時字幕自動推進，支援原聲/人聲/伴奏三軌切換
- **敬拜流程** — 編排歌曲順序，一鍵啟動投影（當前頁轉控制端 + 新視窗投影端）
- **字幕編輯** — 行內編輯文字與時間戳，新增/刪除字幕行
- **伴奏切換** — 原聲、人聲、伴奏三軌切換播放

## 一鍵安裝

```bash
git clone <repo-url>
cd LeaderAtWorship
./setup.sh
```

腳本會自動安裝所有需要的工具：

| 工具 | 用途 | 安裝方式 |
|------|------|----------|
| Homebrew | macOS 套件管理器 | 自動安裝 |
| Python 3.10+ | 程式語言 | brew install (如需要) |
| ffmpeg | 音頻轉檔 | brew install |
| mlx-whisper | 語音轉文字 (Apple Silicon) | pip install |
| Demucs | 人聲分離 | pip install |
| FastAPI + 全部 Python 套件 | 後端框架 | pip install |

安裝完成後：

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

打開 http://localhost:8000 即可使用。

## 手動安裝

如果一鍵安裝失敗，可以手動執行：

```bash
# 1. 安裝系統工具
brew install ffmpeg python@3.12

# 2. 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安裝 Python 套件（含 ML 模型）
pip install -e ".[ml,dev]"

# 4. 設定環境
cp .env.example .env

# 5. 初始化資料庫
mkdir -p data/db data/audio data/exports data/models
alembic upgrade head

# 6. 啟動
uvicorn app.main:app --reload --port 8000
```

## 使用方式

### 1. 處理 YouTube 音頻

首頁貼上 YouTube 連結 -> 點「擷取音頻」-> 自動完成以下流程：

```
下載音頻 → 人聲分離 → 語音轉錄 → 歌詞對齊 → 生成 SRT 字幕
```

支援多行貼上（每行一個連結），批次自動排隊處理。

### 2. 歌曲庫

瀏覽已處理的歌曲，播放音頻同時顯示同步字幕。可切換原聲/人聲/伴奏。

### 3. 字幕編輯

滑鼠移到字幕行上方 -> 點編輯按鈕 -> 修改文字或時間戳。也可新增或刪除字幕行。

### 4. 敬拜流程

新建流程 -> 從歌曲庫加入歌曲 -> 拖曳排序 -> 儲存。

### 5. 即時投影

在流程編輯器點「啟動投影」：

- **當前頁面**自動轉為控制面板（含音頻播放器 + 流程導航）
- **新開視窗**作為投影螢幕（五行歌詞上下文顯示，拖曳到投影機螢幕）

播放音頻時字幕會自動同步推進。控制端支援原聲/人聲/伴奏三軌切換。兩端透過 WebSocket 即時同步。

## 環境設定

所有設定在 `.env` 檔案中，prefix 為 `LAW_`：

```bash
# 語音模型（Apple Silicon 專用）
LAW_WHISPER_MODEL=mlx-community/whisper-large-v3-turbo
LAW_WHISPER_LANGUAGE=auto    # auto=自動偵測, zh=中文, en=英文

# 人聲分離
LAW_DEMUCS_MODEL=htdemucs    # htdemucs=快速, htdemucs_ft=高品質
LAW_DEMUCS_JOBS=8            # 並行數（配合 CPU 核心數）

# 管線並行（預設 1，避免 OOM）
LAW_MAX_CONCURRENT_PIPELINES=1

# 伺服器
LAW_PORT=8000
LAW_DEBUG=true
```

## API 文件

啟動後可查看自動生成的 API 文件：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy 2.0 (async) |
| Database | SQLite (aiosqlite) |
| Speech-to-Text | mlx-whisper (Apple Silicon) |
| Vocal Separation | Demucs |
| Lyrics Search | syncedlyrics |
| Alignment | Custom anchor-based DP algorithm |
| Real-time | WebSocket |
| Frontend | Jinja2 + Vanilla JS |

## License

MIT
