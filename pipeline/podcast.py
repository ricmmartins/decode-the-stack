#!/usr/bin/env python3
"""Generate a short English headline bulletin and its podcast RSS feed."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "editions"
AUDIO_DIR = ROOT / "static" / "podcast" / "audio"
FEED_FILE = ROOT / "static" / "podcast" / "feed.xml"
SITE_URL = "https://decodethestack.pages.dev"
VOICE = "en-US-AriaNeural"
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES_NS)
ET.register_namespace("atom", ATOM_NS)


def episode_script(edition: dict) -> str:
    items = edition.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("The edition has no source-linked headlines.")

    lines = [
        "This is Decode the Stack, the daily tech briefing for software professionals.",
        f"It's {date.fromisoformat(edition['date']):%A, %B} {date.fromisoformat(edition['date']).day}.",
        "Here are today's headlines. Each story is credited to its original publisher. Follow the links in the show notes for the complete reporting and context.",
    ]
    for item in items[:8]:
        lines.append(f"From {item['source']}: {item['title']}.")
    lines.append("That's the Decode the Stack headline briefing. Thanks for listening.")
    return " ".join(lines)


async def _synthesize(text: str, output: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, VOICE).save(str(output))


def _episode_path(day: date) -> Path:
    return AUDIO_DIR / f"{day.isoformat()}.mp3"


def _load_edition(day: date) -> dict | None:
    source = DATA_DIR / f"{day.isoformat()}.json"
    if not source.exists():
        return None
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("date") != day.isoformat():
        raise ValueError(f"Edition date does not match file name: {source}")
    return data


def _add_text(parent: ET.Element, tag: str, value: str, namespace: str | None = None) -> ET.Element:
    qualified = f"{{{namespace}}}{tag}" if namespace else tag
    child = ET.SubElement(parent, qualified)
    child.text = value
    return child


def generate_feed() -> Path:
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    _add_text(channel, "title", "Decode the Stack Podcast")
    _add_text(channel, "link", f"{SITE_URL}/podcast/")
    _add_text(
        channel,
        "description",
        "A short English-language technology headline bulletin. Every story is credited to its original publisher; full context is linked in the accompanying edition.",
    )
    _add_text(channel, "language", "en")
    _add_text(channel, "author", "Decode the Stack", ITUNES_NS)
    _add_text(channel, "explicit", "false", ITUNES_NS)
    category = _add_text(channel, "category", "", ITUNES_NS)
    category.set("text", "Technology")
    image = ET.SubElement(channel, f"{{{ITUNES_NS}}}image")
    image.set("href", f"{SITE_URL}/images/podcast-cover.png")
    owner_email = os.environ.get("PODCAST_OWNER_EMAIL", "").strip()
    if owner_email:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", owner_email):
            raise ValueError("PODCAST_OWNER_EMAIL must be a valid email address.")
        owner = ET.SubElement(channel, f"{{{ITUNES_NS}}}owner")
        _add_text(owner, "name", "Ricardo Martins", ITUNES_NS)
        _add_text(owner, "email", owner_email, ITUNES_NS)

    rss_image = ET.SubElement(channel, "image")
    _add_text(rss_image, "url", f"{SITE_URL}/images/podcast-cover.png")
    _add_text(rss_image, "title", "Decode the Stack Podcast")
    _add_text(rss_image, "link", f"{SITE_URL}/podcast/")
    self_link = ET.SubElement(channel, f"{{{ATOM_NS}}}link")
    self_link.attrib.update({
        "href": f"{SITE_URL}/podcast/feed.xml",
        "rel": "self",
        "type": "application/rss+xml",
    })

    episodes = []
    for metadata_file in sorted(DATA_DIR.glob("*.json"), reverse=True):
        edition = json.loads(metadata_file.read_text(encoding="utf-8"))
        audio = _episode_path(date.fromisoformat(edition["date"]))
        if audio.is_file() and audio.stat().st_size > 1024:
            episodes.append((edition, audio))

    if episodes:
        _add_text(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc)))
    for edition, audio in episodes:
        day = date.fromisoformat(edition["date"])
        item = ET.SubElement(channel, "item")
        title = edition["title"]
        _add_text(item, "title", title)
        _add_text(
            item,
            "description",
            f"A short headline bulletin with {len(edition['items'])} stories, each credited to its original publisher.",
        )
        _add_text(item, "pubDate", format_datetime(datetime.combine(day, datetime.min.time(), timezone.utc)))
        episode_url = f"{SITE_URL}/podcast/audio/{day.isoformat()}.mp3"
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.attrib.update({
            "url": episode_url,
            "length": str(audio.stat().st_size),
            "type": "audio/mpeg",
        })
        _add_text(item, "guid", episode_url).set("isPermaLink", "true")
        _add_text(item, "link", f"{SITE_URL}/posts/{day.isoformat()}-daily/")
        _add_text(item, "author", "Decode the Stack", ITUNES_NS)
        _add_text(item, "explicit", "false", ITUNES_NS)
        _add_text(item, "episodeType", "full", ITUNES_NS)

    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(FEED_FILE, encoding="utf-8", xml_declaration=True)
    print(f"Podcast RSS feed updated with {len(episodes)} real episode(s): {FEED_FILE}")
    return FEED_FILE


def generate_episode(day: date) -> bool:
    edition = _load_edition(day)
    if edition is None:
        print(f"No edition metadata for {day}; no episode generated.")
        return False

    output = _episode_path(day)
    if output.is_file() and output.stat().st_size > 1024:
        print(f"Episode already exists: {output}")
        return True

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".mp3.tmp")
    try:
        asyncio.run(_synthesize(episode_script(edition), temporary))
        if not temporary.is_file() or temporary.stat().st_size <= 1024:
            raise RuntimeError("The speech service returned no usable MP3 audio.")
        with temporary.open("rb") as audio_file:
            if not audio_file.read(3).startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
                raise RuntimeError("The speech service output is not an MP3 stream.")
        temporary.replace(output)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        print(
            f"Audio generation failed ({type(error).__name__}): {error}",
            file=sys.stderr,
        )
        return False

    print(f"Generated English episode: {output} ({output.stat().st_size} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()
    try:
        created = generate_episode(args.date)
        generate_feed()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Podcast publishing failed: {error}", file=sys.stderr)
        return 1
    return 0 if created or not _load_edition(args.date) else 1


if __name__ == "__main__":
    raise SystemExit(main())
