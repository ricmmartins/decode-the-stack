import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import publish


class FeedParsingTests(unittest.TestCase):
    def test_parses_rss_and_cleans_publisher_excerpt(self):
        feed = b"""<rss version="2.0"><channel><item>
          <title>New runtime release</title>
          <link>https://example.com/runtime</link>
          <pubDate>Sat, 31 Oct 2026 10:30:00 GMT</pubDate>
          <description><![CDATA[<p>A <b>new</b> runtime &amp; tools.</p>]]></description>
        </item></channel></rss>"""
        item = publish.parse_feed(
            {"name": "Example", "category": "Engineering", "weight": 5}, feed
        )[0]
        self.assertEqual(item["title"], "New runtime release")
        self.assertEqual(item["summary"], "A new runtime & tools.")
        self.assertEqual(item["published"], datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc))

    def test_parses_atom_alternate_link_and_date(self):
        feed = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
          <title>Cloud release</title>
          <link rel="alternate" href="https://example.com/cloud"/>
          <updated>2026-11-01T10:00:00Z</updated><summary>Release notes</summary>
        </entry></feed>"""
        item = publish.parse_feed(
            {"name": "Example", "category": "Cloud", "weight": 2}, feed
        )[0]
        self.assertEqual(item["url"], "https://example.com/cloud")
        self.assertEqual(item["summary"], "Release notes")

    def test_selects_recent_items_and_deduplicates_urls(self):
        now = datetime.now(timezone.utc)
        items = [
            {"url": "https://example.com/story#top", "title": "first", "published": now, "weight": 1, "source": "Example"},
            {"url": "https://example.com/story", "title": "duplicate", "published": now, "weight": 5, "source": "Example"},
            {"url": "https://example.com/old", "title": "old", "published": now - timedelta(days=4), "weight": 5, "source": "Example"},
        ]
        result = publish.select_recent(items, now - timedelta(days=1))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "duplicate")

    def test_selection_limits_single_publisher_dominance(self):
        now = datetime.now(timezone.utc)
        items = [
            {"url": f"https://example.com/{source}/{number}", "title": f"{source} {number}",
             "published": now - timedelta(minutes=number), "weight": 5, "source": source}
            for source in ("A", "B", "C", "D")
            for number in range(5)
        ]
        result = publish.select_recent(items, now - timedelta(days=1))
        counts = {}
        for item in result:
            counts[item["source"]] = counts.get(item["source"], 0) + 1
        self.assertEqual(len(result), publish.MAX_ITEMS)
        self.assertLessEqual(max(counts.values()), 3)

    def test_edition_preserves_source_links_and_attribution(self):
        edition = publish.render_edition(date(2026, 11, 1), [{
            "title": "Test & title",
            "url": "https://example.com/story?a=1&b=2",
            "summary": "Publisher excerpt.",
            "published": datetime(2026, 11, 1, 10, tzinfo=timezone.utc),
            "source": "Example",
            "category": "Engineering",
        }])
        self.assertIn("**Engineering · Example · Nov 01, 10:00 UTC**", edition)
        self.assertIn("https://example.com/story?a=1&b=2", edition)
        self.assertIn("not independent verification", edition)

    def test_no_recent_items_does_not_create_edition(self):
        with patch.object(publish, "fetch_source", return_value=[]), patch.object(
            publish, "SOURCES_FILE"
        ) as sources_file, patch.object(publish, "POSTS_DIR") as posts_dir:
            sources_file.read_text.return_value = '[{"name":"Example","url":"https://example.com","category":"Engineering"}]'
            result = publish.publish(date(2026, 11, 1))
        self.assertIsNone(result)
        posts_dir.__truediv__.assert_not_called()


if __name__ == "__main__":
    unittest.main()
