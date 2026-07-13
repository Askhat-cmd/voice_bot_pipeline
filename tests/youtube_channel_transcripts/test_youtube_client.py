from youtube_channel_transcripts.youtube_client import YouTubeChannelClient


class Request:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class Channels:
    def list(self, **kwargs):
        assert kwargs["forHandle"] == "@Salsar"
        return Request(
            {
                "items": [
                    {
                        "snippet": {"title": "Salsar"},
                        "contentDetails": {"relatedPlaylists": {"uploads": "UU123"}},
                    }
                ]
            }
        )


class Service:
    def channels(self):
        return Channels()


def test_resolve_uploads_playlist_uses_handle_without_network():
    client = YouTubeChannelClient("test", service=Service())
    assert client.resolve_uploads_playlist("Salsar") == ("UU123", "Salsar")
