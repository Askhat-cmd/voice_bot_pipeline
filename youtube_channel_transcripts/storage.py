"""TXT output and Windows-safe file naming."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from .models import TranscriptResult, VideoItem

_INVALID_WINDOWS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_SPACE_RE = re.compile(r"\s+")
_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_filename_component(value: str, max_length: int = 120) -> str:
    """Return a Windows-safe filename component."""

    cleaned = _INVALID_WINDOWS_CHARS.sub("_", value)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "video"
    if cleaned.upper() in _RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned[:max_length].rstrip(" .") or "video"


def build_output_path(output_root: Path, video: VideoItem, max_filename: int = 190) -> Path:
    """Build ``output/YYYY/MM/YYYY-MM-DD_title_videoid.txt``."""

    date_text = video.published_date
    prefix = f"{date_text}_"
    suffix = f"_{video.video_id}.txt"
    allowed_title = max(20, max_filename - len(prefix) - len(suffix))
    title = safe_filename_component(video.title, allowed_title)
    filename = f"{prefix}{title}{suffix}"
    return output_root / f"{video.published_at.year:04d}" / f"{video.published_at.month:02d}" / filename


def format_txt(video: VideoItem, transcript: TranscriptResult, text: str) -> str:
    """Create the required structured UTF-8 TXT content."""

    date_text = video.published_at.strftime("%d.%m.%Y")
    return (
        f"Название: {video.title}\n"
        f"Дата публикации: {date_text}\n"
        f"Ссылка: {video.url}\n"
        f"ID ролика: {video.video_id}\n"
        "Язык субтитров: русский\n"
        f"Тип субтитров: {transcript.subtitle_type}\n\n"
        "============================================================\n\n"
        f"{text.strip()}\n"
    )


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file in its destination directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_transcript(
    output_root: Path,
    video: VideoItem,
    transcript: TranscriptResult,
    text: str,
) -> Path:
    """Save one transcript and return its path."""

    path = build_output_path(output_root, video)
    atomic_write_text(path, format_txt(video, transcript, text))
    return path
