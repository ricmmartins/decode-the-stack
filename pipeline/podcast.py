"""Generate Decode the Stack's English three-host podcast from its synthesis."""

import os
import json
import hashlib
import shutil
import subprocess
import wave
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
AUDIO_DIR = PROJECT_DIR / "static" / "podcast" / "audio"

MP3_BITRATE_ENV = "PODCAST_MP3_BITRATE"
DEFAULT_MP3_BITRATE = "96k"
MIN_ADAPTIVE_MP3_BITRATE_KBPS = 48
PODCAST_TARGET_MINUTES_ENV = "PODCAST_TARGET_MINUTES"
DEFAULT_PODCAST_TARGET_MINUTES = 15
MIN_PODCAST_TARGET_MINUTES = 5
MAX_PODCAST_TARGET_MINUTES = 30
PODCAST_EDGE_TTS_RATE_ENV = "PODCAST_EDGE_TTS_RATE"
DEFAULT_EDGE_TTS_RATE = "+8%"
MIN_EDGE_TTS_RATE_PERCENT = -20
MAX_EDGE_TTS_RATE_PERCENT = 50
SCRIPT_MIN_WORDS_PER_MINUTE = 145
SCRIPT_MAX_WORDS_PER_MINUTE = 160
CHAPTER_WORDS_PER_MINUTE = 160
INTRO_PAUSE_MS = 600
TOPIC_CHANGE_PAUSE_MS = 450
MIB = 1024 * 1024
CLOUDFLARE_MAX_FILE_BYTES = 25 * MIB
PODCAST_TARGET_FILE_BYTES = 24 * MIB
TARGET_SEGMENT_DBFS = -20.0
MAX_SEGMENT_GAIN_DB = 12.0


def _normalize_mp3_bitrate(value):
    """Return a validated ffmpeg MP3 bitrate such as ``96k``."""
    match = re.fullmatch(r"(\d+)[kK]", value.strip())
    if not match:
        raise ValueError(
            f"{MP3_BITRATE_ENV} must be an integer bitrate ending in 'k' "
            "(for example, 96k)"
        )

    bitrate_kbps = int(match.group(1))
    if not MIN_ADAPTIVE_MP3_BITRATE_KBPS <= bitrate_kbps <= 320:
        raise ValueError(
            f"{MP3_BITRATE_ENV} must be between "
            f"{MIN_ADAPTIVE_MP3_BITRATE_KBPS}k and 320k"
        )
    return f"{bitrate_kbps}k"


def _configured_mp3_bitrate(environ=None):
    """Resolve the configured final/intermediate MP3 bitrate."""
    environ = os.environ if environ is None else environ
    return _normalize_mp3_bitrate(
        environ.get(MP3_BITRATE_ENV, DEFAULT_MP3_BITRATE)
    )


def _configured_target_minutes(environ=None):
    """Resolve a practical target duration for future podcast scripts."""
    environ = os.environ if environ is None else environ
    raw_value = environ.get(
        PODCAST_TARGET_MINUTES_ENV,
        str(DEFAULT_PODCAST_TARGET_MINUTES),
    )
    try:
        target_minutes = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{PODCAST_TARGET_MINUTES_ENV} must be an integer number of minutes"
        ) from error

    if not MIN_PODCAST_TARGET_MINUTES <= target_minutes <= MAX_PODCAST_TARGET_MINUTES:
        raise ValueError(
            f"{PODCAST_TARGET_MINUTES_ENV} must be between "
            f"{MIN_PODCAST_TARGET_MINUTES} and {MAX_PODCAST_TARGET_MINUTES}"
        )
    return target_minutes


def _configured_edge_tts_rate(environ=None):
    """Resolve a validated Edge TTS percentage rate."""
    environ = os.environ if environ is None else environ
    raw_value = environ.get(PODCAST_EDGE_TTS_RATE_ENV, DEFAULT_EDGE_TTS_RATE)
    match = re.fullmatch(r"([+-])(\d+)%", str(raw_value).strip())
    if not match:
        raise ValueError(
            f"{PODCAST_EDGE_TTS_RATE_ENV} must be a signed percentage "
            "(for example, +8%)"
        )

    rate_percent = int(match.group(2))
    if match.group(1) == "-":
        rate_percent *= -1
    if not MIN_EDGE_TTS_RATE_PERCENT <= rate_percent <= MAX_EDGE_TTS_RATE_PERCENT:
        raise ValueError(
            f"{PODCAST_EDGE_TTS_RATE_ENV} must be between "
            f"{MIN_EDGE_TTS_RATE_PERCENT}% and +{MAX_EDGE_TTS_RATE_PERCENT}%"
        )
    return f"{rate_percent:+d}%"


def _script_word_range(target_minutes):
    """Return rounded conversational word bounds for a duration target."""
    minimum_words = target_minutes * SCRIPT_MIN_WORDS_PER_MINUTE
    maximum_words = target_minutes * SCRIPT_MAX_WORDS_PER_MINUTE
    minimum_words = ((minimum_words + 49) // 50) * 50
    maximum_words = (maximum_words // 50) * 50
    return minimum_words, maximum_words


MP3_BITRATE = _configured_mp3_bitrate()
PODCAST_TARGET_MINUTES = _configured_target_minutes()
EDGE_TTS_RATE = _configured_edge_tts_rate()

HOST_A = "Anna"
HOST_B = "Maria"
HOST_C = "Pedro"

EDGE_VOICE_A = "en-US-AriaNeural"
EDGE_VOICE_B = "en-US-JennyNeural"
EDGE_VOICE_C = "en-US-GuyNeural"

OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_VOICE_A = os.environ.get("OPENAI_TTS_VOICE_ANNA", "marin")
OPENAI_VOICE_B = os.environ.get("OPENAI_TTS_VOICE_MARIA", "sage")
OPENAI_VOICE_C = os.environ.get("OPENAI_TTS_VOICE_PEDRO", "ash")
OPENAI_TTS_MAX_CHARS = 4000

OPENAI_VOICE_MAP = {
    HOST_A: OPENAI_VOICE_A,
    HOST_B: OPENAI_VOICE_B,
    HOST_C: OPENAI_VOICE_C,
}
EDGE_VOICE_MAP = {
    HOST_A: EDGE_VOICE_A,
    HOST_B: EDGE_VOICE_B,
    HOST_C: EDGE_VOICE_C,
}

SHARED_VOCAL_DIRECTION = (
    "Speak natural, neutral American English at a lively but comfortable pace, "
    "around 150 words per minute. Use short natural pauses, avoid drawn-out "
    "sentence endings, and pronounce technical terms clearly."
)
HOST_VOCAL_INSTRUCTIONS = {
    HOST_A: (
        "You are Anna, the host of an English-language technology podcast. "
        "Use a warm, curious, energetic voice with moderate enthusiasm. "
        f"{SHARED_VOCAL_DIRECTION}"
    ),
    HOST_B: (
        "You are Maria, the technical analyst on an English-language technology "
        "podcast. Be clear, thoughtful, and confident when explaining technical "
        f"concepts. {SHARED_VOCAL_DIRECTION}"
    ),
    HOST_C: (
        "You are Pedro, the conversational co-host on an English-language "
        "technology podcast. Be relaxed, reflective, and lightly funny. "
        f"{SHARED_VOCAL_DIRECTION}"
    ),
}

# Backward-compatible aliases used by the legacy SSML helper.
VOICE_A = EDGE_VOICE_A
VOICE_B = EDGE_VOICE_B
VOICE_C = EDGE_VOICE_C

HD_VOICES = set()  # No DragonHD voices when using edge-tts
HD_TEMPERATURE = "0.8"  # Kept for reference (unused with edge-tts)

# Intro jingle URL (hosted in site static, optional)
JINGLE_URL = ""

# Background music file (lo-fi, CC0, for ambient bed under voices)
BG_MUSIC_PATH = PROJECT_DIR / "static" / "podcast" / "music" / "bgmusic.mp3"
BG_MUSIC_TARGET_DBFS = -28.0
BG_MUSIC_COMPRESSION_THRESHOLD_DBFS = -24.0

# ── English tech terms for correct pronunciation via <lang> tags ──
ENGLISH_TECH_TERMS = {
    # Multi-word terms (matched first due to longest-first sorting)
    "open source", "cloud native", "edge computing", "feature flag",
    "blue green", "pull request", "a/b testing", "machine learning",
    "deep learning", "large language model", "retrieval augmented generation",
    "prompt engineering", "fine tuning", "zero trust", "hybrid cloud",
    "multi-cloud", "load balancing", "disaster recovery", "dead letter",
    "scale out", "scale up", "on premises",
    # Platforms & tools
    "kubernetes", "docker", "github", "gitlab", "terraform", "ansible",
    "jenkins", "grafana", "prometheus", "elasticsearch", "redis", "kafka",
    "nginx", "cloudflare", "vercel", "netlify", "supabase", "firebase",
    "mongodb", "postgresql", "mysql", "dynamodb", "snowflake", "databricks",
    "airflow", "spark", "hadoop",
    # Cloud
    "lambda", "fargate", "copilot", "sagemaker", "bedrock",
    # Languages & frameworks
    "python", "javascript", "typescript", "rust", "golang",
    "react", "angular", "vue", "svelte", "next", "nuxt", "remix",
    "django", "flask", "fastapi", "express", "spring", "flutter",
    "swift", "kotlin",
    # Concepts
    "devops", "devsecops", "gitops", "mlops", "microservices",
    "serverless", "containers", "cluster", "pipeline", "deploy",
    "deployment", "rollback", "rollout", "observability", "monitoring",
    "autoscaling", "benchmark", "throughput", "latency", "uptime",
    "backdoor", "ransomware", "malware", "phishing", "firewall",
    "proxy", "gateway", "endpoint", "token", "webhook", "middleware",
    "runtime", "sandbox", "changelog", "framework", "dashboard",
    "release", "patch", "hotfix", "workflow", "sprint", "scrum",
    "agile", "kanban",
    # Acronyms
    "api", "sdk", "cli", "saas", "paas", "iaas", "graphql", "grpc",
    "websocket", "llm", "rag", "jwt", "oauth",
    # Companies
    "google", "microsoft", "amazon", "meta", "apple", "nvidia",
    "openai", "anthropic", "mistral", "crowdstrike", "hashicorp",
}

def _escape_xml(text):
    """Escape XML special characters."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _wrap_english_terms(text):
    """Escape dialogue text for English-language SSML."""
    return _escape_xml(text)


def _build_podcast_script_prompt(target_minutes):
    minimum_words, maximum_words = _script_word_range(target_minutes)
    return f"""You are the scriptwriter for Decode the Stack, an English-language daily technology briefing.
Write a lively, accurate dialogue between three distinct hosts:
- {HOST_A}: the warm, curious lead host who guides the show and transitions between stories.
- {HOST_B}: the analytical technical host who adds context, trade-offs, and thoughtful disagreement.
- {HOST_C}: the relaxed co-host who asks listener-minded questions and uses occasional light humor.

OUTPUT AND STRUCTURE:
- Put exactly one spoken turn on each line, prefixed with "{HOST_A}:", "{HOST_B}:", or "{HOST_C}:".
- Start with one or two short teaser turns about the most consequential supplied story.
- Put [INTRO] on its own line after the teaser, then have {HOST_A} welcome listeners to Decode the Stack.
- Introduce the other hosts briefly; vary who speaks and let them react naturally.
- Put [TOPIC_CHANGE] on its own line when moving to a new main topic.
- End with a short, friendly sign-off. Do not claim the show is already listed on Spotify or any other directory.
- Mention the website decodethestack.com for the written briefing and original links.

EDITORIAL RULES:
- Use natural conversational English, concise turns, and a professional but relaxed tone.
- Explain the reporting's context and implications; do not simply read headlines.
- Cover the main stories and mention 3-5 Quick Reads briefly when available.
- Keep each turn to at most three sentences. Alternate hosts and include useful questions, agreement, or disagreement.
- Never invent facts, quotations, numbers, reactions, or conclusions beyond the supplied synthesis.
- Do not use Markdown, URLs, emojis, or publisher/source names in spoken dialogue.
- Do not add a jingle marker or mention audio/music.

DURATION:
- Target approximately {target_minutes} minutes at a conversational pace.
- Keep the script between {minimum_words} and {maximum_words} spoken words, excluding host names and stage markers.
- Prioritize useful context on main stories; keep Quick Reads genuinely brief.

Example:
{HOST_A}: A major runtime change landed this morning, but the performance numbers are only half the story.
{HOST_C}: The other half could change how teams roll it out.
[INTRO]
{HOST_A}: Welcome to Decode the Stack. I'm Anna, and today we're connecting the engineering decisions behind the headlines.
{HOST_B}: I'm Maria. I have a question about the trade-off in that first release.
{HOST_C}: And I'm Pedro. Let's get into it.
[TOPIC_CHANGE]
{HOST_B}: Here's what the source material actually confirms, and where the open questions remain.
"""


PODCAST_SCRIPT_PROMPT = _build_podcast_script_prompt(PODCAST_TARGET_MINUTES)


def _sanitize_script(script):
    """Trim the generated dialogue without changing its factual wording."""
    return script.strip()


def _decode_script_section(response):
    """Require explicit speaker attribution; never infer a host for narration."""
    response = response.strip()
    if not response.startswith("{"):
        _validate_dialogue(response)
        return response
    try:
        payload = json.loads(response)
    except ValueError as error:
        raise ValueError("Podcast section must be valid JSON with explicitly attributed turns.") from error
    if not isinstance(payload, dict) or set(payload) != {"turns"}:
        raise ValueError("Podcast JSON must contain exactly a turns array.")
    turns = payload["turns"]
    if not isinstance(turns, list) or not turns:
        raise ValueError("Podcast JSON turns must be a nonempty array.")
    lines = []
    for turn in turns:
        if not isinstance(turn, dict):
            raise ValueError("Every podcast turn must explicitly name its speaker and text.")
        if set(turn) == {"marker"} and turn["marker"] == "[INTRO]":
            lines.append("[INTRO]")
            continue
        if set(turn) != {"speaker", "text"} or turn["speaker"] not in (HOST_A, HOST_B, HOST_C):
            raise ValueError("Every spoken turn must use speaker Anna, Maria, or Pedro.")
        text = turn["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Every spoken turn must contain nonempty text.")
        if re.search(r"\[(?:INTRO|TOPIC_CHANGE)\]", text):
            raise ValueError("Stage markers must be separate from spoken text.")
        lines.append(f"{turn['speaker']}: {' '.join(text.split())}")
    script = "\n".join(lines)
    _validate_dialogue(script)
    return script


def generate_podcast_script(synthesis_content, checkpoint_path=None):
    """Generate bounded sections so shorter-output providers can meet the duration."""
    from synthesize import _call_llm

    minimum_words, maximum_words = _script_word_range(PODCAST_TARGET_MINUTES)
    section_count = (maximum_words + 399) // 400
    blocks = [
        block.strip()
        for block in re.split(r"(?m)(?=^### |^- \*\*\[)", synthesis_content)
        if block.strip()
    ]
    if len(blocks) < section_count:
        raise ValueError("Insufficient source story sections for a full contextual podcast.")

    checkpoint_key = hashlib.sha256(
        f"speaker-turns-v1:{minimum_words}:{maximum_words}:{synthesis_content}".encode("utf-8")
    ).hexdigest()
    saved_sections = []
    if checkpoint_path is not None and checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"key", "sections"}:
            raise ValueError("Invalid podcast section checkpoint.")
        if checkpoint["key"] != checkpoint_key:
            print("[RECOVERY] Podcast source or duration changed; generating new sections.")
        else:
            saved_sections = checkpoint["sections"]
            if (
                not isinstance(saved_sections, list)
                or len(saved_sections) > section_count
                or not all(isinstance(section, str) for section in saved_sections)
            ):
                raise ValueError("Invalid saved podcast sections.")

    sections = []
    print(f"[AUDIO] Generating {section_count} bounded three-host podcast sections...")
    for index in range(section_count):
        used_words = sum(_spoken_word_count(section) for section in sections)
        if index == section_count - 1:
            section_minimum = max(100, minimum_words - used_words)
            section_maximum = maximum_words - used_words
        else:
            section_minimum = max(100, minimum_words // section_count - 66)
            section_maximum = maximum_words // section_count + 50
        if index < len(saved_sections):
            saved = saved_sections[index]
            _validate_dialogue(saved)
            if not section_minimum <= _spoken_word_count(saved) <= section_maximum:
                raise ValueError(f"Saved podcast section {index + 1} is outside its word budget.")
            sections.append(saved)
            print(f"[RECOVERY] Reusing validated podcast section {index + 1}/{section_count}.")
            continue
        target_words = (section_minimum + section_maximum) // 2
        source = "\n\n".join(
            blocks[index * len(blocks) // section_count:
                   (index + 1) * len(blocks) // section_count]
        )
        position = (
            "Open with a short teaser, then [INTRO] and the show welcome. "
            "Each host must introduce themselves by name: Anna, Maria, Pedro."
            if index == 0 else
            "Finish with a brief sign-off; do not introduce the show again."
            if index == section_count - 1 else
            "Continue the conversation without a welcome, recap, or sign-off."
        )
        prompt = (
            "Write ONE section of Decode the Stack's English technology podcast. "
            f"This is section {index + 1} of {section_count}. {position}\n"
            f"Write {section_minimum}-{section_maximum} spoken words, excluding "
            f"speaker labels and markers. Aim for {target_words} words, safely inside "
            "the allowed interval. Count words in text fields, not JSON keys. "
            "Plan conversational turns totaling that target before returning JSON. "
            "This is a strict section budget, not the "
            "whole episode. Use all three speakers Anna, Maria, and Pedro, "
            "one JSON object per turn, at most three sentences per turn. "
            "Anna is the clear, concise anchor; Maria adds technical depth; "
            "Pedro asks practical questions in a conversational tone. "
            "Explain the supplied stories, engineering trade-offs, uncertainty, "
            "and practical questions using only the supplied evidence. "
            "Never invent facts, quotations, numbers, examples presented as facts, "
            "or publisher claims. Do not pad with repeated summaries. No Markdown, "
            "URLs, stage directions, or markers except [INTRO]. "
            'Return ONLY a JSON object with exactly this structure: {"turns":['
            '{"speaker":"Anna","text":"Spoken words"},'
            '{"marker":"[INTRO]"},'
            '{"speaker":"Maria","text":"Spoken words"},'
            '{"speaker":"Pedro","text":"Spoken words"}]}. '
            "Use the optional INTRO marker only in the opening section. "
            "Repeat speaker/text objects for each conversational turn. Every spoken "
            "word, including the welcome, must be inside an explicitly named speaker's "
            "text field. Never output standalone narration or unlabeled text."
        )
        accepted = None
        feedback = ""
        for attempt in range(4):
            candidate = _call_llm(
                prompt + feedback,
                source,
                f"Podcast section {index + 1}/{section_count}, attempt {attempt + 1}",
                max_tokens=2000,
            )
            if not candidate:
                raise RuntimeError(f"No provider generated podcast section {index + 1}.")
            try:
                candidate = _decode_script_section(_sanitize_script(candidate))
            except ValueError as error:
                if attempt == 3:
                    raise
                feedback = (
                    f"\nThe previous draft was rejected: {error}. "
                    "Rewrite the same supplied source material as the required JSON turns "
                    "array. Every spoken turn needs an explicit speaker and text. "
                    "Do not repeat the rejected standalone narration format."
                )
                continue
            word_count = _spoken_word_count(candidate)
            if section_minimum <= word_count <= section_maximum:
                accepted = candidate
                break
            feedback = (
                f"\nThe previous draft had exactly {word_count} spoken words; "
                f"the permitted interval is {section_minimum}-{section_maximum}. "
                f"Revise it toward {target_words} words: "
                f"{'remove' if word_count > target_words else 'add'} approximately "
                f"{abs(word_count - target_words)} spoken words. "
                "Shorten repetition or expand only source-grounded explanation. "
                "Keep source facts and explicit speaker attribution; return the full revised "
                "JSON section, never a partial patch. The rejected draft follows:\n"
                + json.dumps({"turns": [
                    {"speaker": line.split(":", 1)[0], "text": line.split(":", 1)[1].strip()}
                    if not line.startswith("[") else {"marker": line}
                    for line in (line.strip() for line in candidate.splitlines()) if line
                ]})
            )
        if accepted is None:
            raise ValueError(
                f"Podcast section {index + 1} has {word_count} spoken words; "
                f"required {section_minimum}-{section_maximum}."
            )
        sections.append(accepted)
        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = checkpoint_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps({"key": checkpoint_key, "sections": sections}, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary.replace(checkpoint_path)

    script = "\n[TOPIC_CHANGE]\n".join(sections)
    word_count = _spoken_word_count(script)
    if not minimum_words <= word_count <= maximum_words:
        raise ValueError(f"Podcast has {word_count} words; required {minimum_words}-{maximum_words}.")
    print(f"[OK] Podcast script generated ({word_count} spoken words, {len(script)} chars)")
    return script


def _validate_dialogue(script):
    """Reject material that the speech parser would silently omit."""
    speakers = set()
    for line in script.splitlines():
        line = line.strip()
        if not line or line in {"[INTRO]", "[TOPIC_CHANGE]"}:
            continue
        match = re.fullmatch(r"(Anna|Maria|Pedro):\s*(\S.*)", line)
        if not match:
            raise ValueError(f"Podcast contains an unrecognized dialogue line: {line[:80]}")
        speakers.add(match.group(1))
    if speakers != {HOST_A, HOST_B, HOST_C}:
        raise ValueError("Each podcast section must include all three English hosts.")


def _spoken_word_count(script):
    """Count spoken words, excluding host labels and editorial markers."""
    words = []
    for line in script.splitlines():
        line = line.strip()
        if not line or line in {"[INTRO]", "[TOPIC_CHANGE]"}:
            continue
        line = re.sub(r"^(?:Anna|Maria|Pedro):\s*", "", line)
        line = re.sub(r"\([^)]*\)", "", line)
        words.extend(re.findall(r"\b[\w'-]+\b", line))
    return len(words)


def _classify_line(text):
    """Classify a dialogue line to determine pause, emphasis, and style hints.
    Returns (pause_ms, is_exclamation, is_question, is_short_reaction).
    """
    is_excl = text.rstrip().endswith("!")
    is_q = text.rstrip().endswith("?")
    clean = text.strip().rstrip("!?.)")
    is_short = len(clean) < 30

    # These pauses are used only by the legacy SSML helper.
    if is_short:
        return 100, is_excl, is_q, True
    if len(text) < 100:
        return 160, is_excl, is_q, False
    return 220, is_excl, is_q, False


def script_to_ssml(script):
    """Convert dialogue script to SSML with DragonHD + standard voices.

    DragonHD voices: no <prosody>/<mstts:express-as>, uses temperature param.
    Standard voices: keep prosody and style hints.
    Both: <lang> tags for English terms, <break> for pauses.
    """
    lines = script.strip().split("\n")
    ssml_parts = []

    def build_voice_element(voice, text_ssml, pause_ms, raw_text,
                            style=None, style_degree=None):
        """Build SSML <voice> element, adapting to HD vs standard."""
        is_hd = voice in HD_VOICES
        _, is_excl, is_q, is_short = _classify_line(raw_text)

        if is_hd:
            # DragonHD: simple — auto-detects emotion, no prosody needed
            return (
                f'<voice name="{voice}" parameters="temperature={HD_TEMPERATURE}">'
                f'{text_ssml}'
                f'<break time="{pause_ms}ms"/>'
                f'</voice>'
            )
        else:
            # Standard neural voice: use prosody and optional style
            rate = "1.05" if is_short else "1.0"
            if len(raw_text) > 120:
                rate = "0.95"
            pitch = "+2%"

            inner = f'<prosody rate="{rate}" pitch="{pitch}">{text_ssml}</prosody>'

            # Auto-detect style
            if not style:
                if is_excl and is_short:
                    style = "excited"
                elif "(laughs)" in raw_text.lower() or "haha" in raw_text.lower():
                    style = "cheerful"
                elif is_q:
                    style = "curious"

            if style:
                degree = f' styledegree="{style_degree}"' if style_degree else ""
                inner = f'<mstts:express-as style="{style}"{degree}>{inner}</mstts:express-as>'

            return (
                f'<voice name="{voice}">'
                f'{inner}'
                f'<break time="{pause_ms}ms"/>'
                f'</voice>'
            )

    prev_speaker = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Topic change marker to longer pause
        if line == "[TOPIC_CHANGE]":
            ssml_parts.append(
                f'<voice name="{VOICE_A}" parameters="temperature={HD_TEMPERATURE}">'
                f'<break time="{TOPIC_CHANGE_PAUSE_MS}ms"/></voice>'
            )
            prev_speaker = None
            continue

        # Jingle insertion marker to break (actual jingle overlaid in post-processing)
        if line == "[INTRO]":
            ssml_parts.append(
                f'<voice name="{VOICE_A}" parameters="temperature={HD_TEMPERATURE}">'
                f'<break time="{INTRO_PAUSE_MS}ms"/></voice>'
            )
            prev_speaker = None
            continue

        # Detect speaker
        speaker = None
        text = None
        for host in (HOST_A, HOST_B, HOST_C):
            if line.startswith(f"{host}:"):
                speaker = host
                text = line[len(f"{host}:"):].strip()
                break

        if speaker and text:
            # Speaker-change pause
            if prev_speaker and prev_speaker != speaker:
                gap = 40 if len(text) < 30 else 80
                ssml_parts.append(
                    f'<voice name="{VOICE_A}" parameters="temperature={HD_TEMPERATURE}">'
                    f'<break time="{gap}ms"/></voice>'
                )

            # Strip stage directions from spoken text
            spoken = re.sub(r"\(laughs?\)", "", text, flags=re.IGNORECASE).strip()
            if not spoken:
                continue

            # Prepare SSML text (English wrapping + XML escaping)
            text_ssml = _wrap_english_terms(spoken)
            pause_ms = _classify_line(spoken)[0]

            voice_map = {HOST_A: VOICE_A, HOST_B: VOICE_B, HOST_C: VOICE_C}
            voice = voice_map[speaker]

            ssml_parts.append(
                build_voice_element(voice, text_ssml, pause_ms, spoken)
            )
            prev_speaker = speaker

        elif line:
            # Non-dialogue line (narration)
            text_ssml = _wrap_english_terms(line)
            ssml_parts.append(
                f'<voice name="{VOICE_A}" parameters="temperature={HD_TEMPERATURE}">'
                f'{text_ssml}<break time="300ms"/></voice>'
            )

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
        + "".join(ssml_parts)
        + '</speak>'
    )
    return ssml


def _prepare_background_music(music, duration_ms):
    """Keep the quiet introduction audible without overpowering narration."""
    from pydub.effects import compress_dynamic_range

    if not len(music) or music.rms == 0:
        raise ValueError("Background music must contain non-silent audio.")
    music = compress_dynamic_range(
        music, threshold=BG_MUSIC_COMPRESSION_THRESHOLD_DBFS,
        ratio=4.0, attack=10, release=250,
    )
    music = music.apply_gain(BG_MUSIC_TARGET_DBFS - music.dBFS)
    if len(music) < duration_ms:
        music = music * ((duration_ms // len(music)) + 1)
    return music[:duration_ms].fade_in(3000).fade_out(5000)


def _overlay_background_music(speech_path):
    """Overlay lo-fi background music at low volume under the speech."""
    if not BG_MUSIC_PATH.exists():
        raise FileNotFoundError(f"Required podcast background music is missing: {BG_MUSIC_PATH}")
    from pydub import AudioSegment

    speech = AudioSegment.from_mp3(str(speech_path))
    music = AudioSegment.from_mp3(str(BG_MUSIC_PATH))
    speech_len = len(speech)
    if not speech_len or not len(music):
        raise ValueError("Speech and background music must contain nonempty audio.")
    music = _prepare_background_music(music, speech_len)
    combined = _mix_background_audio(speech, music)
    temporary = Path(speech_path).with_suffix(".mix.mp3")
    try:
        combined.export(str(temporary), format="mp3", bitrate=MP3_BITRATE)
        temporary.replace(speech_path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"[AUDIO] Background music overlaid (target {BG_MUSIC_TARGET_DBFS} dBFS, {speech_len/1000:.0f}s; fades 3s/5s)")


def _mix_background_audio(speech, music):
    """Sum without saturation, reserving 1 dB of shared sample headroom."""
    import numpy as np
    from pydub import AudioSegment

    channels = max(speech.channels, music.channels)
    rate = max(speech.frame_rate, music.frame_rate)
    speech = speech.set_channels(channels).set_frame_rate(rate).set_sample_width(2)
    music = music.set_channels(channels).set_frame_rate(rate).set_sample_width(2)
    speech_samples = np.asarray(speech.get_array_of_samples(), dtype=np.int32)
    music_samples = np.asarray(music.get_array_of_samples(), dtype=np.int32)
    # Millisecond slicing/resampling can differ by one partial millisecond.
    difference = len(speech_samples) - len(music_samples)
    if abs(difference) > rate * channels / 1000:
        raise ValueError("Speech and prepared music must have the same duration.")
    if difference > 0:
        music_samples = np.pad(music_samples, (0, difference))
    samples = speech_samples + music_samples[:len(speech_samples)]
    peak = int(np.max(np.abs(samples))) if len(samples) else 0
    gain_db = min(0.0, 20 * np.log10(32767 / peak) - 1) if peak else 0.0
    scaled = (samples * (10 ** (gain_db / 20))).astype("<i2")
    print(f"[AUDIO] Shared mix headroom adjustment: {gain_db:.2f} dB")
    return AudioSegment(
        scaled.tobytes(), sample_width=2, frame_rate=rate, channels=channels,
    )


def _post_process_audio(output_path):
    """Apply background music and jingle overlay to synthesized speech."""
    _overlay_background_music(output_path)
    _overlay_jingle(output_path)
    return _ensure_final_mp3_size(output_path)


def _overlay_jingle(speech_path):
    """Overlay jingle on the first few seconds of the speech audio."""
    try:
        from pydub import AudioSegment
    except ImportError:
        print("[WARN]  pydub not installed, skipping jingle overlay")
        return

    # Try local file first (always available during CI), fallback to URL download
    local_jingle = PROJECT_DIR / "static" / "podcast" / "audio" / "jingle.mp3"
    jingle_path = None

    if local_jingle.exists():
        jingle_path = str(local_jingle)
        print(f"[AUDIO] Overlaying intro jingle (local: {local_jingle.name})...")
    elif JINGLE_URL:
        import urllib.request
        import tempfile
        print(f"[AUDIO] Downloading jingle from CDN...")
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            urllib.request.urlretrieve(JINGLE_URL, tmp.name)
            jingle_path = tmp.name
        except Exception as e:
            print(f"[WARN]  Jingle download failed: {e}")
            return
    else:
        print("[INFO]  No jingle available, skipping overlay")
        return

    try:
        jingle = AudioSegment.from_mp3(jingle_path)
        speech = AudioSegment.from_mp3(str(speech_path))

        # Jingle: fade in 1s, play full, fade out 3s, volume down
        jingle = jingle.fade_in(1000).fade_out(3000) - 8  # -8 dB

        # Overlay jingle at the very start of speech
        combined = speech.overlay(jingle, position=0)

        combined.export(str(speech_path), format="mp3", bitrate=MP3_BITRATE)
        print(f"[OK] Jingle overlaid on intro ({len(jingle)/1000:.1f}s)")
    except Exception as e:
        print(f"[WARN]  Jingle overlay failed (non-blocking): {e}")
    finally:
        # Clean up temp download if used
        if jingle_path != str(local_jingle):
            Path(jingle_path).unlink(missing_ok=True)


def _ensure_final_mp3_size(output_path):
    """Keep the final MP3 below Cloudflare's limit without regenerating TTS."""
    output_path = Path(output_path)
    if not output_path.exists():
        print(f"[ERROR] Final podcast file is missing: {output_path}")
        return False

    original_size = output_path.stat().st_size
    if original_size <= PODCAST_TARGET_FILE_BYTES:
        return True

    try:
        from pydub import AudioSegment
        from pydub.exceptions import CouldntDecodeError, CouldntEncodeError
    except ImportError:
        if original_size < CLOUDFLARE_MAX_FILE_BYTES:
            print(
                "[WARN]  Final podcast exceeds the 24 MiB target, but remains below "
                "25 MiB; pydub is unavailable for adaptive re-encoding"
            )
            return True
        print(
            "[ERROR] Final podcast exceeds Cloudflare's 25 MiB limit and pydub is "
            "unavailable for adaptive re-encoding"
        )
        return False

    try:
        source_audio = AudioSegment.from_mp3(str(output_path))
    except (CouldntDecodeError, OSError) as error:
        if original_size < CLOUDFLARE_MAX_FILE_BYTES:
            print(
                f"[WARN]  Podcast remains below 25 MiB, but could not be inspected "
                f"for the preferred 24 MiB target: {error}"
            )
            return True
        print(f"[ERROR] Unable to inspect oversized podcast for re-encoding: {error}")
        return False

    duration_seconds = len(source_audio) / 1000
    if duration_seconds <= 0:
        print("[ERROR] Cannot reduce oversized podcast because its duration is invalid")
        return False

    configured_kbps = int(MP3_BITRATE[:-1])
    estimated_safe_kbps = int(
        (PODCAST_TARGET_FILE_BYTES * 8 * 0.97)
        / (duration_seconds * 1000)
    )
    estimated_safe_kbps = (estimated_safe_kbps // 8) * 8
    first_bitrate = min(configured_kbps - 8, estimated_safe_kbps)
    first_bitrate = max(first_bitrate, MIN_ADAPTIVE_MP3_BITRATE_KBPS)
    candidates = range(
        first_bitrate,
        MIN_ADAPTIVE_MP3_BITRATE_KBPS - 1,
        -8,
    )

    temp_path = output_path.with_name(f".{output_path.stem}.size-guard.mp3")
    best_path = output_path.with_name(f".{output_path.stem}.size-guard-best.mp3")
    best_size = None
    best_bitrate = None
    try:
        for bitrate_kbps in candidates:
            source_audio.export(
                str(temp_path),
                format="mp3",
                bitrate=f"{bitrate_kbps}k",
            )
            candidate_size = temp_path.stat().st_size
            if candidate_size <= PODCAST_TARGET_FILE_BYTES:
                temp_path.replace(output_path)
                best_path.unlink(missing_ok=True)
                print(
                    f"[OK] Podcast re-encoded at {bitrate_kbps}k: "
                    f"{candidate_size / MIB:.1f} MiB (24 MiB target)"
                )
                return True
            if candidate_size < CLOUDFLARE_MAX_FILE_BYTES:
                best_size = candidate_size
                best_bitrate = bitrate_kbps
                temp_path.replace(best_path)
    except (CouldntEncodeError, OSError) as error:
        print(f"[ERROR] Adaptive podcast re-encoding failed: {error}")
    finally:
        temp_path.unlink(missing_ok=True)

    if best_size is not None:
        best_path.replace(output_path)
        print(
            f"[WARN]  Podcast is below Cloudflare's limit at {best_bitrate}k "
            f"({best_size / MIB:.1f} MiB) but exceeds the preferred 24 MiB target"
        )
        return True

    best_path.unlink(missing_ok=True)
    if original_size < CLOUDFLARE_MAX_FILE_BYTES:
        print(
            f"[WARN]  Podcast is below Cloudflare's 25 MiB limit "
            f"({original_size / MIB:.1f} MiB) but could not reach the 24 MiB target"
        )
        return True

    print(
        f"[ERROR] Podcast is {original_size / MIB:.1f} MiB and could not be reduced "
        "below Cloudflare Pages' 25 MiB per-file limit"
    )
    return False


def _split_tts_input(text, max_chars=OPENAI_TTS_MAX_CHARS):
    """Split oversized speech input at natural boundaries below API limits."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        candidate = remaining[:max_chars + 1]
        split_at = max(
            candidate.rfind(". "),
            candidate.rfind("? "),
            candidate.rfind("! "),
            candidate.rfind("; "),
            candidate.rfind(", "),
            candidate.rfind(" "),
        )
        if split_at <= 0:
            split_at = max_chars
        else:
            split_at += 1
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return chunks


def _parse_speech_segments(script):
    """Parse host lines and markers into provider-independent audio segments."""
    lines = script.strip().split("\n")
    segments = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line == "[INTRO]":
            segments.append({"type": "pause", "ms": INTRO_PAUSE_MS})
            continue
        if line == "[TOPIC_CHANGE]":
            segments.append({"type": "pause", "ms": TOPIC_CHANGE_PAUSE_MS})
            continue

        speaker = None
        text = None
        for host in (HOST_A, HOST_B, HOST_C):
            if line.startswith(f"{host}:"):
                speaker = host
                text = line[len(f"{host}:"):].strip()
                break

        if speaker and text:
            spoken = re.sub(r"\(laughs?\)", "", text, flags=re.IGNORECASE).strip()
            if spoken:
                chunks = _split_tts_input(spoken)
                for chunk in chunks:
                    segments.append({
                        "type": "speech",
                        "speaker": speaker,
                        "text": chunk,
                    })
    return segments


def _speech_segments(segments):
    return [segment for segment in segments if segment["type"] == "speech"]


class PocketTTSError(RuntimeError):
    pass


def _synthesize_pocket_segments(segments, tmp_dir):
    executable = shutil.which(os.environ.get("POCKET_TTS_CLI_PATH") or "pocket-tts")
    if not executable:
        raise PocketTTSError("Pocket TTS executable is missing; install the verified CPU release.")
    voices = {
        HOST_A: os.environ.get("POCKET_TTS_VOICE_ANNA", "alba"),
        HOST_B: os.environ.get("POCKET_TTS_VOICE_MARIA", "mary"),
        HOST_C: os.environ.get("POCKET_TTS_VOICE_PEDRO", "bill_boerst"),
    }
    approved = {HOST_A: "alba", HOST_B: "mary", HOST_C: "bill_boerst"}
    if voices != approved:
        raise PocketTTSError("Pocket TTS voices must match the attributed production voice set.")
    started = time.monotonic()
    for index, segment in enumerate(_speech_segments(segments)):
        output = tmp_dir / f"seg_{index:04d}.wav"
        try:
            result = subprocess.run(
                [executable, "generate", "--language", "english",
                 "--voice", voices[segment["speaker"]], "--text", "-", "--device", "cpu",
                 "--max-tokens", "50",
                 "--output-path", str(output)],
                input=segment["text"], capture_output=True, text=True, encoding="utf-8",
                timeout=300, check=False,
            )
        except subprocess.TimeoutExpired:
            raise PocketTTSError(f"Pocket TTS segment {index + 1} timed out after 300 seconds.") from None
        except (OSError, UnicodeError):
            raise PocketTTSError(f"Pocket TTS segment {index + 1} could not run.") from None
        if result.returncode != 0:
            raise PocketTTSError(f"Pocket TTS segment {index + 1} exited with code {result.returncode}.")
        try:
            with wave.open(str(output), "rb") as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                channels = audio.getnchannels()
                width = audio.getsampwidth()
                data = audio.readframes(frames)
                if (
                    frames <= 0 or rate <= 0 or audio.getcomptype() != "NONE"
                    or len(data) != frames * channels * width
                ):
                    raise ValueError("Invalid or truncated PCM")
                duration = frames / rate
        except (OSError, EOFError, wave.Error, ValueError):
            raise PocketTTSError(f"Pocket TTS segment {index + 1} returned invalid or empty WAV.") from None
        segment["_file"] = output
        print(f"[AUDIO] Pocket TTS segment {index + 1}: {duration:.2f}s WAV.")
    print(f"[AUDIO] Pocket TTS CPU synthesis completed in {time.monotonic() - started:.1f}s.")
    return True


def _synthesize_openai_segments(segments, tmp_dir):
    """Synthesize all segments once with OpenAI; fail fast for Edge fallback."""
    from openai import OpenAI, OpenAIError

    api_key = os.environ.get("OPENAI_KEY")
    if not api_key:
        return False

    speech_segments = _speech_segments(segments)
    client = OpenAI(api_key=api_key)
    print(
        f"[AUDIO] Synthesizing {len(speech_segments)} speech segments with "
        f"OpenAI ({OPENAI_TTS_MODEL})..."
    )

    try:
        for index, segment in enumerate(speech_segments):
            tmp_file = tmp_dir / f"seg_{index:04d}.mp3"
            response = client.audio.speech.create(
                model=OPENAI_TTS_MODEL,
                voice=OPENAI_VOICE_MAP[segment["speaker"]],
                input=segment["text"],
                instructions=HOST_VOCAL_INSTRUCTIONS[segment["speaker"]],
                response_format="mp3",
            )
            response.stream_to_file(tmp_file)
            if not tmp_file.exists() or tmp_file.stat().st_size == 0:
                raise RuntimeError("OpenAI returned an empty audio segment")
            segment["_file"] = tmp_file
            if (index + 1) % 25 == 0:
                print(f"   [OK] {index + 1}/{len(speech_segments)} segments synthesized")
    except (OpenAIError, OSError, RuntimeError) as error:
        print(
            f"[WARN]  OpenAI TTS failed after a single attempt for the current "
            f"segment: {error}"
        )
        return False

    print(f"   [OK] All {len(speech_segments)} OpenAI segments synthesized")
    return True


def _synthesize_edge_segments(segments, tmp_dir):
    """Synthesize all segments with the free Edge neural TTS fallback."""
    import asyncio

    try:
        import edge_tts
    except ImportError:
        print("[WARN]  edge-tts not installed, skipping TTS fallback")
        return False

    speech_segments = _speech_segments(segments)
    print(f"[AUDIO] Synthesizing {len(speech_segments)} speech segments with Edge TTS...")

    async def synthesize_all():
        for i, seg in enumerate(speech_segments):
            tmp_file = tmp_dir / f"seg_{i:04d}.mp3"
            communicate = edge_tts.Communicate(
                seg["text"],
                EDGE_VOICE_MAP[seg["speaker"]],
                rate=EDGE_TTS_RATE,
            )
            await communicate.save(str(tmp_file))
            seg["_file"] = tmp_file
            if (i + 1) % 25 == 0:
                print(f"   [OK] {i + 1}/{len(speech_segments)} segments synthesized")
        print(f"   [OK] All {len(speech_segments)} segments synthesized")

    try:
        asyncio.run(synthesize_all())
    except Exception as e:
        print(f"[WARN]  Edge TTS synthesis failed: {e}")
        return False
    return True


def _assemble_audio(segments, output_path):
    """Concatenate provider output with consistent host loudness."""
    from pydub import AudioSegment

    combined = AudioSegment.empty()

    for seg in segments:
        if seg["type"] == "pause":
            combined += AudioSegment.silent(duration=seg["ms"])
        elif seg["type"] == "speech" and "_file" in seg:
            try:
                if seg["_file"].suffix == ".wav":
                    audio_seg = AudioSegment.from_wav(str(seg["_file"]))
                else:
                    audio_seg = AudioSegment.from_mp3(str(seg["_file"]))
                if audio_seg.dBFS != float("-inf"):
                    gain_db = min(
                        TARGET_SEGMENT_DBFS - audio_seg.dBFS,
                        MAX_SEGMENT_GAIN_DB,
                    )
                    audio_seg = audio_seg.apply_gain(gain_db)
                combined += audio_seg
            except Exception as e:
                print(f"[WARN]  Failed to load segment: {e}")
                return False

    combined.export(str(output_path), format="mp3", bitrate=MP3_BITRATE)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Audio saved: {output_path} ({size_mb:.1f} MB)")
    return True


def text_to_speech(script, output_path):
    """Synthesize with the explicit provider and atomically publish mixed audio."""
    provider = os.environ.get("TTS_PROVIDER", "auto").strip().lower()
    if provider not in {"pocket", "edge", "auto"}:
        raise ValueError("TTS_PROVIDER must be pocket, edge, or auto.")
    _validate_dialogue(script)

    try:
        import pydub  # noqa: F401
    except ImportError:
        if provider in {"pocket", "edge"}:
            raise RuntimeError("pydub is required for audio publication.") from None
        print("[WARN]  pydub not installed, skipping TTS")
        return False

    segments = _parse_speech_segments(script)
    speech_segments = _speech_segments(segments)
    if not speech_segments:
        print("[WARN]  No speech segments found in script")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = output_path.parent / "_tts_tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(exist_ok=True)
    pending_output = tmp_dir / "episode.mp3"

    success = False
    try:
        if provider == "pocket":
            success = _synthesize_pocket_segments(segments, tmp_dir)
        elif provider == "edge":
            success = _synthesize_edge_segments(segments, tmp_dir)
        elif os.environ.get("OPENAI_KEY"):
            success = _synthesize_openai_segments(segments, tmp_dir)
            if not success:
                print("[WARN]  Falling back to Edge TTS for the complete episode...")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                tmp_dir.mkdir(exist_ok=True)
                for segment in speech_segments:
                    segment.pop("_file", None)
        else:
            print("[INFO]  OPENAI_KEY is absent; using Edge TTS fallback")

        if not success and provider == "auto":
            success = _synthesize_edge_segments(segments, tmp_dir)

        if not success or not _assemble_audio(segments, pending_output):
            if provider in {"pocket", "edge"}:
                raise RuntimeError(f"{provider} audio synthesis or assembly failed; publication blocked.")
            return False
        if not _post_process_audio(pending_output):
            if provider in {"pocket", "edge"}:
                raise RuntimeError(f"{provider} audio post-processing failed; publication blocked.")
            return False
        pending_output.replace(output_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return True


def _generate_chapters(script, date_str):
    """Generate a Podcast 2.0 chapters JSON from the script structure.
    Estimates timestamps from the configured conversational pacing."""
    import json as json_mod

    chapters_dir = PROJECT_DIR / "static" / "podcast" / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    lines = script.strip().split("\n")
    sections = []
    current_section_words = 0
    current_title = "Teaser"
    section_idx = 0

    for line in lines:
        line = line.strip()
        if line == "[INTRO]":
            sections.append({"title": current_title, "words": current_section_words})
            current_title = "Opening"
            current_section_words = 0
            section_idx += 1
        elif line == "[TOPIC_CHANGE]":
            sections.append({"title": current_title, "words": current_section_words})
            section_idx += 1
            current_title = f"Topic {section_idx}"
            current_section_words = 0
        else:
            # Count words (strip speaker prefix)
            for host in (HOST_A, HOST_B, HOST_C):
                if line.startswith(f"{host}:"):
                    line = line[len(f"{host}:"):].strip()
                    break
            current_section_words += len(line.split())

            # Try to extract a meaningful title from first substantial line of section
            if current_title.startswith("Topic") and len(line) > 30:
                # Use first substantive line as chapter title (truncated)
                clean = re.sub(r"\(laughs?\)", "", line, flags=re.IGNORECASE).strip()
                if len(clean) > 20:
                    current_title = clean[:60].rsplit(" ", 1)[0] + "..."

    # Last section
    if current_section_words > 0:
        sections.append({"title": current_title, "words": current_section_words})

    # Convert word counts to timestamps
    chapters = []
    elapsed_seconds = 0
    for sec in sections:
        chapters.append({
            "startTime": round(elapsed_seconds),
            "title": sec["title"],
        })
        duration = (sec["words"] / CHAPTER_WORDS_PER_MINUTE) * 60
        elapsed_seconds += duration

    chapters_data = {"version": "1.2.0", "chapters": chapters}
    output = chapters_dir / f"{date_str}.json"
    with open(output, "w", encoding="utf-8") as f:
        json_mod.dump(chapters_data, f, ensure_ascii=False, indent=2)
    print(f"[CHAPTERS] Chapters generated: {len(chapters)} chapters to {output.name}")


def run(date_str=None, reuse_script=False):
    """Generate podcast for the given date. Returns the audio path or None."""
    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    script_file = DATA_DIR / f"podcast_script_{date}.txt"
    if reuse_script:
        script = script_file.read_text(encoding="utf-8").strip()
        _validate_dialogue(script)
        minimum, maximum = _script_word_range(PODCAST_TARGET_MINUTES)
        words = _spoken_word_count(script)
        if not minimum <= words <= maximum:
            raise ValueError(f"Saved podcast has {words} words; required {minimum}-{maximum}.")
        print(f"[RECOVERY] Reusing saved {words}-word podcast script; no LLM calls.")
        _generate_chapters(script, date)
        audio_path = AUDIO_DIR / f"{date}.mp3"
        return audio_path if text_to_speech(script, audio_path) else None

    # Try synthesis file first, fall back to the published post
    synthesis_file = DATA_DIR / f"synthesis_{date}.md"
    post_file = PROJECT_DIR / "content" / "posts" / f"{date}-daily.md"

    if synthesis_file.exists():
        with open(synthesis_file, "r", encoding="utf-8") as f:
            synthesis_content = f.read()
    elif post_file.exists():
        print("[INFO]  Synthesis file not found, using published post as source")
        with open(post_file, "r", encoding="utf-8") as f:
            raw = f.read()
        # Strip YAML frontmatter and audio player
        synthesis_content = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.DOTALL)
        synthesis_content = re.sub(r"<audio.*?</audio>", "", synthesis_content, flags=re.DOTALL)
    else:
        print(f"[WARN]  No synthesis or post found for {date}, skipping podcast")
        return None

    # Step 1: Generate dialogue script
    script = generate_podcast_script(
        synthesis_content, checkpoint_path=DATA_DIR / f"podcast_sections_{date}.json",
    )
    if not script:
        return None

    # Save script for reference
    with open(script_file, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[SAVE] Script saved: {script_file}")

    # Step 1.5: Generate chapters JSON from script structure
    _generate_chapters(script, date)

    # Step 2: Convert to audio (OpenAI primary, Edge TTS fallback)
    audio_path = AUDIO_DIR / f"{date}.mp3"
    success = text_to_speech(script, audio_path)

    if success:
        return audio_path
    return None


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else None
    run(date)
