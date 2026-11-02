"""Generate a contextual, source-linked weekly Top 10 on Fridays."""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_RANKED_DIR = PROJECT_DIR / "data" / "ranked"
DATA_DIR = PROJECT_DIR / "data"
CONTENT_DIR = PROJECT_DIR / "content" / "posts"
WEEKLY_BUFFER_FILE = DATA_RANKED_DIR / "weekly_buffer.json"

WEEKDAYS_EN = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}

WEEKLY_SYSTEM_PROMPT = """You are an experienced technology editor writing for software professionals.

Create a weekly Top 10 of the most consequential technology stories from the supplied source-linked items.

Rules:
- Write natural, clear English in a professional but approachable voice.
- Explain why each story mattered and connect related developments when the supplied evidence supports it.
- Identify credible weekly patterns without overstating them.
- Do not invent details, quotations, numbers, or causal claims.
- Preserve original titles and source links; distinguish reported facts from analysis.

Markdown format:
---
An introduction of 2-3 sentences about the week's verified technology developments.

## Top 10 Stories of the Week

### 1. [Original title](url)
*Category · Publication date*

Two or three paragraphs explaining impact and context.

### 2. [Original title](url)
Repeat the same structure, through the selected top 10.

## Weekly Trends

Two or three paragraphs on evidence-supported patterns across the selected stories.
---
"""


def load_weekly_buffer():
    """Load the weekly buffer of daily stories."""
    if not WEEKLY_BUFFER_FILE.exists():
        print("[FAIL] No weekly buffer found")
        return []
    try:
        with open(WEEKLY_BUFFER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("entries", [])
    except Exception as e:
        print(f"[FAIL] Error loading weekly buffer: {e}")
        return []


def weekly_score(story):
    """Re-score stories for weekly significance (no recency bias)."""
    score = 0.0

    # Coverage weight (more sources = bigger story)
    coverage = story.get("coverage_count", 1)
    score += min(coverage * 4, 20)

    # Daily score as a signal (but capped to reduce recency influence)
    daily_score = story.get("score", 0)
    score += min(daily_score * 0.3, 10)

    # Main story bonus (was selected as main, not radar)
    if story.get("section") == "main":
        score += 5

    # Category diversity bonus (we want a mix)
    # This is applied later during selection

    return round(score, 2)


def select_top_10(entries):
    """Select top 10 stories of the week from all daily entries."""
    all_stories = []
    for entry in entries:
        date = entry.get("date", "")
        for story in entry.get("stories", []):
            story["pub_date"] = date
            story["weekly_score"] = weekly_score(story)
            all_stories.append(story)

    # Deduplicate by normalized title (same story across days)
    seen_titles = set()
    unique = []
    for story in all_stories:
        title_norm = story.get("title", "").lower().strip()
        if title_norm not in seen_titles:
            seen_titles.add(title_norm)
            unique.append(story)

    # Sort by weekly score
    unique.sort(key=lambda s: -s["weekly_score"])

    # Select top 10 with category diversity
    selected = []
    category_counts = {}
    for story in unique:
        if len(selected) >= 10:
            break
        cat = story.get("category", "dev")
        # Allow max 3 stories per category in top 10
        if category_counts.get(cat, 0) >= 3:
            continue
        selected.append(story)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return selected


def build_weekly_prompt(top_stories, week_start, week_end):
    """Format top stories for weekly synthesis."""
    lines = [
        f"Here are the selected technology stories from {week_start} through {week_end}.\n",
        "Explain why each mattered and add context grounded in the supplied summaries:\n",
    ]
    for i, story in enumerate(top_stories):
        lines.append(f"---\n{i+1}. {story['title']}")
        lines.append(f"   URL: {story['url']}")
        lines.append(f"   Category: {story['category']}")
        lines.append(f"   Published: {story['pub_date']}")
        lines.append(f"   Independent source coverage: {story.get('coverage_count', 1)}")
        lines.append(f"   Publisher context: {story.get('summary', 'N/A')}")
        lines.append("")
    lines.append("---\nSynthesize the selected stories with depth and follow the specified format.")
    return "\n".join(lines)


def _call_llm(system_prompt, user_prompt, label="Weekly"):
    """Use the shared quality-first LLM provider chain."""
    from synthesize import _call_llm as call_llm
    return call_llm(system_prompt, user_prompt, label)


def format_date_en(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{WEEKDAYS_EN[d.weekday()]}, {d.strftime('%B')} {d.day}"


def run(date_str=None, force_day=False):
    """Generate weekly summary. Runs on Fridays only (unless force_day=True)."""
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_obj = datetime.strptime(date, "%Y-%m-%d")

    # Only run on Fridays (weekday 4) unless explicitly forced
    if not force_day and date_obj.weekday() != 4:
        print(f"[SKIP]  Not Friday (weekday={date_obj.weekday()}), skipping weekly summary")
        return None

    # Idempotency: check if weekly post already exists
    weekly_file = CONTENT_DIR / f"{date}-weekly.md"
    if weekly_file.exists():
        print(f"[SKIP]  Weekly post already exists: {weekly_file}")
        return None

    # Load buffer
    entries = load_weekly_buffer()
    if not entries:
        print("[FAIL] No weekly buffer data available")
        return None

    # Get week range: always show full week (Monday to today)
    # regardless of how many days are in the buffer
    week_end = date
    week_end_obj = datetime.strptime(week_end, "%Y-%m-%d")
    # Go back to Monday of this week (weekday 0 = Monday)
    days_since_monday = week_end_obj.weekday()
    week_start_obj = week_end_obj - timedelta(days=days_since_monday)
    week_start = week_start_obj.strftime("%Y-%m-%d")

    week_range_en = f"{format_date_en(week_start)} to {format_date_en(week_end)}"

    print(f"[DATE] Weekly summary: {week_start} to {week_end} ({len(entries)} days of data)")

    # Select top 10
    top_stories = select_top_10(entries)
    if len(top_stories) < 5:
        print(f"[WARN]  Only {len(top_stories)} stories — too few for weekly summary")
        return None

    print(f"[RANK] Top {len(top_stories)} stories selected for weekly summary:")
    for i, s in enumerate(top_stories):
        print(f"  {i+1}. [{s['category']}] {s['title'][:70]} (score: {s['weekly_score']})")

    # Synthesize
    prompt = build_weekly_prompt(top_stories, format_date_en(week_start), format_date_en(week_end))
    content = _call_llm(WEEKLY_SYSTEM_PROMPT, prompt)

    if not content:
        print("[FAIL] Weekly synthesis failed")
        return None

    # Generate Hugo post
    date_en = f"{WEEKDAYS_EN[date_obj.weekday()]}, {date_obj.strftime('%B')} {date_obj.day}, {date_obj.year}"

    # Extract categories from top stories (deduplicated)
    cat_map = {"dev": "Software Engineering", "cloud": "Cloud", "devops": "DevOps & SRE",
               "security": "Security", "ai": "AI/ML", "news": "Software Engineering"}
    categories_display = sorted(set(cat_map.get(c, c.title()) for c in
                                    set(s.get("category", "dev") for s in top_stories)))

    post = f"""---
title: "Weekly Top 10: {week_range_en}"
date: {date}T00:00:00Z
slug: "{date}-weekly"
description: "The week's most consequential technology stories, synthesized in English."
categories: {json.dumps(["Weekly Briefing"] + categories_display, ensure_ascii=False)}
tags: ["weekly-briefing", "top-10"]
draft: false
ShowToc: true
TocOpen: false
---

> **Weekly Top 10**: The most consequential stories from {week_range_en} ({date_en})

{content}
"""

    from humanizer import write_reviewed_post
    write_reviewed_post(weekly_file, post, PROJECT_DIR)

    print(f"[WRITE] Weekly summary generated: {weekly_file}")
    return weekly_file


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    force = "--force" in sys.argv
    run(date, force_day=force)
