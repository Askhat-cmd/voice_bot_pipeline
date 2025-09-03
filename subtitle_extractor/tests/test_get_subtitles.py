import pytest
from unittest.mock import MagicMock, patch
from youtube_transcript_api import CouldNotRetrieveTranscript
from requests.exceptions import HTTPError

from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor


def test_extract_video_id_valid_url(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert extractor.extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_invalid_url(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    assert extractor.extract_video_id("https://example.com") is None


def test_get_subtitles_preferred_language(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    mock_api = MagicMock()
    transcript_list = MagicMock()
    transcript = MagicMock()
    transcript.fetch.return_value = [{"text": "test"}]
    transcript_list.find_transcript.return_value = transcript
    mock_api.list.return_value = transcript_list

    with patch("subtitle_extractor.get_subtitles.YouTubeTranscriptApi", return_value=mock_api):
        subtitles = extractor.get_subtitles("video123", "en")

    assert subtitles == [{"text": "test"}]
    transcript_list.find_transcript.assert_called_once_with(["en"])
    transcript.fetch.assert_called_once()


def test_get_subtitles_fallback_language(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    mock_api = MagicMock()
    transcript_list = MagicMock()
    transcript = MagicMock(language_code="en")
    transcript.fetch.return_value = [{"text": "fallback"}]
    transcript_list.find_transcript.side_effect = Exception("not found")
    transcript_list.__getitem__.return_value = transcript
    mock_api.list.return_value = transcript_list

    with patch("subtitle_extractor.get_subtitles.YouTubeTranscriptApi", return_value=mock_api):
        subtitles = extractor.get_subtitles("video123", "ru")

    assert subtitles == [{"text": "fallback"}]
    transcript.fetch.assert_called_once()


def test_get_subtitles_raises_error(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    mock_api = MagicMock()
    mock_api.list.side_effect = CouldNotRetrieveTranscript("error")

    with patch("subtitle_extractor.get_subtitles.YouTubeTranscriptApi", return_value=mock_api):
        with pytest.raises(CouldNotRetrieveTranscript):
            extractor.get_subtitles("video123", "ru")


def test_get_subtitles_raises_http_error(tmp_path):
    extractor = YouTubeSubtitlesExtractor(output_dir=tmp_path)
    mock_api = MagicMock()
    mock_api.list.side_effect = HTTPError("http error")

    with patch("subtitle_extractor.get_subtitles.YouTubeTranscriptApi", return_value=mock_api):
        with pytest.raises(HTTPError):
            extractor.get_subtitles("video123", "ru")
