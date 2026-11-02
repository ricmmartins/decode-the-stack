---
title: "About Decode the Stack"
description: "How the daily English technology briefing is gathered, clustered, ranked, synthesized, and published."
date: 2026-11-02T00:00:00Z
ShowToc: true
TocOpen: false
---

## What is Decode the Stack?

**Decode the Stack** is a daily English-language technology briefing for
software professionals. It is the sister publication to
[Decodifica.Tech](https://decodifica.tech/), with a separate English edition,
site identity, RSS feed, and podcast.

The English source catalogue contains 242 curated feeds spanning software
engineering, cloud, DevOps and SRE, security, AI/ML, and technology news. Each
edition links to the original reporting and adds context about the engineering
decisions and trade-offs behind the headlines.

## Who is it for?

The briefing is for software engineers, cloud engineers, SREs, security
practitioners, technical leads, and other professionals who need a reliable
picture of what is changing across the technology industry.

## Why?

Technology does not have a shortage of coverage; it has a filtering problem.
The same development can appear across many publications while useful signals
are easy to miss.

Decode the Stack groups related reporting, selects stories for their relevance
and coverage, and connects the details in one source-linked edition. The aim is
to spend less time sorting through duplicate headlines and more time
understanding what happened and why it matters.

## How it works

The English publication uses the same 242-feed catalogue and core editorial
pipeline as its Portuguese counterpart. The maintained English configuration
is [`pipeline/sources.yaml`](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml).

1. **Collection:** The scheduled pipeline reads public RSS and Atom feeds and
   filters items using category-specific recency windows.
2. **Clustering:** URL and title deduplication, TF-IDF, and cosine similarity
   group overlapping coverage into a single story while preserving the
   original source links.
3. **Ranking:** Source authority, coverage, relevance, category balance, and
   recency determine which stories receive deeper coverage and which appear as
   Quick Reads. Quiet days are not padded with weak stories.
4. **Contextual synthesis:** Separate AI passes write the main analysis and
   Quick Reads in English. This is an original synthesis based on the supplied
   reporting, not a translation of the Portuguese edition.
5. **Podcast:** A three-host English dialogue is generated from the
   source-linked synthesis and converted to audio.
6. **Publication:** Hugo builds the daily article, RSS feeds, topic archives,
   search index, and statistics. A weekly Top 10 is synthesized from the
   accumulated story buffer on Fridays.

Publishing runs on the authenticated workflow in the Decodifica.Tech
repository. AI credentials remain on that runner and are not stored in this
public repository.

## Technology stack

| Component | Technology |
|---|---|
| Feed collection | Python, feedparser, requests, and python-dateutil |
| Clustering | scikit-learn TF-IDF and cosine similarity |
| Contextual synthesis | OpenAI, Groq, and Azure OpenAI fallback providers |
| Podcast audio | OpenAI text-to-speech with Edge TTS fallback |
| Static site | Hugo Extended, HTML, CSS, and JavaScript |
| Hosting | Cloudflare Pages on the free `pages.dev` address |
| CI and publishing | GitHub Actions; the English repository's CI only tests and builds |
| Comments | Giscus is prepared but disabled until the English repository authorizes the app |

No analytics or advertising trackers are added by the English publication.

## Sources

The catalogue contains 242 configured feeds. Examples include:

- **Software engineering:** Netflix Tech Blog, Airbnb Engineering, Spotify
  Engineering, Stripe Engineering, GitHub Engineering, and Shopify Engineering.
- **Cloud:** AWS Blog, Azure Blog, Vercel Blog, HashiCorp Blog, Fly.io, and
  Supabase Blog.
- **DevOps and SRE:** Grafana Blog, Azure DevOps Blog, Kubernetes Blog, Docker
  Blog, CNCF Blog, GitLab Blog, and Brendan Gregg.
- **Security:** Krebs on Security, The Hacker News, Schneier on Security,
  Troy Hunt, Google Project Zero, Cloudflare Security, and Microsoft Security
  (MSRC).
- **AI/ML:** OpenAI Blog, Google AI Blog, Anthropic Blog, Hugging Face Blog,
  DeepMind Blog, Microsoft AI Blog, LangChain Blog, and Simon Willison.
- **Technology news:** Hacker News, Lobsters, Ars Technica, The Verge, TechCrunch,
  InfoQ, The New Stack, and TLDR.

The full, current list and its feed categories are available in
[`pipeline/sources.yaml`](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml).

## Daily edition format

Each daily edition includes:

- **Main stories:** Contextual analysis of the selected reporting, grouped by
  technology category.
- **Quick Reads:** Concise notes on other relevant reports.
- **Source links:** Direct links to the original publishers and the reporting
  behind each story.
- **Tags and related editions:** Topics and entities connect coverage across
  the archive.
- **Podcast episode:** A conversational, three-host English audio edition
  with a target length of about 15 minutes.

The number of main stories and Quick Reads varies with the quality and volume
of available reporting.

## Site features

- **Search:** Search the published editions and their source-linked content.
- **Archive:** Browse daily and Friday weekly editions chronologically.
- **Statistics:** View published-edition totals, source coverage, and topic
  trends derived from the English archive.
- **Weekly briefing:** A Friday Top 10 re-ranks the stories accumulated during
  the week.
- **Categories and tags:** Browse by software engineering, cloud, DevOps & SRE,
  security, AI/ML, and technologies or companies.
- **Related editions:** Discover other posts connected by topics and categories.
- **RSS:** Separate feeds are available for written editions and podcast audio.
- **Progressive web app:** Install the site and access pages cached by the
  service worker while offline.
- **SEO:** Canonical URLs, JSON-LD, Open Graph metadata, sitemap, and robots
  directives are included.

## Podcast hosts

| Host | Style |
|---|---|
| **Anna** | The curious, energetic lead host who guides the show and introduces each story. |
| **Maria** | The technical analyst who adds context, trade-offs, and thoughtful disagreement. |
| **Pedro** | The relaxed co-host who asks listener-focused questions and brings occasional light humor. |

The script targets approximately 15 minutes. OpenAI text-to-speech uses the
configured Marin, Sage, and Ash voices; Edge TTS is the fallback. The selected
provider and model are reported in the publishing run.

## AI and editorial safeguards

AI is used to synthesize context and write the podcast dialogue, not as a
source of facts. Original publisher links remain with each story. The script
is grounded in the source-linked edition, and the pipeline stops if all
configured synthesis providers fail rather than publishing a headline-only
fallback as contextual analysis.

Statistics and source counts describe the English catalogue and archive; they
are not estimates of total technology-industry coverage.

## Comments and feedback

Comments remain disabled while the English repository's separate Giscus app
installation is pending. No broken widget or Portuguese discussion identity is
embedded. A podcast-directory listing link can be added once its official URL
is available.

For corrections or suggestions, open an issue in the
[Decode the Stack repository](https://github.com/ricmmartins/decode-the-stack/issues)
and include the edition and original source URLs.

Read our [privacy notice](/privacy/) and [terms of use](/terms/).
