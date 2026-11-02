# Decode the Stack

The daily tech briefing for software professionals.

Decode the Stack is the English-language sister publication to
[Decodifica.Tech](https://decodifica.tech/). It covers software engineering,
cloud, DevOps & SRE, AI/ML, and security through a contextual, source-linked
daily edition and a separate three-host podcast.

## Live site and hosting

The publication is live at
[`https://decodethestack.com/`](https://decodethestack.com/).
It uses free Cloudflare Pages hosting with Git-connected builds and the
owner-purchased custom domain. No Cloudflare token or hosting secret is stored here.

Cloudflare Pages was selected over GitHub Pages because the authenticated Git
integration provided the free branded root address without a project-path
prefix. GitHub remains the source and CI host. Audio is encoded below Pages'
25 MiB per-file limit, with a 24 MiB safety target; larger future media would
require a separate hosting decision rather than silently breaking deployment.

The original `decodethestack.pages.dev` address remains available. Spotify's
feed evaluator rejected that feed domain but accepted the identical XML at
`decodethestack.com`, reaching ownership verification. This does not establish
a blanket restriction on all `pages.dev` addresses. The canonical podcast feed
is `https://decodethestack.com/podcast/feed.xml`; its public owner/contact alias
is `podcast@decodethestack.com`, routed through Cloudflare Email Routing.
The November 2 episode retains its original `pages.dev` enclosure and GUID to
preserve identity; new episodes use the custom domain. Keep that legacy audio
URL available. Existing spoken audio is unchanged.

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

The hosts retain the original names **Anna, Maria, and Pedro**, all speaking
English. `OPENAI_TTS_VOICE_PEDRO` configures Pedro's primary voice; the Edge
fallback uses en-US-AriaNeural, en-US-JennyNeural, and en-US-GuyNeural.
Podcast generation requests structured JSON turns with explicit speaker names,
then validates every turn before audio synthesis. Unattributed narration,
unknown hosts, missing hosts, or invalid section lengths block publication;
they are never silently dropped or assigned a guessed speaker.
Each section has at most four generation attempts, with measured word-count
feedback and the rejected draft supplied for revision. Accepted sections are
saved atomically in `data/podcast_sections_YYYY-MM-DD.json` and revalidated on
resume. A source or duration change invalidates that checkpoint. Failed-run
recovery artifacts include these files, so they can be restored before retrying.
The shared background track is bundled at `static/podcast/music/bgmusic.mp3`,
copied byte-for-byte from Decodifica.Tech's existing track (original commit
`3dd1395`, recorded there as CC0/Pixabay). It loops under the complete episode
with a 3-second fade-in and 5-second fade-out. The source track's quiet opening
was almost inaudible with the original fixed -20 dB attenuation, so music
dynamics are now compressed at -24 dBFS (4:1) and normalized to -28 dBFS before
looping and fades. This keeps the bed roughly 8 dB below the normalized speech
instead of over 20 dB below speech during the opening.
Speech and music receive the same final gain when needed to reserve 1 dB of
sample headroom. Website players use a content-hash query to refresh remixes;
the podcast RSS enclosure URL and episode GUID stay unchanged.
Missing or invalid background music now fails publication
instead of silently producing a dry episode. The Portuguese spoken jingle is
not copied into the English show.

The only production scheduler is the secure workflow in the
`ricmmartins/decodifica.tech` repository, which runs at 12:00 and 12:45 UTC.
This repository's GitHub Actions workflow runs tests and a Hugo build on pushes
and pull requests only; it does not generate editions or deploy to Pages.
Cloudflare Git integration is the deployment path.

The first complete publication was generated on 2 November 2026 using Azure
OpenAI and the complete three-host Edge TTS fallback: 2,335 spoken words,
15:41 of audio. The validated runner artifact was published through local
authenticated Git after the orchestrator's existing fine-grained PAT returned
HTTP 403 on push. The owner subsequently corrected repository authorization;
the orchestrator's site-only run `41450443349` verified write access without
regenerating analysis or audio. The orchestrator now checks
actual write access before spending on generation; API `permissions.push`
alone is not sufficient proof. No token values were copied into this repository.

The same episode was corrected from its saved dialogue to restore Pedro's name
and add the original music bed: 2,342 spoken words and 15:45 of complete English
Edge TTS audio. No source collection, contextual synthesis, or language-model
script generation was repeated; its enclosure URL and GUID remain unchanged.

## Site features

The Hugo site includes a searchable archive, dedicated category pages for
Cloud, AI/ML, DevOps & SRE, Software Engineering, and Security, tag browsing,
publication statistics, site and podcast RSS feeds, JSON-LD metadata, and a
progressive web app with offline page caching. Topic pages remain available
when their published-edition count is zero.

Corrections and suggestions can be sent through the repository's issue tracker.
The podcast is also listed on [Spotify](https://open.spotify.com/show/0wAKdLX0HpJF1qfAj2Yiea).

## Local checks

Install Python 3.12+, the dependencies in `pipeline/requirements.txt`, and
Hugo Extended 0.160.1. Unit tests are offline and do not call AI providers:

```powershell
python -m unittest discover -s pipeline -p "test_*.py"
hugo --minify --cleanDestinationDir --destination public --baseURL https://decodethestack.com/
python pipeline/validate_site.py public
```

To run the full publishing pipeline locally, provide the configured AI and
TTS credentials through environment variables, then run:

```powershell
python pipeline/run_pipeline.py
```

Use `--force` to regenerate the current UTC day's edition. `--skip-ingest` is
for runs with an existing cached feed collection only.

After a recovered analysis-only failure, `--force --reuse-synthesis` resumes
from the dated synthesis and its raw, clustered, and ranked JSON files without
calling ingestion or contextual synthesis again. Missing recovery inputs fail
explicitly. Podcast dialogue is generated in bounded, source-grounded sections
and must total 2200–2400 spoken words for the default 15-minute target.

To regenerate only audio and music from an existing, validated saved dialogue:

```powershell
python pipeline/run_pipeline.py --date 2026-11-02 --force --reuse-synthesis --reuse-podcast-script
```

This fails if the saved script is missing, malformed, or too short; it does not
silently call a language model. FFmpeg and ffprobe must be on `PATH` for audio.
With `OPENAI_KEY` absent, recovery uses the complete free Edge TTS path.

For a bounded voice audition only, run `python pipeline/create_voice_preview.py`.
It creates `static/podcast/previews/naturalness-sample.mp3`, never an RSS item.
The six-turn English sample keeps Aria/Jenny/Guy as Anna/Maria/Pedro, changes
Edge speed from +8% to +0%, uses shorter conversational turns, and trims only
quiet boundary padding below -55 dBFS while retaining 120/180 ms margins.
These audition settings do not change the full episode or production defaults.
Edge receives text and rate, not the OpenAI vocal-direction instructions;
this sample cannot promise equivalent expressive control.

The 3000 × 3000 RGB podcast cover is
`static/images/podcast-cover.png`; regenerate it with
`python pipeline/generate_podcast_cover.py`.

## Editorial review skill

The project includes [Humanizer](https://github.com/blader/humanizer) v3.1.0 at
`.github/skills/humanizer/`, pinned to upstream commit
`0ef9fe5bc3572734fd3ae6c448fe00a30cd5dcf0`. `SKILL.md` and the MIT `LICENSE`
are unmodified upstream copies.

The initial review covered fixed public pages and interface copy, preserving
page structure, facts, links, metadata, and the chosen brand slogans. Historical
editions, audio, and feeds were excluded from that initial review.

Every newly generated daily or weekly post now passes a mandatory editorial
step before it is written. The step loads the entire pinned `SKILL.md`, calls
the configured LLM provider chain to revise prose, and makes a second LLM call
to check preservation of meaning, named entities, attribution, and claims.
Metadata, headings, links, source credits, numbers, quotations, code, HTML,
and functional structure are protected. Failures block publication without
falling back to the unreviewed original. This adds two LLM requests per post
(provider failures may trigger the existing fallback chain), with the
associated token cost.

Successful reviews write content-hash receipts under `data/humanizer/`.
Hugo itself and the offline site validator reject new or modified posts
without a matching receipt, including manual additions and direct builds.
The single existing edition is exempt only at its recorded, unchanged hash;
it has not been retrospectively reviewed. Source changes can deliberately
change these gates: receipts are audit records, not signed attestations.

Visible editorial text must not contain em or en dashes. Before review, the
writer normalizes numeric ranges to `to` and prose separators to colons,
including displayed source titles and metadata. The final review, Python
validator, and direct Hugo build reject remaining visible dashes. Code,
commands, HTML attributes, and URL targets are excluded. Headings and links
keep their structure. The November 2 historical edition received only five
punctuation-only line edits under this policy, and its exact legacy hash was
updated accordingly; this was not a retrospective Humanizer review.

Humanizer is an editorial aid, not a fact-checker or a guarantee of human
authorship. Deterministic preservation checks and the second model pass reduce
the risk of changed meaning but cannot prove every factual claim.
