"""Russian transcript retrieval using youtube-transcript-api."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

from .models import TranscriptResult

LOGGER = logging.getLogger(__name__)


class TranscriptServiceError(RuntimeError):
    """Base error for transcript retrieval."""


class RussianTranscriptNotFound(TranscriptServiceError):
    """Raised when neither manual nor generated Russian subtitles exist."""


class TranscriptUnavailable(TranscriptServiceError):
    """Raised when the video or its transcript endpoint is unavailable."""


class TranscriptTemporaryError(TranscriptServiceError):
    """Raised after retryable transcript failures are exhausted."""


@dataclass(frozen=True, slots=True)
class _ExceptionTypes:
    no_transcript: tuple[type[BaseException], ...]
    unavailable: tuple[type[BaseException], ...]
    retryable: tuple[type[BaseException], ...]
    api_base: tuple[type[BaseException], ...]


class RussianTranscriptService:
    """Fetch manual Russian subtitles first, then generated Russian subtitles."""

    def __init__(
        self,
        api: Any | None = None,
        retries: int = 3,
        retry_delay: float = 1.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if retries < 1:
            raise ValueError("retries must be at least 1")
        if retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")

        self.retries = retries
        self.retry_delay = retry_delay
        self._sleep = sleep

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                AgeRestricted,
                CouldNotRetrieveTranscript,
                InvalidVideoId,
                IpBlocked,
                NoTranscriptFound,
                PoTokenRequired,
                RequestBlocked,
                TranscriptsDisabled,
                VideoUnavailable,
                VideoUnplayable,
                YouTubeRequestFailed,
            )
        except ImportError as exc:  # pragma: no cover - environment validation
            raise TranscriptServiceError(
                "youtube-transcript-api is not installed. "
                "Run: python -m pip install -r requirements-transcripts.txt"
            ) from exc

        self._api = api or YouTubeTranscriptApi()
        self._exceptions = _ExceptionTypes(
            no_transcript=(NoTranscriptFound,),
            unavailable=(
                AgeRestricted,
                InvalidVideoId,
                PoTokenRequired,
                TranscriptsDisabled,
                VideoUnavailable,
                VideoUnplayable,
            ),
            retryable=(YouTubeRequestFailed, RequestBlocked, IpBlocked),
            api_base=(CouldNotRetrieveTranscript,),
        )

    def fetch(self, video_id: str) -> TranscriptResult:
        """Fetch Russian subtitles without using automatic translation."""

        last_retryable: BaseException | None = None
        for attempt in range(1, self.retries + 1):
            try:
                transcript_list = self._api.list(video_id)
                transcript = self._find_russian_track(transcript_list)
                fetched = transcript.fetch()
                snippets = tuple(
                    text
                    for text in (self._snippet_text(item) for item in fetched)
                    if text
                )
                return TranscriptResult(
                    snippets=snippets,
                    subtitle_type="автоматические" if transcript.is_generated else "ручные",
                    language_code=transcript.language_code,
                )
            except RussianTranscriptNotFound:
                raise
            except self._exceptions.no_transcript as exc:
                raise RussianTranscriptNotFound(str(exc)) from exc
            except self._exceptions.unavailable as exc:
                raise TranscriptUnavailable(str(exc)) from exc
            except self._exceptions.retryable as exc:
                last_retryable = exc
                if attempt < self.retries:
                    delay = self.retry_delay * attempt
                    LOGGER.warning(
                        "Temporary transcript error for %s (attempt %s/%s): %s",
                        video_id,
                        attempt,
                        self.retries,
                        exc.__class__.__name__,
                    )
                    self._sleep(delay)
                    continue
                break
            except self._exceptions.api_base as exc:
                raise TranscriptServiceError(str(exc)) from exc
            except Exception as exc:
                raise TranscriptServiceError(
                    f"Unexpected transcript error for {video_id}: {exc}"
                ) from exc

        raise TranscriptTemporaryError(str(last_retryable) if last_retryable else "Unknown error")

    @staticmethod
    def _snippet_text(item: Any) -> str:
        if hasattr(item, "text"):
            return str(item.text)
        if isinstance(item, dict):
            return str(item.get("text", ""))
        return str(item)

    def _find_russian_track(self, transcript_list: Any) -> Any:
        try:
            return transcript_list.find_manually_created_transcript(["ru"])
        except self._exceptions.no_transcript:
            pass

        try:
            return transcript_list.find_generated_transcript(["ru"])
        except self._exceptions.no_transcript as exc:
            raise RussianTranscriptNotFound("Russian subtitles are not available") from exc
