import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import run_pipeline


class RecoveryTests(unittest.TestCase):
    def test_saved_audio_validation_preserves_inputs_and_rejects_bad_chapters(self):
        import podcast
        from pydub import AudioSegment
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            script = data / "podcast_script_2026-11-03.txt"
            script.write_text("\n".join(
                f"{host}: " + " ".join(["context"] * count)
                for host, count in (("Anna", 760), ("Maria", 760), ("Pedro", 760))
            ), encoding="utf-8")
            audio_dir = root / "static/podcast/audio"
            audio_dir.mkdir(parents=True)
            audio = audio_dir / "2026-11-03.mp3"
            audio.write_bytes(b"ID3" + b"\0" * 2048)
            chapters = root / "static/podcast/chapters/2026-11-03.json"
            chapters.parent.mkdir()
            chapters.write_text('{"chapters":[{"startTime":0,"title":"Opening"}]}')
            before = {path: path.read_bytes() for path in (script, audio, chapters)}
            with (
                patch.object(podcast, "PROJECT_DIR", root),
                patch.object(podcast, "DATA_DIR", data),
                patch.object(podcast, "AUDIO_DIR", audio_dir),
                patch.object(AudioSegment, "from_mp3", return_value=AudioSegment.silent(duration=10000)) as decode,
                patch.object(podcast, "text_to_speech", side_effect=AssertionError("No TTS")),
                patch("synthesize._call_llm", side_effect=AssertionError("No LLM")),
            ):
                self.assertEqual(podcast.validate_saved_audio("2026-11-03"), audio)
                for path, content in before.items():
                    self.assertEqual(path.read_bytes(), content)
                chapters.write_text('{"chapters":[{"startTime":-1}]}')
                decode.reset_mock()
                with self.assertRaisesRegex(ValueError, "timestamps"):
                    podcast.validate_saved_audio("2026-11-03")
                decode.assert_not_called()

    def test_editorial_recovery_reuses_audio_and_analysis_without_generating_them(self):
        with tempfile.TemporaryDirectory() as directory:
            audio = Path(directory) / "episode.mp3"
            audio.write_bytes(b"ID3" + b"\0" * 2048)
            with (
                patch.object(run_pipeline, "_load_recovery_inputs", return_value=(10, 5, [], [])),
                patch.object(run_pipeline, "_prepare_synthesis", side_effect=AssertionError("No synthesis")),
                patch.object(run_pipeline, "validate_saved_audio", return_value=audio) as validate,
                patch.object(run_pipeline, "podcast_run", side_effect=AssertionError("No TTS or script")),
                patch.object(run_pipeline, "generate_post", return_value=("post.md", 20, 30)) as post,
                patch.object(run_pipeline, "generate_daily_stats"),
                patch.object(run_pipeline, "generate_trend_data"),
                patch.object(run_pipeline, "save_weekly_buffer"),
                patch.object(run_pipeline, "_try_weekly"),
                patch.object(run_pipeline, "generate_publication_stats"),
                patch.object(run_pipeline, "podcast_feed_run"),
            ):
                run_pipeline.run_pipeline("2026-11-03", force=True, reuse_synthesis=True, reuse_audio=True)
            validate.assert_called_once_with("2026-11-03")
            post.assert_called_once_with("2026-11-03", has_audio=True)
        with self.assertRaisesRegex(ValueError, "requires --reuse-synthesis"):
            run_pipeline.run_pipeline(reuse_audio=True)

    def test_script_recovery_requires_analysis_recovery_before_any_work(self):
        with (
            patch.object(run_pipeline, "_prepare_synthesis") as prepare,
            self.assertRaisesRegex(ValueError, "requires --reuse-synthesis"),
        ):
            run_pipeline.run_pipeline(force=True, reuse_podcast_script=True)
        prepare.assert_not_called()

    def test_script_recovery_selects_audio_only_not_text_publication(self):
        with (
            patch.object(run_pipeline, "_load_recovery_inputs", return_value=(376, 317, [], [])),
            patch.object(run_pipeline, "_publish_synthesis") as publish,
            patch.object(run_pipeline, "_publish_audio_only") as audio,
        ):
            run_pipeline.run_pipeline(
                "2026-11-02", force=True, reuse_synthesis=True, reuse_podcast_script=True,
            )
        publish.assert_not_called()
        audio.assert_called_once_with("2026-11-02")

    def test_audio_only_preserves_reviewed_text_and_never_calls_editorial_generation(self):
        import humanizer
        import synthesize
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / ".github/skills/humanizer/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_bytes(humanizer.SKILL_PATH.read_bytes())
            post = root / "content/posts/2026-11-02-daily.md"
            post.parent.mkdir(parents=True)
            post.write_text("---\ntitle: Reviewed edition\n---\nVerified text.\n", encoding="utf-8")
            receipt = root / "data/humanizer/2026-11-02-daily.json"
            receipt.parent.mkdir(parents=True)
            hashed = humanizer.digest(post.read_text(encoding="utf-8"))
            receipt.write_text(json.dumps({
                "version": 1, "post_sha256": hashed, "input_sha256": hashed,
                "skill_sha256": humanizer.SKILL_SHA256, "meaning_verified": True,
            }), encoding="utf-8")
            synthesis = root / "data/synthesis_2026-11-02.md"
            script = root / "data/podcast_script_2026-11-02.txt"
            synthesis.write_text("Saved analysis.", encoding="utf-8")
            script.write_text("Saved validated script.", encoding="utf-8")
            files = {path: path.read_bytes() for path in (post, receipt, synthesis, script)}
            audio = root / "episode.mp3"
            audio.write_bytes(b"audio" * 1000)
            with (
                patch.object(run_pipeline, "PROJECT_DIR", root),
                patch.object(run_pipeline, "podcast_run", return_value=audio) as speak,
                patch.object(run_pipeline, "podcast_feed_run") as feed,
                patch.object(run_pipeline, "generate_post", side_effect=AssertionError("No post rewrite")),
                patch.object(run_pipeline, "generate_daily_stats", side_effect=AssertionError("No stats rewrite")),
                patch.object(run_pipeline, "weekly_run", side_effect=AssertionError("No weekly generation")),
                patch.object(synthesize, "_call_llm", side_effect=AssertionError("No LLM")),
            ):
                run_pipeline._publish_audio_only("2026-11-02")
                speak.assert_called_once_with("2026-11-02", reuse_script=True)
                feed.assert_called_once()
                for path, content in files.items():
                    self.assertEqual(path.read_bytes(), content)
                post.write_text("Tampered text.", encoding="utf-8")
                speak.reset_mock()
                with self.assertRaises(humanizer.HumanizerError):
                    run_pipeline._publish_audio_only("2026-11-02")
                speak.assert_not_called()
                receipt.unlink()
                with self.assertRaises(humanizer.HumanizerError):
                    run_pipeline._publish_audio_only("2026-11-02")

    def test_reuses_analysis_without_remote_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            data.mkdir()
            (data / "synthesis_2026-11-02.md").write_text("Verified English synthesis.", encoding="utf-8")
            for name in (
                "raw/articles", "clustered/stories", "ranked/top", "ranked/quick",
            ):
                path = data / f"{name}_2026-11-02.json"
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps([{"title": name}]), encoding="utf-8")
            with (
                patch.object(run_pipeline, "PROJECT_DIR", root),
                patch.object(run_pipeline, "CONTENT_DIR", root / "posts"),
                patch.object(run_pipeline, "_prepare_synthesis") as prepare,
                patch.object(run_pipeline, "_publish_synthesis") as publish,
            ):
                run_pipeline.run_pipeline("2026-11-02", force=True, reuse_synthesis=True)
        prepare.assert_not_called()
        self.assertEqual(publish.call_args.args[:3], ("2026-11-02", 1, 1))

    def test_missing_recovery_data_does_not_fall_back_to_new_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(run_pipeline, "PROJECT_DIR", Path(directory)),
                patch.object(run_pipeline, "CONTENT_DIR", Path(directory) / "posts"),
                patch.object(run_pipeline, "_prepare_synthesis") as prepare,
                self.assertRaisesRegex(ValueError, "No nonempty recovered synthesis"),
            ):
                run_pipeline.run_pipeline("2026-11-02", force=True, reuse_synthesis=True)
        prepare.assert_not_called()
