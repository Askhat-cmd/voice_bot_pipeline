"""Data models used by the transcript downloader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class VideoItem:
    """A public video discovered in a channel uploads playlist."""

    video_id: str
    title: str
    published_at: datetime
    url: str

    @property
    def published_date(self) -> str:
        """Return the publication date in ISO ``YYYY-MM-DD`` format."""

        return self.published_at.date().isoformat()


@dataclass(frozen=True, slots=True)
class TranscriptResult:
    """A fetched transcript and its metadata."""

    snippets: tuple[str, ...]
    subtitle_type: str
    language_code: str = "ru"


@dataclass(slots=True)
class RunStats:
    """Counters shown at the end of a CLI run."""

    found: int = 0
    saved: int = 0
    no_russian: int = 0
    already_processed: int = 0
    unavailable: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return counters as a serializable mapping."""

        return {
            "found": self.found,
            "saved": self.saved,
            "no_russian": self.no_russian,
            "already_processed": self.already_processed,
            "unavailable": self.unavailable,
            "failed": self.failed,
        }
