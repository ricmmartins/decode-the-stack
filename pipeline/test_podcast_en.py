import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from pipeline import podcast, synthesize


class EnglishPodcastTests(unittest.TestCase):
    def test_saved_script_recovery_does_not_call_language_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = self.dialogue(2300)
            (root / "podcast_script_2026-11-02.txt").write_text(script, encoding="utf-8")
            with (
                patch.object(podcast, "DATA_DIR", root),
                patch.object(podcast, "AUDIO_DIR", root),
                patch.object(podcast, "generate_podcast_script") as generate,
                patch.object(podcast, "_generate_chapters") as chapters,
                patch.object(podcast, "text_to_speech", return_value=True) as speak,
            ):
                result = podcast.run("2026-11-02", reuse_script=True)
            generate.assert_not_called()
            chapters.assert_called_once_with(script, "2026-11-02")
            speak.assert_called_once_with(script, root / "2026-11-02.mp3")
            self.assertEqual(result, root / "2026-11-02.mp3")

    def test_missing_or_short_saved_script_never_calls_tts_or_llm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(podcast, "DATA_DIR", root),
                patch.object(podcast, "generate_podcast_script") as generate,
                patch.object(podcast, "text_to_speech") as speak,
            ):
                with self.assertRaises(FileNotFoundError):
                    podcast.run("2026-11-02", reuse_script=True)
                (root / "podcast_script_2026-11-02.txt").write_text(self.dialogue(100), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "required 2200-2400"):
                    podcast.run("2026-11-02", reuse_script=True)
            generate.assert_not_called()
            speak.assert_not_called()

    def test_music_bed_has_controlled_audible_level_loop_and_fades(self):
        from pydub import AudioSegment
        from pydub.generators import Sine

        speech = AudioSegment.silent(duration=12000, frame_rate=44100)
        music = Sine(440).to_audio_segment(duration=4000).apply_gain(-10)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / "music.mp3"
            asset.touch()
            output = root / "episode.mp3"
            captured = []

            def export(segment, path, **kwargs):
                captured.append(segment)
                Path(path).write_bytes(b"mixed")

            with (
                patch.object(podcast, "BG_MUSIC_PATH", asset),
                patch.object(AudioSegment, "from_mp3", side_effect=[speech, music]),
                patch.object(AudioSegment, "export", new=export),
            ):
                podcast._overlay_background_music(output)
            mixed = captured[0]
            self.assertEqual(len(mixed), len(speech))
            self.assertAlmostEqual(mixed[4000:5000].dBFS, -28, delta=0.2)
            self.assertGreater(mixed[11000:11500].rms, 0)
            self.assertLess(mixed[0:500].rms, mixed[3000:3500].rms)
            self.assertLess(mixed[-500:].rms, mixed[-5500:-5000].rms)
            self.assertEqual(output.read_bytes(), b"mixed")

    def test_quiet_music_intro_is_lifted_without_changing_full_bed_target(self):
        from pydub.generators import Sine
        music = (
            Sine(440).to_audio_segment(duration=5000).apply_gain(-20)
            + Sine(440).to_audio_segment(duration=5000).apply_gain(-8)
        )
        bed = podcast._prepare_background_music(music, 20000)
        self.assertGreater(bed[3500:4500].dBFS, -34)
        self.assertLess(bed[6500:7500].dBFS, -25)
        self.assertGreater(bed[13500:14500].rms, 0)

    def test_mix_reserves_headroom_without_clipping(self):
        from pydub.generators import Sine
        speech = Sine(440).to_audio_segment(duration=1000)
        mixed = podcast._mix_background_audio(speech, speech)
        self.assertAlmostEqual(mixed.max_dBFS, -1, delta=0.01)
        self.assertEqual(len(mixed), len(speech))

    def test_missing_music_fails_instead_of_publishing_dry_episode(self):
        with (
            patch.object(podcast, "BG_MUSIC_PATH", Path("nonexistent-music.mp3")),
            self.assertRaisesRegex(FileNotFoundError, "Required podcast background music"),
        ):
            podcast._overlay_background_music(Path("episode.mp3"))

    def test_mix_aligns_submillisecond_sample_rounding(self):
        from pydub.generators import Sine
        speech = Sine(440).to_audio_segment(duration=1000)
        music = speech._spawn(speech.raw_data[:-2])
        mixed = podcast._mix_background_audio(speech, music)
        self.assertEqual(mixed.frame_count(), speech.frame_count())
        with self.assertRaisesRegex(ValueError, "same duration"):
            podcast._mix_background_audio(speech, music[:900])

    def test_duration_targets_fifteen_minutes(self):
        self.assertEqual(podcast.DEFAULT_PODCAST_TARGET_MINUTES, 15)
        self.assertEqual(podcast._script_word_range(15), (2200, 2400))

    def test_three_distinct_english_hosts_and_voices_are_configured(self):
        self.assertEqual((podcast.HOST_A, podcast.HOST_B, podcast.HOST_C), ("Anna", "Maria", "Pedro"))
        self.assertEqual(
            set(podcast.OPENAI_VOICE_MAP),
            {"Anna", "Maria", "Pedro"},
        )
        self.assertEqual(len(set(podcast.OPENAI_VOICE_MAP.values())), 3)
        self.assertTrue(all("English-language" in instruction for instruction in podcast.HOST_VOCAL_INSTRUCTIONS.values()))

    def test_dialogue_parser_handles_english_hosts_and_chapter_markers(self):
        script = """Anna: Welcome to Decode the Stack.
[INTRO]
Maria: Here is what the reporting confirms.
[TOPIC_CHANGE]
Pedro: Let us look at the engineering trade-offs."""
        segments = podcast._parse_speech_segments(script)
        self.assertEqual(
            [segment["speaker"] for segment in segments if segment["type"] == "speech"],
            ["Anna", "Maria", "Pedro"],
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
            for host, size in zip(("Anna", "Maria", "Pedro"), sizes)
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

    def test_structured_turns_keep_every_word_and_explicit_host(self):
        response = json.dumps({"turns": [
            {"speaker": "Anna", "text": "A teaser.\nWelcome to Decode the Stack."},
            {"marker": "[INTRO]"},
            {"speaker": "Maria", "text": "Technical context."},
            {"speaker": "Pedro", "text": "A practical question."},
        ]})
        self.assertEqual(podcast._decode_script_section(response), (
            "Anna: A teaser. Welcome to Decode the Stack.\n[INTRO]\n"
            "Maria: Technical context.\nPedro: A practical question."
        ))

    def test_structured_turns_reject_unattributed_narration_and_unknown_hosts(self):
        for turn in (
            {"text": "Welcome without a speaker."},
            {"speaker": "Narrator", "text": "Welcome."},
            {"speaker": "Anna", "text": ""},
            {"speaker": "Anna", "text": "Welcome.", "extra": "Unspoken words."},
            {"speaker": "Anna", "text": "Welcome [INTRO]"},
        ):
            with self.subTest(turn=turn), self.assertRaises(ValueError):
                podcast._decode_script_section(json.dumps({"turns": [turn]}))
        with self.assertRaises(ValueError):
            podcast._decode_script_section(
                "Anna: A teaser.\nWelcome to Decode the Stack, where we dive deep.\n"
                "Maria: Context.\nPedro: A question."
            )

    def test_unlabeled_welcome_is_retried_as_structured_turns_without_dropping_words(self):
        bad = "Anna: Teaser.\nWelcome to Decode the Stack.\nMaria: Context.\nPedro: Question."
        good = json.dumps({"turns": [
            {"speaker": host, "text": " ".join(["context"] * size)}
            for host, size in (("Anna", 126), ("Maria", 126), ("Pedro", 128))
        ]})
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", side_effect=[bad, *[good] * 6]) as call,
        ):
            script = podcast.generate_podcast_script(synthesis)
        self.assertEqual(podcast._spoken_word_count(script), 2280)
        self.assertEqual(call.call_count, 7)
        self.assertIn("required JSON turns", call.call_args_list[1].args[0])

    def test_repeated_unlabeled_welcome_still_blocks_generation(self):
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict("sys.modules", {"synthesize": synthesize}),
            patch.object(synthesize, "_call_llm", return_value="Welcome to Decode the Stack.") as call,
            self.assertRaisesRegex(ValueError, "unrecognized dialogue line"),
        ):
            podcast.generate_podcast_script(synthesis)
        self.assertEqual(call.call_count, 2)

    def test_tts_fallback_restarts_entire_three_host_episode(self):
        def partial_openai(segments, directory):
            podcast._speech_segments(segments)[0]["_file"] = directory / "partial.mp3"
            return False

        def complete_edge(segments, directory):
            speech = podcast._speech_segments(segments)
            self.assertEqual({segment["speaker"] for segment in speech}, {"Anna", "Maria", "Pedro"})
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
