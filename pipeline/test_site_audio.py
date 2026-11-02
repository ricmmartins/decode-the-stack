import re
import json
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup


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
                    'categories: ["Cloud", "AI/ML", "DevOps & SRE", "Software Engineering", "Security"]\n---\n'
                    '<audio controls><source src="/podcast/audio/2026-11-02.mp3" '
                    'type="audio/mpeg"></audio>\nVerified story context.\n',
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
                    digest = hashlib.sha256(
                        (root / "static/podcast/audio/2026-11-02.mp3").read_bytes()
                    ).hexdigest()[:12]
                    self.assertEqual(sources, [f"/podcast/audio/2026-11-02.mp3?v={digest}"])
                home = (root / "public" / "index.html").read_text(encoding="utf-8")
                self.assertIn("Newer text-only edition", home)
                home_soup = BeautifulSoup(home, "html.parser")
                self.assertEqual(
                    home_soup.select_one(".hero .eyebrow").get_text(strip=True),
                    "Your daily technology briefing",
                )
                self.assertNotIn("English", home_soup.select_one(".signal-strip").get_text())
                self.assertEqual(
                    home_soup.select_one(".footer-brand p").get_text(strip=True),
                    "Many sources. One direction.",
                )
                self.assertEqual(home_soup.html["lang"], "en")
                edition = (root / "public" / "posts" / "2026-11-02-daily" / "index.html")
                self.assertIn("<audio", edition.read_text(encoding="utf-8"))
                for page in ("index.html", "categories/index.html"):
                    soup = BeautifulSoup((root / "public" / page).read_text(encoding="utf-8"), "html.parser")
                    cards = {
                        card["href"]: int(card.select_one(".topic-count").get_text().split()[0])
                        for card in soup.select("a.topic-card")
                    }
                    self.assertEqual(cards, {
                        "/categories/cloud/": 2 if categories == ["Cloud"] else 1,
                        "/categories/ai-ml/": 1, "/categories/devops-sre/": 1,
                        "/categories/software-engineering/": 1, "/categories/security/": 1,
                    })
                for category in ("cloud", "ai-ml", "devops-sre", "software-engineering", "security"):
                    page = root / "public" / "categories" / category / "index.html"
                    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
                    self.assertIsNotNone(soup.select_one('main a[href="/posts/2026-11-02-daily/"]'))
                archive = BeautifulSoup((root / "public/archive/index.html").read_text(encoding="utf-8"), "html.parser")
                self.assertIsNotNone(archive.select_one('main a[href="/posts/2026-11-02-daily/"]'))
                index = json.loads((root / "public/search-index.json").read_text(encoding="utf-8"))
                entry = next(item for item in index if item["title"] == "Daily audio edition")
                self.assertEqual(entry["url"], "/posts/2026-11-02-daily/")
                self.assertIn("Verified story context.", entry["content"])
                statistics = BeautifulSoup((root / "public/stats/index.html").read_text(encoding="utf-8"), "html.parser")
                data = json.loads((root / "data/stats.json").read_text(encoding="utf-8"))
                self.assertEqual(int(statistics.select_one('[data-stat="published-stories"]').get_text()), data["headlines_published"])
                pipeline = json.loads((root / "static/data/pipeline_stats.json").read_text(encoding="utf-8"))
                for field, key in (
                    ("articles-ingested", "articles_ingested"), ("clusters-formed", "clusters_formed"),
                    ("main-stories", "main_stories"), ("quick-reads", "radar_items"),
                ):
                    self.assertEqual(int(statistics.select_one(f'[data-stat="{field}"]').get_text()), pipeline[key])


if __name__ == "__main__":
    unittest.main()
