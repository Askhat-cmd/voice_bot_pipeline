"""Official YouTube Data API client for enumerating channel uploads."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Iterator

from .models import VideoItem

LOGGER = logging.getLogger(__name__)


class YouTubeClientError(RuntimeError):
    """Raised when the channel or its uploads cannot be read."""


class YouTubeChannelClient:
    """Read videos from a channel uploads playlist via YouTube Data API v3."""

    def __init__(self, api_key: str, service: Any | None = None) -> None:
        if not api_key and service is None:
            raise ValueError("YouTube API key is required")

        if service is not None:
            self._youtube = service
            return

        try:
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover - environment validation
            raise YouTubeClientError(
                "google-api-python-client is not installed. "
                "Run: python -m pip install -r requirements-transcripts.txt"
            ) from exc

        self._youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    @staticmethod
    def normalize_handle(handle: str) -> str:
        """Normalize a channel handle for ``channels.list(forHandle=...)``."""

        value = handle.strip()
        if not value:
            raise ValueError("Channel handle cannot be empty")
        return value if value.startswith("@") else f"@{value}"

    @staticmethod
    def parse_rfc3339(value: str) -> datetime:
        """Parse a YouTube RFC3339 timestamp into an aware UTC datetime."""

        normalized = value.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def resolve_uploads_playlist(self, handle: str) -> tuple[str, str]:
        """Return ``(uploads_playlist_id, channel_title)`` for a handle."""

        normalized = self.normalize_handle(handle)
        try:
            response = (
                self._youtube.channels()
                .list(part="snippet,contentDetails", forHandle=normalized, maxResults=1)
                .execute()
            )
        except Exception as exc:  # google client exposes several transport errors
            raise YouTubeClientError(f"YouTube API channel request failed: {exc}") from exc

        items = response.get("items", [])
        if not items:
            raise YouTubeClientError(f"Channel not found for handle {normalized}")

        item = items[0]
        try:
            playlist_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        except (KeyError, TypeError) as exc:
            raise YouTubeClientError("Channel uploads playlist is missing in API response") from exc

        title = item.get("snippet", {}).get("title") or normalized
        return playlist_id, title

    def iter_videos(
        self,
        uploads_playlist_id: str,
        from_date: date,
        to_date: date,
    ) -> Iterator[VideoItem]:
        """Yield public videos whose publication dates are inside the inclusive range."""

        if from_date > to_date:
            raise ValueError("from_date cannot be later than to_date")

        page_token: str | None = None
        reached_older_items = False

        while True:
            try:
                response = (
                    self._youtube.playlistItems()
                    .list(
                        part="snippet,contentDetails",
                        playlistId=uploads_playlist_id,
                        maxResults=50,
                        pageToken=page_token,
                    )
                    .execute()
                )
            except Exception as exc:
                raise YouTubeClientError(f"YouTube API playlist request failed: {exc}") from exc

            for item in response.get("items", []):
                snippet = item.get("snippet") or {}
                content = item.get("contentDetails") or {}
                video_id = content.get("videoId") or (
                    snippet.get("resourceId") or {}
                ).get("videoId")
                title = (snippet.get("title") or "").strip()
                published_raw = content.get("videoPublishedAt") or snippet.get("publishedAt")

                if not video_id or not published_raw:
                    LOGGER.debug("Skipping playlist item without video id or date")
                    continue
                if title.casefold() in {"private video", "deleted video"}:
                    LOGGER.debug("Skipping inaccessible video %s", video_id)
                    continue

                try:
                    published_at = self.parse_rfc3339(published_raw)
                except (TypeError, ValueError):
                    LOGGER.warning("Skipping %s: invalid publication date %r", video_id, published_raw)
                    continue

                published_day = published_at.date()
                if published_day > to_date:
                    continue
                if published_day < from_date:
                    reached_older_items = True
                    continue

                yield VideoItem(
                    video_id=video_id,
                    title=title or f"Video {video_id}",
                    published_at=published_at,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )

            if reached_older_items:
                break

            page_token = response.get("nextPageToken")
            if not page_token:
                break
