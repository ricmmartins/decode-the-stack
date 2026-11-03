import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import diagnose_editorial as diagnose_humanizer
import humanizer


class HumanizerDiagnosticTests(unittest.TestCase):
    def test_one_rejected_review_saves_evidence_without_publishing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "diagnostic"

            def reject(original, diagnostic_dir):
                diagnostic_dir.mkdir(exist_ok=True)
                (diagnostic_dir / "original.txt").write_text(original)
                (diagnostic_dir / "candidate.txt").write_text("Candidate text.")
                (diagnostic_dir / "assessment.json").write_text('{"facts_preserved":false}')
                raise humanizer.HumanizerMeaningError("Rejected")

            with (
                patch.object(diagnose_humanizer, "validate_saved_audio"),
                patch.object(diagnose_humanizer, "generate_post", return_value="Original text.") as draft,
                patch.object(diagnose_humanizer, "review_post", side_effect=reject) as review,
                patch.object(diagnose_humanizer, "_json_response", return_value={"differences": []}) as explain,
            ):
                self.assertFalse(diagnose_humanizer.diagnose("2026-11-03", output))
            draft.assert_called_once_with("2026-11-03", has_audio=True, draft_only=True)
            self.assertEqual(review.call_count, 1)
            self.assertEqual(explain.call_count, 1)
            self.assertEqual(json.loads((output / "explanation.json").read_text()), {"differences": []})

    def test_repository_output_directory_is_rejected_before_provider_calls(self):
        with (
            patch.object(diagnose_humanizer, "validate_saved_audio") as validate,
            self.assertRaisesRegex(ValueError, "outside"),
        ):
            diagnose_humanizer.diagnose("2026-11-03", humanizer.PROJECT_DIR / "data/rejected")
        validate.assert_not_called()
