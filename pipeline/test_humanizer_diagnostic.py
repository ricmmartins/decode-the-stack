import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import diagnose_editorial as diagnose_humanizer
import humanizer


class HumanizerDiagnosticTests(unittest.TestCase):
    def test_correction_restores_only_selected_original_blocks_and_binds_source(self):
        original = "---\ntitle: Test\n---\n\nOriginal provenance.\n\nOriginal interpretation."
        candidate = original.replace("Original provenance.", "Lost provenance.").replace(
            "Original interpretation.", "Source attribution."
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "original.txt").write_text(original, encoding="utf-8")
            (source / "candidate.txt").write_bytes(candidate.encode("utf-8"))
            (source / "assessment.json").write_text(json.dumps({
                "facts_preserved": False, "names_preserved": True,
                "attribution_preserved": False, "no_new_claims": True,
            }))
            hashed = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
            corrected = diagnose_humanizer.corrected_candidate(original, source, hashed, [2, 4])
            self.assertEqual(corrected, original)
            with self.assertRaisesRegex(ValueError, "current generated draft"):
                diagnose_humanizer.corrected_candidate(original + "Changed", source, hashed, [2, 4])
            with self.assertRaisesRegex(ValueError, "selected hash"):
                diagnose_humanizer.corrected_candidate(original, source, "bad", [2, 4])

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

    def test_corrected_candidate_rejection_never_rewrites_or_calls_explanation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "diagnostic"
            with (
                patch.object(diagnose_humanizer, "validate_saved_audio"),
                patch.object(diagnose_humanizer, "generate_post", return_value="Original"),
                patch.object(diagnose_humanizer, "corrected_candidate", return_value="Corrected"),
                patch.object(diagnose_humanizer, "review_post", side_effect=humanizer.HumanizerMeaningError("Rejected")) as review,
                patch.object(diagnose_humanizer, "_json_response") as explain,
            ):
                self.assertFalse(diagnose_humanizer.diagnose(
                    "2026-11-03", output, candidate_dir="selected", candidate_sha256="hash", restore_blocks=[2, 4],
                ))
            review.assert_called_once_with("Original", diagnostic_dir=output.resolve(), candidate="Corrected")
            explain.assert_not_called()
            self.assertFalse((output / "approved-post.txt").exists())
            self.assertFalse((output / "receipt.json").exists())
