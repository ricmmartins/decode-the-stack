# Decode the Stack

The daily tech briefing for software professionals.

Decode the Stack is an English-language, source-linked briefing about software
engineering, cloud, AI, security, and operations. Its small daily pipeline reads
public RSS/Atom feeds, keeps recent items, and publishes the original headline,
publisher-provided description, and a direct source link. It does not invent
reporting or claim that feed excerpts are independently verified.

## Live site and hosting decision

The free branded address is
[`https://decodethestack.pages.dev/`](https://decodethestack.pages.dev/).
The project uses Cloudflare Pages' free `pages.dev` address and Git-connected
builds. No paid domain or Cloudflare credentials are stored in this repository.

## Daily publishing

GitHub Actions runs `pipeline/publish.py` once a day and can also be started
manually. The generator:

1. Fetches the public feeds listed in `pipeline/sources.json`.
2. Selects up to 12 recent, dated items across engineering, cloud, DevOps,
   security, and AI sources.
3. Writes a dated English edition with the original title, a cleaned excerpt
   supplied by the publisher, and a direct link to each source.
4. Commits a new edition only when the day has not already been published.
5. Recalculates publication statistics and validates the static site; the
   resulting Git commit triggers the Cloudflare Pages build.

No model API key or paid service is required for the daily edition or audio.
Voice synthesis uses Microsoft Edge TTS's network service with no API key.
Failed individual feeds are reported in the workflow log; if no feed can be
fetched, the
publication step fails instead of producing an empty or success-shaped issue.

## Podcast

Decode the Stack has a distinct podcast identity and a dedicated
[`/podcast/`](https://decodethestack.pages.dev/podcast/) page.
The first episode is an actual Edge TTS-rendered English headline bulletin.
The podcast RSS feed includes an enclosure only when the corresponding
non-empty MP3 exists. The site RSS at `/index.xml` carries written editions.
This launch does not claim Spotify distribution or reuse the Portuguese show's
feed or audio.

The RSS owner name and email are included for directory verification. No
Spotify or other podcast-directory submission is claimed.

## Local preview

Install [Hugo Extended](https://gohugo.io/installation/) and Python 3.11+:

```powershell
python pipeline\publish.py
python pipeline\podcast.py
hugo --minify --cleanDestinationDir --destination public --baseURL https://decodethestack.pages.dev/
python pipeline\validate_site.py public
hugo server
```

The optional `--date` argument is intended for local checks. Production uses
the current UTC date. The feed parser and edition generator have offline unit
tests:

```powershell
python -m unittest discover -s pipeline -p "test_*.py"
```

The podcast cover is a 3000 × 3000 RGB PNG at
`static/images/podcast-cover.png`; Pillow is included in `requirements.txt` for
regenerating it with `python pipeline\generate_podcast_cover.py`.

## Repository setup

Cloudflare Pages is connected to this public repository's `main` branch. Its
Hugo build uses version `0.160.1`, command
`hugo --minify --destination public --baseURL https://decodethestack.pages.dev/`,
and output directory `public`. The daily GitHub Actions workflow collects new
source items, generates an English headline bulletin when Edge TTS is available,
recalculates the publication statistics, validates the built site, and commits
the edition. That commit triggers the Cloudflare Git integration. The
authorized RSS owner email is stored as a GitHub Actions secret; the English
repository contains no Cloudflare credentials.
