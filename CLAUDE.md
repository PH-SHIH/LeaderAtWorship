# CLAUDE.md - LeaderAtWorship

## Project Overview

Worship subtitle generation and live projection control tool built with FastAPI for Apple Silicon Macs. Pipeline: YouTube download -> Demucs vocal separation -> mlx-whisper transcription -> anchor-based lyrics alignment -> SRT/VTT subtitle generation -> real-time WebSocket projection.

## Quick Start

```bash
# Install dependencies
pip install -e ".[ml,dev]"

# Run dev server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Run migrations
alembic upgrade head
```

## Architecture

```
app/
  main.py              # FastAPI app, page routes, lifespan
  config.py            # Settings via pydantic-settings (.env prefix: LAW_)
  database.py          # AsyncIO SQLAlchemy + aiosqlite

  api/v1/              # REST endpoints
    songs.py           # Song CRUD + lyrics
    subtitles.py       # Subtitle CRUD + line editing (PATCH/POST/DELETE)
    audio.py           # Background pipeline + audio streaming (HTTP Range)
    flows.py           # Worship flow CRUD with song enrichment
    projection.py      # Projection session creation + flow data preload

  api/ws/
    projection.py      # WebSocket: display/controller roles

  models/              # SQLAlchemy ORM
    song.py            # Song, SongLyrics, LyricsLine
    subtitle.py        # SubtitleFile, SubtitleLine (source_type tracking)
    worship_flow.py    # WorshipFlow, FlowItem (ordered, with song FK)
    session.py         # ProjectionSession

  schemas/             # Pydantic v2 (from_attributes=True)
    song.py, subtitle.py, worship_flow.py, projection.py

  services/            # Business logic
    youtube.py         # yt-dlp download -> WAV
    separator.py       # Demucs -> (vocals, no_vocals) paths
    transcriber.py     # mlx-whisper -> segments with timestamps
    lyrics_fetcher.py  # syncedlyrics online search (multi-strategy)
    lyrics_aligner.py  # Anchor-based DP alignment algorithm
    subtitle_generator.py  # SRT/VTT file generation
    projection_manager.py  # WebSocket state + broadcasting

  tasks/
    audio_pipeline.py  # Orchestrator: download->separate->transcribe->align->save
    task_store.py      # In-memory task dict (no persistence)

  utils/
    lrc_parser.py      # LRC format parser
    deps_check.py      # check_demucs(), check_whisper()
```

## Database

SQLite async via aiosqlite. Migrations managed by Alembic.

Key relationships:
- Song 1:N SongLyrics 1:N LyricsLine
- Song 1:N SubtitleFile 1:N SubtitleLine
- WorshipFlow 1:N FlowItem N:1 Song
- ProjectionSession N:1 WorshipFlow

## API Endpoints

### Songs: `/api/v1/songs`
- GET `/` — list (optional `?q=` search)
- POST `/` — create
- GET `/{id}` — detail with lyrics
- PUT `/{id}` — update
- DELETE `/{id}` — cascade delete
- POST `/{id}/lyrics` — add lyrics

### Subtitles: `/api/v1/subtitles`
- GET `/` — list all
- GET `/{id}` — detail with lines
- GET `/by-song/{song_id}` — by song
- PATCH `/lines/{line_id}` — edit line (auto-sets source_type=manual)
- POST `/{subtitle_id}/lines` — insert line (auto reindex)
- DELETE `/lines/{line_id}` — delete line (auto reindex)

### Audio: `/api/v1/audio`
- POST `/extract` — submit YouTube URL -> background pipeline
- GET `/tasks` — list all tasks
- GET `/tasks/{task_id}` — poll status
- GET `/tasks/{task_id}/download` — download SRT
- GET `/stream/{song_id}?track=original|vocals|accompaniment` — HTTP Range streaming

### Flows: `/api/v1/flows`
- GET `/` — list with song titles enriched
- POST `/` — create with items
- GET `/{id}` — detail
- PUT `/{id}` — update (replace-all items strategy)
- DELETE `/{id}` — cascade delete

### Projection: `/api/v1/projection`
- POST `/sessions` — create (optional flow_id, preloads subtitles)

### WebSocket: `/ws/projection/{session_id}?role=display|controller`
Commands: next_line, prev_line, goto_line, next_item, prev_item, goto_item, toggle_blank, set_text

## Page Routes

- `/` — Dashboard
- `/songs` — Song library
- `/songs/{id}` — Song detail + player + subtitle editor
- `/flows` — Worship flow editor
- `/audio` — Audio processing (YouTube URL input)
- `/projection/display/{session_id}` — Full-screen projection
- `/projection/control/{session_id}` — Controller panel

## Key Patterns

- **Async-first**: All DB operations use AsyncSession
- **selectinload**: Eager-load relationships (lines, items, songs)
- **Background tasks**: asyncio.create_task for pipeline, poll via task_store
- **source_type tracking**: SubtitleLine.source_type = anchor|interpolated|extrapolated|phantom|greedy|manual
- **Alignment confidence**: Per-file (alignment_confidence) and per-line (confidence)
- **Bilingual support**: text + text_secondary on SubtitleLine

## ML Dependencies (Optional)

- `mlx-whisper` — Required for transcription (Apple Silicon only)
- `demucs` — Optional for vocal separation
- `librosa` — Optional for BPM beat-snapping

## Environment Variables

Prefix: `LAW_` (loaded from .env)

Key settings in `app/config.py`:
- `LAW_DATABASE_URL` — SQLite connection string
- `LAW_WHISPER_MODEL` — mlx-whisper model name
- `LAW_DEMUCS_MODEL` — Demucs model (htdemucs)
- Various alignment thresholds (anchor_ratio, confidence, etc.)

## Testing

```bash
pytest                    # run all tests
pytest --cov=app         # with coverage
```
