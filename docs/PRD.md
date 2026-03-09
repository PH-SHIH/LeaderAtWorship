# LeaderAtWorship 產品需求文件（PRD）

> 版本：1.2 | 更新日期：2026-03-09

---

## 1. 產品概述

### 1.1 產品名稱
**LeaderAtWorship** — 敬拜字幕生成與即時投影控制工具

### 1.2 產品定位
為教會敬拜團隊打造的一站式字幕製作與投影控制系統。從 YouTube 影片自動產生同步字幕，並透過 WebSocket 即時投影到螢幕上。專為 Apple Silicon Mac 優化，利用 mlx-whisper 與 Demucs 實現本地端 ML 推論。

### 1.3 目標使用者

| 角色 | 使用場景 | 關鍵需求 |
|------|---------|---------|
| **敬拜主領** | 編排流程、選歌、排練 | 快速建立敬拜流程，一鍵啟動投影 |
| **投影操作員** | 現場控制投影、切換字幕 | 直覺的控制介面，即時同步 |
| **媒體同工** | 管理歌曲庫、編輯字幕 | 批次處理 YouTube 連結，精確調整時間軸 |

### 1.4 目標平台

| 項目 | 規格 |
|------|------|
| 作業系統 | macOS Apple Silicon（M1/M2/M3/M4） |
| 瀏覽器 | Chrome / Safari / Firefox（最新版本） |
| 最低硬體 | 8GB RAM（建議 16GB 以上） |
| 磁碟空間 | 約 5GB（ML 模型 + 音頻檔案） |
| 網路 | 首次處理歌曲時需要（下載 YouTube + 搜尋歌詞） |

---

## 2. 功能需求

### 2.1 YouTube 音頻處理（FR-001）

| 項目 | 說明 |
|------|------|
| **優先級** | P0（核心功能） |
| **描述** | 使用者輸入 YouTube 連結，系統自動完成下載→人聲分離→語音辨識→歌詞對齊→字幕生成 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-001.1 | 支援單一 YouTube 連結輸入 | ✅ |
| FR-001.2 | 支援多行 YouTube 連結批次處理（每行一個連結） | ✅ |
| FR-001.3 | 背景非同步處理，前端即時顯示進度百分比（含排隊狀態） | ✅ |
| FR-001.4 | 處理完成後自動建立歌曲與字幕記錄 | ✅ |
| FR-001.5 | 支援下載產生的 SRT 字幕檔 | ✅ |
| FR-001.6 | 批次處理自動排隊，避免同時執行多條管線導致記憶體耗盡 | ✅ |

**處理管線：**
```
YouTube URL → yt-dlp 下載 → Demucs 人聲分離 → mlx-whisper 語音辨識
→ syncedlyrics 線上歌詞搜尋 → 錨點式對齊演算法 → SRT 字幕生成 → 資料庫儲存
```

**管線狀態流轉：**
```
pending → queued（排隊等候） → downloading → separating → transcribing
→ aligning → generating → saving → completed / failed
```

---

### 2.2 歌曲庫管理（FR-002）

| 項目 | 說明 |
|------|------|
| **優先級** | P0（核心功能） |
| **描述** | 管理所有已處理的歌曲，支援搜尋、新增、編輯、刪除 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-002.1 | 歌曲列表頁面，顯示標題、藝人、調號 | ✅ |
| FR-002.2 | 關鍵字搜尋（模糊匹配標題） | ✅ |
| FR-002.3 | 新增歌曲（標題、藝人、調號、歌詞） | ✅ |
| FR-002.4 | 編輯歌曲元資料（標題、藝人、調號、節奏、標籤） | ✅ |
| FR-002.5 | 刪除歌曲（級聯刪除關聯的歌詞與字幕） | ✅ |
| FR-002.6 | 新增歌詞（多語言、主要/次要標記） | ✅ |

---

### 2.3 伴奏切換與音頻播放（FR-003）

| 項目 | 說明 |
|------|------|
| **優先級** | P1（重要功能） |
| **描述** | 播放已處理歌曲的三種音軌，支援 HTTP Range 串流播放 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-003.1 | 歌曲詳情頁音頻播放器（播放/暫停、進度拖曳、時間顯示） | ✅ |
| FR-003.2 | 三軌切換：原聲 / 人聲 / 伴奏 | ✅ |
| FR-003.3 | HTTP Range 串流支援（支援大檔案快速 seek） | ✅ |
| FR-003.4 | 控制端音頻播放器（投影模式下使用） | ✅ |
| FR-003.5 | 控制端三軌切換（投影模式下切換音軌） | ✅ |

---

### 2.4 字幕編輯（FR-004）

| 項目 | 說明 |
|------|------|
| **優先級** | P1（重要功能） |
| **描述** | 編輯自動生成的字幕，支援行內修改、新增、刪除 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-004.1 | 列出歌曲的所有字幕檔與字幕行 | ✅ |
| FR-004.2 | 行內編輯字幕文字與時間戳（PATCH） | ✅ |
| FR-004.3 | 編輯後自動標記 source_type 為 `manual` | ✅ |
| FR-004.4 | 插入新字幕行（指定位置，自動重新編號） | ✅ |
| FR-004.5 | 刪除字幕行（自動重新編號） | ✅ |
| FR-004.6 | 顯示對齊資訊（信心度、匹配數、演算法） | ✅ |
| FR-004.7 | 雙語字幕支援（主文字 + 次要文字） | ✅ |

---

### 2.5 敬拜流程管理（FR-005）

| 項目 | 說明 |
|------|------|
| **優先級** | P0（核心功能） |
| **描述** | 編排敬拜歌曲順序，支援多種項目類型 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-005.1 | 建立敬拜流程（名稱、日期、備註） | ✅ |
| FR-005.2 | 從歌曲庫搜尋並加入歌曲 | ✅ |
| FR-005.3 | 新增自訂項目（禱告、讀經、公告等） | ✅ |
| FR-005.4 | 拖曳排序流程項目 | ✅ |
| FR-005.5 | 為每個項目設定標籤與過場備註 | ✅ |
| FR-005.6 | 編輯 / 刪除流程（級聯刪除項目） | ✅ |
| FR-005.7 | 流程列表顯示已關聯的歌曲標題 | ✅ |

**流程項目類型：**

| 類型 | 說明 |
|------|------|
| `song` | 歌曲（關聯歌曲庫，載入字幕） |
| `prayer` | 禱告 |
| `reading` | 讀經 |
| `announcement` | 公告 |

---

### 2.6 即時投影（FR-006）

| 項目 | 說明 |
|------|------|
| **優先級** | P0（核心功能） |
| **描述** | WebSocket 即時同步投影，雙視窗架構 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-006.1 | 當前頁面轉為控制端，另開新視窗為投影端 | ✅ |
| FR-006.2 | 五行歌詞上下文顯示（前二行 + 高亮當前行 + 後二行） | ✅ |
| FR-006.3 | 控制端音頻播放器（播放/暫停/進度拖曳） | ✅ |
| FR-006.4 | 控制端逐行 / 逐項導航按鈕 | ✅ |
| FR-006.5 | 投影空白切換（隱藏/顯示字幕） | ✅ |
| FR-006.6 | 手動文字覆蓋（即時輸入自訂文字） | ✅ |
| FR-006.7 | 流程導航面板（顯示所有項目與字幕行） | ✅ |
| FR-006.8 | 多裝置支援（同一 Wi-Fi 下其他裝置可開啟控制面板） | ✅ |
| FR-006.9 | 控制端音頻播放器支援原聲/人聲/伴奏三軌切換 | ✅ |
| FR-006.10 | WebSocket 連線狀態指示器 | ✅ |
| FR-006.11 | 音頻播放自動同步字幕推進（timeupdate 事件） | ✅ |
| FR-006.12 | 投影端不顯示 Whisper 原始逐字稿，只顯示對齊後歌詞 | ✅ |

**投影架構：**
```
┌───────────────────┐    WebSocket     ┌───────────────────┐
│   Control Panel   │ ◄────────────►   │  Display Screen   │
│   （當前頁面）      │    state_sync    │  （新開視窗）       │
│                   │    state_update   │                   │
│  • 流程導航        │                  │  • 五行歌詞        │
│  • 音頻播放器      │                  │  • 高亮當前行      │
│  • 三軌切換        │                  │  • 空白覆蓋        │
│  • 逐行/逐項控制   │                  │                   │
└───────────────────┘                  └───────────────────┘
```

**WebSocket 指令：**

| 指令 | 說明 |
|------|------|
| `next_line` | 下一行字幕 |
| `prev_line` | 上一行字幕 |
| `goto_line` | 跳到指定行 |
| `next_item` | 下一首歌曲/項目 |
| `prev_item` | 上一首歌曲/項目 |
| `goto_item` | 跳到指定項目 |
| `toggle_blank` | 切換空白投影 |
| `set_text` | 手動覆蓋文字 |

---

### 2.7 智慧歌詞對齊（FR-007）

| 項目 | 說明 |
|------|------|
| **優先級** | P1（重要功能） |
| **描述** | 自研錨點式動態規劃演算法，將線上歌詞與 Whisper 轉錄精準對齊 |

**細項需求：**

| 編號 | 需求 | 狀態 |
|------|------|------|
| FR-007.1 | 線上歌詞搜尋（syncedlyrics 多策略） | ✅ |
| FR-007.2 | 錨點式 DP 對齊演算法（自動偵測高信心度匹配點） | ✅ |
| FR-007.3 | 品質閘門（信心度 + 匹配比率雙重門檻） | ✅ |
| FR-007.4 | 品質不達標時自動回退使用 Whisper 原始結果 | ✅ |
| FR-007.5 | 簡繁體中文自動轉換 | ✅ |
| FR-007.6 | 雙語歌詞處理（斜線分隔標題） | ✅ |
| FR-007.7 | 幻影行偵測（phantom detection） | ✅ |
| FR-007.8 | 貪婪回退演算法（greedy fallback） | ✅ |
| FR-007.9 | 每行信心度與來源類型標記 | ✅ |
| FR-007.10 | 可選 BPM 節拍對齊（需 librosa） | ✅ |

**來源類型標記：**

| 標記 | 說明 |
|------|------|
| `anchor` | 高信心度錨點匹配 |
| `interpolated` | 錨點間內插計算 |
| `extrapolated` | 邊界外推計算 |
| `phantom` | 幻影行（無對應 Whisper 段落） |
| `greedy` | 貪婪回退匹配 |
| `manual` | 使用者手動編輯 |

---

## 3. 非功能需求

### 3.1 效能需求（NFR-001）

| 指標 | 目標 |
|------|------|
| 音頻處理延遲 | 單首歌 ≤ 5 分鐘（首次需下載 ML 模型） |
| 投影延遲 | WebSocket 狀態同步 ≤ 100ms |
| 音頻串流 | 支援 HTTP Range，seek 響應 ≤ 200ms |
| 頁面載入 | 所有頁面 ≤ 2 秒 |
| 批次處理 | N 首歌序列完成，總時間約 N × 5 分鐘 |

### 3.2 相容性需求（NFR-002）

| 項目 | 需求 |
|------|------|
| 瀏覽器 | Chrome / Safari / Firefox 最新版本 |
| 作業系統 | macOS 13+ (Apple Silicon) |
| Python | 3.10+ |
| 多裝置 | 同一區域網路內任何裝置可存取 |

### 3.3 易用性需求（NFR-003）

| 項目 | 需求 |
|------|------|
| 上手時間 | 首次使用者 ≤ 10 分鐘內完成第一次投影 |
| 安裝 | 一鍵安裝腳本（setup.sh） |
| 操作 | 所有核心功能 ≤ 3 次點擊內完成 |
| 語言 | UI 全繁體中文 |

### 3.4 儲存需求（NFR-004）

| 項目 | 預估 |
|------|------|
| 每首歌音頻 | 50-200 MB（原聲 + 人聲 + 伴奏） |
| ML 模型 | ~3 GB（首次下載後快取） |
| 資料庫 | < 10 MB（純元資料） |
| SRT 字幕 | < 50 KB / 首 |

### 3.5 安全性需求（NFR-005）

| 項目 | 需求 |
|------|------|
| 部署模式 | 單機本地部署（不暴露到公網） |
| 資料庫 | SQLite 本地檔案，無認證需求 |
| 依賴 | 所有套件透過 pip 安裝，版本鎖定 |

---

## 4. 系統約束

| 約束項目 | 說明 |
|---------|------|
| 硬體 | 需要 Apple Silicon Mac（mlx-whisper 依賴） |
| 網路 | 首次處理需要網路（下載 YouTube、搜尋歌詞） |
| 儲存 | 每首歌約 50-200 MB（原聲 + 人聲 + 伴奏） |
| 並行處理 | 預設單一管線序列執行（Semaphore=1），可透過 `LAW_MAX_CONCURRENT_PIPELINES` 調整 |
| 資料庫 | SQLite 不支援高並發寫入 |

---

## 5. 資料模型

### 5.1 實體關聯圖

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐
│    Song      │ 1───N │  SongLyrics  │ 1───N │ LyricsLine  │
│─────────────│       │──────────────│       │─────────────│
│ id (PK)     │       │ id (PK)      │       │ id (PK)     │
│ title ◄─idx │       │ song_id (FK) │       │ lyrics_id   │
│ artist      │       │ language     │       │ line_number │
│ key_signatr │       │ content      │       │ text        │
│ tempo_bpm   │       │ is_primary   │       │ section_lbl │
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
       │              │ align_*      │       │ text_second │
       │              │ created_at   │       │ confidence  │
       │              └──────────────┘       │ source_type │
       │                                     └─────────────┘
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
                      │ is_live      │
                      │ is_blank     │
                      │ started_at   │
                      └──────────────┘
```

### 5.2 實體摘要

| 實體 | 說明 | 關鍵欄位 |
|------|------|---------|
| Song | 歌曲主檔 | title, artist, audio_path, vocals_path, accompaniment_path |
| SongLyrics | 歌詞版本（支援多語言） | language, content, is_primary |
| LyricsLine | 歌詞逐行 | line_number, text, section_label |
| SubtitleFile | 字幕檔案 | format, source, alignment_* 元資料 |
| SubtitleLine | 字幕逐行 | start_ms, end_ms, text, text_secondary, confidence, source_type |
| WorshipFlow | 敬拜流程 | name, date, notes |
| FlowItem | 流程項目 | item_type, position, song_id, label |
| ProjectionSession | 投影會話 | flow_id, is_live, is_blank |

---

## 6. API 端點

### 6.1 Songs API (`/api/v1/songs`)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 列出所有歌曲（支援 `?q=` 搜尋） |
| POST | `/` | 新增歌曲 |
| GET | `/{id}` | 歌曲詳情（含歌詞） |
| PUT | `/{id}` | 更新歌曲元資料 |
| DELETE | `/{id}` | 刪除歌曲（級聯） |
| POST | `/{id}/lyrics` | 新增歌詞 |

### 6.2 Subtitles API (`/api/v1/subtitles`)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 列出所有字幕檔 |
| GET | `/{id}` | 字幕詳情（含所有行） |
| GET | `/by-song/{song_id}` | 依歌曲查詢字幕 |
| PATCH | `/lines/{line_id}` | 編輯字幕行（自動標記 manual） |
| POST | `/{subtitle_id}/lines` | 插入字幕行（自動重新編號） |
| DELETE | `/lines/{line_id}` | 刪除字幕行（自動重新編號） |

### 6.3 Audio API (`/api/v1/audio`)

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/extract` | 提交 YouTube URL 進入處理管線 |
| GET | `/tasks` | 列出所有背景任務 |
| GET | `/tasks/{task_id}` | 輪詢任務狀態（進度、錯誤、結果） |
| GET | `/tasks/{task_id}/download` | 下載已完成任務的 SRT 檔案 |
| GET | `/stream/{song_id}?track=` | HTTP Range 音頻串流（original/vocals/accompaniment） |

### 6.4 Flows API (`/api/v1/flows`)

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 列出所有流程（含歌曲標題） |
| POST | `/` | 建立流程（含項目清單） |
| GET | `/{id}` | 流程詳情 |
| PUT | `/{id}` | 更新流程（全部替換策略） |
| DELETE | `/{id}` | 刪除流程（級聯） |

### 6.5 Projection API (`/api/v1/projection`)

| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | `/sessions` | 建立投影會話（可選載入流程資料） |

### 6.6 WebSocket (`/ws/projection/{session_id}`)

| 參數 | 說明 |
|------|------|
| `role=display` | 投影端（接收狀態更新） |
| `role=controller` | 控制端（發送指令 + 接收狀態） |

---

## 7. 頁面路由

| 路由 | 頁面 | 說明 |
|------|------|------|
| `/` | 首頁 Dashboard | 快速導航卡片 + YouTube 連結輸入 |
| `/songs` | 歌曲庫 | 搜尋、新增、瀏覽歌曲 |
| `/songs/{id}` | 歌曲詳情 | 音頻播放器 + 字幕編輯器 + 歌詞 |
| `/flows` | 敬拜流程 | 流程建立與編輯（拖曳排序） |
| `/audio` | 音頻處理 | YouTube URL 輸入 + 處理進度 + 歷史 |
| `/projection/display/{id}` | 投影畫面 | 全螢幕五行歌詞投影 |
| `/projection/control/{id}` | 控制面板 | 逐行控制 + 音頻播放器 + 流程導航 |

---

## 8. ML 管線技術規格

### 8.1 音頻下載（yt-dlp）

| 項目 | 規格 |
|------|------|
| 輸入 | YouTube URL |
| 輸出 | WAV 音頻檔案 + 元資料（標題、藝人、時長、video_id） |
| 格式 | bestaudio → FFmpeg 轉 WAV |
| 輸出路徑 | `data/audio/{video_id}.wav` |

### 8.2 人聲分離（Demucs）

| 項目 | 規格 |
|------|------|
| 模型 | htdemucs（預設）/ htdemucs_ft（高品質）/ mdx_extra（最快） |
| 裝置 | CPU（推薦）/ MPS（實驗性） |
| 輸出 | vocals.wav + no_vocals.wav |
| 快取 | 重複處理自動跳過 |
| 可調參數 | shifts, segment, overlap, jobs |

### 8.3 語音辨識（mlx-whisper）

| 項目 | 規格 |
|------|------|
| 模型 | mlx-community/whisper-large-v3-turbo |
| 語言 | 自動偵測 / 指定（zh, en 等） |
| 特性 | word-level timestamps, 敬拜專用 initial prompt |
| 抗幻覺 | condition_on_previous_text=False, no_speech_threshold=0.5 |
| 輸出 | segments\[\]{start_ms, end_ms, text, avg_logprob} |

### 8.4 歌詞搜尋（syncedlyrics）

| 項目 | 規格 |
|------|------|
| 搜尋策略 | 6 種策略（原始標題、藝人-歌名分離、簡體變體等） |
| 雙語處理 | 斜線分隔標題拆解、"By" 藝人提取 |
| 輸出格式 | LRC（含時間戳） |

### 8.5 歌詞對齊（自研演算法）

| 項目 | 規格 |
|------|------|
| 演算法 | 錨點式動態規劃（Anchor-based DP） |
| 錨點偵測 | Whisper 高信心度段落（logprob > 閾值 + 文字相似度 > 閾值） |
| 回退機制 | 錨點不足時啟用貪婪匹配（greedy fallback） |
| 品質閘門 | min_confidence ≥ 0.5, min_match_ratio ≥ 0.4 |
| 中文轉換 | opencc 簡→繁自動轉換 |
| 可選增強 | BPM 節拍對齊（需 librosa） |

---

## 9. 設定系統

所有設定透過環境變數管理，prefix `LAW_`（自動從 `.env` 載入）：

### 9.1 資料庫

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_DATABASE_URL` | `sqlite+aiosqlite:///./data/db/leader_at_worship.db` | SQLite 連線字串 |

### 9.2 音頻處理

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_AUDIO_DIR` | `data/audio` | 音頻下載目錄 |
| `LAW_EXPORT_DIR` | `data/exports` | 字幕輸出目錄 |

### 9.3 Whisper 語音辨識

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_WHISPER_MODEL` | `mlx-community/whisper-large-v3-turbo` | 模型名稱 |
| `LAW_WHISPER_LANGUAGE` | `auto` | 語言（auto / zh / en） |
| `LAW_WHISPER_INITIAL_PROMPT` | 敬拜詞彙提示 | 初始提示語 |

### 9.4 Demucs 人聲分離

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_DEMUCS_MODEL` | `htdemucs` | 模型（htdemucs / htdemucs_ft / mdx_extra） |
| `LAW_DEMUCS_DEVICE` | `cpu` | 裝置（cpu / mps） |
| `LAW_DEMUCS_SHIFTS` | `1` | 等變性偏移（1=快, 10=最佳品質） |
| `LAW_DEMUCS_SEGMENT` | `7` | 分段秒數 |
| `LAW_DEMUCS_OVERLAP` | `0.1` | 分段重疊率 |
| `LAW_DEMUCS_JOBS` | `8` | 並行線程數 |

### 9.5 歌詞對齊

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_ALIGNMENT_ENABLED` | `true` | 啟用對齊 |
| `LAW_ALIGNMENT_ANCHOR_THRESHOLD` | `0.55` | 錨點最低分數 |
| `LAW_ALIGNMENT_LOGPROB_THRESHOLD` | `-0.7` | Whisper logprob 門檻 |
| `LAW_ALIGNMENT_MIN_ANCHOR_RATIO` | `0.4` | 最低錨點比率 |
| `LAW_ALIGNMENT_PHANTOM_THRESHOLD_MS` | `3000` | 幻影行偵測距離（ms） |
| `LAW_ALIGNMENT_OUTPUT_TRADITIONAL` | `true` | 輸出繁體中文 |
| `LAW_ALIGNMENT_MATCH_THRESHOLD` | `0.55` | 文字匹配門檻 |
| `LAW_ALIGNMENT_MIN_CONFIDENCE` | `0.5` | 品質閘門：最低信心度 |
| `LAW_ALIGNMENT_MIN_MATCH_RATIO` | `0.4` | 品質閘門：最低匹配比率 |
| `LAW_ALIGNMENT_BPM_SNAP` | `false` | BPM 節拍對齊 |
| `LAW_ALIGNMENT_BPM_SNAP_TOLERANCE_MS` | `150` | 節拍容差（ms） |

### 9.6 管線並行

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_MAX_CONCURRENT_PIPELINES` | `1` | 同時執行的管線數（避免 OOM） |

### 9.7 伺服器

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LAW_HOST` | `0.0.0.0` | 綁定地址 |
| `LAW_PORT` | `8000` | 埠號 |
| `LAW_DEBUG` | `false` | 除錯模式 |

---

## 10. 技術棧

| 層級 | 元件 | 技術 |
|------|------|------|
| Frontend | 模板引擎 | Jinja2 SSR |
| Frontend | 互動 | Vanilla JavaScript |
| Frontend | 即時通訊 | WebSocket |
| Frontend | 音頻播放 | HTMLAudioElement + timeupdate |
| Backend | Web 框架 | FastAPI |
| Backend | ASGI 伺服器 | Uvicorn |
| Backend | ORM | SQLAlchemy 2.0 (async) |
| Backend | 資料庫 | SQLite (aiosqlite) |
| Backend | 遷移 | Alembic |
| ML | 語音辨識 | mlx-whisper (Apple Silicon) |
| ML | 人聲分離 | Demucs |
| ML | 節拍偵測 | librosa（選用） |
| Pipeline | 下載 | yt-dlp + FFmpeg |
| Pipeline | 歌詞 | syncedlyrics |
| Pipeline | 對齊 | 自研 Anchor-based DP |
| Pipeline | 文字處理 | rapidfuzz, opencc/hanziconv |
| Pipeline | 並行控制 | asyncio.Semaphore |

---

## 11. 安裝與部署

### 11.1 一鍵安裝

```bash
git clone <repo-url> && cd LeaderAtWorship && ./setup.sh
```

自動安裝：Homebrew → ffmpeg → Python 3.10+ → 虛擬環境 → pip 依賴 → 資料庫初始化。

### 11.2 依賴分組

| 分組 | 指令 | 內容 |
|------|------|------|
| 核心 | `pip install -e .` | FastAPI, SQLAlchemy, yt-dlp 等 |
| ML | `pip install -e ".[ml]"` | mlx-whisper, demucs, torch |
| 開發 | `pip install -e ".[ml,dev]"` | 加上 pytest, ruff 等 |

### 11.3 目錄結構

```
data/
  db/        → SQLite 資料庫
  audio/     → 下載的音頻檔案
  exports/   → 生成的 SRT 字幕
  models/    → ML 模型快取
```

---

## 12. 錯誤處理策略

### 12.1 管線錯誤

| 步驟 | 失敗情境 | 處理方式 |
|------|---------|---------|
| YouTube 下載 | URL 無效 / 網路錯誤 | 任務標記 `failed`，回傳錯誤訊息 |
| 人聲分離 | Demucs 未安裝 | 跳過分離，使用原始音頻繼續 |
| 語音辨識 | mlx-whisper 未安裝 | 任務失敗（核心步驟，不可跳過） |
| 歌詞搜尋 | 找不到歌詞 | 跳過對齊，使用 Whisper 原始結果 |
| 歌詞對齊 | 品質不達標 | 回退使用 Whisper 原始結果 |
| 資料庫寫入 | SQLite 鎖定 | Semaphore 已避免，若仍失敗則任務標記 `failed` |

### 12.2 WebSocket 錯誤

| 情境 | 處理方式 |
|------|---------|
| 連線斷開 | Client 自動重連 |
| Session 不存在 | 回傳錯誤並關閉連線 |
| 無效指令 | 忽略並記錄 warning |

### 12.3 依賴檢查

| 依賴 | 必要性 | 缺失時行為 |
|------|--------|----------|
| mlx-whisper | **必要** | 拋出 `MLDependencyError`，任務失敗 |
| Demucs | 選用 | 跳過人聲分離，使用原始音頻 |
| librosa | 選用 | 跳過 BPM 節拍對齊 |

---

## 13. 未來擴展（Roadmap）

| 階段 | 功能 |
|------|------|
| v1.3 | 字幕匯入/匯出（SRT/VTT/LRC 格式互轉） |
| v1.4 | 投影模板（自訂字型、大小、顏色、背景） |
| v1.5 | 多螢幕支援（舞台返送、會眾螢幕） |
| v2.0 | 雲端版本（多裝置協作） |
| v2.1 | 歌曲資料庫共享（教會間分享字幕） |

---

*LeaderAtWorship v1.2 | Product Requirements Document | 2026-03-09*
