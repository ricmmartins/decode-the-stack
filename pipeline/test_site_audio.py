import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("hugo"), "Hugo is required for template integration tests")
class SiteAudioTests(unittest.TestCase):
    def test_latest_available_audio_survives_newer_text_and_same_day_weekly_posts(self):
        for date, categories in (
            ("2026-11-03T00:00:00Z", ["Cloud"]),
            ("2026-11-02T23:00:00Z", ["Weekly Briefing"]),
        ):
            with self.subTest(date=date), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copy2(ROOT / "hugo.toml", root / "hugo.toml")
                for name in ("assets", "layouts", "content", "data", "static"):
                    ignore = shutil.ignore_patterns("posts") if name == "content" else None
                    shutil.copytree(ROOT / name, root / name, ignore=ignore)
                (root / "content" / "posts").mkdir()
                (root / "content" / "posts" / "2026-11-02-daily.md").write_text(
                    '---\ntitle: "Daily audio edition"\ndate: 2026-11-02T00:00:00Z\n'
                    'categories: ["Cloud"]\n---\n'
                    '<audio controls><source src="/podcast/audio/2026-11-02.mp3" '
                    'type="audio/mpeg"></audio>\n',
                    encoding="utf-8",
                )
                (root / "content" / "posts" / "newer-text.md").write_text(
                    '---\ntitle: "Newer text-only edition"\n'
                    f'date: {date}\ncategories: {categories!r}\n---\n'
                    "This edition has no separate audio episode.\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    ["hugo", "--minify", "--buildFuture", "--source", str(root)],
                    check=True, capture_output=True, text=True,
                )
                for page in ("index.html", "podcast/index.html"):
                    content = (root / "public" / page).read_text(encoding="utf-8")
                    sources = re.findall(r"<source\b[^>]*\bsrc=[\"']?([^\"'\s>]+)", content)
                    self.assertEqual(sources, ["/podcast/audio/2026-11-02.mp3"])
                home = (root / "public" / "index.html").read_text(encoding="utf-8")
                self.assertIn("Newer text-only edition", home)
                edition = (root / "public" / "posts" / "2026-11-02-daily" / "index.html")
                self.assertIn("<audio", edition.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
