---
title: "About Decode the Stack"
description: "How the daily English technology briefing is gathered, clustered, ranked, synthesized, and published."
date: 2026-11-02T00:00:00Z
ShowToc: true
TocOpen: false
---

## What is Decode the Stack?

**Decode the Stack** is the English-language sister publication to
[Decodifica.Tech](https://decodifica.tech/), built for software professionals
who want useful context without another firehose of headlines. It covers
software engineering, cloud, DevOps and SRE, AI/ML, and security.

Each edition links back to the original reporting. The editorial goal is to
connect verified developments and explain their engineering implications, not
to reproduce publisher articles or invent facts.

## How an edition is made

The English edition uses the same curated-source and editorial pipeline as its
Portuguese counterpart. The source catalogue is maintained in
[`pipeline/sources.yaml`](https://github.com/ricmmartins/decode-the-stack/blob/main/pipeline/sources.yaml).

1. **Collect:** A scheduled UTC job reads the configured public RSS and Atom
   feeds and keeps items within their category-specific recency windows.
2. **Cluster:** URL and title deduplication plus TF-IDF and cosine similarity
   group overlapping coverage into stories while retaining the source links.
3. **Rank:** Source authority, coverage, relevance, category balance, and
   recency determine which stories become the main edition and which remain
   Quick Reads. The selection is score-based; it does not pad a quiet day with
   weak stories.
4. **Synthesize:** The pipeline makes separate contextual English synthesis
   passes for the main stories and Quick Reads. It explains what changed,
   trade-offs, and implications using only the supplied reporting. Provider
   fallback and the model actually selected are logged by each run.
5. **Publish:** Hugo builds the dated article, site RSS, category and tag
   archives, statistics, and the audio episode. A weekly Top 10 is synthesized
   on Fridays from the accumulated story buffer.

The production workflow runs automatically each day. It uses the original
publication's authenticated runner for AI credentials; secret values are not
stored in this public repository.

## AI and editorial safeguards

AI is used for contextual synthesis and podcast-script generation, not as a
source of facts. Each edition keeps links to the original publisher pages, and
the podcast script is grounded in the generated source-linked edition. If the
configured synthesis providers fail, the pipeline stops rather than publishing
a headline-only fallback that would be presented as contextual analysis.

Daily pipeline statistics, source counts, and story trends are computed from
the editions and source configuration actually present in this repository.
They are not estimates of total industry coverage.

## Podcast

The separate English podcast is a three-host dialogue between Anna, Maria,
and Alex. Its target script is approximately 15 minutes. OpenAI text-to-speech
uses the configured Marin, Sage, and Ash voices; Edge TTS is the fallback.
Provider and model selection are reported in the publishing run.

The show has an RSS feed with its own artwork, episode routes, and stable
date-based episode GUIDs. It has **not** been submitted to Spotify or any other
podcast directory; creator-account submission and platform review remain
separate steps.

## Browse the publication

- **Editions** contains the daily briefings and Friday weekly editions.
- **Categories** separates Cloud, AI/ML, DevOps & SRE, Software Engineering,
  and Security. A topic remains browsable when its current edition count is
  zero.
- **Tags** organizes editions by technologies and companies identified in the
  reporting.
- **Archive** offers chronological browsing; **Search** searches article
  titles, descriptions, and body text.
- **Statistics** reports published-edition totals and source/category
  coverage.
- **News RSS** and **Podcast RSS** are separate feeds. The site is also
  installable as a progressive web app and supports offline access to cached
  pages.

## Comments and feedback

Comments are not active yet. The English repository's GitHub Discussions
integration requires a separate Giscus app installation, which is still
pending repository authorization; no broken or Portuguese discussion widget is
embedded in the meantime.

For corrections or suggestions, open an issue in the
[Decode the Stack repository](https://github.com/ricmmartins/decode-the-stack/issues)
and include the edition and original source URLs.

Read our [privacy notice](/privacy/) and [terms of use](/terms/).
