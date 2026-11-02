#!/usr/bin/env python3
"""Validate the built English publication, its shared chrome, and public feeds."""

import json
import html
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


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
    for expected in (
        "MANY SOURCES. ONE DIRECTION.",
        "decode --topic tech --language en",
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


def validate(root):
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

    about = _read(root / "about" / "index.html")
    if "Table of contents" not in about or "How an edition is made" not in about:
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
