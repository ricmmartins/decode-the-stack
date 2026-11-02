#!/usr/bin/env python3
"""Validate the built English publication, its shared chrome, and public feeds."""

import json
import html
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import yaml
from bs4 import BeautifulSoup


SITE_URL = "https://decodethestack.pages.dev/"
REQUIRED = [
    "index.html",
    "index.xml",
    "search/index.html",
    "search-index.json",
    "posts/index.html",
    "archive/index.html",
    "stats/index.html",
    "privacy/index.html",
    "terms/index.html",
    "categories/index.html",
    "categories/cloud/index.html",
    "categories/ai-ml/index.html",
    "categories/devops-sre/index.html",
    "categories/software-engineering/index.html",
    "categories/security/index.html",
    "about/index.html",
    "podcast/index.html",
    "podcast/feed.xml",
    "manifest.json",
    "sw.js",
    "images/brand-mark.svg",
    "images/podcast-cover.png",
    "podcast/music/bgmusic.mp3",
    "404.html",
]
ATOM_NS = "http://www.w3.org/2005/Atom"
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


def _read(path):
    return path.read_text(encoding="utf-8")


def _validate_shared_layout(root):
    html_files = list(root.rglob("*.html"))
    if not html_files:
        raise ValueError("The Hugo output contains no HTML pages.")
    for path in html_files:
        text = _read(path)
        if re.search(r"<meta\b[^>]*\bhttp-equiv=[\"']?refresh", text, re.I):
            continue
        if not re.search(r"<link\b(?=[^>]*\brel=[\"']?manifest(?:[\"'\s>]|$))", text, re.I):
            raise ValueError(f"The PWA manifest link is missing from {path.relative_to(root)}.")
        if not re.search(
            r"<script\b(?=[^>]*\btype=[\"']?application/ld\+json(?:[\"'\s>]|$))",
            text,
            re.I,
        ):
            raise ValueError(f"JSON-LD metadata is missing from {path.relative_to(root)}.")
        if 'aria-label="More about Decode the Stack"' not in text:
            raise ValueError(f"The shared footer is missing from {path.relative_to(root)}.")


def _validate_home(root):
    home = _read(root / "index.html")
    project_root = Path(__file__).resolve().parent.parent
    sources = yaml.safe_load(
        (project_root / "pipeline" / "sources.yaml").read_text(encoding="utf-8")
    )
    source_count = len(sources.get("sources", [])) if isinstance(sources, dict) else 0
    if source_count < 200:
        raise ValueError(f"The English source catalogue is incomplete: only {source_count} feeds.")
    stats = json.loads(
        (project_root / "data" / "stats.json").read_text(encoding="utf-8")
    )
    if stats.get("configured_feeds") != source_count:
        raise ValueError("The displayed source count does not match pipeline/sources.yaml.")
    if f"{source_count} curated sources" not in home:
        raise ValueError("The home page does not display the full curated source count.")
    for expected in (
        "MANY SOURCES. ONE DIRECTION.",
        "decode --topic tech",
        "Filter the noise. Connect the dots.",
        "Less hype. More engineering.",
        "categories/cloud/",
        "categories/ai-ml/",
        "categories/devops-sre/",
        "categories/software-engineering/",
        "categories/security/",
    ):
        if expected not in home:
            raise ValueError(f"The home page is missing required terminal or category content: {expected}")
    if SITE_URL not in home or not re.search(
        r"<link\b(?=[^>]*\brel=[\"']?canonical(?:[\"'\s>]|$))", home, re.I
    ):
        raise ValueError("The home page is missing its canonical Cloudflare Pages URL.")
    if len(re.findall(r"<source\b[^>]*\bsrc=[\"']?[^\"'\s>]+", home, re.I)) != 1:
        raise ValueError("The home page must include exactly one latest-episode audio source.")
    if "Instagram" in home or "open.spotify.com" in home:
        raise ValueError("Portuguese social or podcast links must not appear on the English home page.")


def _validate_search(root):
    index = json.loads(_read(root / "search-index.json"))
    if not isinstance(index, list):
        raise ValueError("The search index is not a JSON list.")
    if not index:
        raise ValueError("The search index contains no published editions.")
    for item in index:
        if not all(item.get(key) for key in ("title", "url", "date")):
            raise ValueError("A search-index entry is missing its title, URL, or date.")


def _validate_written_feed(root):
    rss = ET.parse(root / "index.xml").getroot()
    channel = rss.find("channel")
    if channel is None or not channel.findall("item"):
        raise ValueError("The written RSS feed has no published editions.")
    atom_link = channel.find(f"{{{ATOM_NS}}}link")
    if atom_link is None or atom_link.get("href") != f"{SITE_URL}index.xml":
        raise ValueError("The written RSS feed has an incorrect self link.")
    for item in channel.findall("item"):
        if not item.findtext("link", "").startswith(SITE_URL):
            raise ValueError("The written RSS feed contains an unbranded edition URL.")


def _validate_podcast_feed(root):
    feed_path = root / "podcast" / "feed.xml"
    feed_text = _read(feed_path)
    if "images/podcast-cover.png" not in feed_text:
        raise ValueError("The podcast feed is missing its show artwork.")
    if "Anna, Maria, and Pedro" not in feed_text or "Alex" in feed_text:
        raise ValueError("The podcast feed must identify the original hosts Anna, Maria, and Pedro.")
    channel = ET.parse(feed_path).getroot().find("channel")
    if channel is None:
        raise ValueError("The podcast RSS feed has no channel.")
    atom_link = channel.find(f"{{{ATOM_NS}}}link")
    if atom_link is None or atom_link.get("href") != f"{SITE_URL}podcast/feed.xml":
        raise ValueError("The podcast RSS feed has an incorrect self link.")
    owner = channel.find(f"{{{ITUNES_NS}}}owner")
    if owner is None:
        raise ValueError("The podcast RSS feed is missing owner metadata.")
    if owner.findtext(f"{{{ITUNES_NS}}}name") != "Ricardo Martins":
        raise ValueError("The podcast RSS feed has the wrong owner name.")
    if not owner.findtext(f"{{{ITUNES_NS}}}email"):
        raise ValueError("The podcast RSS feed is missing its authorized owner email.")

    advertised_audio = set()
    for episode in channel.findall("item"):
        enclosure = episode.find("enclosure")
        if enclosure is None or enclosure.get("type") != "audio/mpeg":
            raise ValueError("A podcast RSS item is missing its MP3 enclosure.")
        url = enclosure.get("url", "")
        if not url.startswith(f"{SITE_URL}podcast/audio/"):
            raise ValueError(f"The podcast feed contains an unbranded enclosure URL: {url}")
        local_path = root / urlparse(url).path.lstrip("/")
        if not local_path.is_file() or local_path.stat().st_size <= 1024:
            raise ValueError(f"Podcast enclosure has no published MP3: {url}")
        if int(enclosure.get("length", "0")) != local_path.stat().st_size:
            raise ValueError(f"Podcast enclosure length does not match the MP3: {url}")
        with local_path.open("rb") as audio_file:
            header = audio_file.read(3)
        if not header.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
            raise ValueError(f"Podcast enclosure is not an MP3 stream: {url}")
        guid = episode.findtext("guid", "")
        if guid != url:
            raise ValueError(f"Podcast episode GUID is not stable with its enclosure URL: {url}")
        advertised_audio.add(local_path.resolve())

    actual_audio = {
        path.resolve()
        for path in (root / "podcast" / "audio").glob("*.mp3")
        if path.stat().st_size > 1024
    } if (root / "podcast" / "audio").exists() else set()
    if actual_audio != advertised_audio:
        raise ValueError("The podcast RSS episodes do not match the published date-based MP3 files.")


def _validate_podcast_page(root):
    podcast = _read(root / "podcast" / "index.html")
    sources = re.findall(r"<source\b[^>]*\bsrc=[\"']?([^\"'\s>]+)", podcast, re.I)
    if len(sources) != len(set(sources)):
        raise ValueError("The podcast page repeats an episode audio player.")

def _validate_published_values(root):
    """Compare rendered counts and listings against actual published content."""
    project = Path(__file__).resolve().parent.parent
    category_slugs = {
        "Cloud": "cloud", "AI/ML": "ai-ml", "DevOps & SRE": "devops-sre",
        "Software Engineering": "software-engineering", "Security": "security",
    }
    counts = dict.fromkeys(category_slugs.values(), 0)
    search = {item["url"]: item for item in json.loads(_read(root / "search-index.json"))}
    archive = BeautifulSoup(_read(root / "archive/index.html"), "html.parser")
    headline_total = 0
    for path in (project / "content/posts").glob("*.md"):
        text = _read(path)
        metadata = yaml.safe_load(text.split("---", 2)[1])
        url = f"/posts/{metadata.get('slug', path.stem)}/"
        if metadata.get("draft"):
            continue
        if url not in search:
            raise ValueError(f"The search index omits published edition {url}.")
        item = search[url]
        if item["title"] != metadata["title"] or not item.get("content"):
            raise ValueError(f"The search index has stale title/content for {url}.")
        first_story = re.search(r"(?m)^### \[(.*?)\]", text)
        indexed_content = html.unescape(item["content"]).replace("\u2019", "'")
        if first_story and first_story.group(1).replace("\u2019", "'") not in indexed_content:
            raise ValueError(f"The search index omits the published story content for {url}.")
        for category in metadata.get("categories", []):
            if category not in category_slugs:
                continue
            slug = category_slugs[category]
            counts[slug] += 1
            term = BeautifulSoup(_read(root / f"categories/{slug}/index.html"), "html.parser")
            if not term.select_one(f'main a[href="{url}"]'):
                raise ValueError(f"The {category} category omits published edition {url}.")
        if path.name.endswith("-daily.md"):
            headline_total += int(metadata.get("mainCount", 0)) + int(metadata.get("quickCount", 0))
    for page in ("index.html", "categories/index.html"):
        soup = BeautifulSoup(_read(root / page), "html.parser")
        for slug, count in counts.items():
            card = soup.select_one(f'a.topic-card[href="/categories/{slug}/"] .topic-count')
            if card is None or int(card.get_text().split()[0]) != count:
                raise ValueError(f"The {slug} topic count on {page} must be {count}.")
    latest = max(search.values(), key=lambda item: item["date"], default=None)
    if latest and not archive.select_one(f'main a[href="{latest["url"]}"]'):
        raise ValueError("The archive does not list the latest published edition.")
    stats = json.loads(_read(project / "data/stats.json"))
    if stats.get("headlines_published") != headline_total:
        raise ValueError("Publication statistics count ranked candidates instead of published stories.")
    rendered = BeautifulSoup(_read(root / "stats/index.html"), "html.parser")
    values = {"published-stories": headline_total}
    pipeline_path = project / "static/data/pipeline_stats.json"
    if pipeline_path.is_file():
        pipeline = json.loads(_read(pipeline_path))
        values.update({
            "articles-ingested": pipeline["articles_ingested"],
            "clusters-formed": pipeline["clusters_formed"],
            "main-stories": pipeline["main_stories"],
            "quick-reads": pipeline["radar_items"],
        })
    for field, expected in values.items():
        element = rendered.select_one(f'[data-stat="{field}"]')
        if element is None or int(element.get_text()) != expected:
            raise ValueError(f"The statistics page must display {field}={expected}.")


def validate(root):
    from humanizer import validate_posts
    from editorial_punctuation import visible_html_dashes
    validate_posts()
    missing = [path for path in REQUIRED if not (root / path).is_file()]
    if missing:
        raise ValueError("Missing required site output: " + ", ".join(missing))

    for path in REQUIRED:
        if (root / path).stat().st_size == 0:
            raise ValueError(f"Required site output is empty: {path}")

    _validate_shared_layout(root)
    _validate_home(root)
    _validate_search(root)
    _validate_written_feed(root)
    _validate_podcast_feed(root)
    _validate_podcast_page(root)
    _validate_published_values(root)

    about = _read(root / "about" / "index.html")
    if "Table of contents" not in about or "How it works" not in about:
        raise ValueError("The About page is missing its table of contents or editorial pipeline explanation.")
    categories = html.unescape(_read(root / "categories" / "index.html"))
    for category in ("Cloud", "AI/ML", "DevOps & SRE", "Software Engineering", "Security"):
        if category not in categories:
            raise ValueError(f"The categories page is missing {category}.")

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".html", ".xml", ".txt", ".json", ".js", ".css"
        }:
            continue
        text = _read(path)
        if path.suffix.lower() == ".html" and visible_html_dashes(text):
            raise ValueError(f"Prohibited visible editorial dash in {path.relative_to(root)}.")
        if "ricardomartins.com.br" in text or "ricmmartins.github.io" in text:
            raise ValueError(f"A personal-domain or GitHub Pages URL leaked into {path.relative_to(root)}.")
        if "open.spotify.com/show/0775yERUMPLZiKpocJyBqm" in text:
            raise ValueError(f"The Portuguese Spotify show URL leaked into {path.relative_to(root)}.")

    print(f"Validated {len(REQUIRED)} required outputs, shared layout, search, categories, and both RSS feeds.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_site.py <built-site-directory>")
    try:
        validate(Path(sys.argv[1]))
    except (OSError, ValueError, ET.ParseError, json.JSONDecodeError) as error:
        raise SystemExit(f"Site validation failed: {error}") from error
