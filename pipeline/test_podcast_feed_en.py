import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from pipeline import podcast_feed


class PodcastFeedTests(unittest.TestCase):
    def test_published_mp3_has_stable_enclosure_and_owner_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "static" / "podcast" / "audio"
            posts = root / "content" / "posts"
            static = root / "static"
            audio.mkdir(parents=True)
            posts.mkdir(parents=True)
            (audio / "2026-11-02.mp3").write_bytes(b"ID3" + b"\0" * 2048)
            (posts / "2026-11-02-daily.md").write_text(
                '---\ntitle: "An English edition"\ndescription: "Context for engineers."\n---\n',
                encoding="utf-8",
            )

            with patch.multiple(
                podcast_feed,
                PROJECT_DIR=root,
                AUDIO_DIR=audio,
                CONTENT_DIR=posts,
                FEED_FILE=static / "podcast" / "feed.xml",
                SITE_URL="https://decodethestack.pages.dev",
                _duration_seconds=lambda _path: None,
            ):
                feed_file = podcast_feed.generate_feed()

            channel = ET.parse(feed_file).getroot().find("channel")
            episode = channel.find("item")
            enclosure = episode.find("enclosure")
            owner = channel.find(f"{{{podcast_feed.ITUNES_NS}}}owner")

        expected_url = "https://decodethestack.pages.dev/podcast/audio/2026-11-02.mp3"
        self.assertEqual(enclosure.get("url"), expected_url)
        self.assertEqual(episode.findtext("guid"), expected_url)
        self.assertEqual(enclosure.get("length"), "2051")
        self.assertEqual(episode.findtext("title"), "An English edition")
        self.assertIn("Anna, Maria, and Pedro", channel.findtext("description"))
        self.assertNotIn("Alex", channel.findtext("description"))
        self.assertEqual(
            owner.findtext(f"{{{podcast_feed.ITUNES_NS}}}name"),
            "Ricardo Martins",
        )
        self.assertEqual(
            owner.findtext(f"{{{podcast_feed.ITUNES_NS}}}email"),
            "rmmartins@outlook.com",
        )

    def test_feed_has_no_episode_without_a_published_audio_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            static = root / "static"
            feed = static / "podcast" / "feed.xml"
            with patch.multiple(
                podcast_feed,
                PROJECT_DIR=root,
                AUDIO_DIR=root / "missing-audio",
                CONTENT_DIR=root / "missing-posts",
                FEED_FILE=feed,
                SITE_URL="https://decodethestack.pages.dev",
            ):
                podcast_feed.generate_feed()
            channel = ET.parse(feed).getroot().find("channel")
        self.assertIsNone(channel.find("item"))


if __name__ == "__main__":
    unittest.main()
