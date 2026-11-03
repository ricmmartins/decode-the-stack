import re
import json
import hashlib
import shutil
import subprocess
import tempfile
import os
import signal
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from humanizer import SKILL_SHA256, digest as post_digest


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("hugo"), "Hugo is required for template integration tests")
class SiteAudioTests(unittest.TestCase):
    def test_development_build_does_not_load_google_analytics(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                ["hugo", "--source", str(ROOT), "--environment", "development",
                 "--destination", directory],
                check=True, capture_output=True, text=True, timeout=90,
            )
            for page in Path(directory).rglob("*.html"):
                text = page.read_text(encoding="utf-8")
                self.assertNotIn("googletagmanager.com/gtag/js", text)
                self.assertNotIn("gtag('config'", text)

    def test_latest_available_audio_survives_newer_text_and_same_day_weekly_posts(self):
        for date, categories in (
            ("2026-11-03T00:00:00Z", ["Cloud"]),
            ("2026-11-02T23:00:00Z", ["Weekly Briefing"]),
        ):
            with self.subTest(date=date), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copy2(ROOT / "hugo.toml", root / "hugo.toml")
                (root / "pipeline").mkdir()
                shutil.copy2(ROOT / "pipeline/sources.yaml", root / "pipeline/sources.yaml")
                for name in ("assets", "layouts", "content", "data", "static", ".github"):
                    ignore = shutil.ignore_patterns("posts") if name == "content" else None
                    shutil.copytree(ROOT / name, root / name, ignore=ignore)
                (root / "content" / "posts").mkdir()
                (root / "content" / "posts" / "2026-11-02-daily.md").write_text(
                    '---\ntitle: "Daily audio edition"\ndate: 2026-11-02T00:00:00Z\n'
                    'categories: ["Cloud", "AI/ML", "DevOps & SRE", "Software Engineering", "Security"]\n---\n'
                    '<audio controls><source src="/podcast/audio/2026-11-02.mp3?v=000000000000" '
                    'type="audio/mpeg"></audio>\nVerified story context.\n',
                    encoding="utf-8",
                )
                (root / "content" / "posts" / "newer-text.md").write_text(
                    '---\ntitle: "Newer text-only edition"\n'
                    f'date: {date}\ncategories: {categories!r}\n---\n'
                    "This edition has no separate audio episode.\n",
                    encoding="utf-8",
                )
                receipts = root / "data/humanizer"
                receipts.mkdir(exist_ok=True)
                for post in (root / "content/posts").glob("*.md"):
                    hashed = post_digest(post.read_text(encoding="utf-8"))
                    (receipts / f"{post.stem}.json").write_text(json.dumps({
                        "version": 1, "post_sha256": hashed, "input_sha256": hashed,
                        "skill_sha256": SKILL_SHA256, "meaning_verified": True,
                    }), encoding="utf-8")
                subprocess.run(
                    ["hugo", "--minify", "--buildFuture", "--source", str(root)],
                    check=True, capture_output=True, text=True, timeout=90,
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
                    "https://decodethestack.com/podcast/feed.xml",
                )
                rows = podcast_page.select("main table tbody tr")
                self.assertEqual(len(rows), 3)
                styles = "\n".join(
                    (root / "public" / link["href"].lstrip("/")).read_text(encoding="utf-8")
                    for link in podcast_page.select('link[rel="stylesheet"]')
                )
                compact_styles = re.sub(r"\s+", "", styles)
                editions = BeautifulSoup(
                    (root / "public/posts/index.html").read_text(encoding="utf-8"), "html.parser",
                )
                self.assertEqual(len(editions.select("main .editions-list > .post-entry")), 2)
                self.assertIsNone(editions.select_one("main .editions-grid"))
                self.assertIn(
                    ".editions-list{display:flex;flex-direction:column;gap:18px}",
                    compact_styles,
                )
                self.assertIn(
                    ".editions-list.post-entry{margin:0;padding:20px;min-width:0;overflow-wrap:anywhere}",
                    compact_styles,
                )
                self.assertIn(
                    ".editions-list.entry-headerh2{font-size:22px;line-height:1.3}",
                    compact_styles,
                )
                self.assertIn(
                    ".post-contentpre{margin:20px0;padding:10px;overflow-x:auto;background:var(--code-block-bg);border-radius:6px}",
                    compact_styles,
                )
                self.assertIn(
                    ".post-contentprecode{display:block;padding:0;color:#e5e5e5;background:00;font:14px/1.5var(--mono);white-space:pre}",
                    compact_styles,
                )
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
                spotify = podcast_page.select_one('a[href="https://open.spotify.com/show/0wAKdLX0HpJF1qfAj2Yiea"]')
                self.assertIsNotNone(spotify)
                self.assertEqual(spotify.get_text(strip=True), "Listen to Decode the Stack")
                self.assertEqual(len(podcast_page.select('a[href*="open.spotify.com/show/"]')), 1)
                for unwanted in ("Instagram", "4qDnpZwEzYOzPPgDXezMxu", "0775yERUMPLZiKpocJyBqm",
                                 "Azure", "7–12", "directory", "Published episodes"):
                    self.assertNotIn(unwanted, main_text)
                self.assertIn("Approximately 15 minutes", main_text)
                self.assertIn("Edge TTS available as an explicit rollback", main_text)
                self.assertIn("Alba MacKenna", main_text)
                self.assertIn("speaker p228", main_text)
                self.assertIn("speaker p229", main_text)
                self.assertIsNotNone(podcast_page.select_one('a[href="https://creativecommons.org/licenses/by/4.0/"]'))
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
                               "07:00 EST", "08:00 EDT", "07:45 EST", "08:45 EDT",
                               "20", "10", "15 minutes",
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
                self.assertIsNotNone(about.select_one('a[href="mailto:podcast@decodethestack.com"]'))
                self.assertEqual(
                    about.select_one("main .post-content > p:last-child em").get_text(),
                    "Decode the Stack: Decoding the tech that matters.",
                )
                home = (root / "public" / "index.html").read_text(encoding="utf-8")
                self.assertIn("Newer text-only edition", home)
                home_soup = BeautifulSoup(home, "html.parser")
                spotify_cta = home_soup.select_one(
                    '.podcast-links a[href="https://open.spotify.com/show/0wAKdLX0HpJF1qfAj2Yiea"]'
                )
                self.assertIsNotNone(spotify_cta)
                self.assertIn("Listen on Spotify", spotify_cta.get_text())
                self.assertEqual(spotify_cta["target"], "_blank")
                self.assertTrue({"noopener", "noreferrer"}.issubset(spotify_cta["rel"]))
                external_icon = spotify_cta.select_one('svg.brand-icon[aria-hidden="true"]')
                self.assertEqual(external_icon.select_one("path")["d"], "M7 17 17 7M7 7h10v10")
                self.assertEqual(external_icon["stroke-width"], "1.6")
                self.assertIn("opens in a new tab", spotify_cta["aria-label"])
                self.assertIsNotNone(home_soup.select_one('.community-actions a[href="/podcast/feed.xml"]'))
                self.assertNotIn("Subscribe to podcast RSS", home)
                catalogue = "https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml"
                for selector in (".hero-description", ".signal-strip"):
                    link = home_soup.select_one(f'{selector} a[href="{catalogue}"]')
                    self.assertIsNotNone(link)
                    self.assertEqual(link.get_text(" ", strip=True), "242 curated sources")
                self.assertEqual(
                    [link.get_text(" ", strip=True) for link in about.select(
                        f'.post-content a[href="{catalogue}"]'
                    )],
                    ["242 feeds", "242 RSS feeds", "242 international feeds",
                     "242 international technology feeds", "pipeline/sources.yaml"],
                )
                self.assertNotIn("<a", about.select_one('meta[name="description"]')["content"])
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
                self.assertEqual(
                    BeautifulSoup(edition.read_text(encoding="utf-8"), "html.parser").select_one("audio source")["src"],
                    f"/podcast/audio/2026-11-02.mp3?v={digest}",
                )
                for built_page in (root / "public").rglob("*"):
                    if built_page.suffix in (".html", ".js", ".css"):
                        self.assertNotIn("giscus", built_page.read_text(encoding="utf-8").lower())
                    if built_page.suffix == ".html":
                        page = BeautifulSoup(built_page.read_text(encoding="utf-8"), "html.parser")
                        if page.select_one('meta[http-equiv="refresh"]'):
                            continue
                        analytics = page.select('script[src="https://www.googletagmanager.com/gtag/js?id=G-VS7SSSLN7H"]')
                        self.assertEqual(len(analytics), 1, str(built_page))
                        self.assertTrue(analytics[0].has_attr("async"))
                        self.assertEqual(len([
                            script for script in page.select("script:not([src])")
                            if "G-VS7SSSLN7H" in script.get_text()
                        ]), 1)
                for generator in ("generate_post.py", "weekly_summary.py"):
                    self.assertNotIn("comments:", (ROOT / "pipeline" / generator).read_text(encoding="utf-8"))
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
                for row, entry in zip(statistics.select(".trend-row"), data["history"]):
                    unit = "story" if entry["headlines"] == 1 else "stories"
                    self.assertEqual(row.select_one("strong").get_text(), f'{entry["headlines"]} {unit}')
                publishers = statistics.select_one('[aria-labelledby="publishers-title"]')
                tables = publishers.select("table")
                actual_publishers = [
                    (row.select_one("td").get_text(), int(row.select("td")[1].get_text()))
                    for table in tables for row in table.select("tbody tr")
                ]
                self.assertEqual(actual_publishers, [(entry["name"], entry["headlines"]) for entry in data["source_counts"]])
                self.assertEqual(len(tables[0].select("tbody tr")), min(10, len(data["source_counts"])))
                if len(data["source_counts"]) > 10:
                    details = publishers.select_one("details")
                    self.assertFalse(details.has_attr("open"))
                    self.assertIn(f'{len(data["source_counts"]) - 10} more publishers', details.select_one("summary").get_text())
                self.assertEqual(int(statistics.select_one('[data-stat="published-stories"]').get_text()), data["headlines_published"])
                self.assertEqual(statistics.select_one('[data-stat="configured-feeds"]').get_text(), "242")
                pipeline = json.loads((root / "static/data/pipeline_stats.json").read_text(encoding="utf-8"))
                for field, key in (
                    ("articles-ingested", "articles_ingested"), ("clusters-formed", "clusters_formed"),
                    ("main-stories", "main_stories"), ("quick-reads", "radar_items"),
                ):
                    self.assertEqual(int(statistics.select_one(f'[data-stat="{field}"]').get_text()), pipeline[key])

                history = {
                    path: path.read_bytes()
                    for folder in ("content/posts", "data")
                    for path in (root / folder).rglob("*") if path.is_file()
                }
                audio_path = root / "static/podcast/audio/2026-11-02.mp3"
                audio_path.write_bytes(audio_path.read_bytes() + b"cache-version-regression")
                updated_digest = hashlib.sha256(audio_path.read_bytes()).hexdigest()[:12]
                self.assertNotEqual(updated_digest, digest)
                catalogue_path = root / "pipeline/sources.yaml"
                original_catalogue = catalogue_path.read_text(encoding="utf-8")
                catalogue_path.write_text(
                    original_catalogue + '\n  - name: Build test feed\n'
                    '    url: https://example.com/feed.xml\n    category: dev\n    tier: 2\n',
                    encoding="utf-8",
                )
                subprocess.run(
                    ["hugo", "--minify", "--buildFuture", "--source", str(root)],
                    check=True, capture_output=True, text=True, timeout=90,
                )
                for rebuilt in (root / "public/index.html", edition):
                    self.assertEqual(
                        BeautifulSoup(rebuilt.read_text(encoding="utf-8"), "html.parser").select_one("audio source")["src"],
                        f"/podcast/audio/2026-11-02.mp3?v={updated_digest}",
                    )
                for route, expected in (
                    ("index.html", "243 curated sources"),
                    ("about/index.html", "243 international technology feeds"),
                    ("stats/index.html", "243"),
                ):
                    updated = BeautifulSoup((root / "public" / route).read_text(encoding="utf-8"), "html.parser")
                    if route.startswith("stats"):
                        self.assertEqual(updated.select_one('[data-stat="configured-feeds"]').get_text(), expected)
                    else:
                        self.assertIn(expected, updated.select_one("main").get_text(" ", strip=True))
                    if route.startswith("about"):
                        self.assertIn("Engineering (173 feeds)", updated.get_text(" ", strip=True))
                        description = updated.select_one('meta[name="description"]')["content"]
                        self.assertNotRegex(description, r"\b24[23]\b")
                        for schema in updated.select('script[type="application/ld+json"]'):
                            self.assertNotRegex(json.loads(schema.string)["description"], r"\b24[23]\b")
                for path, content in history.items():
                    self.assertEqual(path.read_bytes(), content, path)
                for invalid in ("sources: []", "sources: invalid", "sources: ["):
                    with self.subTest(catalogue=invalid):
                        catalogue_path.write_text(invalid, encoding="utf-8")
                        with subprocess.Popen(
                            ["hugo", "--source", str(root)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                        ) as process:
                            try:
                                stdout, stderr = process.communicate(timeout=60)
                            except subprocess.TimeoutExpired:
                                if os.name != "nt":
                                    process.send_signal(signal.SIGQUIT)
                                else:
                                    process.kill()
                                try:
                                    stdout, stderr = process.communicate(timeout=5)
                                except subprocess.TimeoutExpired:
                                    process.kill()
                                    stdout, stderr = process.communicate()
                                self.fail(
                                    f"Hugo timed out for {invalid!r}; stdout={stdout}; stderr={stderr}"
                                )
                            self.assertNotEqual(process.returncode, 0, invalid)
                catalogue_path.unlink()
                result = subprocess.run(["hugo", "--source", str(root)], capture_output=True, text=True, timeout=60)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
