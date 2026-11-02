"""Contextual English synthesis with explicit Copilot or legacy API selection."""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from copilot_client import _call_copilot

PROJECT_DIR = Path(__file__).parent.parent
DATA_RANKED_DIR = PROJECT_DIR / "data" / "ranked"
DATA_DIR = PROJECT_DIR / "data"

MAIN_SYSTEM_PROMPT = """You are an experienced technology editor writing for software professionals.

Synthesize the day's most relevant reporting into an original, contextual English briefing.

EDITORIAL RULES:
- Write natural, clear English. Do not translate publisher copy sentence by sentence.
- Synthesize rather than merely summarize: explain implications, trade-offs, and what changed.
- Group stories under Cloud, AI/ML, DevOps & SRE, Software Engineering, or Security.
- Give each main story 2-3 substantial paragraphs, grounded only in supplied facts.
- Preserve the original story title and link to every source used.
- Never invent details, quotations, numbers, product behavior, or causal claims.
- Distinguish reported facts from analysis; note uncertainty where the source material is incomplete.
- Use a professional, approachable voice and restrained section emojis.

MARKDOWN OUTPUT:
---
HEADLINE: One concise narrative headline, at most 60 characters; do not make a list of product names.

Write a 2-3 sentence introduction connecting the day's strongest verified themes.

## 🧑‍💻 Software Engineering

### [Original story title](primary-source-url)
*A one-sentence English framing of why the story matters.*

Two or three paragraphs of original synthesis, context, implications, and caveats.

*Sources: [Publisher](source-url), [Additional publisher](source-url)*

Leave a blank line before every Sources line.

## Cloud
Use the same story structure.

## 🔧 DevOps & SRE
Use the same story structure.

## Security
Use the same story structure.

## AI/ML
Use the same story structure.
"""

QUICK_SYSTEM_PROMPT = """You are a technology editor writing for software professionals.

Write the "Quick Reads" section: one or two concise, factual English sentences per supplied story.
Keep the original title and link, credit its publisher, and do not invent facts or imply independent verification.

Markdown format:
---
## Quick Reads

- **[Original title](url)** — One or two useful sentences. *Source: [Publisher](url)*
"""


def load_ranked_stories(date_str=None):
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = DATA_RANKED_DIR / f"top_{date}.json"
    quick_filepath = DATA_RANKED_DIR / f"quick_{date}.json"
    main_stories = []
    quick_stories = []
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            main_stories = json.load(f)
    else:
        print(f"[FAIL] No ranked stories found for {date}")
    if quick_filepath.exists():
        with open(quick_filepath, "r", encoding="utf-8") as f:
            quick_stories = json.load(f)
    return main_stories, quick_stories, date


WEEKDAYS_EN = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}


def build_main_prompt(stories, date_str=None):
    """Format main stories for deep synthesis."""
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    weekday = WEEKDAYS_EN[date_obj.weekday()]
    lines = [
        f"Today is {weekday}, {date} UTC. If you refer to today, use that exact weekday; do not infer a different date.\n",
        "Synthesize these selected main stories with depth (2-3 paragraphs each):\n",
    ]
    for i, story in enumerate(stories):
        sources_str = ", ".join(
            f"{s['name']} ({s['url']})" for s in story.get("sources", [])[:5]
        )
        lines.append(f"---\nStory {i+1}:")
        lines.append(f"Original title: {story['title']}")
        lines.append(f"Primary URL: {story['url']}")
        lines.append(f"Category: {story['category']}")
        lines.append(f"Independent source coverage: {story.get('coverage_count', 1)}")
        lines.append(f"Sources: {sources_str}")
        lines.append(f"Publisher-provided context: {story.get('summary', 'N/A')}")
        lines.append("")
    lines.append(f"---\nSynthesize all {len(stories)} stories with depth. Follow the specified format.")
    return "\n".join(lines)


def build_quick_prompt(stories):
    """Format quick read stories for brief synthesis."""
    lines = ["Write one or two concise sentences for each of these Quick Reads:\n"]
    for i, story in enumerate(stories):
        lines.append(f"{i+1}. [{story['title']}]({story['url']}) — Source: {story.get('source_name', 'N/A')}")
        summary = story.get('summary', '')[:150]
        if summary:
            lines.append(f"   Publisher context: {summary}")
    lines.append(f"\n---\nWrite 1-2 factual sentences for each of the {len(stories)} stories. Follow the specified format.")
    return "\n".join(lines)


def _call_openai(system_prompt, user_prompt, label="", max_tokens=6000, temperature=0.7):
    """Single direct OpenAI API call."""
    from openai import OpenAI, OpenAIError

    api_key = os.environ.get("OPENAI_KEY")
    if not api_key:
        return None

    model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI(api_key=api_key)

    print(f"[AI] [{label}] Sending to OpenAI ({model})...")
    try:
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=max_tokens,
        )
        content = response.output_text.strip()
        if not content:
            print(f"[WARN]  [{label}] OpenAI returned empty content")
            return None
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0)
        actual_model = getattr(response, "model", "not returned")
        print(f"[OK] [{label}] OpenAI model={actual_model} complete ({len(content)} chars, {tokens} tokens)")
        return content
    except OpenAIError as e:
        print(f"[WARN]  [{label}] OpenAI error: {e}")
        return None


def _call_groq(system_prompt, user_prompt, label="", max_tokens=6000, temperature=0.7):
    """Single Groq API call."""
    from openai import OpenAI

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    print(f"[AI] [{label}] Sending to Groq (Llama 3.3 70B)...")
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        print(f"[OK] [{label}] Groq complete ({len(content)} chars, {tokens} tokens)")
        return content
    except Exception as e:
        print(f"[WARN]  [{label}] Groq error: {e}")
        return None


def _call_azure_openai(system_prompt, user_prompt, label="", max_tokens=6000, temperature=0.7):
    """Single Azure OpenAI API call."""
    from openai import AzureOpenAI

    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    if not api_key or not endpoint:
        return None

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version="2025-01-01-preview",
    )

    print(f"[AI] [{label}] Sending to Azure OpenAI...")
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        actual_model = getattr(response, "model", "not returned")
        print(f"[OK] [{label}] Azure OpenAI model={actual_model} complete ({len(content)} chars, {tokens} tokens)")
        return content
    except Exception as e:
        print(f"[WARN]  [{label}] Azure OpenAI error: {str(e).replace(deployment, '[deployment]')}")
        return None


def _call_llm(system_prompt, user_prompt, label="", max_tokens=6000, temperature=0.7):
    """Use the selected text provider, with no API fallback from Copilot."""
    provider = os.environ.get("LLM_PROVIDER", "auto").strip().lower()
    if provider == "copilot":
        print(f"[AI] [{label}] Using authenticated Copilot CLI text provider.")
        return _call_copilot(system_prompt, user_prompt)
    if provider != "auto":
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}; use copilot or auto.")
    providers = [
        ("OpenAI", bool(os.environ.get("OPENAI_KEY")), _call_openai),
        ("Groq", bool(os.environ.get("GROQ_API_KEY")), _call_groq),
        (
            "Azure OpenAI",
            bool(
                os.environ.get("AZURE_OPENAI_API_KEY")
                and os.environ.get("AZURE_OPENAI_ENDPOINT")
            ),
            _call_azure_openai,
        ),
    ]

    configured = False
    for name, is_configured, call_provider in providers:
        if not is_configured:
            continue
        configured = True
        content = call_provider(
            system_prompt,
            user_prompt,
            label,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if content:
            return content
        print(f"[WARN]  [{label}] {name} failed; trying next configured provider...")

    if not configured:
        print(f"[WARN]  [{label}] No LLM provider is configured")
    return None


def synthesize_two_pass(main_stories, quick_stories, date_str):
    """Two-pass synthesis: main stories + quick reads in separate API calls."""

    # Pass 1: Main stories (deep synthesis)
    main_prompt = build_main_prompt(main_stories, date_str)
    main_content = _call_llm(MAIN_SYSTEM_PROMPT, main_prompt, "Main stories")

    # Small delay to avoid rate limiting between calls
    time.sleep(2)

    # Pass 2: Quick reads (brief)
    quick_content = None
    if quick_stories:
        quick_prompt = build_quick_prompt(quick_stories)
        quick_content = _call_llm(QUICK_SYSTEM_PROMPT, quick_prompt, "Quick Reads")

    # Enforce the section heading in code rather than relying on model formatting.
    if main_content and quick_content:
        radar_re = re.compile(r"\n*##\s*Quick Reads.*", re.DOTALL | re.IGNORECASE)
        main_content = radar_re.sub("", main_content)

        quick_stripped = quick_content.lstrip()
        lines = quick_stripped.split("\n")
        cleaned_lines = [
            l for l in lines
            if not re.match(r"^#{1,3}\s*Quick Reads", l.strip(), re.IGNORECASE)
        ]
        quick_stripped = "\n".join(cleaned_lines).strip()

        combined = main_content.rstrip() + "\n\n## Quick Reads\n\n" + quick_stripped
    elif main_content:
        combined = main_content
    else:
        return None

    return combined


def save_synthesis(content, date_str):
    output_file = DATA_DIR / f"synthesis_{date_str}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[SAVE] Saved to {output_file}")


def run(date_str=None):
    main_stories, quick_stories, date = load_ranked_stories(date_str)
    if not main_stories:
        return None

    content = synthesize_two_pass(main_stories, quick_stories, date)
    if content:
        save_synthesis(content, date)
        print(f"[STATS] Two-pass synthesis complete")
    else:
        print("[FAIL] Contextual synthesis failed: every configured AI provider was unavailable.")
        return None
    return content


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run(date)
