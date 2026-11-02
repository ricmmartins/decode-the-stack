---
title: "About Decode the Stack: Your Daily Technology Briefing"
description: "Meet Decode the Stack: an automated pipeline that collects, filters, and synthesizes reporting from curated international cloud, AI, DevOps, security, and software engineering feeds into a daily briefing."
date: 2026-11-02T00:00:00Z
ShowToc: true
TocOpen: false
---

## What is Decode the Stack?

**Decode the Stack** is your daily technology briefing.

Our automated pipeline collects and filters stories from [{{< source-count >}} feeds](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml), then writes a morning briefing. It runs at 07:00 EST (08:00 EDT during daylight saving time), with a backup 45 minutes later.

## How it works

[**{{< source-count >}} RSS feeds**](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml) → Collection → Clustering → Ranking → AI synthesis → Podcast → **Post on the site**

1. **Collection:** The pipeline fetches recent articles from [**{{< source-count >}} international feeds**](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml), including engineering blogs, news outlets, and industry experts. Recency windows vary by source and category.
2. **Clustering:** When 20 sites cover the same news, the pipeline groups them into one story with the best source. TF-IDF and cosine similarity identify duplicate coverage.
3. **Ranking:** Each story receives a score based on source authority, coverage (how many sites reported it), content quality, and recency. The main-story threshold is 20 and the Quick Reads threshold is 10. Category balance and minimum/maximum selection limits also affect the selection. The number of stories varies with the day's reporting and its quality.
4. **Synthesis:** The pipeline tries configured OpenAI, Groq, and Azure OpenAI providers in that order to write an English post with context and implications. Availability depends on each provider's access and quota. The pipeline writes from those sources rather than translating the Portuguese edition.
5. **Podcast:** The pipeline writes a dialogue for Anna, Maria, and Pedro, then attempts OpenAI text-to-speech, with Edge TTS as a fallback. The hosts talk casually, like friends discussing tech at a bar. A player appears at the top of each daily post.
6. **Publication:** The scheduled pipeline generates and publishes the post and audio automatically.

## Who is it for?

Technology professionals: **developers, sysadmins, DevOps practitioners, security engineers, cloud engineers, and tech leads**.

## Why?

There is plenty of technology coverage. Finding useful stories among it takes time.

Every day, 20 outlets cover the same story in 20 different ways. Important developments can get buried under that repetition.

Decode the Stack reduces the noise by filtering that coverage, with the aim of saving you 30+ minutes of morning reading.

## Technology stack

| Component | Technology |
|-----------|------------|
| Data pipeline | Python 3.12 (feedparser, scikit-learn, python-dateutil) |
| Clustering | TF-IDF + cosine similarity + Union-Find |
| AI synthesis | OpenAI, Groq, and Azure OpenAI fallback providers |
| Podcast (TTS) | OpenAI text-to-speech (Marin, Sage, Ash); Edge fallback (en-US-AriaNeural, en-US-JennyNeural, en-US-GuyNeural) |
| Branding | Logo and podcast cover generated with Pillow |
| Site generator | Hugo Extended with custom templates adapted from PaperMod |
| Hosting | Cloudflare Pages, at decodethestack.com |
| CI/CD | GitHub Actions (daily publishing at 07:00 EST / 08:00 EDT; backup at 07:45 EST / 08:45 EDT); English repository CI tests and builds |

## Sources

We cover [**{{< source-count >}} international technology feeds**](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml):

- **Engineering ({{< source-count category="dev" >}} feeds):** Netflix, Airbnb, Spotify, Stripe, Cloudflare, GitHub, Meta, Google, Microsoft, Visual Studio, PowerShell, GitHub Blog, Discord, Shopify, Slack, Dropbox, Databricks, PayPal, eBay, NVIDIA, Jane Street, Tailscale, PostHog, Palantir, Zapier, Squarespace, Thoughtbot, Evil Martians, Martin Fowler, Julia Evans, Dan Luu, Paul Graham, Bryan Cantrill, Guido van Rossum, and many more
- **Cloud:** AWS, Azure, Vercel, Supabase, HashiCorp, Fly.io, Render, PlanetScale, Cloudinary, Akamai, Fastly
- **DevOps/SRE:** Kubernetes, Docker, CNCF, Azure DevOps, Grafana, GitLab, Brendan Gregg, SRE Weekly, Charity Majors, Prometheus, Pulumi
- **Security:** Krebs on Security, Schneier on Security, Troy Hunt, Google Project Zero, The Hacker News, Cloudflare Security, Microsoft Security (MSRC), Google Security, Mozilla Security, PortSwigger, Filippo Valsorda
- **AI/ML:** OpenAI, Anthropic, DeepMind, Hugging Face, LangChain, Google AI, Microsoft AI, Apple Machine Learning, Mistral, Chip Huyen, Lilian Weng, Simon Willison
- **News:** Hacker News, Ars Technica, TechCrunch, InfoQ, The New Stack, The Verge, Lobsters, TLDR, Wired

The complete catalogue is maintained in [pipeline/sources.yaml](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml).

## Daily post format

Each post contains:

- **Main stories:** Analysis in 2 to 3 paragraphs, grouped by category (Engineering, Cloud, DevOps, Security, AI/ML). Selection uses a score threshold of 20, category balance, and selection limits.
- **Quick Reads:** Summaries of secondary stories in 1 to 2 sentences, using a score threshold of 10.
- **Audio podcast:** A relaxed English conversation between Anna, Maria, and Pedro, approximately 15 minutes long.
- **Smart tags:** Automatically extracted technologies, companies, and products for browsing by topic.
- **Related editions:** Posts that share tags and categories, listed at the end of each post.
- **Original source links:** Attribution and links to the original reporting.

## Site features

- **Search:** Full-text search across published posts using custom JavaScript.
- **Archive:** All posts organized chronologically.
- **Statistics:** A public dashboard with pipeline figures (sources, articles, clusters).
- **Weekly briefing:** A re-ranked Top 10 of the week, published every Friday.
- **PWA:** Install the site as an app and access cached pages offline.
- **SEO:** JSON-LD (Article/WebSite), Open Graph, sitemap, and robots.txt.
- **RSS:** A full feed at `/index.xml`.
- **Categories and tags:** Browse by topic and technology.

## Contact

Have suggestions, feedback, or want to contribute?

📧 [Send an email](mailto:podcast@decodethestack.com)

For corrections or suggestions, open an issue in the [Decode the Stack repository](https://github.com/ricmmartins/decode-the-stack/issues).

---

*Decode the Stack: Decoding the tech that matters.*
