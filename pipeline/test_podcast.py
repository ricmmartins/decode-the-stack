import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from unittest.mock import patch

import podcast


class PodcastFeedTests(unittest.TestCase):
    def test_episode_script_reads_headlines_and_credits_sources(self):
        script = podcast.episode_script({
            "date": "2026-11-02",
            "items": [{"title": "A runtime release", "source": "Example"}],
        })
        self.assertIn("A runtime release", script)
        self.assertIn("From Example", script)
        self.assertIn("complete reporting and context", script)

    def test_feed_adds_an_enclosure_only_for_a_real_episode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            audio_dir = root / "audio"
            feed_file = root / "feed.xml"
            data_dir.mkdir()
            episode = {
                "date": "2026-11-02",
                "title": "The engineering briefing — November 2, 2026",
                "items": [{"title": "Headline", "source": "Example"}],
            }
            (data_dir / "2026-11-02.json").write_text(json.dumps(episode), encoding="utf-8")
            audio_dir.mkdir()
            (audio_dir / "2026-11-02.mp3").write_bytes(b"ID3" + b"\x00" * 2048)
            with patch.multiple(
                podcast,
                DATA_DIR=data_dir,
                AUDIO_DIR=audio_dir,
                FEED_FILE=feed_file,
                SITE_URL="https://example.test/decode-the-stack",
            ):
                podcast.generate_feed()
            channel = ET.parse(feed_file).getroot().find("channel")
            item = channel.find("item")
            enclosure = item.find("enclosure")
            self.assertEqual(enclosure.get("type"), "audio/mpeg")
            self.assertEqual(enclosure.get("length"), "2051")
            self.assertEqual(enclosure.get("url"), "https://example.test/decode-the-stack/podcast/audio/2026-11-02.mp3")
            self.assertEqual(item.find("guid").text, enclosure.get("url"))

    def test_feed_has_no_fake_item_without_audio_or_owner_email(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            data_dir.mkdir()
            (data_dir / "2026-11-02.json").write_text(
                json.dumps({"date": "2026-11-02", "title": "Brief", "items": []}),
                encoding="utf-8",
            )
            feed_file = root / "feed.xml"
            with patch.multiple(podcast, DATA_DIR=data_dir, AUDIO_DIR=root / "audio", FEED_FILE=feed_file), patch.dict(
                "os.environ", {"PODCAST_OWNER_EMAIL": ""}, clear=False
            ):
                podcast.generate_feed()
            channel = ET.parse(feed_file).getroot().find("channel")
            self.assertIsNone(channel.find("item"))
            self.assertIsNone(channel.find(f"{{{podcast.ITUNES_NS}}}owner"))

    def test_feed_includes_authorized_owner_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            feed_file = root / "feed.xml"
            with patch.multiple(
                podcast,
                DATA_DIR=root / "missing-editions",
                AUDIO_DIR=root / "missing-audio",
                FEED_FILE=feed_file,
            ), patch.dict("os.environ", {"PODCAST_OWNER_EMAIL": "owner@example.com"}, clear=False):
                podcast.generate_feed()
            channel = ET.parse(feed_file).getroot().find("channel")
            owner = channel.find(f"{{{podcast.ITUNES_NS}}}owner")
            self.assertEqual(owner.find(f"{{{podcast.ITUNES_NS}}}name").text, "Ricardo Martins")
            self.assertEqual(owner.find(f"{{{podcast.ITUNES_NS}}}email").text, "owner@example.com")


if __name__ == "__main__":
    unittest.main()
