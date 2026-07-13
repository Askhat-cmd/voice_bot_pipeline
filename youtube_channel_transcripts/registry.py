"""Crash-safe JSON registry for resumable transcript downloads."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import VideoItem


class RegistryError(RuntimeError):
    """Raised when a registry cannot be read or written safely."""


class TranscriptRegistry:
    """Persist per-video processing status after each video."""

    VERSION = "1.0"

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": self.VERSION, "updated_at": None, "videos": {}}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryError(f"Cannot read registry {self.path}: {exc}") from exc

        if not isinstance(data, dict) or not isinstance(data.get("videos"), dict):
            raise RegistryError(f"Invalid registry structure: {self.path}")
        data.setdefault("version", self.VERSION)
        data.setdefault("updated_at", None)
        return data

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get(self, video_id: str) -> dict[str, Any] | None:
        """Return a video record when present."""

        record = self.data["videos"].get(video_id)
        return record if isinstance(record, dict) else None

    def should_process(
        self,
        video_id: str,
        *,
        force: bool = False,
        retry_skipped: bool = False,
        retry_failed: bool = False,
    ) -> bool:
        """Decide whether a video should run during the current invocation."""

        if force:
            return True
        record = self.get(video_id)
        if not record:
            return True

        status = record.get("status")
        if status == "processed":
            return False
        if status == "skipped_no_russian_subtitles":
            return retry_skipped
        if status in {"failed", "unavailable"}:
            return retry_failed
        return True  # includes stale ``processing`` records

    def update(
        self,
        video: VideoItem,
        *,
        status: str,
        subtitle_type: str | None = None,
        output_file: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update a video record and atomically persist the registry."""

        self.data["videos"][video.video_id] = {
            "video_id": video.video_id,
            "title": video.title,
            "published_date": video.published_date,
            "url": video.url,
            "status": status,
            "subtitle_type": subtitle_type,
            "output_file": output_file,
            "processed_at": self._now(),
            "error": error,
        }
        self.save()

    def save(self) -> None:
        """Write the registry atomically through a same-directory temporary file."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = self._now()
        payload = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise RegistryError(f"Cannot save registry {self.path}: {exc}") from exc
        finally:
            temporary.unlink(missing_ok=True)
