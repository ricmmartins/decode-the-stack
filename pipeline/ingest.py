"""
TechBlog — RSS Feed Ingestion
Pulls articles from curated sources and stores as JSON.
"""

import feedparser
import requests
import yaml
import json
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent
PROJECT_DIR = PIPELINE_DIR.parent
DATA_RAW_DIR = PROJECT_DIR / "data" / "raw"
DATA_DIR = PROJECT_DIR / "data"
SOURCES_FILE = PIPELINE_DIR / "sources.yaml"
SEEN_FILE = DATA_DIR / "seen_articles.json"

USER_AGENT = "DecodeTheStack-Publication/1.0"
FETCH_TIMEOUT = 15  # seconds
MAX_RETRIES = 1
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# ── Content Relevance Filter ──
# Mixed-content sources (news/media) need filtering to block non-tech articles.
# Engineering and vendor blogs are already curated — no filtering needed.

_BLOCKLIST_PATTERNS = re.compile(
    r'\b('
    r'promo\s*code|coupon|discount\s*code|%\s*off|free\s+shipping'
    r'|deal\s+of\s+the\s+day|flash\s+sale|clearance\s+sale'
    r'|best\s+deals|price\s+drop|save\s+\$|shop\s+now'
    r'|affiliate|sponsored\s+content|buy\s+now'
    r'|horoscope|astrology|zodiac|recipe|workout\s+routine'
    r'|fashion\s+trend|beauty\s+tip|skincare|makeup'
    r'|weight\s+loss|diet\s+plan|fitness\s+gear'
    r'|gift\s+guide|holiday\s+sale|black\s+friday\s+deal'
    r')\b', re.IGNORECASE
)

_TECH_KEYWORDS = re.compile(
    r'\b('
    r'software|programming|developer|engineering|open[\s-]?source'
    r'|codebase|source\s*code|code\s*review|code\s*generation|coding'
    r'|API|SDK|framework|library|database|server|cloud'
    r'|kubernetes|docker|linux|windows|macos|android|iOS'
    r'|python|javascript|typescript|rust|golang|java|\.NET|C\+\+'
    r'|machine\s*learning|deep\s*learning|neural\s*network'
    r'|LLM|GPT|ChatGPT|Claude|Copilot|Gemini|transformer'
    r'|diffusion|generative\s+AI|AI\s+model|AI\s+agent'
    r'|artificial\s*intelligence|computer\s*vision|NLP'
    r'|cybersecurity|vulnerability|exploit|malware|ransomware|CVE'
    r'|encryption|authentication|zero[\s-]?day|breach|phishing'
    r'|DevOps|CI/CD|infrastructure|terraform|ansible|helm'
    r'|microservice|container|orchestration|deployment|pipeline'
    r'|startup|funding|IPO|acquisition|open[\s-]?source|GitHub'
    r'|AWS|Azure|GCP|Google\s*Cloud|data\s*center|SaaS|PaaS'
    r'|algorithm|compiler|runtime|kernel|protocol|CPU|GPU|chip'
    r'|robotics|quantum|blockchain|crypto(?:graphy|graphic)'
    r'|semiconductor|processor|NVIDIA|AMD|Intel|Apple\s*Silicon'
    r'|IDE|VS\s*Code|Visual\s*Studio|JetBrains|Xcode'
    r'|tech\s*industry|Big\s*Tech|Silicon\s*Valley'
    r')\b', re.IGNORECASE
)

# Categories that need relevance filtering (mixed editorial content)
_FILTERED_CATEGORIES = {"news"}

_relevance_filtered_count = 0


def _is_tech_relevant(title, summary, category):
    """Check if an article is tech-relevant. Only filters mixed-content sources."""
    global _relevance_filtered_count

    if category not in _FILTERED_CATEGORIES:
        return True

    text = f"{title} {summary}"

    if _BLOCKLIST_PATTERNS.search(text):
        _relevance_filtered_count += 1
        return False

    if _TECH_KEYWORDS.search(text):
        return True

    _relevance_filtered_count += 1
    return False


# Default lookback hours per category when source doesn't specify lookback_days
_DEFAULT_LOOKBACK = {
    "news": 36,       # News sites: 36h (catches late-night posts)
    "dev": 168,        # Engineering blogs: 7 days
    "cloud": 168,
    "devops": 168,
    "security": 72,    # Security: 3 days
    "ai": 72,
}


def load_sources(tier_filter=None):
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    if tier_filter:
        sources = [s for s in sources if s.get("tier") == tier_filter]
    return sources


def make_article_id(url, title):
    raw = f"{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _fetch_feed_content(url):
    """Fetch feed content with proper headers, timeout, and retry on transient errors.
    Falls back to browser-like headers on 403 (some sites block RSS user-agents)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"}
    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    last_exc = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT, allow_redirects=True)
            if resp.status_code in _RETRYABLE_STATUS:
                retry_after = int(resp.headers.get("Retry-After", 2))
                time.sleep(min(retry_after, 5))
                last_exc = Exception(f"HTTP {resp.status_code}")
                continue
            if resp.status_code == 403:
                # Retry once with browser-like headers
                resp = requests.get(url, headers=browser_headers, timeout=FETCH_TIMEOUT, allow_redirects=True)
                if resp.status_code >= 400:
                    return None, f"HTTP {resp.status_code}"
                return resp.content, None
            if resp.status_code >= 400:
                return None, f"HTTP {resp.status_code}"
            return resp.content, None
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(2)
    return None, str(last_exc)


def _extract_date(entry):
    """Extract published date from a feed entry with multiple fallbacks."""
    # 1. Parsed time tuples (feedparser's native parsing)
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "created_parsed") and entry.created_parsed:
        return datetime(*entry.created_parsed[:6], tzinfo=timezone.utc)

    # 2. Raw date strings — try dateutil parser
    for field in ("published", "updated", "created", "dc_date", "date"):
        raw = entry.get(field) or getattr(entry, field, None)
        if raw and isinstance(raw, str):
            try:
                dt = dateparser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except (ValueError, OverflowError):
                continue

    return None


def parse_feed(source):
    """Parse a single RSS feed and return normalized articles."""
    articles = []
    # Per-source lookback: explicit days, or category default
    lookback_h = source.get("lookback_days", 0) * 24
    if not lookback_h:
        lookback_h = _DEFAULT_LOOKBACK.get(source.get("category", "dev"), 48)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_h)

    try:
        content, fetch_err = _fetch_feed_content(source["url"])
        if fetch_err:
            print(f"  [WARN] Failed to fetch: {source['name']} ({fetch_err})")
            return articles

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            exc_info = getattr(feed, "bozo_exception", "unknown error")
            print(f"  [WARN] Failed to parse: {source['name']} ({exc_info})")
            return articles
        if feed.bozo and feed.entries:
            print(f"  [WARN] Partial parse: {source['name']} ({len(feed.entries)} entries despite errors)")

        no_date_count = 0
        for entry in feed.entries[:20]:  # max 20 per source
            published = _extract_date(entry)

            # Skip articles outside this source's lookback window
            if published and published < cutoff:
                continue

            if not published:
                no_date_count += 1

            summary = ""
            if hasattr(entry, "summary"):
                summary = entry.summary[:1000]
            elif hasattr(entry, "description"):
                summary = entry.description[:1000]

            link = entry.get("link", "")
            title = entry.get("title", "No title")

            # Filter non-tech articles from mixed-content sources
            category = source.get("category", "dev")
            if not _is_tech_relevant(title, summary, category):
                continue

            article = {
                "id": make_article_id(link, title),
                "title": title,
                "url": link,
                "source_name": source["name"],
                "source_url": source["url"],
                "category": category,
                "tier": source.get("tier", 2),
                "summary": summary,
                "published": published.isoformat() if published else None,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
            articles.append(article)

        if no_date_count:
            print(f"[{no_date_count} without date]", end=" ")

    except Exception as e:
        print(f"  [FAIL] Error fetching {source['name']}: {e}")

    return articles


def _extract_og_meta(html):
    """Extract Open Graph and JSON-LD metadata from an HTML page."""
    meta = {}
    for prop in ("og:title", "og:description", "article:published_time"):
        m = re.search(rf'<meta\s+(?:property|name)="{prop}"\s+content="([^"]*)"', html)
        if not m:
            m = re.search(rf'<meta\s+content="([^"]*)"\s+(?:property|name)="{prop}"', html)
        if m:
            meta[prop] = m.group(1)
    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            ld = json.loads(m.group(1))
            if isinstance(ld, dict):
                for k in ("datePublished", "headline", "description"):
                    if k in ld:
                        meta[k] = ld[k]
        except (json.JSONDecodeError, ValueError):
            pass
    return meta


def parse_sitemap(source):
    """Scrape articles from a sitemap for sites without RSS feeds.

    Expects source to have:
      url: sitemap URL
      url_patterns: (optional) list of path substrings to filter URLs (e.g. ["/blog/", "/news/"])
      base_url: (optional) base domain for resolving relative URLs
    """
    articles = []
    lookback_h = source.get("lookback_days", 0) * 24
    if not lookback_h:
        lookback_h = _DEFAULT_LOOKBACK.get(source.get("category", "dev"), 48)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_h)
    cutoff_date = cutoff.strftime("%Y-%m-%d")

    url_patterns = source.get("url_patterns", [])

    try:
        content, fetch_err = _fetch_feed_content(source["url"])
        if fetch_err:
            print(f"  [WARN] Failed to fetch sitemap: {source['name']} ({fetch_err})")
            return articles

        # Parse sitemap XML for URLs and lastmod dates
        entries = []
        for m in re.finditer(r"<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?", content.decode("utf-8", errors="replace")):
            url = m.group(1)
            lastmod = m.group(2) or ""
            entries.append((url, lastmod))

        # Filter by URL path patterns if configured
        if url_patterns:
            entries = [(u, lm) for u, lm in entries if any(p in u for p in url_patterns)]

        # Separate entries with and without dates
        dated = [(u, lm) for u, lm in entries if lm]
        undated = [(u, lm) for u, lm in entries if not lm]

        if dated:
            recent = [(u, lm) for u, lm in dated if lm >= cutoff_date]
            recent.sort(key=lambda x: x[1], reverse=True)
            recent = recent[:20]
        elif undated:
            # No dates available — sample a few pages and check metadata dates
            recent = undated[:10]
        else:
            recent = []

        # Fetch each page to extract metadata
        browser_headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DecodeTheStack/1.0)",
            "Accept": "text/html,*/*",
        }
        for url, lastmod in recent:
            try:
                page = requests.get(url, headers=browser_headers, timeout=FETCH_TIMEOUT)
                if page.status_code != 200:
                    continue
                meta = _extract_og_meta(page.text)
                title = meta.get("og:title", meta.get("headline", ""))
                if not title:
                    # Fallback to <title> tag
                    tm = re.search(r"<title>([^<]+)</title>", page.text)
                    title = tm.group(1).strip() if tm else url.rstrip("/").split("/")[-1]
                summary = meta.get("og:description", meta.get("description", ""))[:1000]

                # Parse date: prefer article:published_time > datePublished > lastmod
                published = None
                for date_str in (meta.get("article:published_time"), meta.get("datePublished"), lastmod):
                    if date_str:
                        try:
                            dt = dateparser.parse(date_str)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            published = dt
                            break
                        except (ValueError, OverflowError):
                            continue

                # Skip date re-check for entries that already passed the
                # sitemap-level date filter (lastmod is date-only so midnight
                # can fall just before the exact cutoff).
                if published and published < cutoff and not lastmod:
                    continue
                # Skip articles with no date at all — can't verify recency
                if not published and not lastmod:
                    continue

                article = {
                    "id": make_article_id(url, title),
                    "title": title,
                    "url": url,
                    "source_name": source["name"],
                    "source_url": source["url"],
                    "category": source.get("category", "dev"),
                    "tier": source.get("tier", 2),
                    "summary": summary,
                    "published": published.isoformat() if published else None,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                }
                articles.append(article)
            except requests.exceptions.RequestException:
                continue

    except Exception as e:
        print(f"  [FAIL] Error scraping sitemap {source['name']}: {e}")

    return articles


def parse_source(source):
    """Route to the appropriate parser based on source type."""
    source_type = source.get("type", "rss")
    if source_type == "sitemap":
        return parse_sitemap(source)
    return parse_feed(source)


def filter_recent(articles, hours=24):
    """Keep only articles from the last N hours. Skip articles without dates.
    NOTE: This is now a fallback filter — primary filtering happens per-source
    in parse_feed. This catches articles without dates or edge cases."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    skipped_no_date = 0
    skipped_old = 0
    for a in articles:
        if not a.get("published"):
            skipped_no_date += 1
            continue
        try:
            pub = dateparser.parse(a["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                recent.append(a)
            else:
                skipped_old += 1
        except Exception:
            skipped_no_date += 1
    print(f"  [INFO] Skipped: {skipped_old} old, {skipped_no_date} without date")
    return recent


def deduplicate(articles):
    """Remove exact duplicate articles by ID."""
    seen = set()
    unique = []
    for a in articles:
        if a["id"] not in seen:
            seen.add(a["id"])
            unique.append(a)
    return unique


def _load_seen():
    """Load set of article IDs already used in previous pipeline runs."""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, encoding="utf-8") as f:
                data = json.load(f)
            # Keep only last 30 days of IDs (prune old entries)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            return {k: v for k, v in data.items() if v > cutoff}
        except Exception:
            return {}
    return {}


def _save_seen(seen_dict):
    """Persist seen articles to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_dict, f, ensure_ascii=False)


def _filter_already_seen(articles, seen_dict):
    """Remove articles that were already processed in previous runs."""
    fresh = []
    skipped = 0
    for a in articles:
        if a["id"] not in seen_dict:
            fresh.append(a)
        else:
            skipped += 1
    if skipped:
        print(f"  [INFO] Skipped {skipped} previously seen articles")
    return fresh


def ingest(tier_filter=None, hours=168, date_str=None, force=False):
    """Main ingestion pipeline.
    hours param is max lookback for the fallback filter (default 7 days).
    Per-source lookback is handled in parse_feed."""
    global _relevance_filtered_count
    _relevance_filtered_count = 0
    sources = load_sources(tier_filter)
    print(f"[FEED] Ingesting from {len(sources)} sources...")

    all_articles = []
    for i, source in enumerate(sources):
        print(f"  [{i+1}/{len(sources)}] {source['name']}...", end=" ")
        articles = parse_source(source)
        print(f"{len(articles)} articles")
        all_articles.extend(articles)

    print(f"\n[DOWNLOAD] Total raw: {len(all_articles)}")
    if _relevance_filtered_count:
        print(f"  [FILTER] Filtered {_relevance_filtered_count} non-tech articles from news sources")

    # Log articles without dates but keep them (they still have value)
    no_dates = sum(1 for a in all_articles if not a.get("published"))
    if no_dates:
        print(f"  [INFO] Note: {no_dates} articles without date (kept, no recency bonus)")

    all_articles = deduplicate(all_articles)
    print(f"[UPDATE] After dedup: {len(all_articles)}")

    # Remove already-seen articles from previous runs
    seen_dict = _load_seen()
    if not force:
        all_articles = _filter_already_seen(all_articles, seen_dict)
    print(f"[NEW] New articles: {len(all_articles)}")

    # Mark these articles as seen for future runs
    now = datetime.now(timezone.utc).isoformat()
    for a in all_articles:
        seen_dict[a["id"]] = now
    _save_seen(seen_dict)

    # Save to data/raw/
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = DATA_RAW_DIR / f"articles_{today}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"[SAVE] Saved {len(all_articles)} articles to {output_file}")
    return all_articles


if __name__ == "__main__":
    tier = int(sys.argv[1]) if len(sys.argv) > 1 else None
    ingest(tier_filter=tier)
