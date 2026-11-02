"""
TechBlog — Story Clustering & Deduplication
Groups articles covering the same story using TF-IDF similarity.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

PROJECT_DIR = Path(__file__).parent.parent
DATA_RAW_DIR = PROJECT_DIR / "data" / "raw"
DATA_CLUSTERED_DIR = PROJECT_DIR / "data" / "clustered"

SIMILARITY_THRESHOLD = 0.35


def load_articles(date_str=None):
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = DATA_RAW_DIR / f"articles_{date_str}.json"
    if not filepath.exists():
        print(f"[FAIL] No articles found for {date_str}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def cluster_articles(articles):
    """Group articles about the same story using TF-IDF cosine similarity."""
    if not articles:
        return []

    texts = [f"{a['title']} {a.get('summary', '')}" for a in articles]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(texts)
    sim_matrix = cosine_similarity(tfidf_matrix)

    # Union-Find clustering
    n = len(articles)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] >= SIMILARITY_THRESHOLD:
                union(i, j)

    # Group by cluster
    clusters = {}
    for i in range(n):
        root = find(i)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(i)

    # Build story objects
    stories = []
    for indices in clusters.values():
        cluster_articles_list = [articles[i] for i in indices]

        # Pick the best representative (tier 1 > tier 2, longest summary)
        best = sorted(
            cluster_articles_list,
            key=lambda a: (a.get("tier", 2), -len(a.get("summary", ""))),
        )[0]  # lowest tier number = highest priority

        story = {
            "id": best["id"],
            "title": best["title"],
            "url": best["url"],
            "summary": best["summary"],
            "category": best["category"],
            "source_name": best["source_name"],
            "published": best["published"],
            "coverage_count": len(cluster_articles_list),
            "sources": [
                {"name": a["source_name"], "url": a["url"]}
                for a in cluster_articles_list
            ],
        }
        stories.append(story)

    stories.sort(key=lambda s: -s["coverage_count"])
    return stories


def run(date_str=None):
    articles = load_articles(date_str)
    if not articles:
        return []

    print(f"[LINK] Clustering {len(articles)} articles...")
    stories = cluster_articles(articles)
    print(f"[BOX] Clustered into {len(stories)} unique stories")

    DATA_CLUSTERED_DIR.mkdir(parents=True, exist_ok=True)
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = DATA_CLUSTERED_DIR / f"stories_{date}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)

    print(f"[SAVE] Saved {len(stories)} stories to {output_file}")
    return stories


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run(date)
