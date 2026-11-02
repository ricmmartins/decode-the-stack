"""
TechBlog — Story Ranking
Scores and selects the top stories for the daily post.
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateparser
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_CLUSTERED_DIR = PROJECT_DIR / "data" / "clustered"
DATA_RANKED_DIR = PROJECT_DIR / "data" / "ranked"
PUBLISHED_HISTORY_FILE = DATA_RANKED_DIR / "published_history.json"

# Source authority scores
AUTHORITY_SCORES = {
    "Hacker News (Best)": 10,
    "Ars Technica": 9,
    "InfoQ": 9,
    "Cloudflare Blog": 9,
    "Netflix Tech Blog": 9,
    "Krebs on Security": 9,
    "The New Stack": 8,
    "TechCrunch": 8,
    "GitHub Engineering": 9,
    "Stripe Engineering": 9,
    "Google Developers Blog": 8,
    "Microsoft DevBlogs": 8,
    "AWS Blog": 8,
    "Azure Blog": 8,
    "OpenAI Blog": 9,
    "Anthropic Blog": 9,
    "Martin Fowler": 9,
    "Julia Evans": 8,
    "Pragmatic Engineer": 9,
    "Schneier on Security": 9,
    "Troy Hunt": 8,
}

# Target category distribution for a balanced daily post
CATEGORY_TARGETS = {
    "dev": 3,
    "cloud": 2,
    "devops": 2,
    "security": 2,
    "ai": 2,
    "news": 1,
}

# Dynamic selection: score thresholds instead of fixed limits
MAIN_MIN_SCORE = 20    # minimum score for main stories
MAIN_MIN_COUNT = 8     # always include at least this many
MAIN_MAX_COUNT = 20    # cap to keep post manageable
QUICK_MIN_SCORE = 10   # minimum score for quick reads
QUICK_MAX_COUNT = 30   # cap for radar rápido


def normalize_url(url):
    """Normalize URL for dedup: strip query params, fragments, trailing slash, lowercase."""
    if not url:
        return ""
    url = url.split("?")[0].split("#")[0].rstrip("/").lower()
    # Strip common tracking prefixes
    url = re.sub(r"https?://(www\.)?", "", url)
    return url


def normalize_title(title):
    """Normalize title for dedup: lowercase, strip punctuation, collapse whitespace."""
    if not title:
        return ""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def load_published_history():
    """Load rolling history of published story URLs and titles (last 3 days)."""
    if not PUBLISHED_HISTORY_FILE.exists():
        return {"entries": []}
    try:
        with open(PUBLISHED_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"entries": []}


def save_published_history(history):
    """Save published history, keeping only last 3 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    history["entries"] = [e for e in history["entries"] if e.get("date", "") >= cutoff]
    DATA_RANKED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUBLISHED_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_published_fingerprints(history, exclude_date=None):
    """Get sets of normalized URLs and titles from published history."""
    urls = set()
    titles = set()
    for entry in history.get("entries", []):
        if exclude_date and entry.get("date") == exclude_date:
            continue
        urls.update(entry.get("urls", []))
        titles.update(entry.get("titles", []))
    return urls, titles


def filter_already_published(stories, published_urls, published_titles):
    """Remove stories that were already published in recent days."""
    fresh = []
    dupes = 0
    for story in stories:
        story_url = normalize_url(story.get("url", ""))
        story_title = normalize_title(story.get("title", ""))
        # Also check all source URLs from the cluster
        source_urls = {normalize_url(s.get("url", "")) for s in story.get("sources", [])}

        if story_url in published_urls or story_title in published_titles:
            dupes += 1
            continue
        if source_urls & published_urls:
            dupes += 1
            continue
        fresh.append(story)

    if dupes:
        print(f"[UPDATE] Cross-day dedup: removed {dupes} already-published stories")
    return fresh


def record_published(history, date_str, main_stories, quick_stories):
    """Record today's published stories into history."""
    urls = set()
    titles = set()
    for story in main_stories + quick_stories:
        urls.add(normalize_url(story.get("url", "")))
        titles.add(normalize_title(story.get("title", "")))
        for s in story.get("sources", []):
            urls.add(normalize_url(s.get("url", "")))

    urls.discard("")
    titles.discard("")

    # Remove any existing entry for today (idempotent re-runs)
    history["entries"] = [e for e in history["entries"] if e.get("date") != date_str]
    history["entries"].append({
        "date": date_str,
        "urls": sorted(urls),
        "titles": sorted(titles),
    })
    save_published_history(history)


def score_story(story):
    """Score a story based on multiple signals."""
    score = 0.0

    # Coverage: more sources = bigger story
    coverage = story.get("coverage_count", 1)
    score += min(coverage * 3, 15)  # cap at 15

    # Source authority
    source = story.get("source_name", "")
    score += AUTHORITY_SCORES.get(source, 5)

    # Summary quality (longer = more substance)
    summary_len = len(story.get("summary", ""))
    score += min(summary_len / 100, 5)  # cap at 5

    # Recency bonus: newer articles score higher
    published = story.get("published")
    if published:
        try:
            pub = dateparser.parse(published)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            hours_ago = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
            if hours_ago < 6:
                score += 8  # very fresh
            elif hours_ago < 12:
                score += 5
            elif hours_ago < 18:
                score += 3
            elif hours_ago < 24:
                score += 1
        except Exception:
            pass

    return round(score, 2)


def select_balanced(stories, min_count=MAIN_MIN_COUNT, max_count=MAIN_MAX_COUNT, min_score=MAIN_MIN_SCORE):
    """Select stories ensuring category balance, using dynamic score threshold."""
    selected = []
    category_counts = {cat: 0 for cat in CATEGORY_TARGETS}

    # First pass: fill category targets with highest-scored
    for cat, target in CATEGORY_TARGETS.items():
        cat_stories = [s for s in stories if s["category"] == cat]
        for story in cat_stories[:target]:
            if len(selected) < max_count:
                selected.append(story)
                category_counts[cat] = category_counts.get(cat, 0) + 1

    # Second pass: add remaining stories that meet the score threshold
    remaining = [s for s in stories if s not in selected]
    for story in remaining:
        if len(selected) >= max_count:
            break
        if len(selected) >= min_count and story["score"] < min_score:
            break
        selected.append(story)

    return selected


def run(date_str=None):
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = DATA_CLUSTERED_DIR / f"stories_{date}.json"

    if not filepath.exists():
        print(f"[FAIL] No clustered stories found for {date}")
        return [], []

    with open(filepath, "r", encoding="utf-8") as f:
        stories = json.load(f)

    print(f"[RANK] Ranking {len(stories)} stories...")

    # Cross-day dedup: remove stories already published in the last 3 days
    history = load_published_history()
    published_urls, published_titles = get_published_fingerprints(history, exclude_date=date)
    if published_urls or published_titles:
        stories = filter_already_published(stories, published_urls, published_titles)
        print(f"[INFO] After cross-day dedup: {len(stories)} stories remaining")

    # Score all stories
    for story in stories:
        story["score"] = score_story(story)

    # Sort by score descending
    stories.sort(key=lambda s: -s["score"])

    # Select main stories (balanced, dynamic)
    main_stories = select_balanced(stories)

    # Select quick reads from remaining (score threshold)
    remaining = [s for s in stories if s not in main_stories]
    quick_reads = [s for s in remaining if s["score"] >= QUICK_MIN_SCORE][:QUICK_MAX_COUNT]

    all_selected = main_stories + quick_reads

    print(f"[OK] Selected {len(main_stories)} main + {len(quick_reads)} quick reads:")
    for i, s in enumerate(main_stories):
        print(f"  [STORY] {i+1}. [{s['category']}] {s['title'][:80]} (score: {s['score']})")
    for i, s in enumerate(quick_reads):
        print(f"  [QUICK] {i+1}. [{s['category']}] {s['title'][:80]} (score: {s['score']})")

    DATA_RANKED_DIR.mkdir(parents=True, exist_ok=True)

    # Save main stories
    output_file = DATA_RANKED_DIR / f"top_{date}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(main_stories, f, ensure_ascii=False, indent=2)

    # Save quick reads
    quick_file = DATA_RANKED_DIR / f"quick_{date}.json"
    with open(quick_file, "w", encoding="utf-8") as f:
        json.dump(quick_reads, f, ensure_ascii=False, indent=2)

    # Record published stories for cross-day dedup
    record_published(history, date, main_stories, quick_reads)

    print(f"[SAVE] Saved to {output_file} + {quick_file}")
    return main_stories, quick_reads


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run(date)
