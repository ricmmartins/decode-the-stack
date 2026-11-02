"""Run the English edition pipeline: ingest, cluster, rank, synthesize, and publish."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from ingest import ingest
from cluster import run as cluster_run
from rank import run as rank_run
from synthesize import run as synthesize_run
from generate_post import generate_post
from podcast import run as podcast_run
from podcast_feed import generate_feed as podcast_feed_run
from stats import (
    generate_daily_stats,
    generate_publication_stats,
    generate_trend_data,
    save_weekly_buffer,
)
from weekly_summary import run as weekly_run

PROJECT_DIR = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_DIR / "content" / "posts"
DATA_RAW_DIR = PROJECT_DIR / "data" / "raw"
DATA_CLUSTERED_DIR = PROJECT_DIR / "data" / "clustered"


def _set_github_output(key, value):
    """Set a GitHub Actions output variable (no-op outside Actions)."""
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"{key}={value}\n")


def run_pipeline(date_str=None, skip_ingest=False, force=False):
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Idempotency guard: scheduled retries do not regenerate an existing edition.
    post_file = CONTENT_DIR / f"{date}-daily.md"
    if post_file.exists() and not force:
        print(f"[SKIP]  Post for {date} already exists ({post_file}). Use --force to regenerate.")
        _try_weekly(date)
        return

    print(f"{'='*60}")
    print(f"[START] Decode the Stack publishing pipeline — {date} (UTC)")
    print(f"{'='*60}\n")

    # Step 1: Ingest public source feeds.
    articles_count = 0
    if not skip_ingest:
        print("[FEED] Step 1/7: Ingesting feeds...")
        articles = ingest(date_str=date, force=force)
        articles_count = len(articles) if articles else 0
    else:
        print("[SKIP]  Step 1/7: Skipping ingestion (--skip-ingest)")
        raw_file = DATA_RAW_DIR / f"articles_{date}.json"
        if raw_file.exists():
            with open(raw_file, encoding="utf-8") as f:
                articles_count = len(json.load(f))
        else:
            raise FileNotFoundError(f"No cached raw articles are available for {date}: {raw_file}")

    # Step 2: Cluster
    print(f"\n[LINK] Step 2/7: Clustering stories...")
    cluster_run(date)
    clusters_count = 0
    clustered_file = DATA_CLUSTERED_DIR / f"stories_{date}.json"
    if clustered_file.exists():
        with open(clustered_file, encoding="utf-8") as f:
            clusters_count = len(json.load(f))

    # Step 3: Rank
    print(f"\n[RANK] Step 3/7: Ranking stories...")
    main_stories, quick_stories = rank_run(date)

    # Step 4: Synthesize
    print(f"\n[AI] Step 4/7: Synthesizing in English...")
    synthesis = synthesize_run(date)
    if not synthesis:
        raise RuntimeError(f"AI synthesis did not produce an English edition for {date}.")

    # Step 5: A complete edition includes its three-host audio episode.
    print(f"\n[AUDIO]  Step 5/7: Generating podcast...")
    audio_path = podcast_run(date)
    if not audio_path or not Path(audio_path).is_file() or Path(audio_path).stat().st_size <= 1024:
        raise RuntimeError(f"Podcast generation did not produce a playable MP3 for {date}.")
    has_audio = True

    # Step 6: Generate post
    print(f"\n[WRITE] Step 6/7: Generating Hugo post...")
    post_result = generate_post(date, has_audio=has_audio)
    if not post_result:
        raise RuntimeError(f"Hugo post generation failed for {date}.")
    post_file, real_main, real_quick = post_result

    # Step 7: Stats, trends & weekly buffer
    print(f"\n[STATS] Step 7/7: Generating stats & trends...")
    tag_counts = _count_tags(main_stories, quick_stories)
    generate_daily_stats(
        date,
        articles_count=articles_count,
        clusters_count=clusters_count,
        main_count=real_main,
        quick_count=real_quick,
        tag_counts=tag_counts,
    )
    generate_trend_data(date, tag_counts)
    save_weekly_buffer(date, main_stories, quick_stories)

    # Weekly summary (Fridays only)
    _try_weekly(date)

    # Rebuild site-level totals after the daily and optional weekly posts exist.
    generate_publication_stats()

    # Rebuild the English RSS feed while retaining stable episode URLs/GUIDs.
    podcast_feed_run()

    _set_github_output("ran", "true")

    print(f"\n{'='*60}")
    print(f"[OK] Pipeline complete! Post: {post_file}")
    print(f"{'='*60}")


def _count_tags(main_stories, quick_stories):
    """Count tag occurrences across stories for trend tracking."""
    from generate_post import _ENTITY_PATTERNS
    tag_counts = {}
    for story in main_stories + quick_stories:
        text = f"{story.get('title', '')} {story.get('summary', '')}"
        for pattern, tag in _ENTITY_PATTERNS:
            if pattern.search(text):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return tag_counts


def _try_weekly(date):
    """Attempt weekly summary generation (Fridays only, with own idempotency)."""
    try:
        print(f"\n[DATE] Checking weekly summary...")
        weekly_run(date)
    except Exception as e:
        print(f"[WARN]  Weekly summary failed (non-blocking): {e}")


def _try_podcast_feed():
    """Compatibility wrapper retained for callers from earlier pipeline versions."""
    print(f"\n[FEED] Generating podcast RSS feed...")
    podcast_feed_run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Decode the Stack English publishing pipeline")
    parser.add_argument("--date", help="Date to process (YYYY-MM-DD)", default=None)
    parser.add_argument("--skip-ingest", action="store_true", help="Skip feed ingestion")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if post exists")
    args = parser.parse_args()

    run_pipeline(date_str=args.date, skip_ingest=args.skip_ingest, force=args.force)
