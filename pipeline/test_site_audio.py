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
                    'categories: ["Cloud", "AI/ML", "DevOps & SRE", "Software Engineering", "Security"]\ncomments: true\n---\n'
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
                for page in ("index.html",):
                    content = (root / "public" / page).read_text(encoding="utf-8")
                    sources = re.findall(r"<source\b[^>]*\bsrc=[\"']?([^\"'\s>]+)", content)
                    digest = hashlib.sha256(
                        (root / "static/podcast/audio/2026-11-02.mp3").read_bytes()
                    ).hexdigest()[:12]
                    self.assertEqual(sources, [f"/podcast/audio/2026-11-02.mp3?v={digest}"])
                podcast_page = BeautifulSoup(
                    (root / "public/podcast/index.html").read_text(encoding="utf-8"), "html.parser",
                )
                self.assertEqual(
                    [heading.get_text(strip=True) for heading in podcast_page.select("main h3")],
                    ["Where to listen", "The hosts", "About", "RSS feed"],
                )
                self.assertIsNone(podcast_page.select_one("main audio, .podcast-show, .episode-card, .toc"))
                self.assertEqual(
                    podcast_page.select_one("main pre code").get_text().strip(),
                    "https://decodethestack.pages.dev/podcast/feed.xml",
                )
                rows = podcast_page.select("main table tbody tr")
                self.assertEqual(len(rows), 3)
                styles = "\n".join(
                    (root / "public" / link["href"].lstrip("/")).read_text(encoding="utf-8")
                    for link in podcast_page.select('link[rel="stylesheet"]')
                )
                compact_styles = re.sub(r"\s+", "", styles)
                self.assertIn(
                    ".post-contenttable:not(.highlighttable){display:block;width:100%;overflow-x:auto;border-collapse:collapse;font-size:inherit;margin-bottom:24px}",
                    compact_styles,
                )
                self.assertIn(
                    ".post-contenttable:not(.highlighttable)th,.post-contenttable:not(.highlighttable)td{min-width:80px;padding:6px13px;border:1pxsolidvar(--border);text-align:start;line-height:1.5}",
                    compact_styles,
                )
                for row, name, trait in zip(rows, ("Anna", "Maria", "Pedro"), ("charisma", "historical context", "creative analogies")):
                    self.assertIn(name, row.get_text())
                    self.assertIn(trait, row.get_text())
                main_text = podcast_page.select_one("main").get_text()
                self.assertNotIn("🎙", podcast_page.get_text())
                self.assertIn("🧠", main_text)
                self.assertIn("😄", main_text)
                for unwanted in ("Instagram", "Spotify", "Azure", "7–12", "directory", "Published episodes"):
                    self.assertNotIn(unwanted, main_text)
                self.assertIn("Approximately 15 minutes", main_text)
                self.assertIn("Edge TTS fallback", main_text)
                about = BeautifulSoup(
                    (root / "public/about/index.html").read_text(encoding="utf-8"), "html.parser",
                )
                self.assertEqual(
                    [heading.get_text(strip=True) for heading in about.select("main h2")],
                    ["What is Decode the Stack?", "How it works", "Who is it for?", "Why?",
                     "Technology stack", "Sources", "Daily post format", "Site features", "Contact"],
                )
                self.assertIsNotNone(about.select_one(".toc"))
                about_text = about.select_one("main .post-content").get_text(" ", strip=True)
                for phrase in ("242 international technology feeds", "Engineering (172 feeds)",
                               "09:00", "09:45", "20", "10", "15 minutes",
                               "en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural",
                               "custom JavaScript", "reduces the noise", "30+ minutes"):
                    self.assertIn(phrase, about_text)
                groups = about.select_one("#sources").find_next_sibling("ul").select("li")
                self.assertEqual(len(groups), 6)
                for group, examples in zip(groups, (
                    ("Netflix", "Guido van Rossum", "Evil Martians"),
                    ("AWS", "Azure", "Fastly"), ("Kubernetes", "Charity Majors", "Pulumi"),
                    ("Krebs", "PortSwigger", "Filippo Valsorda"),
                    ("OpenAI", "Lilian Weng", "Simon Willison"),
                    ("Hacker News", "Wired", "TLDR"),
                )):
                    for example in examples:
                        self.assertIn(example, group.get_text())
                for unwanted in ("Instagram", "FLUX", "290", "200+", "Fuse.js", "DragonHD",
                                 "Google Analytics", "AdSense", "$0.20", "0775yERUMPLZiKpocJyBqm",
                                 "Podcast hosts", "AI and editorial safeguards"):
                    self.assertNotIn(unwanted, about_text)
                self.assertIsNotNone(about.select_one('a[href="mailto:rmmartins@outlook.com"]'))
                self.assertEqual(
                    about.select_one("main .post-content > p:last-child em").get_text(),
                    "Decode the Stack — Decoding the tech that matters.",
                )
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
                self.assertEqual(
                    home_soup.select_one(".terminal-code p").get_text(" ", strip=True),
                    "$ decode --topic tech",
                )
                for selector in (".hero-actions .button-secondary", ".podcast-card .eyebrow"):
                    element = home_soup.select_one(selector)
                    icon = element.select_one("svg.brand-icon")
                    self.assertIsNotNone(icon)
                    self.assertEqual(icon["aria-hidden"], "true")
                    self.assertEqual(len(icon.select("rect")), 2)
                edition = (root / "public" / "posts" / "2026-11-02-daily" / "index.html")
                self.assertIn("<audio", edition.read_text(encoding="utf-8"))
                edition_soup = BeautifulSoup(edition.read_text(encoding="utf-8"), "html.parser")
                widget = edition_soup.select_one('script[src="https://giscus.app/client.js"]')
                self.assertIsNotNone(widget)
                self.assertEqual(widget["data-repo"], "ricmmartins/decode-the-stack")
                self.assertEqual(widget["data-repo-id"], "R_kgDOVfkfHw")
                self.assertEqual(widget["data-category-id"], "DIC_kwDOVfkfH84DKLrd")
                self.assertEqual(widget["data-mapping"], "pathname")
                self.assertEqual(widget["data-lang"], "en")
                self.assertIsNone(podcast_page.select_one('script[src="https://giscus.app/client.js"]'))
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
                trends = json.loads((root / "static/data/trends.json").read_text(encoding="utf-8"))
                totals = {
                    tag: sum(day["tags"].get(tag, 0) for day in trends["days"])
                    for tag in trends["top_tags"]
                }
                rows = statistics.select(".tag-bar-row")
                self.assertEqual([row["data-tag"] for row in rows], trends["top_tags"])
                self.assertEqual(
                    [int(row.select_one(".tag-bar-value").get_text()) for row in rows],
                    list(totals.values()),
                )
                maximum = max(totals.values())
                for row in rows:
                    percentage = max(2, int(totals[row["data-tag"]] / maximum * 100 + 0.5))
                    self.assertIn(f"width:{percentage}%", row.select_one(".tag-bar-fill")["style"].replace(" ", ""))
                self.assertEqual(statistics.select_one("#frequent-tags-title").get_text(), "Most frequent tags")
                self.assertNotIn("🔥", statistics.get_text())
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
