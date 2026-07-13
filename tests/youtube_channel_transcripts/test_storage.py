from datetime import datetime, timezone
from pathlib import Path

from youtube_channel_transcripts.models import TranscriptResult, VideoItem
from youtube_channel_transcripts.storage import build_output_path, safe_filename_component, save_transcript


def make_video(title="Bad: title? <test>"):
    return VideoItem(
        video_id="abcdefghijk",
        title=title,
        published_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        url="https://www.youtube.com/watch?v=abcdefghijk",
    )


def test_windows_safe_filename_preserves_video_id():
    path = build_output_path(Path("out"), make_video())
    assert path.name.endswith("_abcdefghijk.txt")
    assert not any(char in path.name for char in '<>:"/\\|?*')


def test_reserved_windows_name_is_prefixed():
    assert safe_filename_component("CON") == "_CON"


def test_save_transcript_writes_structured_utf8_txt(tmp_path):
    video = make_video("Название")
    transcript = TranscriptResult(("текст",), "автоматические")
    path = save_transcript(tmp_path, video, transcript, "Полный текст")
    content = path.read_text(encoding="utf-8")
    assert "Название: Название" in content
    assert "Дата публикации: 15.06.2025" in content
    assert "Тип субтитров: автоматические" in content
    assert content.rstrip().endswith("Полный текст")
