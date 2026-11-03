import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import podcast
import pydub


SCRIPT = "Anna: Verified first story.\n[INTRO]\nMaria: Technical context.\nPedro: Practical question."


def write_wav(path):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(b"\x01\x00" * 2400)


class PocketTTSTests(unittest.TestCase):
    def test_cli_voice_mapping_and_validated_wav(self):
        def generate(args, **kwargs):
            write_wav(Path(args[args.index("--output-path") + 1]))
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as directory:
            segments = podcast._parse_speech_segments(SCRIPT)
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(podcast.shutil, "which", return_value="/pocket-tts"),
                patch.object(podcast.subprocess, "run", side_effect=generate) as call,
            ):
                self.assertTrue(podcast._synthesize_pocket_segments(segments, Path(directory)))
            self.assertEqual(call.call_count, 3)
            self.assertEqual(
                [entry.args[0][entry.args[0].index("--voice") + 1] for entry in call.call_args_list],
                ["vera", "anna", "bill_boerst"],
            )
            for entry in call.call_args_list:
                self.assertEqual(entry.args[0][:4], ["/pocket-tts", "generate", "--language", "english"])
                self.assertEqual(entry.kwargs["timeout"], 300)
                self.assertEqual(entry.args[0][entry.args[0].index("--text") + 1], "-")
                self.assertTrue(entry.kwargs["input"])
                self.assertNotIn("shell", entry.kwargs)
            self.assertTrue(all(s["_file"].suffix == ".wav" for s in podcast._speech_segments(segments)))

    def test_failed_missing_truncated_empty_and_timeout_outputs_block(self):
        def invalid(args, **kwargs):
            Path(args[-1]).write_bytes(b"not WAV")
            return SimpleNamespace(returncode=0)
        def empty(args, **kwargs):
            with wave.open(args[-1], "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
            return SimpleNamespace(returncode=0)
        for effect in (
            lambda *args, **kwargs: SimpleNamespace(returncode=1),
            lambda *args, **kwargs: SimpleNamespace(returncode=0),
            invalid, empty, subprocess.TimeoutExpired("pocket", 300), OSError("private detail"),
        ):
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.dict(os.environ, {}, clear=True),
                patch.object(podcast.shutil, "which", return_value="/pocket-tts"),
                patch.object(podcast.subprocess, "run", side_effect=effect),
                self.assertRaises(podcast.PocketTTSError),
            ):
                podcast._synthesize_pocket_segments(podcast._parse_speech_segments(SCRIPT), Path(directory))

    def test_missing_executable_and_unattributed_voice_fail_before_launch(self):
        for executable, env in ((None, {}), ("/pocket", {"POCKET_TTS_VOICE_ANNA": "unlicensed"})):
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(podcast.shutil, "which", return_value=executable),
                patch.object(podcast.subprocess, "run") as call,
                self.assertRaises(podcast.PocketTTSError),
            ):
                podcast._synthesize_pocket_segments([], Path("."))
            call.assert_not_called()

    def test_pocket_no_paid_fallback_and_atomic_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "episode.mp3"
            output.write_bytes(b"previous-episode")
            with (
                patch.dict(os.environ, {"TTS_PROVIDER": "pocket", "OPENAI_KEY": "unused"}, clear=True),
                patch.object(podcast, "_synthesize_openai_segments") as paid,
                patch.object(podcast, "_synthesize_edge_segments") as edge,
                patch.object(podcast, "_synthesize_pocket_segments", return_value=True),
                patch.object(podcast, "_assemble_audio", side_effect=lambda segments, path: (
                    path.write_bytes(b"new-audio") > 0
                )),
                patch.object(podcast, "_post_process_audio", return_value=True),
            ):
                self.assertTrue(podcast.text_to_speech(SCRIPT, output))
            paid.assert_not_called()
            edge.assert_not_called()
            self.assertEqual(output.read_bytes(), b"new-audio")
            self.assertFalse((Path(directory) / "_tts_tmp").exists())

    def test_failure_preserves_existing_episode_and_removes_partial_files(self):
        for phase in ("synthesis", "assembly", "postprocess"):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "episode.mp3"
                output.write_bytes(b"previous-episode")
                with (
                    patch.dict(os.environ, {"TTS_PROVIDER": "pocket"}, clear=True),
                    patch.object(podcast, "_synthesize_pocket_segments",
                        side_effect=podcast.PocketTTSError("failed") if phase == "synthesis" else None,
                        return_value=True),
                    patch.object(podcast, "_assemble_audio", return_value=phase != "assembly"),
                    patch.object(podcast, "_post_process_audio", return_value=phase != "postprocess"),
                    self.assertRaises(RuntimeError),
                ):
                    podcast.text_to_speech(SCRIPT, output)
                self.assertEqual(output.read_bytes(), b"previous-episode")
                self.assertFalse((Path(directory) / "_tts_tmp").exists())

    def test_edge_rollback_does_not_use_pocket_or_openai(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {"TTS_PROVIDER": "edge", "OPENAI_KEY": "unused"}, clear=True),
            patch.object(podcast, "_synthesize_pocket_segments") as pocket,
            patch.object(podcast, "_synthesize_openai_segments") as paid,
            patch.object(podcast, "_synthesize_edge_segments", return_value=True) as edge,
            patch.object(podcast, "_assemble_audio", side_effect=lambda segments, path: (
                path.write_bytes(b"edge-audio") > 0
            )),
            patch.object(podcast, "_post_process_audio", return_value=True),
        ):
            self.assertTrue(podcast.text_to_speech(SCRIPT, Path(directory) / "episode.mp3"))
        edge.assert_called_once()
        pocket.assert_not_called()
        paid.assert_not_called()
