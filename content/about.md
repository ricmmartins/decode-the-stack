---
title: "About Decode the Stack — Your Daily Technology Briefing"
description: "Meet Decode the Stack: an automated pipeline that collects, filters, and synthesizes reporting from 242 international cloud, AI, DevOps, security, and software engineering feeds into a daily briefing."
date: 2026-11-02T00:00:00Z
ShowToc: true
TocOpen: false
---

## What is Decode the Stack?

**Decode the Stack** is your daily technology briefing.

Every morning (scheduled for 09:00 Brasília time, with a backup at 09:45), our automated pipeline collects, filters, and synthesizes the most relevant technology stories — so you don't have to read 242 feeds.

## How it works

**242 RSS feeds** → Collection → Clustering → Ranking → AI synthesis → Podcast → **Post on the site**

1. **Collection** — Fetches recent articles from **242 international feeds**: leading engineering blogs, news outlets, and industry experts. Recency windows vary by source and category.
2. **Clustering** — If 20 sites cover the same news, it becomes one story with the best source. A clustering algorithm (TF-IDF + cosine similarity) automatically removes duplicate coverage.
3. **Ranking** — Dynamic, score-based selection. Each story receives a score based on source authority, coverage (how many sites reported it), content quality, and recency. The main-story threshold is 20 and the Quick Reads threshold is 10, with category balance and minimum/maximum selection limits. Busy days bring more stories; quieter days bring fewer — without padding the edition with weak content.
4. **Synthesis** — AI, using OpenAI, Groq, and Azure OpenAI fallback providers, turns the top stories into a well-written, natural English post. This is not a translation — it is synthesis with context and implications.
5. **Podcast** — A dialogue between three hosts (Anna, Maria, and Pedro) is generated automatically and converted into English audio using OpenAI text-to-speech, with Edge TTS as a fallback. The tone is relaxed and fun — like friends talking tech at a bar. A player appears at the top of each daily post.
6. **Publication** — The post and audio are generated and published automatically through the scheduled pipeline.

## Who is it for?

Technology professionals: **developers, sysadmins, DevOps practitioners, security engineers, cloud engineers, and tech leads**.

## Why?

The technology world does not have a content *supply* problem. It has a **filtering** problem.

Every day, the same story gets covered in 20 different ways by 20 different outlets. Meanwhile, genuinely important signals get buried.

**More content doesn't help. Better filtering does.**

Instead of adding noise, Decode the Stack **reduces the noise**. The aim is to save you 30+ minutes of morning reading.

## Technology stack

| Component | Technology |
|-----------|------------|
| Data pipeline | Python 3.12 (feedparser, scikit-learn, python-dateutil) |
| Clustering | TF-IDF + cosine similarity + Union-Find |
| AI synthesis | OpenAI, Groq, and Azure OpenAI fallback providers |
| Podcast (TTS) | OpenAI text-to-speech (Marin, Sage, Ash); Edge fallback (en-US-AriaNeural, en-US-JennyNeural, en-US-GuyNeural) |
| Branding | Logo and podcast cover generated with Pillow |
| Site generator | Hugo Extended with custom templates adapted from PaperMod |
| Hosting | Cloudflare Pages, on the free pages.dev address |
| CI/CD | GitHub Actions (daily publishing at 09:00 Brasília time; backup at 09:45); English repository CI tests and builds |
| Comments | Giscus (GitHub Discussions), prepared but currently disabled |

## Sources

We cover **242 international technology feeds**:

- **Engineering (172 feeds):** Netflix, Airbnb, Spotify, Stripe, Cloudflare, GitHub, Meta, Google, Microsoft, Visual Studio, PowerShell, GitHub Blog, Discord, Shopify, Slack, Dropbox, Databricks, PayPal, eBay, NVIDIA, Jane Street, Tailscale, PostHog, Palantir, Zapier, Squarespace, Thoughtbot, Evil Martians, Martin Fowler, Julia Evans, Dan Luu, Paul Graham, Bryan Cantrill, Guido van Rossum, and many more
- **Cloud:** AWS, Azure, Vercel, Supabase, HashiCorp, Fly.io, Render, PlanetScale, Cloudinary, Akamai, Fastly
- **DevOps/SRE:** Kubernetes, Docker, CNCF, Azure DevOps, Grafana, GitLab, Brendan Gregg, SRE Weekly, Charity Majors, Prometheus, Pulumi
- **Security:** Krebs on Security, Schneier on Security, Troy Hunt, Google Project Zero, The Hacker News, Cloudflare Security, Microsoft Security (MSRC), Google Security, Mozilla Security, PortSwigger, Filippo Valsorda
- **AI/ML:** OpenAI, Anthropic, DeepMind, Hugging Face, LangChain, Google AI, Microsoft AI, Apple Machine Learning, Mistral, Chip Huyen, Lilian Weng, Simon Willison
- **News:** Hacker News, Ars Technica, TechCrunch, InfoQ, The New Stack, The Verge, Lobsters, TLDR, Wired

The complete catalogue is maintained in [pipeline/sources.yaml](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml).

## Daily post format

Each post contains:

- **Main stories** (a dynamic selection using a score threshold of 20, category balance, and selection limits) — in-depth synthesis in 2–3 paragraphs, grouped by category (Engineering, Cloud, DevOps, Security, AI/ML)
- **Quick Reads** (score threshold of 10) — 1–2 sentence summaries of secondary stories
- **Audio podcast** — a relaxed English conversation between three hosts (Anna, Maria, and Pedro), approximately 15 minutes long
- **Smart tags** — automatically extracted entities (technologies, companies, products) for browsing by topic
- **Related editions** — posts connected by tags and categories at the end of each post
- **Original source links** — always with attribution

## Site features

- **Search** — full-text search across published posts using custom JavaScript
- **Archive** — all posts organized chronologically
- **Statistics** — a public dashboard with pipeline figures (sources, articles, clusters)
- **Weekly briefing** — every Friday, a re-ranked Top 10 of the week
- **Comments** — Giscus (GitHub Discussions) integration is prepared but not currently enabled
- **PWA** — install the site as an app and access cached pages offline
- **SEO** — JSON-LD (Article/WebSite), Open Graph, sitemap, robots.txt
- **RSS** — a full feed at `/index.xml`
- **Categories and tags** — browse by topic and technology

## Contact

Have suggestions, feedback, or want to contribute?

📧 [Send an email](mailto:rmmartins@outlook.com)

You can also open an issue in the [Decode the Stack repository](https://github.com/ricmmartins/decode-the-stack/issues). Comments on posts are not currently enabled; the prepared [Giscus](https://giscus.app/) integration connects comments to GitHub Discussions and requires a GitHub account when enabled.

---

*Decode the Stack — Decoding the tech that matters.*
