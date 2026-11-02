import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from unittest.mock import patch

from pipeline import podcast_feed


class PodcastFeedTests(unittest.TestCase):
    def assert_owner_contract(self, feed_file):
        raw = feed_file.read_bytes()
        self.assertTrue(raw.startswith(b'<?xml version="1.0" encoding="UTF-8"?>'))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        raw.decode("utf-8")
        root = ET.fromstring(raw)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.get("version"), "2.0")
        self.assertEqual(len(root.findall("channel")), 1)
        channel = root.find("channel")
        owners = channel.findall(f"{{{podcast_feed.ITUNES_NS}}}owner")
        self.assertEqual(len(owners), 1)
        emails = owners[0].findall(f"{{{podcast_feed.ITUNES_NS}}}email")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].text, "podcast@decodethestack.com")
        self.assertEqual(emails[0].text.encode("ascii"), b"podcast@decodethestack.com")
        self.assertIsNone(channel.find("owner"))
        self.assertIsNone(channel.find("email"))

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
                SITE_URL="https://decodethestack.com",
                _duration_seconds=lambda _path: None,
            ):
                feed_file = podcast_feed.generate_feed()
            self.assert_owner_contract(feed_file)

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
            "podcast@decodethestack.com",
        )

    def test_checked_in_feed_exposes_exact_namespaced_verification_email(self):
        self.assert_owner_contract(podcast_feed.FEED_FILE)

    def test_domain_migration_keeps_legacy_identity_and_uses_new_domain_for_new_episodes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "audio"
            audio.mkdir()
            for date in ("2026-11-02", "2026-11-03"):
                (audio / f"{date}.mp3").write_bytes(b"ID3" + b"\0" * 2048)
            output = root / "feed.xml"
            with patch.multiple(
                podcast_feed, AUDIO_DIR=audio, CONTENT_DIR=root / "posts",
                CHAPTERS_DIR=root / "chapters", FEED_FILE=output,
                SITE_URL="https://decodethestack.com",
                _duration_seconds=lambda _path: None,
            ):
                podcast_feed.generate_feed()
            self.assert_owner_contract(output)
            channel = ET.parse(output).getroot().find("channel")
            self.assertEqual(channel.findtext("link"), "https://decodethestack.com/")
            self.assertEqual(
                channel.find(f"{{{podcast_feed.ATOM_NS}}}link").get("href"),
                "https://decodethestack.com/podcast/feed.xml",
            )
            self.assertEqual(
                channel.find(f"{{{podcast_feed.ITUNES_NS}}}image").get("href"),
                "https://decodethestack.com/images/podcast-cover.png",
            )
            episodes = channel.findall("item")
            for episode, expected in zip(episodes, (
                "https://decodethestack.com/podcast/audio/2026-11-03.mp3",
                "https://decodethestack.pages.dev/podcast/audio/2026-11-02.mp3",
            )):
                self.assertEqual(episode.find("enclosure").get("url"), expected)
                self.assertEqual(episode.findtext("guid"), expected)
                self.assertEqual(episode.find("guid").get("isPermaLink"), "true")
                self.assertTrue(episode.findtext("link").startswith("https://decodethestack.com/"))

    def test_regenerating_existing_episode_preserves_complete_feed(self):
        original = podcast_feed.FEED_FILE.read_text(encoding="utf-8")
        channel = ET.fromstring(original).find("channel")
        timestamp = parsedate_to_datetime(channel.findtext("lastBuildDate"))
        durations = {
            item.find("enclosure").get("url").rsplit("/", 1)[-1]: (
                int(item.findtext(f"{{{podcast_feed.ITUNES_NS}}}duration"))
                if item.findtext(f"{{{podcast_feed.ITUNES_NS}}}duration") else None
            )
            for item in channel.findall("item")
        }

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return timestamp.astimezone(tz)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "feed.xml"
            with (
                patch.object(podcast_feed, "FEED_FILE", output),
                patch.object(podcast_feed, "datetime", FrozenDatetime),
                patch.object(podcast_feed, "_duration_seconds", side_effect=lambda path: durations[path.name]),
            ):
                podcast_feed.generate_feed()
            self.assert_owner_contract(output)
            self.assertEqual(output.read_text(encoding="utf-8"), original)

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
                SITE_URL="https://decodethestack.com",
            ):
                podcast_feed.generate_feed()
            channel = ET.parse(feed).getroot().find("channel")
        self.assertIsNone(channel.find("item"))


if __name__ == "__main__":
    unittest.main()
