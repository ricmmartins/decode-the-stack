import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from pipeline import generate_post, weekly_summary


class PostGenerationTests(unittest.TestCase):
    def test_extracts_english_title_and_intro(self):
        content = (
            "HEADLINE: Platform changes are reshaping AI infrastructure\n\n"
            "A sufficiently long English introduction that describes the "
            "verified developments and why they matter to engineers.\n\n"
            "## Cloud\n"
        )
        self.assertEqual(
            generate_post.build_dynamic_title(content, []),
            "Platform changes are reshaping AI infrastructure",
        )
        self.assertIn("verified developments", generate_post.extract_intro_paragraph(content))

    def test_maps_pipeline_categories_to_site_categories(self):
        stories = [
            {"category": category}
            for category in ("dev", "cloud", "devops", "security", "ai", "news")
        ]
        self.assertEqual(
            generate_post.extract_categories(stories),
            ["AI/ML", "Cloud", "DevOps & SRE", "Security", "Software Engineering"],
        )

    def test_generates_hugo_post_with_stable_route_and_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            ranked = data / "ranked"
            posts = root / "content" / "posts"
            ranked.mkdir(parents=True)
            data.joinpath("synthesis_2026-11-02.md").write_text(
                "HEADLINE: Secure cloud systems are changing\n\n"
                "This is a sufficiently long introduction describing a "
                "verified change for software engineering teams.\n\n"
                "## Security\n\n"
                "### [A verified source story](https://example.com/story)\n\n"
                "Context grounded in the source.\n\n"
                "## Quick Reads\n\n"
                "- **[Another report](https://example.com/other)** — A factual note.\n",
                encoding="utf-8",
            )
            (ranked / "top_2026-11-02.json").write_text(
                json.dumps([{"title": "A verified source story", "summary": "Cloud security"}]),
                encoding="utf-8",
            )
            (ranked / "quick_2026-11-02.json").write_text(
                json.dumps([{"title": "Another report", "summary": "Software"}]),
                encoding="utf-8",
            )
            sources = root / "sources.yaml"
            sources.write_text("sources:\n  - name: Example\n", encoding="utf-8")
            audio = root / "static/podcast/audio/2026-11-02.mp3"
            audio.parent.mkdir(parents=True)
            audio.write_bytes(b"ID3-test-audio")
            with patch.multiple(
                generate_post,
                PROJECT_DIR=root,
                DATA_DIR=data,
                DATA_RANKED_DIR=ranked,
                CONTENT_DIR=posts,
                SOURCES_FILE=sources,
            ):
                output, main_count, quick_count = generate_post.generate_post(
                    "2026-11-02", has_audio=True
                )
            text = output.read_text(encoding="utf-8")

        self.assertEqual(output.name, "2026-11-02-daily.md")
        self.assertEqual((main_count, quick_count), (1, 1))
        self.assertIn('slug: "2026-11-02-daily"', text)
        self.assertIn("/podcast/audio/2026-11-02.mp3", text)
        self.assertRegex(text, r"/podcast/audio/2026-11-02\.mp3\?v=[0-9a-f]{12}")
        self.assertIn("Monday, 2 November 2026", text)
        self.assertIn("comments: true", text)


class WeeklyDateTests(unittest.TestCase):
    def test_formats_weekly_ranges_in_english(self):
        self.assertEqual(
            weekly_summary.format_date_en("2026-11-02"),
            "Monday, November 2",
        )


if __name__ == "__main__":
    unittest.main()
