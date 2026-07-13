"""Conservative cleanup for subtitle fragments."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_STAGE_RE = re.compile(
    r"^\s*[\[(](?:музыка|аплодисменты|смех|шум|тишина|music|applause|laughter)[\])]\s*[.!…]*\s*$",
    re.IGNORECASE,
)
_NOTE_RE = re.compile(r"^\s*[♪♫]+\s*$")


def clean_fragment(value: str) -> str:
    """Normalize one subtitle fragment without rewriting its content."""

    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    text = text.replace("\u200b", " ").replace("\ufeff", " ")
    text = _SPACE_RE.sub(" ", text).strip()
    if not text or _STAGE_RE.fullmatch(text) or _NOTE_RE.fullmatch(text):
        return ""
    return text


def _normalized_tokens(text: str) -> list[str]:
    return text.casefold().split()


def _append_without_overlap(parts: list[str], current: str, max_overlap: int = 20) -> None:
    """Append a caption while removing exact rolling-caption overlap."""

    if not parts:
        parts.append(current)
        return

    previous = parts[-1]
    prev_norm = previous.casefold()
    current_norm = current.casefold()

    if current_norm == prev_norm or prev_norm.startswith(current_norm):
        return
    if current_norm.startswith(prev_norm + " "):
        remainder = current[len(previous) :].strip()
        if remainder:
            parts.append(remainder)
        return

    prev_tokens = _normalized_tokens(previous)
    current_tokens = current.split()
    current_norm_tokens = [token.casefold() for token in current_tokens]
    limit = min(len(prev_tokens), len(current_norm_tokens), max_overlap)

    overlap = 0
    for size in range(limit, 1, -1):
        if prev_tokens[-size:] == current_norm_tokens[:size]:
            overlap = size
            break

    if overlap:
        remainder = " ".join(current_tokens[overlap:]).strip()
        if remainder:
            parts.append(remainder)
    else:
        parts.append(current)


def clean_transcript(fragments: Iterable[str]) -> str:
    """Combine subtitle fragments into one cleaned text without timestamps."""

    parts: list[str] = []
    for fragment in fragments:
        cleaned = clean_fragment(fragment)
        if cleaned:
            _append_without_overlap(parts, cleaned)
    return _SPACE_RE.sub(" ", " ".join(parts)).strip()
