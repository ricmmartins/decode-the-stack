import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import humanizer
import run_pipeline
import weekly_summary


POST = """---
title: "A release"
date: 2026-11-06T00:00:00Z
---

## Cloud

### [Original title](https://example.com/report)

Acme released version 12 with "exact words" and `safe_code`.

*Sources: [Publisher](https://example.com/source)*

```python
value = 42
```

<audio src="/podcast/audio/2026-11-06.mp3"></audio>
"""

VERDICT = dict(facts_preserved=True, names_preserved=True,
               attribution_preserved=True, no_new_claims=True)


def successful_editor(system, user, label):
    if label == "Humanizer editorial review":
        return user.replace("Acme released", "Acme shipped")
    return json.dumps(VERDICT)


class HumanizerTests(unittest.TestCase):
    def test_existing_approval_binds_original_output_and_skill_without_provider_calls(self):
        with patch.object(humanizer, "_call_llm", side_effect=successful_editor):
            output, receipt = humanizer.review_post(POST)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.install_skill(root)
            path = root / "content/posts/2026-11-06-daily.md"
            for original, candidate, record in (
                (POST + "Changed original", output, receipt),
                (POST, output + "Changed candidate", receipt),
                (POST, output, {**receipt, "meaning_verified": False}),
                (POST, output, {**receipt, "skill_sha256": "0" * 64}),
                (POST, output, {**receipt, "version": True}),
                (POST, output, {}),
            ):
                with patch.object(humanizer, "_call_llm") as call, self.assertRaises(humanizer.HumanizerError):
                    humanizer.write_reviewed_post(path, original, root, approved_review=(candidate, record))
                call.assert_not_called()
                self.assertFalse(path.exists())
                self.assertFalse((root / "data/humanizer").exists())
            with patch.object(humanizer, "_call_llm") as call:
                humanizer.write_reviewed_post(path, POST, root, approved_review=(output, receipt))
            call.assert_not_called()
            self.assertEqual(path.read_text(encoding="utf-8"), output)
            self.assertEqual(json.loads((root / "data/humanizer/2026-11-06-daily.json").read_text()), receipt)
            humanizer.validate_posts(root)

    def test_corrected_candidate_runs_same_invariants_and_one_semantic_check(self):
        candidate = POST.replace("Acme released", "Acme shipped")
        with patch.object(humanizer, "_call_llm", return_value=json.dumps(VERDICT)) as call:
            output, receipt = humanizer.review_post(POST, candidate=candidate)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.args[2], "Humanizer meaning verification")
        self.assertEqual(output, candidate)
        self.assertEqual(receipt["post_sha256"], humanizer.digest(candidate))
        self.assertEqual(receipt["input_sha256"], humanizer.digest(POST))
        for invalid in (
            candidate.replace('title: "A release"', 'title: "Changed title"'),
            candidate.replace("https://example.com/report", "https://other.example"),
            candidate.replace("version 12", "version 13"),
            candidate.replace("## Cloud", "## Security"),
            candidate.replace("Acme shipped", "Acme shipped\n\nNew paragraph"),
        ):
            with patch.object(humanizer, "_call_llm") as call, self.assertRaises(humanizer.HumanizerError):
                humanizer.review_post(POST, candidate=invalid)
            call.assert_not_called()
        with (
            patch.object(humanizer, "_call_llm", return_value=json.dumps({**VERDICT, "facts_preserved": False})) as call,
            self.assertRaises(humanizer.HumanizerMeaningError),
        ):
            humanizer.review_post(POST, candidate=candidate)
        self.assertEqual(call.call_count, 1)

    def test_meaning_retries_restart_original_and_never_publish_rejected_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "content/posts/test.md"
            accepted = {"version": 1}
            with patch.object(humanizer, "review_post", side_effect=[
                humanizer.HumanizerMeaningError("Rejected"),
                ("Accepted original meaning.", accepted),
            ]) as review:
                humanizer.write_reviewed_post(path, POST, root)
            self.assertEqual([call.args for call in review.call_args_list], [(POST,), (POST,)])
            self.assertEqual(path.read_text(), "Accepted original meaning.")
            path.unlink()
            receipt = root / "data/humanizer/test.json"
            receipt.unlink()
            with (
                patch.object(humanizer, "review_post", side_effect=humanizer.HumanizerMeaningError("Rejected")) as review,
                self.assertRaises(humanizer.HumanizerMeaningError),
            ):
                humanizer.write_reviewed_post(path, POST, root)
            self.assertEqual(review.call_count, 3)
            self.assertFalse(path.exists())
            self.assertFalse(receipt.exists())

    def install_skill(self, root):
        path = root / ".github/skills/humanizer/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(humanizer.SKILL_PATH, path)

    def test_loads_complete_pinned_skill_and_preserves_protected_material(self):
        with patch.object(humanizer, "_call_llm", side_effect=successful_editor) as call:
            output, receipt = humanizer.review_post(POST)
        self.assertEqual(call.call_count, 2)
        self.assertIn(humanizer.load_skill(), call.call_args_list[0].args[0])
        self.assertIn("Do not infer chronology or causation", call.call_args_list[0].args[0])
        self.assertIn("publication's interpretation", call.call_args_list[0].args[0])
        self.assertIn("evidentiary cautions as cautions", call.call_args_list[0].args[0])
        self.assertEqual(output, POST.replace("Acme released", "Acme shipped"))
        self.assertEqual(receipt["post_sha256"], humanizer.digest(output))
        self.assertEqual(receipt["skill_sha256"], humanizer.SKILL_SHA256)

    def test_missing_or_changed_skill_blocks_before_any_llm_call(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            for content in (None, "Changed skill"):
                if content:
                    path.write_text(content)
                with patch.object(humanizer, "SKILL_PATH", path), patch.object(humanizer, "_call_llm") as call:
                    with self.assertRaises(humanizer.HumanizerError):
                        humanizer.review_post(POST)
                    call.assert_not_called()

    def test_provider_failure_does_not_create_or_overwrite_post(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.install_skill(root)
            path = root / "content/posts/2026-11-06-daily.md"
            for existing in (False, True):
                if existing:
                    path.parent.mkdir(parents=True)
                    path.write_text("Existing publication")
                with patch.object(humanizer, "_call_llm", side_effect=humanizer.HumanizerError("Provider failed")):
                    with self.assertRaises(humanizer.HumanizerError):
                        humanizer.write_reviewed_post(path, POST, root)
                self.assertEqual(path.read_text() if path.exists() else None, "Existing publication" if existing else None)
                self.assertFalse((root / "data/humanizer").exists())

    def test_invalid_or_fact_changing_output_is_rejected(self):
        def malformed(system, user, label):
            return "Not JSON"

        def changed_token(system, user, label):
            return user.replace("__HUMANIZER_0__", "Different")

        def added_number(system, user, label):
            return user.replace("Acme released", "Acme released 99")

        def semantic_loss(system, user, label):
            return user if label == "Humanizer editorial review" else json.dumps({**VERDICT, "names_preserved": False})

        def missing_paragraph(system, user, label):
            return '{"paragraphs":[]}'

        def empty(system, user, label):
            return ""

        def added_link(system, user, label):
            return user.replace("Acme released", "See https://unverified.example. Acme released")

        for response in (malformed, changed_token, added_number, semantic_loss, missing_paragraph, empty, added_link):
            with self.subTest(response=response.__name__), patch.object(humanizer, "_call_llm", side_effect=response):
                with self.assertRaises(humanizer.HumanizerError):
                    humanizer.review_post(POST)

    def test_receipt_blocks_unreviewed_manual_additions_and_later_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.install_skill(root)
            path = root / "content/posts/2026-11-06-daily.md"
            with patch.object(humanizer, "_call_llm", side_effect=successful_editor):
                humanizer.write_reviewed_post(path, POST, root)
            humanizer.validate_posts(root)
            path.write_text(path.read_text() + "\nUnreviewed change.")
            with self.assertRaisesRegex(humanizer.HumanizerError, "Stale"):
                humanizer.validate_posts(root)
            (root / "data/humanizer/2026-11-06-daily.json").unlink()
            with self.assertRaisesRegex(humanizer.HumanizerError, "Missing"):
                humanizer.validate_posts(root)

    def test_weekly_runner_does_not_swallow_editorial_failure(self):
        with patch.object(run_pipeline, "weekly_run", side_effect=humanizer.HumanizerError("Rejected")):
            with self.assertRaises(humanizer.HumanizerError):
                run_pipeline._try_weekly("2026-11-06")

    def test_provider_empty_result_or_exception_blocks_review(self):
        import synthesize
        for result in (None, ""):
            with patch.object(synthesize, "_call_llm", return_value=result):
                with self.assertRaises(humanizer.HumanizerError):
                    humanizer.review_post(POST)
        with patch.object(synthesize, "_call_llm", side_effect=RuntimeError("API failed")):
            with self.assertRaises(humanizer.HumanizerError):
                humanizer.review_post(POST)

    def test_weekly_generator_uses_review_and_does_not_write_on_failure(self):
        stories = [{
            "title": f"Report {index}", "url": f"https://example.com/{index}",
            "category": "cloud" if index < 3 else "dev", "summary": "Verified source",
        } for index in range(5)]
        for fail in (True, False):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.install_skill(root)
                with (
                    patch.object(weekly_summary, "PROJECT_DIR", root),
                    patch.object(weekly_summary, "CONTENT_DIR", root / "content/posts"),
                    patch.object(weekly_summary, "load_weekly_buffer", return_value=[{"date": "2026-11-06", "stories": stories}]),
                    patch.object(weekly_summary, "_call_llm", return_value=POST.split("---", 2)[2]),
                    patch.object(humanizer, "_call_llm", side_effect=humanizer.HumanizerError("Rejected") if fail else successful_editor),
                ):
                    if fail:
                        with self.assertRaises(humanizer.HumanizerError):
                            weekly_summary.run("2026-11-06")
                        self.assertFalse((root / "content/posts").exists())
                    else:
                        result = weekly_summary.run("2026-11-06")
                        self.assertTrue(result.is_file())
                        humanizer.validate_posts(root)

    @unittest.skipUnless(shutil.which("hugo"), "Hugo required for direct build gate")
    def test_direct_hugo_build_blocks_manual_posts_and_modified_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = humanizer.PROJECT_DIR
            shutil.copy2(project / "hugo.toml", root / "hugo.toml")
            (root / "pipeline").mkdir()
            shutil.copy2(project / "pipeline/sources.yaml", root / "pipeline/sources.yaml")
            for name in ("assets", "layouts", "content", "data", "static", ".github"):
                shutil.copytree(project / name, root / name)
            def build():
                return subprocess.run(["hugo", "--buildFuture", "--source", str(root)], capture_output=True, text=True, timeout=60)
            result = build()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manual = root / "content/posts/2026-11-06-manual.md"
            manual.write_text(POST, encoding="utf-8")
            result = build()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Humanizer receipt", result.stdout + result.stderr)
            with patch.object(humanizer, "_call_llm", side_effect=successful_editor):
                humanizer.write_reviewed_post(manual, POST, root)
            result = build()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt_path = root / "data/humanizer/2026-11-06-manual.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for change in (
                {"version": 2}, {"version": "1"}, {"meaning_verified": False},
                {"post_sha256": "0" * 64}, {"skill_sha256": "0" * 64},
                {"input_sha256": "invalid"},
            ):
                receipt_path.write_text(json.dumps({**receipt, **change}), encoding="utf-8")
                self.assertNotEqual(build().returncode, 0, change)
                with self.assertRaises(humanizer.HumanizerError):
                    humanizer.validate_posts(root)
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with patch.object(humanizer, "_call_llm", side_effect=successful_editor):
                humanizer.write_reviewed_post(
                    manual,
                    POST.replace("value = 42", 'value = "literal \u2014 code"')
                    .replace("https://example.com/report", "https://example.com/report\u2014id"),
                    root,
                )
            result = build()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            humanizer.validate_posts(root)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            reviewed_text = manual.read_text(encoding="utf-8")
            for change in (
                reviewed_text.replace("Original title", "Original \u2014 title"),
                reviewed_text.replace('title: "A release"', 'title: "A release \u2013 today"'),
                reviewed_text.replace("Acme shipped", "Acme shipped \u2014"),
            ):
                manual.write_text(change, encoding="utf-8")
                receipt_path.write_text(json.dumps({
                    **receipt, "post_sha256": humanizer.digest(change),
                }), encoding="utf-8")
                result = build()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("editorial dash", result.stdout + result.stderr)
                with self.assertRaisesRegex(humanizer.HumanizerError, "editorial dash"):
                    humanizer.validate_posts(root)
            manual.write_text(reviewed_text, encoding="utf-8")
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            manual.write_text(manual.read_text(encoding="utf-8") + "\nChanged after review.", encoding="utf-8")
            self.assertNotEqual(build().returncode, 0)
            manual.unlink()
            legacy = root / "content/posts/2026-11-02-daily.md"
            original_legacy = legacy.read_text(encoding="utf-8")
            legacy.write_text(legacy.read_text(encoding="utf-8") + "\nUnreviewed edit", encoding="utf-8")
            self.assertNotEqual(build().returncode, 0)
            with self.assertRaises(humanizer.HumanizerError):
                humanizer.validate_posts(root)
            legacy.write_text(original_legacy, encoding="utf-8")
            humanizer.validate_posts(root)
            (root / ".github/skills/humanizer/SKILL.md").write_text("Modified skill")
            self.assertNotEqual(build().returncode, 0)
