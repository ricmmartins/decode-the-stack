"""Generate the English show's RSS feed from real, locally published MP3 episodes."""

import os
import hashlib
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_DIR / "static" / "podcast" / "audio"
CHAPTERS_DIR = PROJECT_DIR / "static" / "podcast" / "chapters"
CONTENT_DIR = PROJECT_DIR / "content" / "posts"
FEED_FILE = PROJECT_DIR / "static" / "podcast" / "feed.xml"

SITE_URL = os.environ.get(
    "DECODE_SITE_URL", "https://decodethestack.com"
).rstrip("/")
PODCAST_TITLE = "Decode the Stack"
PODCAST_DESCRIPTION = (
    "A daily English-language technology briefing for software professionals. "
    "Anna, Maria, and Pedro connect the context behind engineering, cloud, "
    "DevOps, security, and AI/ML stories."
)
PODCAST_AUTHOR = "Decode the Stack"
PODCAST_OWNER_NAME = "Ricardo Martins"
PODCAST_OWNER_EMAIL = os.environ.get(
    "PODCAST_OWNER_EMAIL", "podcast@decodethestack.com"
)
PODCAST_LANGUAGE = "en-US"
PODCAST_IMAGE = f"{SITE_URL}/images/podcast-cover.png"
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
LEGACY_EPISODE_URLS = {
    "2026-11-02": "https://decodethestack.pages.dev/podcast/audio/2026-11-02.mp3",
}


def episode_audio_url(date_str):
    """Keep published episode identity stable across the custom-domain migration."""
    return LEGACY_EPISODE_URLS.get(date_str, f"{SITE_URL}/podcast/audio/{date_str}.mp3")


def _episode_post(date_str):
    candidates = [
        CONTENT_DIR / f"{date_str}-daily.md",
        CONTENT_DIR / f"{date_str}.md",
        CONTENT_DIR / f"{date_str}-weekly.md",
    ]
    return next((path for path in candidates if path.is_file()), None)


def _episode_metadata(date_str):
    post_file = _episode_post(date_str)
    if not post_file:
        return f"Decode the Stack — {date_str}", f"Daily English briefing for {date_str}."

    text = post_file.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, re.DOTALL)
    metadata = yaml.safe_load(match.group(1)) if match else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    title = str(metadata.get("title") or f"Decode the Stack — {date_str}")
    description = str(metadata.get("description") or f"Daily English briefing for {date_str}.")
    return title, description


def _format_date(date_str):
    """Return a stable UTC publication timestamp for the episode date."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=12, minute=0, tzinfo=timezone.utc
    )
    return format_datetime(dt)


def _duration_seconds(path):
    """Return an MP3's measured duration; omit duration metadata if it cannot be read."""
    try:
        from pydub import AudioSegment

        return max(1, round(len(AudioSegment.from_mp3(str(path))) / 1000))
    except (ImportError, OSError, ValueError):
        return None


def generate_feed():
    """Version audio downloads by content while preserving episode GUIDs."""
    items = []
    for mp3 in sorted(AUDIO_DIR.glob("*.mp3"), reverse=True):
        date_str = mp3.stem
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            continue
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        size = mp3.stat().st_size
        if size <= 1024:
            raise ValueError(f"Podcast episode is empty or too small: {mp3}")
        identity_url = episode_audio_url(date_str)
        version = hashlib.sha256(mp3.read_bytes()).hexdigest()[:12]
        audio_url = f"{identity_url}?v={version}"
        post_url = f"{SITE_URL}/posts/{date_str}-daily/"
        title, description = _episode_metadata(date_str)
        duration = _duration_seconds(mp3)
        duration_tag = f"\n      <itunes:duration>{duration}</itunes:duration>" if duration else ""
        chapters_file = CHAPTERS_DIR / f"{date_str}.json"
        chapters_tag = (
            f'\n      <podcast:chapters url="{SITE_URL}/podcast/chapters/{date_str}.json" '
            'type="application/json+chapters"/>'
            if chapters_file.is_file()
            else ""
        )
        items.append(f"""    <item>
      <title>{escape(title)}</title>
      <description>{escape(description)}</description>
      <pubDate>{_format_date(date_str)}</pubDate>
      <enclosure url="{escape(audio_url, {'"': '&quot;'})}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="true">{escape(identity_url)}</guid>
      <link>{escape(post_url)}</link>
      <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
      <itunes:summary>{escape(description)}</itunes:summary>{duration_tag}
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>{chapters_tag}
    </item>""")

    now_rfc = format_datetime(datetime.now(timezone.utc))
    feed_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="{ITUNES_NS}"
     xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="{ATOM_NS}"
     xmlns:podcast="{PODCAST_NS}">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{SITE_URL}/</link>
    <language>{PODCAST_LANGUAGE}</language>
    <description>{escape(PODCAST_DESCRIPTION)}</description>
    <lastBuildDate>{now_rfc}</lastBuildDate>
    <atom:link href="{SITE_URL}/podcast/feed.xml" rel="self" type="application/rss+xml"/>
    <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
    <itunes:summary>{escape(PODCAST_DESCRIPTION)}</itunes:summary>
    <itunes:owner>
      <itunes:name>{escape(PODCAST_OWNER_NAME)}</itunes:name>
      <itunes:email>{escape(PODCAST_OWNER_EMAIL)}</itunes:email>
    </itunes:owner>
    <itunes:image href="{PODCAST_IMAGE}"/>
    <itunes:category text="Technology">
      <itunes:category text="Tech News"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <image>
      <url>{PODCAST_IMAGE}</url>
      <title>{escape(PODCAST_TITLE)}</title>
      <link>{SITE_URL}/</link>
    </image>
{chr(10).join(items)}
  </channel>
</rss>
"""
    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEED_FILE.write_text(feed_xml, encoding="utf-8")
    print(f"[OK] English podcast feed written: {FEED_FILE} ({len(items)} episodes)")
    return FEED_FILE


if __name__ == "__main__":
    generate_feed()
