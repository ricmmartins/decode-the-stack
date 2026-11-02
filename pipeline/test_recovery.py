import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import run_pipeline


class RecoveryTests(unittest.TestCase):
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
