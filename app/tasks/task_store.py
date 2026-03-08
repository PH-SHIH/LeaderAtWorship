"""
In-memory task store shared between API endpoints and background tasks.

Keys are UUID strings, values are dicts with:
  - status: str (pending|downloading|separating|transcribing|generating|saving|completed|failed)
  - progress: int (0-100)
  - error: str | None
  - result_id: int | None (SubtitleFile.id after completion)
  - video_title: str | None (YouTube video title for display)
  - detail: str | None (additional status info)
"""

task_store: dict[str, dict] = {}
