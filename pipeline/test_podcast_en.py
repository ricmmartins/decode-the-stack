import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from pipeline import podcast, synthesize


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

    @staticmethod
    def dialogue(words):
        sizes = [words // 3, words // 3, words - 2 * (words // 3)]
        return "\n".join(
            f"{host}: " + " ".join(["context"] * size)
            for host, size in zip(("Anna", "Maria", "Alex"), sizes)
        )

    def test_bounded_sections_meet_full_duration_and_use_distinct_source_blocks(self):
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting {i}." for i in range(12))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", return_value=self.dialogue(380)) as call,
        ):
            script = podcast.generate_podcast_script(synthesis)
        self.assertEqual(podcast._spoken_word_count(script), 2280)
        self.assertEqual(call.call_count, 6)
        self.assertEqual(script.count("[TOPIC_CHANGE]"), 5)
        self.assertEqual(len({entry.args[1] for entry in call.call_args_list}), 6)

    def test_short_section_is_retried_without_rewriting_successful_sections(self):
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", side_effect=[
                self.dialogue(100), *[self.dialogue(380)] * 6,
            ]) as call,
        ):
            script = podcast.generate_podcast_script(synthesis)
        self.assertEqual(podcast._spoken_word_count(script), 2280)
        self.assertEqual(call.call_count, 7)
        self.assertEqual(call.call_args_list[0].args[1], call.call_args_list[1].args[1])

    def test_persistent_short_output_fails_instead_of_publishing_short_audio(self):
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", return_value=self.dialogue(100)) as call,
            self.assertRaisesRegex(ValueError, "required 300-450"),
        ):
            podcast.generate_podcast_script(synthesis)
        self.assertEqual(call.call_count, 2)

    def test_final_section_adapts_to_prior_lengths_without_weakening_total(self):
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", side_effect=[
                *[self.dialogue(350)] * 5, self.dialogue(500),
            ]) as call,
        ):
            script = podcast.generate_podcast_script(synthesis)
        self.assertEqual(podcast._spoken_word_count(script), 2250)
        self.assertIn("450-650 spoken words", call.call_args.args[0])

    def test_unspoken_narration_or_missing_host_is_rejected(self):
        for dialogue in ("Anna: Hello.\nMaria: Hello.", "Narrator: Hello."):
            with self.subTest(dialogue=dialogue), self.assertRaises(ValueError):
                podcast._validate_dialogue(dialogue)

    def test_tts_fallback_restarts_entire_three_host_episode(self):
        def partial_openai(segments, directory):
            podcast._speech_segments(segments)[0]["_file"] = directory / "partial.mp3"
            return False

        def complete_edge(segments, directory):
            speech = podcast._speech_segments(segments)
            self.assertEqual({segment["speaker"] for segment in speech}, {"Anna", "Maria", "Alex"})
            self.assertTrue(all("_file" not in segment for segment in speech))
            return True

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict("os.environ", {"OPENAI_KEY": "test-key"}),
                patch.object(podcast, "_synthesize_openai_segments", side_effect=partial_openai),
                patch.object(podcast, "_synthesize_edge_segments", side_effect=complete_edge),
                patch.object(podcast, "_assemble_audio", return_value=True),
                patch.object(podcast, "_post_process_audio", return_value=True),
            ):
                self.assertTrue(podcast.text_to_speech(self.dialogue(30), Path(directory) / "episode.mp3"))

    def test_failed_tts_never_assembles_partial_episode(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict("os.environ", {"OPENAI_KEY": "test-key"}),
                patch.object(podcast, "_synthesize_openai_segments", return_value=False),
                patch.object(podcast, "_synthesize_edge_segments", return_value=False),
                patch.object(podcast, "_assemble_audio") as assemble,
            ):
                self.assertFalse(podcast.text_to_speech(self.dialogue(30), Path(directory) / "episode.mp3"))
            assemble.assert_not_called()


if __name__ == "__main__":
    unittest.main()
