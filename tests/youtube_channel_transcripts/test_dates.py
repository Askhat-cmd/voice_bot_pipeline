from datetime import date

import pytest

from youtube_channel_transcripts.cli import CLIArgumentError, build_parser, validate_args
from youtube_channel_transcripts.youtube_client import YouTubeChannelClient


class Request:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class PlaylistItems:
    def __init__(self, response):
        self.response = response

    def list(self, **kwargs):
        return Request(self.response)


class Service:
    def __init__(self, response):
        self.response = response

    def playlistItems(self):
        return PlaylistItems(self.response)


def test_inclusive_date_boundaries():
    response = {
        "items": [
            {
                "snippet": {"title": "Start"},
                "contentDetails": {
                    "videoId": "aaaaaaaaaaa",
                    "videoPublishedAt": "2025-01-01T00:00:00Z",
                },
            },
            {
                "snippet": {"title": "End"},
                "contentDetails": {
                    "videoId": "bbbbbbbbbbb",
                    "videoPublishedAt": "2025-01-31T23:59:59Z",
                },
            },
        ]
    }
    client = YouTubeChannelClient("test", service=Service(response))
    videos = list(client.iter_videos("uploads", date(2025, 1, 1), date(2025, 1, 31)))
    assert [video.title for video in videos] == ["Start", "End"]


def test_from_date_after_to_date_is_rejected():
    parser = build_parser()
    args = parser.parse_args(
        ["--from-date", "2025-02-01", "--to-date", "2025-01-01"]
    )
    with pytest.raises(CLIArgumentError):
        validate_args(args)
