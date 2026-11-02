# Decode the Stack

The daily tech briefing for software professionals.

Decode the Stack is an English-language, source-linked briefing about software
engineering, cloud, AI, security, and operations. Its small daily pipeline reads
public RSS/Atom feeds, keeps recent items, and publishes the original headline,
publisher-provided description, and a direct source link. It does not invent
reporting or claim that feed excerpts are independently verified.

## Live site and hosting decision

The launch address is
[`https://ricardomartins.com.br/decode-the-stack/`](https://ricardomartins.com.br/decode-the-stack/).
GitHub Pages was selected over Cloudflare Pages because the authenticated
GitHub account can create and deploy this repository, while no independent
Cloudflare authorization is available for this project. Pages redirects its
`ricmmartins.github.io` project address to the account's already-configured
custom Pages domain. That existing domain configuration was not changed and no
domain was purchased for this launch. The deployment uses GitHub Actions and
the official Pages artifact workflow; it needs no Cloudflare token.

The site URL includes the repository path. Hugo's `baseURL`, navigation,
canonical metadata, search index, images, and feeds are configured to preserve
that path.

## Daily publishing

GitHub Actions runs `pipeline/publish.py` once a day and can also be started
manually. The generator:

1. Fetches the public feeds listed in `pipeline/sources.json`.
2. Selects up to 12 recent, dated items across engineering, cloud, DevOps,
   security, and AI sources.
3. Writes a dated English edition with the original title, a cleaned excerpt
   supplied by the publisher, and a direct link to each source.
4. Commits a new edition only when the day has not already been published.
5. Builds the static site and deploys it to GitHub Pages.

No model API, account secret, or paid service is required. Failed individual
feeds are reported in the workflow log; if no feed can be fetched, the
publication step fails instead of producing an empty or success-shaped issue.

## Podcast

Decode the Stack has a distinct podcast identity and a dedicated
[`/podcast/`](https://ricardomartins.com.br/decode-the-stack/podcast/) page.
There are no English episodes or audio files at launch, so the page says so
clearly and the podcast RSS feed contains no fabricated episode. The feed is
available at `/podcast/feed.xml` for future use; the site RSS at `/index.xml`
already carries the written editions. This launch does not claim Spotify
distribution or reuse the Portuguese show's feed or audio.

## Local preview

Install [Hugo Extended](https://gohugo.io/installation/) and Python 3.11+:

```powershell
python pipeline\publish.py
hugo --minify
hugo server
```

The optional `--date` argument is intended for local checks. Production uses
the current UTC date. The feed parser and edition generator have offline unit
tests:

```powershell
python -m unittest discover -s pipeline -p "test_*.py"
```

The podcast cover is a 3000 × 3000 RGB PNG at
`static/images/podcast-cover.png`; regenerate it with
`python pipeline\generate_podcast_cover.py` after installing Pillow.

## Repository setup

Enable GitHub Pages with **GitHub Actions** as the build and deployment source.
The included `.github/workflows/publish.yml` builds and deploys the site on
every push to `main` and on its daily schedule. No repository secrets are
required.
