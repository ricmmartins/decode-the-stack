import json
import os
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import copilot_client as client
import synthesize
import humanizer
import weekly_summary
import podcast
import run_pipeline


def output(content="COPILOT_OK"):
    return "\n".join(json.dumps(event) for event in [
        {"type": "assistant.message", "data": {"content": content}},
        {"type": "result", "exitCode": 0},
    ])


class CopilotClientTests(unittest.TestCase):
    def test_isolated_stdin_call_uses_github_auth_and_no_tools_or_byok(self):
        env = {
            "COPILOT_GITHUB_TOKEN": "test-token", "COPILOT_MODEL": "test-model",
            "GITHUB_TOKEN": "collection-token", "GH_TOKEN": "collection-token",
            "OPENAI_KEY": "tts-key", "OPENAI_API_KEY": "other-key",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch.object(client.shutil, "which", return_value="/bin/copilot"),
            patch.object(client.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout=output(),
            )) as call,
        ):
            self.assertEqual(client._call_copilot("rules", "facts"), "COPILOT_OK")
        args, kwargs = call.call_args
        self.assertEqual(args[0], [
            "/bin/copilot", "--silent", "--output-format", "json",
            "--no-custom-instructions", "--disable-builtin-mcps",
            "--available-tools=", "--deny-tool=*", "--no-ask-user", "--no-auto-update",
            "--model", "test-model",
        ])
        self.assertTrue(kwargs["input"].endswith("## SYSTEM\n\nrules\n\n## USER\n\nfacts"))
        self.assertIn("Do not call tools", kwargs["input"])
        self.assertEqual(kwargs["timeout"], 300)
        self.assertFalse(Path(kwargs["cwd"]).exists())
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["env"]["COPILOT_GITHUB_TOKEN"], "test-token")
        for key in ("GITHUB_TOKEN", "GH_TOKEN", "OPENAI_KEY", "OPENAI_API_KEY"):
            self.assertNotIn(key, kwargs["env"])

    def test_model_flag_is_omitted_until_supported_model_is_explicitly_configured(self):
        with (
            patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True),
            patch.object(client.shutil, "which", return_value="/bin/copilot"),
            patch.object(client.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout=output(),
            )) as call,
        ):
            client._call_copilot("rules", "facts")
        self.assertNotIn("--model", call.call_args.args[0])

    def test_auth_missing_and_byok_overrides_are_rejected_before_launch(self):
        for env in ({}, {"COPILOT_GITHUB_TOKEN": "token", "COPILOT_PROVIDER_BASE_URL": "url"},
                    {"COPILOT_GITHUB_TOKEN": "token", "COPILOT_PROVIDER_API_KEY": "key"}):
            with (
                patch.dict(os.environ, env, clear=True),
                patch.object(client.subprocess, "run") as call,
                self.assertRaises(client.CopilotError),
            ):
                client._call_copilot("rules", "facts")
            call.assert_not_called()

    def test_missing_cli_timeout_start_failure_and_nonzero_exit_block(self):
        with (
            patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True),
            patch.object(client.shutil, "which", return_value=None),
            self.assertRaisesRegex(client.CopilotError, "missing"),
        ):
            client._call_copilot("rules", "facts")
        for error in (subprocess.TimeoutExpired("copilot", 300), OSError("private detail")):
            with (
                patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True),
                patch.object(client.shutil, "which", return_value="/bin/copilot"),
                patch.object(client.subprocess, "run", side_effect=error),
                self.assertRaises(client.CopilotError),
            ):
                client._call_copilot("rules", "facts")
        with (
            patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "token"}, clear=True),
            patch.object(client.shutil, "which", return_value="/bin/copilot"),
            patch.object(client.subprocess, "run", return_value=SimpleNamespace(
                returncode=1, stdout="secret", stderr="secret",
            )),
            self.assertRaisesRegex(client.CopilotError, "code 1") as raised,
        ):
            client._call_copilot("rules", "facts")
        self.assertNotIn("secret", str(raised.exception))

    def test_malformed_missing_failed_or_tool_events_are_rejected(self):
        cases = [
            "", "not JSON", "[]", '{"type":"result","exitCode":false}',
            '{"type":"result","exitCode":1}', '{"type":"result","exitCode":0}',
            output(" "), output() + "\n{}",
        ]
        for event in (
            {"type": "session.error", "data": {"message": "auth"}},
            {"type": "tool.execution_start"},
            {"type": "assistant.message", "data": {"toolRequests": [{}]}},
        ):
            cases.append(json.dumps(event) + "\n" + output())
        for case in cases:
            with self.subTest(case=case), self.assertRaises(client.CopilotError):
                client.parse_copilot_output(case)

    def test_selected_copilot_never_calls_billed_fallback_even_on_failure(self):
        with (
            patch.dict(os.environ, {"LLM_PROVIDER": "copilot", "OPENAI_KEY": "tts"}, clear=True),
            patch.object(synthesize, "_call_copilot", side_effect=client.CopilotError("auth")) as call,
            patch.object(synthesize, "_call_openai") as openai,
            patch.object(synthesize, "_call_groq") as groq,
            patch.object(synthesize, "_call_azure_openai") as azure,
            self.assertRaises(client.CopilotError),
        ):
            synthesize._call_llm("rules", "facts")
        call.assert_called_once_with("rules", "facts")
        for provider in (openai, groq, azure):
            provider.assert_not_called()
        with patch.dict(os.environ, {"LLM_PROVIDER": "typo"}, clear=True), self.assertRaises(ValueError):
            synthesize._call_llm("rules", "facts")

    def test_tool_rejection_reports_only_structure_and_never_request_content(self):
        event = {
            "type": "assistant.message",
            "data": {"content": "private text", "toolRequests": [
                {"name": "private-tool", "arguments": {"token": "private-secret"}}
            ]},
        }
        with self.assertRaisesRegex(client.CopilotError, "type=list, count=1") as raised:
            client.parse_copilot_output(json.dumps(event) + "\n" + output())
        self.assertNotIn("private", str(raised.exception))
        with self.assertRaisesRegex(client.CopilotError, "not an object"):
            client.parse_copilot_output(
                json.dumps({"type": "assistant.message", "data": []}) + "\n" + output()
            )

    def test_all_text_surfaces_dispatch_through_selected_provider(self):
        script = "\n".join(
            host + ": " + " ".join(["context"] * count)
            for host, count in (("Anna", 126), ("Maria", 126), ("Pedro", 128))
        )
        synthesis = "\n\n".join(f"### Story {i}\nVerified reporting." for i in range(6))
        with (
            patch.dict(os.environ, {"LLM_PROVIDER": "copilot"}, clear=True),
            patch.object(synthesize, "_call_copilot", return_value=script) as call,
            patch.object(synthesize.time, "sleep"),
        ):
            synthesize.synthesize_two_pass([], [{"title": "Report", "url": "https://example.com",
                "category": "dev", "summary": "Facts", "sources": []}], "2026-11-02")
            weekly_summary._call_llm("weekly rules", "weekly facts")
            humanizer._call_llm("review rules", "review facts", "Humanizer editorial review")
            humanizer._call_llm("meaning rules", "meaning facts", "Humanizer meaning verification")
            self.assertEqual(podcast._spoken_word_count(podcast.generate_podcast_script(synthesis)), 2280)
        self.assertEqual(call.call_count, 11)

    def test_weekly_copilot_error_blocks_instead_of_being_swallowed(self):
        with (
            patch.object(run_pipeline, "weekly_run", side_effect=client.CopilotError("auth")),
            self.assertRaises(client.CopilotError),
        ):
            run_pipeline._try_weekly("2026-11-06")
