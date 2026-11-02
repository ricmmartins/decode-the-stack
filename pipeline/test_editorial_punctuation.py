import re
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

import humanizer
from editorial_punctuation import (
    has_editorial_dashes, normalize_editorial_dashes, visible_html_dashes,
)
from test_humanizer import POST, successful_editor


ROOT = Path(__file__).resolve().parent.parent


class EditorialPunctuationTests(unittest.TestCase):
    def test_contextual_normalization_preserves_code_urls_and_heading_structure(self):
        source = (
            '---\ntitle: "Daily \u2014 briefing"\n---\n'
            '### [Report \u2014 details](https://example.com/a\u2014b)\n\n'
            'Read 7\u201312 reports \u2014 today &mdash; tomorrow.\n'
            '`tool --flag a\u2014b` and https://example.com/a\u2014b\n\n'
            '```sh\ntool \u2014 argument\n```\n'
            '<audio src="/a\u2014b.mp3"></audio>\n'
            '<code>option \u2014 literal</code>\n'
        )
        output = normalize_editorial_dashes(source)
        self.assertIn('title: "Daily: briefing"', output)
        self.assertIn('### [Report: details](https://example.com/a\u2014b)', output)
        self.assertIn('Read 7 to 12 reports: today: tomorrow.', output)
        for protected in ('`tool --flag a\u2014b`', '```sh\ntool \u2014 argument\n```',
                          '<audio src="/a\u2014b.mp3">', '<code>option \u2014 literal</code>'):
            self.assertIn(protected, output)
        self.assertFalse(has_editorial_dashes(output))

    def test_final_review_rejects_reintroduced_dash(self):
        def editor(system, user, label):
            if label == "Humanizer editorial review":
                return user.replace("Acme released", "Acme released \u2014")
            return successful_editor(system, user, label)
        with patch.object(humanizer, "_call_llm", side_effect=editor):
            with self.assertRaisesRegex(humanizer.HumanizerError, "editorial dash"):
                humanizer.review_post(POST)

    def test_heading_link_label_dash_is_normalized_before_protected_review(self):
        source = POST.replace("Original title", "Original \u2014 title")
        with patch.object(humanizer, "_call_llm", side_effect=successful_editor):
            output, receipt = humanizer.review_post(source)
        self.assertIn("### [Original: title](https://example.com/report)", output)
        self.assertEqual(receipt["input_sha256"], humanizer.digest(source))
        self.assertFalse(has_editorial_dashes(output))

    def test_rendered_gate_checks_prose_and_titles_but_not_code_or_attributes(self):
        self.assertTrue(visible_html_dashes("<title>A &mdash; B</title>"))
        self.assertTrue(visible_html_dashes("<h3>A \u2013 B</h3>"))
        self.assertFalse(visible_html_dashes(
            '<a href="/a\u2014b">Report</a><code>x \u2014 y</code><pre>x \u2013 y</pre>'
        ))

    def test_fixed_pages_and_legacy_source_are_dash_free(self):
        for path in (ROOT / "content").rglob("*.md"):
            self.assertFalse(has_editorial_dashes(path.read_text(encoding="utf-8")), path)

    def test_historical_migration_preserves_streams_or_replacement_has_full_review(self):
        current = (ROOT / "content/posts/2026-11-02-daily.md").read_text(encoding="utf-8")
        if humanizer.digest(current) != humanizer.LEGACY_POSTS["2026-11-02-daily.md"]:
            self.assertTrue((ROOT / "data/humanizer/2026-11-02-daily.json").is_file())
            humanizer.validate_posts(ROOT)
            return
        # Original e858677 word/URL streams, independent of shallow CI history.
        words = re.findall(r"\w+", current)
        urls = re.findall(r"https?://[^\s<>\"')]+", current)
        hashed = lambda values: hashlib.sha256("\n".join(values).encode()).hexdigest()
        self.assertEqual(hashed(words), "470f974c284e9913075cfb94efb0fcaec7031b6a0d26c941f2708998a3125cfa")
        self.assertEqual(hashed(urls), "8ca1e929620f1d30254c98e90712b6ebf6a3a72d060a0a7a5c1833c308594e89")
