"""Command-line interface for channel transcript downloading."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from .models import RunStats
from .registry import RegistryError, TranscriptRegistry
from .storage import save_transcript
from .text_cleaner import clean_transcript
from .transcript_service import (
    RussianTranscriptNotFound,
    RussianTranscriptService,
    TranscriptServiceError,
    TranscriptTemporaryError,
    TranscriptUnavailable,
)
from .youtube_client import YouTubeChannelClient, YouTubeClientError


class CLIArgumentError(ValueError):
    """Raised instead of terminating inside argparse."""


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CLIArgumentError(message)


def parse_date(value: str) -> date:
    """Parse ``YYYY-MM-DD`` for argparse."""

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = ArgumentParser(
        description="Download Russian subtitles from a YouTube channel by inclusive date range."
    )
    parser.add_argument("--from-date", required=True, type=parse_date, help="Start date YYYY-MM-DD")
    parser.add_argument("--to-date", required=True, type=parse_date, help="End date YYYY-MM-DD")
    parser.add_argument("--channel", default="@Salsar", help="YouTube channel handle")
    parser.add_argument("--output", type=Path, default=Path("transcript_output"))
    parser.add_argument(
        "--registry", type=Path, default=Path("data/transcript_registry.json")
    )
    parser.add_argument("--force", action="store_true", help="Reprocess every matching video")
    parser.add_argument(
        "--retry-skipped",
        action="store_true",
        help="Retry videos previously skipped without Russian subtitles",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed and unavailable videos",
    )
    parser.add_argument("--limit", type=int, help="Process at most N matching videos")
    parser.add_argument("--dry-run", action="store_true", help="List videos without writing files")
    parser.add_argument("--verbose", action="store_true", help="Enable detailed logging")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.from_date > args.to_date:
        raise CLIArgumentError("--from-date cannot be later than --to-date")
    if args.limit is not None and args.limit < 1:
        raise CLIArgumentError("--limit must be at least 1")


def _print_stats(stats: RunStats) -> None:
    print("\nИтоги:")
    print(f"Найдено видео: {stats.found}")
    print(f"Сохранено: {stats.saved}")
    print(f"Без русских субтитров: {stats.no_russian}")
    print(f"Уже обработано: {stats.already_processed}")
    print(f"Недоступно: {stats.unavailable}")
    print(f"Ошибок: {stats.failed}")


def _short_error(exc: BaseException, limit: int = 240) -> str:
    value = " ".join(str(exc).split())
    return value[:limit] + ("…" if len(value) > limit else "")


def run(args: argparse.Namespace) -> int:
    """Execute one CLI run. Per-video failures do not abort the batch."""

    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[ERROR] YOUTUBE_API_KEY is missing in .env or environment", file=sys.stderr)
        return 1

    try:
        client = YouTubeChannelClient(api_key)
        playlist_id, channel_title = client.resolve_uploads_playlist(args.channel)
        videos = list(client.iter_videos(playlist_id, args.from_date, args.to_date))
    except (YouTubeClientError, ValueError) as exc:
        print(f"[ERROR] {_short_error(exc)}", file=sys.stderr)
        return 1

    if args.limit is not None:
        videos = videos[: args.limit]

    print(f"Канал: {channel_title} ({YouTubeChannelClient.normalize_handle(args.channel)})")
    print(f"Диапазон: {args.from_date.isoformat()} — {args.to_date.isoformat()} включительно")
    print(f"Найдено: {len(videos)}")

    if args.dry_run:
        for index, video in enumerate(videos, 1):
            print(f"[{index}/{len(videos)}] {video.published_date} — {video.title}")
        print("\n[DRY-RUN] Субтитры не запрашивались, файлы и реестр не изменялись.")
        return 0

    try:
        registry = TranscriptRegistry(args.registry)
        transcript_service = RussianTranscriptService()
    except (RegistryError, TranscriptServiceError, ValueError) as exc:
        print(f"[ERROR] {_short_error(exc)}", file=sys.stderr)
        return 1

    stats = RunStats(found=len(videos))
    output_root: Path = args.output

    for index, video in enumerate(videos, 1):
        print(f"\n[{index}/{len(videos)}] {video.published_date} — {video.title}")
        if not registry.should_process(
            video.video_id,
            force=args.force,
            retry_skipped=args.retry_skipped,
            retry_failed=args.retry_failed,
        ):
            stats.already_processed += 1
            print("[SKIP] Уже обработано или исключено реестром")
            continue

        try:
            registry.update(video, status="processing")
            transcript = transcript_service.fetch(video.video_id)
            text = clean_transcript(transcript.snippets)
            if not text:
                raise TranscriptServiceError("Transcript is empty after cleanup")
            output_path = save_transcript(output_root, video, transcript, text)
            registry.update(
                video,
                status="processed",
                subtitle_type=transcript.subtitle_type,
                output_file=str(output_path),
            )
            stats.saved += 1
            print(f"[OK] Сохранено: {output_path}")
        except RussianTranscriptNotFound as exc:
            registry.update(
                video,
                status="skipped_no_russian_subtitles",
                error=_short_error(exc),
            )
            stats.no_russian += 1
            print("[SKIP] Русские субтитры отсутствуют")
        except TranscriptUnavailable as exc:
            registry.update(video, status="unavailable", error=_short_error(exc))
            stats.unavailable += 1
            print(f"[SKIP] Видео или субтитры недоступны: {_short_error(exc)}")
        except (TranscriptTemporaryError, TranscriptServiceError, OSError) as exc:
            try:
                registry.update(video, status="failed", error=_short_error(exc))
            except RegistryError as registry_exc:
                print(f"[ERROR] Реестр недоступен: {_short_error(registry_exc)}", file=sys.stderr)
                return 1
            stats.failed += 1
            print(f"[ERROR] {_short_error(exc)}")
        except RegistryError as exc:
            print(f"[ERROR] Реестр недоступен: {_short_error(exc)}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\n[STOP] Остановлено пользователем. Следующий запуск продолжит обработку.")
            _print_stats(stats)
            return 130

    _print_stats(stats)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point returning a process exit code."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        validate_args(args)
    except CLIArgumentError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        parser.print_usage(sys.stderr)
        return 2

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return run(args)
