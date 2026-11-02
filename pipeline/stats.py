"""
TechBlog — Stats & Trend Data Generator
Generates stats.json, stats_history.json, trends.json and weekly_buffer.json
for the public stats page and trend history charts.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).parent.parent
SITE_DATA_DIR = PROJECT_DIR / "static" / "data"
HUGO_DATA_DIR = PROJECT_DIR / "data"
DATA_RANKED_DIR = PROJECT_DIR / "data" / "ranked"
CONTENT_DIR = PROJECT_DIR / "content" / "posts"
SOURCES_FILE = PROJECT_DIR / "pipeline" / "sources.yaml"

HISTORY_DAYS = 30
TREND_TOP_N = 20


def _load_json(path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_source_count():
    """Count total sources from sources.yaml."""
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict) or not isinstance(config.get("sources"), list):
        raise ValueError(f"Invalid source configuration: {SOURCES_FILE}")
    return len(config["sources"])


def generate_daily_stats(date_str, articles_count=0, clusters_count=0,
                         main_count=0, quick_count=0, tag_counts=None):
    """Generate today's stats and append to history."""
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    today_stats = {
        "date": date_str,
        "total_sources": get_source_count(),
        "articles_ingested": articles_count,
        "clusters_formed": clusters_count,
        "main_stories": main_count,
        "radar_items": quick_count,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save current day stats
    _save_json(SITE_DATA_DIR / "pipeline_stats.json", today_stats)

    # Append to rolling history (last N days)
    history_path = SITE_DATA_DIR / "stats_history.json"
    history = _load_json(history_path, [])
    if not isinstance(history, list):
        history = []

    # Upsert: replace existing entry for today
    history = [h for h in history if h.get("date") != date_str]
    history.append(today_stats)

    # Keep only last N days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    history = [h for h in history if h.get("date", "") >= cutoff]
    history.sort(key=lambda h: h.get("date", ""))

    _save_json(SITE_DATA_DIR / "stats_history.json", history)
    print(f"[STATS] Stats saved: {main_count} main, {quick_count} radar, {articles_count} articles from {today_stats['total_sources']} sources")


def generate_trend_data(date_str, tag_counts):
    """Update rolling trend data with today's tag frequencies."""
    if not tag_counts:
        return

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    trends_path = SITE_DATA_DIR / "trends.json"
    trends = _load_json(trends_path, {"days": []})

    if not isinstance(trends.get("days"), list):
        trends["days"] = []

    # Upsert today's entry
    trends["days"] = [d for d in trends["days"] if d.get("date") != date_str]
    trends["days"].append({
        "date": date_str,
        "tags": tag_counts,
    })

    # Keep only last N days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    trends["days"] = [d for d in trends["days"] if d.get("date", "") >= cutoff]
    trends["days"].sort(key=lambda d: d.get("date", ""))

    # Compute top-N tags across all days for chart rendering
    all_tags = {}
    for day in trends["days"]:
        for tag, count in day.get("tags", {}).items():
            all_tags[tag] = all_tags.get(tag, 0) + count
    trends["top_tags"] = sorted(all_tags.keys(), key=lambda t: -all_tags[t])[:TREND_TOP_N]

    _save_json(SITE_DATA_DIR / "trends.json", trends)
    print(f"[TREND] Trend data saved: {len(tag_counts)} tags for {date_str}")


def _read_ranked_stories(date_str):
    stories = []
    for kind in ("top", "quick"):
        path = DATA_RANKED_DIR / f"{kind}_{date_str}.json"
        if path.is_file():
            with path.open(encoding="utf-8") as source_file:
                data = json.load(source_file)
            if not isinstance(data, list):
                raise ValueError(f"Ranked story data must be a list: {path}")
            stories.extend(data)
    return stories


def generate_publication_stats():
    """Rebuild archive totals from published English editions and their ranking data."""
    daily_posts = sorted(CONTENT_DIR.glob("*-daily.md"))
    source_counts = {}
    category_counts = {}
    history = []
    headline_total = 0

    for post_path in daily_posts:
        date_str = post_path.name.removesuffix("-daily.md")
        story_data = _read_ranked_stories(date_str)
        main_path = DATA_RANKED_DIR / f"top_{date_str}.json"
        quick_path = DATA_RANKED_DIR / f"quick_{date_str}.json"
        main_stories = []
        quick_stories = []
        if main_path.is_file():
            with main_path.open(encoding="utf-8") as source_file:
                main_stories = json.load(source_file)
        if quick_path.is_file():
            with quick_path.open(encoding="utf-8") as source_file:
                quick_stories = json.load(source_file)

        if not story_data:
            frontmatter = post_path.read_text(encoding="utf-8").split("---", 2)
            metadata = yaml.safe_load(frontmatter[1]) if len(frontmatter) > 2 else {}
            main_count = int((metadata or {}).get("mainCount", 0))
            quick_count = int((metadata or {}).get("quickCount", 0))
            count = main_count + quick_count
        else:
            count = len(story_data)
        headline_total += count

        publishers_for_day = set()
        for story in story_data:
            category = str(story.get("category") or "news").lower()
            category_name = {
                "dev": "Software Engineering",
                "news": "Software Engineering",
                "cloud": "Cloud",
                "devops": "DevOps & SRE",
                "security": "Security",
                "ai": "AI/ML",
            }.get(category, category.title())
            category_counts[category_name] = category_counts.get(category_name, 0) + 1

            names = {story.get("source_name", "")}
            names.update(
                source.get("name", "")
                for source in story.get("sources", [])
                if isinstance(source, dict)
            )
            for name in names - {""}:
                publishers_for_day.add(name)
                source_counts[name] = source_counts.get(name, 0) + 1

        history.append({
            "date": date_str,
            "headlines": count,
            "sources": len(publishers_for_day),
        })

    latest = history[-1] if history else None
    stats = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "configured_feeds": get_source_count(),
        "editions_published": len(daily_posts),
        "headlines_published": headline_total,
        "sources_credited": len(source_counts),
        "latest_edition_date": latest["date"] if latest else None,
        "latest_headlines": latest["headlines"] if latest else 0,
        "source_counts": [
            {"name": name, "headlines": count}
            for name, count in sorted(
                source_counts.items(), key=lambda entry: (-entry[1], entry[0].casefold())
            )
        ],
        "category_counts": [
            {"name": name, "headlines": count}
            for name, count in sorted(
                category_counts.items(), key=lambda entry: (-entry[1], entry[0].casefold())
            )
        ],
        "history": history[-HISTORY_DAYS:],
    }
    _save_json(HUGO_DATA_DIR / "stats.json", stats)
    print(
        f"[STATS] Publication stats rebuilt: {stats['editions_published']} editions, "
        f"{headline_total} items, {stats['sources_credited']} credited publishers"
    )
    return stats


def save_weekly_buffer(date_str, main_stories, quick_stories):
    """Save today's top stories to the weekly buffer for Friday summary."""
    buffer_path = DATA_RANKED_DIR / "weekly_buffer.json"
    buffer = _load_json(buffer_path, {"entries": []})

    if not isinstance(buffer.get("entries"), list):
        buffer["entries"] = []

    # Upsert today's entry
    buffer["entries"] = [e for e in buffer["entries"] if e.get("date") != date_str]

    # Save compact story data (just what's needed for weekly ranking)
    stories_compact = []
    for s in main_stories:
        stories_compact.append({
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "category": s.get("category", ""),
            "score": s.get("score", 0),
            "coverage_count": s.get("coverage_count", 1),
            "source_name": s.get("source_name", ""),
            "summary": s.get("summary", "")[:200],
            "section": "main",
        })
    for s in quick_stories:
        stories_compact.append({
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "category": s.get("category", ""),
            "score": s.get("score", 0),
            "coverage_count": s.get("coverage_count", 1),
            "source_name": s.get("source_name", ""),
            "summary": s.get("summary", "")[:200],
            "section": "radar",
        })

    buffer["entries"].append({
        "date": date_str,
        "stories": stories_compact,
    })

    # Keep only current week (last 7 days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    buffer["entries"] = [e for e in buffer["entries"] if e.get("date", "") >= cutoff]
    buffer["entries"].sort(key=lambda e: e.get("date", ""))

    _save_json(buffer_path, buffer)
    print(f"[INFO] Weekly buffer: {len(stories_compact)} stories saved for {date_str}")
