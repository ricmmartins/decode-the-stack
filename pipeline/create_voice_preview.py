"""Generate a bounded free Edge audition, never an RSS episode."""

import asyncio
import tempfile
from pathlib import Path

import edge_tts
from pydub import AudioSegment
from pydub.silence import detect_leading_silence

import podcast


TURNS = (
    ("Anna", "I'm Anna. Welcome to Decode the Stack. Today, we're looking at how developers make their tools more reliable."),
    ("Maria", "I'm Maria. One developer described moving from vibe coding to prompt contracts. The idea is to write down what you expect before asking an AI tool to build it."),
    ("Pedro", "And I'm Pedro. So, clearer instructions up front. Does that help the rest of the team, too?"),
    ("Anna", "It can. Explicit expectations give people something concrete to review. But changing the way a team works takes time."),
    ("Maria", "Right. It's one developer's experience, not proof that every team should work the same way."),
    ("Pedro", "That's the useful distinction. Try the approach, look at the results, and decide whether it actually helps your team."),
)
OUTPUT = podcast.PROJECT_DIR / "static/podcast/previews/naturalness-sample.mp3"


def prepare_turn(audio):
    if not len(audio) or not audio.rms:
        raise ValueError("A preview turn must contain speech.")
    leading = detect_leading_silence(audio, silence_threshold=-55, chunk_size=10)
    trailing = detect_leading_silence(audio.reverse(), silence_threshold=-55, chunk_size=10)
    audio = audio[max(0, leading - 120):len(audio) - max(0, trailing - 180)]
    return audio.apply_gain(min(
        podcast.TARGET_SEGMENT_DBFS - audio.dBFS,
        podcast.MAX_SEGMENT_GAIN_DB,
        -1 - audio.max_dBFS,
    ))


async def main():
    combined = AudioSegment.empty()
    with tempfile.TemporaryDirectory() as directory:
        for index, (host, text) in enumerate(TURNS):
            path = Path(directory) / f"{index}.mp3"
            await edge_tts.Communicate(
                text, podcast.EDGE_VOICE_MAP[host], rate="+0%",
            ).save(str(path))
            combined += prepare_turn(AudioSegment.from_mp3(path))
    if not 30_000 <= len(combined) <= 60_000:
        raise ValueError(f"Preview must last 30-60 seconds, got {len(combined)} ms.")
    music = podcast._prepare_background_music(
        AudioSegment.from_mp3(podcast.BG_MUSIC_PATH), len(combined),
    )
    mixed = podcast._mix_background_audio(combined, music)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    mixed.export(OUTPUT, format="mp3", bitrate=podcast.MP3_BITRATE)
    print(f"Preview: {OUTPUT} ({len(mixed)/1000:.2f}s; 6 complete turns)")


if __name__ == "__main__":
    asyncio.run(main())
