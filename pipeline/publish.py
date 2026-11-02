#!/usr/bin/env python3
"""Publish a source-linked daily edition from public English RSS/Atom feeds."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "pipeline" / "sources.json"
POSTS_DIR = ROOT / "content" / "posts"
USER_AGENT = "DecodeTheStack/1.0 (+https://ricmmartins.github.io/decode-the-stack/)"
MAX_FEED_BYTES = 2_000_000
MAX_ITEMS = 12


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in element.iter():
        if child is not element and _local_name(child.tag) in wanted:
            return "".join(child.itertext()).strip()
    return ""


def _entry_link(entry: ET.Element) -> str:
    for child in entry:
        if _local_name(child.tag) == "link":
            href = child.attrib.get("href")
            if href and child.attrib.get("rel", "alternate") == "alternate":
                return href.strip()
            if child.text and child.text.strip():
                return child.text.strip()
    return ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _clean_excerpt(value: str) -> str:
    value = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>", " ", value)
    value = re.sub(r"(?i)\s*the post .+? appeared first on .+?\s*$", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()[:700]


def parse_feed(source: dict, payload: bytes) -> list[dict]:
    """Parse RSS 2.0, RDF/RSS 1.0, or Atom entries without third-party packages."""
    root = ET.fromstring(payload)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"item", "entry"}]
    parsed = []
    for entry in entries[:30]:
        title = _child_text(entry, "title")
        link = _entry_link(entry)
        if not title or not link:
            continue
        published_text = _child_text(entry, "published", "pubdate", "date", "updated")
        published = _parse_date(published_text)
        summary = _clean_excerpt(_child_text(entry, "description", "summary", "encoded", "content"))
        parsed.append({
            "title": title.strip(),
            "url": link,
            "summary": summary,
            "published": published,
            "source": source["name"],
            "category": source["category"],
            "weight": int(source.get("weight", 1)),
        })
    return parsed


def fetch_source(source: dict) -> list[dict]:
    request = urllib.request.Request(
        source["url"],
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError(f"Feed exceeds {MAX_FEED_BYTES} bytes")
    return parse_feed(source, payload)


def select_recent(items: list[dict], cutoff: datetime) -> list[dict]:
    by_url: dict[str, dict] = {}
    for item in items:
        published = item.get("published")
        if not published or published > datetime.now(timezone.utc) + timedelta(hours=2) or published < cutoff:
            continue
        url = item["url"].split("#", 1)[0].rstrip("/")
        current = by_url.get(url)
        if current is None or item["weight"] > current["weight"]:
            by_url[url] = item
    ranked = sorted(
        by_url.values(),
        key=lambda item: (-item["weight"], -item["published"].timestamp(), item["title"].casefold()),
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in ranked:
        grouped[item["source"]].append(item)

    source_order = sorted(
        grouped,
        key=lambda source: (
            -grouped[source][0]["weight"],
            -grouped[source][0]["published"].timestamp(),
            source.casefold(),
        ),
    )
    selected = []
    for round_number in range(3):
        for source in source_order:
            if len(grouped[source]) > round_number:
                selected.append(grouped[source][round_number])
                if len(selected) == MAX_ITEMS:
                    return selected
    return selected


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_edition(day: date, items: list[dict]) -> str:
    category_list = sorted({item["category"] for item in items})
    headline = "A source-linked briefing on " + ", ".join(category_list[:-1])
    if len(category_list) > 1:
        headline += " and " + category_list[-1]
    elif category_list:
        headline = "A source-linked briefing on " + category_list[0]
    else:
        headline = "A source-linked technology briefing"

    lines = [
        "---",
        f"title: {_yaml_string(f'The engineering briefing — {day:%B} {day.day}, {day.year}')}",
        f"date: {day.isoformat()}T12:00:00Z",
        f"description: {_yaml_string(headline + '.')}",
        "categories:",
        "  - Daily Briefing",
        "tags:",
        "  - daily-briefing",
        "sources:",
    ]
    for source in sorted({item["source"] for item in items}):
        lines.append(f"  - {_yaml_string(source)}")
    lines.extend(["---", "", f"## The brief for {day:%A, %B} {day.day}", ""])
    lines.extend([
        "This edition brings together recent items from the sources below. Headlines and excerpts are attributed to their original publishers; follow each link for the complete report and context.",
        "",
    ])
    for index, item in enumerate(items, start=1):
        lines.extend([
            f"### {index}. [{item['title']}]({item['url']})",
            "",
            f"**{item['category']} · {item['source']} · {item['published']:%b %d, %H:%M UTC}**",
            "",
            item["summary"] or f"Read the original report from {item['source']}.",
            "",
            f"[Read the original at {item['source']} →]({item['url']})",
            "",
        ])
    lines.extend([
        "---",
        "",
        "*Decode the Stack links to original reporting and preserves the publisher's attribution. Excerpts are supplied by the linked sources; they are not independent verification or a substitute for the original article.*",
        "",
    ])
    return "\n".join(lines)


def publish(day: date | None = None, max_age_hours: int = 48) -> Path | None:
    day = day or datetime.now(timezone.utc).date()
    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    fetched: list[dict] = []
    successes = 0
    errors = []
    for source in sources:
        try:
            found = fetch_source(source)
            fetched.extend(found)
            successes += 1
            print(f"{source['name']}: {len(found)} feed items")
        except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError, ValueError) as error:
            errors.append((source["name"], str(error)))
            print(f"Feed unavailable: {source['name']}: {error}", file=sys.stderr)

    if not successes:
        raise RuntimeError("No configured feed could be fetched; refusing to publish an empty edition.")
    cutoff = datetime.combine(day, datetime.min.time(), timezone.utc) - timedelta(hours=max_age_hours)
    items = select_recent(fetched, cutoff)
    if not items:
        print("No recent dated stories; no edition was created.")
        return None

    output = POSTS_DIR / f"{day.isoformat()}-daily.md"
    if output.exists():
        print(f"Edition already exists: {output}")
        return output
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    output.write_text(render_edition(day, items), encoding="utf-8")
    print(f"Published {len(items)} source-linked items to {output}")
    if errors:
        print(f"{len(errors)} source(s) were unavailable; see feed warnings above.", file=sys.stderr)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="Edition date (YYYY-MM-DD); defaults to UTC today")
    parser.add_argument("--max-age-hours", type=int, default=48)
    args = parser.parse_args()
    if args.max_age_hours < 1:
        parser.error("--max-age-hours must be positive")
    try:
        publish(args.date, args.max_age_hours)
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Publication failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
