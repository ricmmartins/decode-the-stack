"""
TechBlog — Hugo Post Generator
Converts synthesis output into a Hugo-compatible markdown post.
"""

import json
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DATA_RANKED_DIR = PROJECT_DIR / "data" / "ranked"
CONTENT_DIR = PROJECT_DIR / "content" / "posts"
SOURCES_FILE = PROJECT_DIR / "pipeline" / "sources.yaml"

import unicodedata

def slugify(text):
    """Convert text to URL-friendly slug."""
    # Normalize unicode and remove accents
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lowercase, replace non-alphanumeric with hyphens
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    # Cap at 80 chars on word boundary
    if len(text) > 80:
        text = text[:77].rsplit("-", 1)[0]
    return text


def get_source_count():
    """Get the total number of configured sources from sources.yaml."""
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = yaml.safe_load(f)
    if not isinstance(sources, dict) or not isinstance(sources.get("sources"), list):
        raise ValueError(f"Invalid source configuration: {SOURCES_FILE}")
    return len(sources["sources"])


def count_main_stories_in_synthesis(content):
    """Count actual story headings before the Quick Reads section."""
    radar_marker = "## Quick Reads"
    main_section = content.split(radar_marker)[0] if radar_marker in content else content
    # Count ### headings (each main story gets a ### heading)
    return len(re.findall(r"^### ", main_section, re.MULTILINE))


def count_radar_items_in_synthesis(content):
    """Count actual bullet items in the Quick Reads section."""
    radar_marker = "## Quick Reads"
    if radar_marker not in content:
        return 0
    radar_section = content.split(radar_marker, 1)[1]
    # Count lines starting with "- " (bullet items)
    return len(re.findall(r"^- ", radar_section, re.MULTILINE))


def build_category_breakdown(content):
    """Extract category headings and count stories per category from synthesis."""
    radar_marker = "## Quick Reads"
    main_section = content.split(radar_marker)[0] if radar_marker in content else content

    # Find all ## category headings and count ### stories under each
    category_re = re.compile(r"^## (.+)$", re.MULTILINE)
    story_re = re.compile(r"^### ", re.MULTILINE)

    categories = category_re.findall(main_section)
    breakdown = []
    for i, cat in enumerate(categories):
        # Get section between this ## and the next ## (or end)
        start = main_section.index(f"## {cat}") + len(f"## {cat}")
        next_cat_match = category_re.search(main_section, start)
        end = next_cat_match.start() if next_cat_match else len(main_section)
        section = main_section[start:end]
        count = len(story_re.findall(section))
        # Strip emoji from category name for the description
        cat_clean = re.sub(r"^[^\w]+", "", cat).strip()
        if count > 0:
            breakdown.append(f"{cat_clean} ({count})")
    return breakdown


def build_dynamic_title(content, stories):
    """Extract the AI-generated headline from the synthesis content.
    
    Looks for 'HEADLINE: ...' line at the start of the synthesis.
    Falls back to top entity tags if no headline found.
    """
    # Try to extract AI-generated headline
    headline_re = re.compile(
        r"^(?:\*{1,2})?HEADLINE:(?:\*{1,2})?\s*(.+)$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = headline_re.search(content)
    if match:
        title = match.group(1).strip().strip('"').strip("'")
        # Cap at 120 chars (allow longer narrative titles)
        if len(title) > 120:
            title = title[:117].rsplit(" ", 1)[0] + "…"
        return title
    
    # Fallback: top entity tags
    tags = extract_entity_tags(stories) if stories else []
    if tags:
        top = tags[:4]
        if len(top) >= 3:
            return f"{', '.join(top[:-1])} and {top[-1]}"
        elif len(top) == 2:
            return f"{top[0]} and {top[1]}"
        return top[0]
    
    return None


def extract_intro_paragraph(content):
    """Extract the natural intro paragraph from the synthesis (before first ## heading)."""
    first_heading = re.search(r"^## ", content, re.MULTILINE)
    if not first_heading:
        return ""
    intro_section = content[:first_heading.start()].strip()
    # Get non-empty lines that aren't blockquotes, metadata, audio, or HTML
    paragraphs = []
    for line in intro_section.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(">") or line.startswith("---") or line.startswith("<"):
            continue
        if line.startswith("[AUDIO]") or "**Listen" in line:
            continue
        if re.match(
            r"^(?:\*{1,2})?HEADLINE:(?:\*{1,2})?",
            line,
            re.IGNORECASE,
        ):
            continue
        if len(line) > 40:  # skip short fragments
            paragraphs.append(line)
    if paragraphs:
        # Return first real paragraph, truncated for SEO (~250 chars)
        intro = paragraphs[0]
        if len(intro) > 260:
            intro = intro[:257].rsplit(" ", 1)[0] + "…"
        return intro
    return ""

WEEKDAYS_EN = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}

# Canonical tech entities: pattern to tag slug
# Patterns are matched case-insensitively against title + summary
# Order matters for overlapping patterns (longer/more specific first)
ENTITY_MAP = {
    # Cloud Providers
    r"\bAWS\b": "aws",
    r"\bAmazon Web Services\b": "aws",
    r"\bAzure\b": "azure",
    r"\bGoogle Cloud\b": "gcp",
    r"\bGCP\b": "gcp",
    r"\bCloudflare\b": "cloudflare",
    r"\bVercel\b": "vercel",
    r"\bDigitalOcean\b": "digitalocean",
    r"\bSupabase\b": "supabase",
    r"\bFly\.io\b": "fly-io",
    r"\bHeroku\b": "heroku",
    r"\bOracle Cloud\b": "oracle-cloud",
    # AI/ML
    r"\bOpenAI\b": "openai",
    r"\bGPT[-\s]?4o?\b": "gpt",
    r"\bGPT[-\s]?5\b": "gpt",
    r"\bChatGPT\b": "chatgpt",
    r"\bClaude\b": "claude",
    r"\bAnthropic\b": "anthropic",
    r"\bGemini\b": "gemini",
    r"\bLlama\b": "llama",
    r"\bMistral\b": "mistral",
    r"\bDeepSeek\b": "deepseek",
    r"\bCopilot\b": "copilot",
    r"\bHugging\s?Face\b": "hugging-face",
    r"\bLangChain\b": "langchain",
    r"\bLLM\b": "llm",
    r"\bRAG\b": "rag",
    r"\bStable Diffusion\b": "stable-diffusion",
    r"\bMidjourney\b": "midjourney",
    r"\bDeepMind\b": "deepmind",
    # Languages & Runtimes
    r"\bRust\b": "rust",
    r"\bGo(?:lang)?\b": "golang",
    r"\bPython\b": "python",
    r"\bTypeScript\b": "typescript",
    r"\bJavaScript\b": "javascript",
    r"\bNode\.?js\b": "nodejs",
    r"\bDeno\b": "deno",
    r"\bBun\b": "bun",
    r"\bJava\b(?!\s*Script)": "java",
    r"\bKotlin\b": "kotlin",
    r"\bSwift\b": "swift",
    r"\bC\+\+\b": "cpp",
    r"\bC#|\.NET|dotnet\b": "dotnet",
    r"\bRuby\b": "ruby",
    r"\bPHP\b": "php",
    r"\bZig\b": "zig",
    r"\bElixir\b": "elixir",
    r"\bWebAssembly\b|WASM\b": "wasm",
    # Frameworks & Libraries
    r"\bReact\b": "react",
    r"\bNext\.?js\b": "nextjs",
    r"\bVue\b": "vue",
    r"\bSvelte\b": "svelte",
    r"\bAngular\b": "angular",
    r"\bDjango\b": "django",
    r"\bFastAPI\b": "fastapi",
    r"\bFlask\b": "flask",
    r"\bSpring\b": "spring",
    r"\bRails\b": "rails",
    r"\bLaravel\b": "laravel",
    r"\bTailwind\b": "tailwind",
    # DevOps & Infra
    r"\bKubernetes\b|(?<!\w)K8s\b": "kubernetes",
    r"\bDocker\b": "docker",
    r"\bTerraform\b": "terraform",
    r"\bAnsible\b": "ansible",
    r"\bPulumi\b": "pulumi",
    r"\bHelm\b": "helm",
    r"\bIstio\b": "istio",
    r"\bEnvoy\b": "envoy",
    r"\bPrometheus\b": "prometheus",
    r"\bGrafana\b": "grafana",
    r"\bArgo\s?CD\b": "argocd",
    r"\bJenkins\b": "jenkins",
    r"\bGitHub Actions\b": "github-actions",
    r"\bGitLab CI\b": "gitlab-ci",
    r"\bCI/CD\b": "cicd",
    r"\bNginx\b|NGINX\b": "nginx",
    r"\bCaddy\b": "caddy",
    # Databases
    r"\bPostgreSQL\b|Postgres\b": "postgresql",
    r"\bMySQL\b": "mysql",
    r"\bRedis\b": "redis",
    r"\bMongoDB\b": "mongodb",
    r"\bSQLite\b": "sqlite",
    r"\bDynamoDB\b": "dynamodb",
    r"\bCassandra\b": "cassandra",
    r"\bElasticsearch\b": "elasticsearch",
    r"\bClickHouse\b": "clickhouse",
    r"\bSurrealDB\b": "surrealdb",
    r"\bDragonfly\b": "dragonfly",
    r"\bValkey\b": "valkey",
    r"\bNeon\b": "neon",
    r"\bPlanetScale\b": "planetscale",
    r"\bTurso\b": "turso",
    # Security
    r"\bCVE[-\s]?\d": "cve",
    r"\bzero[-\s]?day\b": "zero-day",
    r"\bransomware\b": "ransomware",
    r"\bphishing\b": "phishing",
    r"\bOAuth\b": "oauth",
    r"\bSSO\b": "sso",
    r"\bMFA\b|2FA\b": "mfa",
    r"\bZero Trust\b": "zero-trust",
    r"\bSOC\b": "soc",
    r"\bSIEM\b": "siem",
    # Companies / Platforms
    r"\bGitHub\b": "github",
    r"\bGitLab\b": "gitlab",
    r"\bMicrosoft\b": "microsoft",
    r"\bGoogle\b": "google",
    r"\bApple\b": "apple",
    r"\bMeta\b": "meta",
    r"\bNvidia\b|NVIDIA\b": "nvidia",
    r"\bAMD\b": "amd",
    r"\bIntel\b": "intel",
    r"\bNetflix\b": "netflix",
    r"\bUber\b": "uber",
    r"\bStripe\b": "stripe",
    r"\bSpotify\b": "spotify",
    r"\bSlack\b": "slack",
    r"\bLinux\b": "linux",
    r"\bHashiCorp\b": "hashicorp",
    r"\bDatadog\b": "datadog",
    r"\bSnowflake\b": "snowflake",
    r"\bDatabricks\b": "databricks",
    # Concepts
    r"\bmicroservices?\b": "microservices",
    r"\bserverless\b": "serverless",
    r"\bcontainer(?:s|ization)?\b": "containers",
    r"\bAPI\b": "api",
    r"\bGraphQL\b": "graphql",
    r"\bgRPC\b": "grpc",
    r"\bWebSocket\b": "websocket",
    r"\bopen[\s-]?source\b": "open-source",
    r"\bDevEx\b|developer experience\b": "developer-experience",
    r"\bSRE\b": "sre",
    r"\bplatform engineering\b": "platform-engineering",
    r"\beBPF\b": "ebpf",
    r"\bservice mesh\b": "service-mesh",
    r"\binfrastructure as code\b|IaC\b": "iac",
    r"\bobservability\b": "observability",
    r"\bMLOps\b": "mlops",
    r"\bFinOps\b": "finops",
    r"\bDevSecOps\b": "devsecops",
}

# Compile patterns once for performance
_ENTITY_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE), tag)
    for pattern, tag in ENTITY_MAP.items()
]

# Display names for tags that need special casing (acronyms, brands, etc.)
# Tags not listed here use the slug as-is (e.g., "rust" to "rust")
TAG_DISPLAY = {
    "aws": "AWS", "gcp": "GCP", "api": "API", "llm": "LLM", "rag": "RAG",
    "cve": "CVE", "sso": "SSO", "mfa": "MFA", "soc": "SOC", "siem": "SIEM",
    "sre": "SRE", "cicd": "CI/CD", "iac": "IaC", "grpc": "gRPC",
    "ebpf": "eBPF", "mlops": "MLOps", "finops": "FinOps", "php": "PHP",
    "cpp": "C++", "wasm": "WebAssembly", "amd": "AMD", "nvidia": "NVIDIA",
    "oauth": "OAuth", "graphql": "GraphQL", "websocket": "WebSocket",
    "nodejs": "Node.js", "nextjs": "Next.js", "fastapi": "FastAPI",
    "mongodb": "MongoDB", "mysql": "MySQL", "postgresql": "PostgreSQL",
    "sqlite": "SQLite", "dynamodb": "DynamoDB", "clickhouse": "ClickHouse",
    "surrealdb": "SurrealDB", "planetscale": "PlanetScale", "argocd": "ArgoCD",
    "dotnet": ".NET", "chatgpt": "ChatGPT", "openai": "OpenAI", "deepmind": "DeepMind",
    "deepseek": "DeepSeek", "langchain": "LangChain", "gpt": "GPT",
    "gitlab": "GitLab", "github": "GitHub", "hashicorp": "HashiCorp",
    "datadog": "Datadog", "databricks": "Databricks", "fly-io": "Fly.io",
    "digitalocean": "DigitalOcean", "kubernetes": "Kubernetes",
    "terraform": "Terraform", "ansible": "Ansible", "pulumi": "Pulumi",
    "prometheus": "Prometheus", "grafana": "Grafana", "elasticsearch": "Elasticsearch",
    "github-actions": "GitHub Actions", "gitlab-ci": "GitLab CI",
    "typescript": "TypeScript", "javascript": "JavaScript",
    "hugging-face": "Hugging Face", "stable-diffusion": "Stable Diffusion",
    "zero-day": "Zero-Day", "zero-trust": "Zero Trust",
    "microservices": "Microservices", "observability": "Observability",
    "devsecops": "DevSecOps", "platform-engineering": "Platform Engineering",
    "developer-experience": "Developer Experience", "service-mesh": "Service Mesh",
    "open-source": "Open Source",
}


def format_date_en(date_obj):
    return f"{WEEKDAYS_EN[date_obj.weekday()]}, {date_obj.day} {date_obj.strftime('%B %Y')}"


def extract_categories(stories):
    """Get unique categories from ranked stories."""
    cats = set()
    for s in stories:
        cat = s.get("category", "dev")
        cat_map = {
            "dev": "Software Engineering",
            "cloud": "Cloud",
            "devops": "DevOps & SRE",
            "security": "Security",
            "ai": "AI/ML",
            "ai/ml": "AI/ML",
            "news": "Software Engineering",
        }
        cats.add(cat_map.get(cat.lower(), cat.title()))
    return sorted(cats)


def extract_entity_tags(stories):
    """Extract specific tech entity tags from story titles and summaries.
    
    Only includes tags that appear in 2+ stories to reduce noise.
    Falls back to 1+ if not enough tags meet the threshold.
    """
    tag_counts = {}
    for story in stories:
        text = f"{story.get('title', '')} {story.get('summary', '')}"
        found_in_story = set()
        for pattern, tag in _ENTITY_PATTERNS:
            if pattern.search(text) and tag not in found_in_story:
                found_in_story.add(tag)
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Prefer tags appearing in 2+ stories (stronger signal)
    strong_slugs = sorted(
        [t for t, c in tag_counts.items() if c >= 2],
        key=lambda t: -tag_counts[t]
    )
    # If too few strong tags, include 1-count tags as fallback
    if len(strong_slugs) < 5:
        weak_slugs = sorted(
            [t for t, c in tag_counts.items() if c == 1],
            key=lambda t: -tag_counts.get(t, 0)
        )
        slugs = strong_slugs + weak_slugs
    else:
        slugs = strong_slugs

    # Convert slugs to display names (proper casing for acronyms, brands)
    tags = [TAG_DISPLAY.get(slug, slug.title()) for slug in slugs]

    # Cap at 15 tags per post (focused, not spammy)
    return tags[:15]


def generate_post(date_str=None, has_audio=False):
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_obj = datetime.strptime(date, "%Y-%m-%d")

    # Load synthesis
    synthesis_file = DATA_DIR / f"synthesis_{date}.md"
    if not synthesis_file.exists():
        print(f"[FAIL] No synthesis found for {date}")
        return None

    with open(synthesis_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Load ranked stories for metadata
    ranked_file = DATA_RANKED_DIR / f"top_{date}.json"
    quick_file = DATA_RANKED_DIR / f"quick_{date}.json"
    stories = []
    quick_stories = []
    if ranked_file.exists():
        with open(ranked_file, "r", encoding="utf-8") as f:
            stories = json.load(f)
    if quick_file.exists():
        with open(quick_file, "r", encoding="utf-8") as f:
            quick_stories = json.load(f)

    all_stories = stories + quick_stories
    categories = extract_categories(all_stories)
    # Use only main stories for entity tags (more relevant, less noise)
    tags = extract_entity_tags(stories)

    # Count actual stories in synthesis output (not JSON length)
    main_count = count_main_stories_in_synthesis(content)
    quick_count = count_radar_items_in_synthesis(content)
    # Fallback: use JSON counts if synthesis parsing fails
    if main_count == 0:
        main_count = len(stories)
    if quick_count == 0:
        quick_count = len(quick_stories)

    # Dynamic source count: unique sources that contributed to THIS post
    total_sources = get_source_count()  # total configured (e.g., 281)
    active_sources = set()
    for s in all_stories:
        active_sources.add(s.get("source_name", ""))
        for src in s.get("sources", []):
            active_sources.add(src.get("name", ""))
    active_sources.discard("")
    active_count = len(active_sources) if active_sources else total_sources

    # Build a unique description from the synthesis intro paragraph
    intro = extract_intro_paragraph(content)
    if intro:
        description = intro.replace('"', '\\"')
    else:
        # Fallback: category breakdown
        cat_breakdown = build_category_breakdown(content)
        if cat_breakdown:
            description = f"Today: {', '.join(cat_breakdown)} + {quick_count} quick reads"
        else:
            top_tags_str = ", ".join(tags[:5]).upper() if tags else "tech"
            description = f"{main_count} stories on {top_tags_str} + {quick_count} quick reads"

    date_en = format_date_en(date_obj)

    # Build dynamic title from top stories
    dynamic_title = build_dynamic_title(content, stories)
    if dynamic_title:
        post_title = dynamic_title.replace('"', '\\"')
    else:
        post_title = f"Decode the Stack — {date_en}"

    post_slug = f"{date}-daily"

    print(f"[NEWS] Title: {post_title}")
    print(f"[LINK] Slug: {post_slug}")
    print(f"[TAGS]  Extracted tags: {', '.join(tags[:15])}{'...' if len(tags) > 15 else ''}")
    print(f"[STATS] Counts: {main_count} main stories, {quick_count} quick reads ({active_count} active of {total_sources} configured sources)")

    front_matter = f"""---
title: "{post_title}"
date: {date}T00:00:00Z
slug: "{post_slug}"
description: "{description}"
categories: {json.dumps(categories, ensure_ascii=False)}
tags: {json.dumps(tags, ensure_ascii=False)}
mainCount: {main_count}
quickCount: {quick_count}
draft: false
ShowToc: true
TocOpen: false
---

> 🧠 **{main_count} main stories** + **{quick_count} quick reads** — {date_en}
>
> *Top stories: in-depth context on the day's most relevant reporting.*<br>
> *Quick Reads: brief notes on other stories worth tracking.*

"""

    # Add audio player if podcast was generated
    if has_audio:
        audio_path = PROJECT_DIR / "static" / "podcast" / "audio" / f"{date}.mp3"
        audio_version = hashlib.sha256(audio_path.read_bytes()).hexdigest()[:12]
        front_matter += f"""[AUDIO] **Listen to today's podcast** — with Anna, Maria, and Pedro:

<audio controls preload="metadata" style="width:100%; margin-bottom: 1.5em;">
  <source src="/podcast/audio/{date}.mp3?v={audio_version}" type="audio/mpeg">
</audio>

"""

    # Add toc-split marker so banner+podcast render before TOC
    front_matter += "<!-- toc-split -->\n\n"

    # Strip the intro paragraph from content body (it's already in the description,
    # which PaperMod renders before the TOC on single pages)
    first_heading = re.search(r"^## ", content, re.MULTILINE)
    if first_heading:
        content = content[first_heading.start():]

    # Clean up synthesis artifacts
    content = re.sub(r"\n---\s*\n+---\n", "\n---\n", content)   # double ---
    content = re.sub(r"\n---\s*$", "\n", content)                # trailing ---

    # Convert *Sources: ...* to styled HTML for subtler display
    def _fontes_to_html(m):
        inner = m.group(1)
        html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', inner)
        return f'<p class="story-sources">{html}</p>'

    content = re.sub(
        r"^\*(Sources?: .+)\*$", _fontes_to_html, content, flags=re.MULTILINE
    )

    # Convert Quick Reads bullets to #### headings so they appear in the TOC.
    radar_marker = "## Quick Reads"
    if radar_marker in content:
        # Remove duplicate Quick Reads headings and keep the first.
        parts = content.split(radar_marker)
        before_radar = parts[0]
        # Join all radar body parts (in case there were duplicates)
        radar_body = "\n\n".join(p for p in parts[1:])

        # Strip any leftover duplicate headings inside the radar body
        radar_body = radar_body.replace(radar_marker, "")

        def _bullet_to_h4(m):
            title, url, rest = m.group(1), m.group(2), m.group(3).strip()
            # Separate the description from the *Source:* suffix.
            fonte_m = re.search(r"\s*\*(Sources?: .+)\*\s*$", rest)
            if fonte_m:
                desc = rest[: fonte_m.start()].rstrip(" .")
                fonte_inner = fonte_m.group(1)
                fonte_html = re.sub(
                    r"\[([^\]]+)\]\(([^)]+)\)",
                    lambda lm: f'<a href="{lm.group(2)}">{lm.group(1)}</a>',
                    fonte_inner,
                )
                return (
                    f"\n#### [{title}]({url})\n\n"
                    f"{desc}.\n\n"
                    f'<p class="story-sources">{fonte_html}</p>\n'
                )
            return f"\n#### [{title}]({url})\n\n{rest}\n"

        radar_body = re.sub(
            r"^- \*\*\[([^\]]+)\]\(([^)]+)\)\*\* — (.+)$",
            _bullet_to_h4,
            radar_body,
            flags=re.MULTILINE,
        )

        # Ensure blank lines between consecutive #### blocks
        radar_body = re.sub(r"(</p>)\n*(####)", r"\1\n\n\2", radar_body)

        content = before_radar + radar_marker + "\n" + radar_body

    post_content = "\n".join(
        line.rstrip() for line in (front_matter + content).splitlines()
    ).rstrip() + "\n"

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = CONTENT_DIR / f"{date}-daily.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(post_content)

    print(f"[WRITE] Generated post: {output_file}")
    return output_file, main_count, quick_count


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    generate_post(date)
