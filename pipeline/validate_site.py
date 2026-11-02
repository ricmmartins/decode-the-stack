#!/usr/bin/env python3
"""Fail the deployment if essential pages, assets, or feeds are missing."""

from pathlib import Path
import sys


def validate(root: Path) -> None:
    required = [
        "index.html",
        "index.xml",
        "search/index.html",
        "search-index.json",
        "posts/index.html",
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
    if "https://ricardomartins.com.br/decode-the-stack/" not in home:
        raise SystemExit("The canonical site URL is missing from the home page.")
    if "Decodifica.Tech" in home or "decodifica.tech" in home:
        raise SystemExit("Portuguese site branding leaked into the English site.")

    podcast_feed = (root / "podcast/feed.xml").read_text(encoding="utf-8")
    if "<item>" in podcast_feed or "<enclosure" in podcast_feed:
        raise SystemExit("The launch podcast feed must not contain fabricated episodes.")
    if "images/podcast-cover.png" not in podcast_feed:
        raise SystemExit("The podcast feed is missing its show artwork.")

    for path in required:
        if (root / path).stat().st_size == 0:
            raise SystemExit(f"Required site output is empty: {path}")
    print(f"Validated {len(required)} required pages, assets, and feeds.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_site.py <built-site-directory>")
    validate(Path(sys.argv[1]))
