import sys
import types

import pytest

from youtube_channel_transcripts.transcript_service import RussianTranscriptService


class CouldNotRetrieveTranscript(Exception):
    pass


class NoTranscriptFound(CouldNotRetrieveTranscript):
    pass


class AgeRestricted(CouldNotRetrieveTranscript):
    pass


class InvalidVideoId(CouldNotRetrieveTranscript):
    pass


class IpBlocked(CouldNotRetrieveTranscript):
    pass


class PoTokenRequired(CouldNotRetrieveTranscript):
    pass


class RequestBlocked(CouldNotRetrieveTranscript):
    pass


class TranscriptsDisabled(CouldNotRetrieveTranscript):
    pass


class VideoUnavailable(CouldNotRetrieveTranscript):
    pass


class VideoUnplayable(CouldNotRetrieveTranscript):
    pass


class YouTubeRequestFailed(CouldNotRetrieveTranscript):
    pass


class FakeYouTubeTranscriptApi:
    pass


@pytest.fixture(autouse=True)
def fake_youtube_transcript_modules(monkeypatch):
    package = types.ModuleType("youtube_transcript_api")
    package.YouTubeTranscriptApi = FakeYouTubeTranscriptApi
    errors = types.ModuleType("youtube_transcript_api._errors")
    for cls in [
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
    ]:
        setattr(errors, cls.__name__, cls)
    monkeypatch.setitem(sys.modules, "youtube_transcript_api", package)
    monkeypatch.setitem(sys.modules, "youtube_transcript_api._errors", errors)


class Track:
    def __init__(self, generated, text):
        self.is_generated = generated
        self.language_code = "ru"
        self._text = text

    def fetch(self):
        return [{"text": self._text}]


class ListWithManual:
    def find_manually_created_transcript(self, languages):
        assert languages == ["ru"]
        return Track(False, "ручной текст")

    def find_generated_transcript(self, languages):
        raise AssertionError("generated track must not be requested")


class ListWithGeneratedOnly:
    def find_manually_created_transcript(self, languages):
        raise NoTranscriptFound()

    def find_generated_transcript(self, languages):
        return Track(True, "автоматический текст")


class Api:
    def __init__(self, transcript_list):
        self.transcript_list = transcript_list

    def list(self, video_id):
        assert video_id == "abcdefghijk"
        return self.transcript_list


def test_manual_russian_track_has_priority():
    service = RussianTranscriptService(api=Api(ListWithManual()), sleep=lambda _: None)
    result = service.fetch("abcdefghijk")
    assert result.subtitle_type == "ручные"
    assert result.snippets == ("ручной текст",)


def test_generated_russian_track_is_fallback():
    service = RussianTranscriptService(api=Api(ListWithGeneratedOnly()), sleep=lambda _: None)
    result = service.fetch("abcdefghijk")
    assert result.subtitle_type == "автоматические"
    assert result.snippets == ("автоматический текст",)
