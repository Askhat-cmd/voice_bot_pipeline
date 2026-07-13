import json
from datetime import datetime, timezone

from youtube_channel_transcripts.models import VideoItem
from youtube_channel_transcripts.registry import TranscriptRegistry


def make_video():
    return VideoItem(
        video_id="abcdefghijk",
        title="Видео",
        published_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        url="https://www.youtube.com/watch?v=abcdefghijk",
    )


def test_processed_video_is_skipped_on_next_run(tmp_path):
    path = tmp_path / "registry.json"
    registry = TranscriptRegistry(path)
    registry.update(make_video(), status="processed", output_file="out.txt")

    reloaded = TranscriptRegistry(path)
    assert reloaded.should_process("abcdefghijk") is False
    assert reloaded.should_process("abcdefghijk", force=True) is True


def test_stale_processing_record_is_retried(tmp_path):
    registry = TranscriptRegistry(tmp_path / "registry.json")
    registry.update(make_video(), status="processing")
    assert registry.should_process("abcdefghijk") is True


def test_registry_is_valid_json_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "registry.json"
    registry = TranscriptRegistry(path)
    registry.update(make_video(), status="failed", error="test")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["videos"]["abcdefghijk"]["status"] == "failed"
    assert list(tmp_path.glob("*.tmp")) == []
