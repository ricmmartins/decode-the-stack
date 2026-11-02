import unittest

from pipeline import podcast


class EnglishPodcastTests(unittest.TestCase):
    def test_duration_targets_fifteen_minutes(self):
        self.assertEqual(podcast.DEFAULT_PODCAST_TARGET_MINUTES, 15)
        self.assertEqual(podcast._script_word_range(15), (2200, 2400))

    def test_three_distinct_english_hosts_and_voices_are_configured(self):
        self.assertEqual((podcast.HOST_A, podcast.HOST_B, podcast.HOST_C), ("Anna", "Maria", "Alex"))
        self.assertEqual(
            set(podcast.OPENAI_VOICE_MAP),
            {"Anna", "Maria", "Alex"},
        )
        self.assertEqual(len(set(podcast.OPENAI_VOICE_MAP.values())), 3)
        self.assertTrue(all("English-language" in instruction for instruction in podcast.HOST_VOCAL_INSTRUCTIONS.values()))

    def test_dialogue_parser_handles_english_hosts_and_chapter_markers(self):
        script = """Anna: Welcome to Decode the Stack.
[INTRO]
Maria: Here is what the reporting confirms.
[TOPIC_CHANGE]
Alex: Let us look at the engineering trade-offs."""
        segments = podcast._parse_speech_segments(script)
        self.assertEqual(
            [segment["speaker"] for segment in segments if segment["type"] == "speech"],
            ["Anna", "Maria", "Alex"],
        )
        self.assertEqual(
            [segment["ms"] for segment in segments if segment["type"] == "pause"],
            [podcast.INTRO_PAUSE_MS, podcast.TOPIC_CHANGE_PAUSE_MS],
        )

    def test_script_length_uses_only_spoken_words(self):
        script = (
            "Anna: Welcome to the show.\n"
            "[INTRO]\n"
            "Maria: Here is the context."
        )
        self.assertEqual(podcast._spoken_word_count(script), 8)


if __name__ == "__main__":
    unittest.main()
