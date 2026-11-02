import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import stats


class PublicationStatsTests(unittest.TestCase):
    def test_only_published_stories_contribute_to_totals_and_breakdowns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            posts, ranked = root / "posts", root / "ranked"
            posts.mkdir()
            ranked.mkdir()
            (posts / "2026-11-02-daily.md").write_text(
                "---\nmainCount: 1\nquickCount: 1\n---\n"
                "### [Published main](https://example.com/main)\nContext.\n"
                "#### [Published quick](https://example.com/quick)\nContext.\n",
                encoding="utf-8",
            )
            (ranked / "top_2026-11-02.json").write_text(json.dumps([
                {"url": "https://example.com/main", "category": "cloud", "source_name": "Published"},
                {"url": "https://example.com/omitted", "category": "security", "source_name": "Omitted"},
            ]), encoding="utf-8")
            (ranked / "quick_2026-11-02.json").write_text(json.dumps([
                {"url": "https://example.com/quick", "category": "ai", "source_name": "Quick"},
            ]), encoding="utf-8")
            with (
                patch.multiple(stats, CONTENT_DIR=posts, DATA_RANKED_DIR=ranked, HUGO_DATA_DIR=root),
                patch.object(stats, "get_source_count", return_value=242),
            ):
                result = stats.generate_publication_stats()
            self.assertEqual(result["headlines_published"], 2)
            self.assertEqual(result["latest_headlines"], 2)
            self.assertEqual(result["history"][0]["headlines"], 2)
            self.assertEqual(result["sources_credited"], 2)
            self.assertEqual({row["name"] for row in result["source_counts"]}, {"Published", "Quick"})
            self.assertEqual({row["name"] for row in result["category_counts"]}, {"Cloud", "AI/ML"})


if __name__ == "__main__":
    unittest.main()
