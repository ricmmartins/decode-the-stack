#!/usr/bin/env python3
"""Fail the deployment if essential pages, assets, or feeds are missing."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse


def validate(root: Path) -> None:
    site_url = "https://decodethestack.pages.dev/"
    required = [
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
        "about/index.html",
        "podcast/index.html",
        "podcast/feed.xml",
        "images/brand-mark.svg",
        "images/podcast-cover.png",
        "404.html",
    ]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        raise SystemExit("Missing required site output: " + ", ".join(missing))

    home = (root / "index.html").read_text(encoding="utf-8")
    if site_url not in home:
        raise SystemExit("The canonical site URL is missing from the home page.")
    if "Decodifica.Tech" in home or "decodifica.tech" in home:
        raise SystemExit("Portuguese site branding leaked into the English site.")
    if "Latest edition" not in home or "first edition is being assembled" in home:
        raise SystemExit("The home page does not display the published edition.")
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".xml", ".txt", ".json", ".js", ".css"}:
            text = path.read_text(encoding="utf-8")
            if "ricardomartins.com.br" in text or "ricmmartins.github.io" in text:
                raise SystemExit(f"Personal-domain or GitHub Pages URL leaked into {path.relative_to(root)}.")

    written_feed = ET.parse(root / "index.xml").getroot()
    written_channel = written_feed.find("channel")
    if written_channel is None or not written_channel.findall("item"):
        raise SystemExit("The written RSS feed has no published editions.")

    podcast_feed = (root / "podcast/feed.xml").read_text(encoding="utf-8")
    if "images/podcast-cover.png" not in podcast_feed:
        raise SystemExit("The podcast feed is missing its show artwork.")
    feed_root = ET.parse(root / "podcast/feed.xml").getroot()
    channel = feed_root.find("channel")
    if channel is None:
        raise SystemExit("The podcast RSS feed has no channel.")
    owner = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}owner")
    if owner is None or not owner.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}email"):
        raise SystemExit("The podcast RSS feed is missing its authorized owner email.")
    owner_name = owner.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}name")
    if owner_name != "Ricardo Martins":
        raise SystemExit("The podcast RSS feed has the wrong owner name.")
    urls = [
        channel.findtext("link", ""),
        channel.find("{http://www.w3.org/2005/Atom}link").get("href", ""),
        channel.find("image/url").text or "",
        channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image").get("href", ""),
    ]
    episodes = channel.findall("item")
    audio_files = list((root / "podcast" / "audio").glob("*.mp3")) if (root / "podcast" / "audio").exists() else []
    if audio_files and not episodes:
        raise SystemExit("Published podcast audio is missing from the RSS feed.")
    if not episodes:
        raise SystemExit("The launch podcast feed has no playable episode.")
    if episodes and not audio_files:
        raise SystemExit("The podcast feed advertises episodes without published audio.")
    for episode in episodes:
        enclosure = episode.find("enclosure")
        if enclosure is None or enclosure.get("type") != "audio/mpeg":
            raise SystemExit("A podcast RSS item is missing its MP3 enclosure.")
        audio_path = root / urlparse(enclosure.get("url", "")).path.lstrip("/")
        if not audio_path.is_file() or audio_path.stat().st_size <= 1024:
            raise SystemExit(f"Podcast enclosure does not resolve to a non-empty local MP3: {enclosure.get('url')}")
        urls.extend([
            enclosure.get("url", ""),
            episode.findtext("guid", ""),
            episode.findtext("link", ""),
        ])
        if int(enclosure.get("length", "0")) != audio_path.stat().st_size:
            raise SystemExit(f"Podcast enclosure length does not match the MP3: {enclosure.get('url')}")
        with audio_path.open("rb") as audio_file:
            if not audio_file.read(3).startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
                raise SystemExit(f"Podcast enclosure is not an MP3 stream: {enclosure.get('url')}")
    if any(not url.startswith(site_url) for url in urls):
        raise SystemExit("The podcast feed contains a URL outside the branded Pages address.")

    for path in required:
        if (root / path).stat().st_size == 0:
            raise SystemExit(f"Required site output is empty: {path}")
    print(f"Validated {len(required)} required pages, assets, and feeds.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_site.py <built-site-directory>")
    validate(Path(sys.argv[1]))
