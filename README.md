# Decode the Stack

The daily tech briefing for software professionals.

Decode the Stack is the English-language sister publication to
[Decodifica.Tech](https://decodifica.tech/). It covers software engineering,
cloud, DevOps & SRE, AI/ML, and security through a contextual, source-linked
daily edition and a separate three-host podcast.

## Live site and hosting

The publication is live at
[`https://decodethestack.pages.dev/`](https://decodethestack.pages.dev/).
It uses the free Cloudflare Pages `pages.dev` address with Git-connected builds;
no paid domain, Cloudflare token, or hosting secret is stored here.

## Editorial pipeline

The full Python pipeline is in `pipeline/` and reuses the Portuguese
publication's curated source list, ingestion, clustering, ranking,
two-pass contextual synthesis, weekly ranking, statistics, and podcast
generation logic with English prompts and voices:

1. Ingest recent public feeds from `pipeline/sources.yaml`, with category
   recency windows and deduplication.
2. Cluster overlapping coverage with TF-IDF and cosine similarity.
3. Rank stories using source authority, coverage, relevance, category balance,
   and recency; retain the main-story and Quick Reads distinction.
4. Synthesize contextual English analysis in separate main-story and
   Quick Reads passes. The provider chain is OpenAI, Groq, then Azure OpenAI;
   the configured provider and model are logged at runtime. If all providers
   fail, the pipeline stops instead of publishing a headline-only fallback.
5. Generate a three-host English dialogue and audio, update the Friday weekly
   story buffer, public statistics and trends, then rebuild the RSS feed.

OpenAI TTS (`gpt-4o-mini-tts`, Marin/Sage/Ash) is primary; Edge TTS is the
fallback. The script target is about 15 minutes. Provider credentials remain
on the authenticated original publishing runner and are not copied into this
repository.

The only production scheduler is the secure workflow in the
`ricmmartins/decodifica.tech` repository, which runs at 12:00 and 12:45 UTC.
This repository's GitHub Actions workflow runs tests and a Hugo build on pushes
and pull requests only; it does not generate editions or deploy to Pages.
Cloudflare Git integration is the deployment path.

## Site features

The Hugo site includes a searchable archive, dedicated category pages for
Cloud, AI/ML, DevOps & SRE, Software Engineering, and Security, tag browsing,
publication statistics, site and podcast RSS feeds, JSON-LD metadata, and a
progressive web app with offline page caching. Topic pages remain available
when their published-edition count is zero.

Comments are not enabled: the English repository still needs a separate
Giscus app installation. A podcast-directory listing link can be added once
its official URL is available.

## Local checks

Install Python 3.12+, the dependencies in `pipeline/requirements.txt`, and
Hugo Extended 0.160.1. Unit tests are offline and do not call AI providers:

```powershell
python -m unittest discover -s pipeline -p "test_*.py"
hugo --minify --cleanDestinationDir --destination public --baseURL https://decodethestack.pages.dev/
python pipeline/validate_site.py public
```

To run the full publishing pipeline locally, provide the configured AI and
TTS credentials through environment variables, then run:

```powershell
python pipeline/run_pipeline.py
```

Use `--force` to regenerate the current UTC day's edition. `--skip-ingest` is
for runs with an existing cached feed collection only.

The 3000 × 3000 RGB podcast cover is
`static/images/podcast-cover.png`; regenerate it with
`python pipeline/generate_podcast_cover.py`.
