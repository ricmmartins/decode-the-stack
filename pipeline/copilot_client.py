"""Text-only Copilot CLI adapter; provider failures always block publication."""

import json
import os
import shutil
import subprocess
import tempfile


class CopilotError(RuntimeError):
    pass


def parse_copilot_output(output):
    events = []
    try:
        for line in output.splitlines():
            if line.strip():
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("Event must be an object")
                events.append(event)
    except (ValueError, TypeError) as error:
        raise CopilotError("Copilot CLI returned malformed JSON events.") from error
    results = [event for event in events if event.get("type") == "result"]
    if (
        len(results) != 1
        or events[-1] is not results[0]
        or type(results[0].get("exitCode")) is not int
        or results[0]["exitCode"] != 0
    ):
        raise CopilotError("Copilot CLI did not complete successfully; check authentication and usage limits.")
    messages = []
    for event in events:
        kind = event.get("type", "")
        if not isinstance(kind, str):
            raise CopilotError("Copilot CLI returned an invalid event type.")
        data = event.get("data", {})
        if kind in {"error", "session.error"} or kind.startswith("tool."):
            raise CopilotError("Copilot CLI reported an error or attempted tool execution.")
        if kind == "assistant.message":
            if not isinstance(data, dict) or data.get("toolRequests"):
                raise CopilotError("Copilot CLI returned an invalid or tool-requesting message.")
            content = data.get("content")
            if isinstance(content, str) and content.strip():
                messages.append(content)
    if not messages:
        raise CopilotError("Copilot CLI returned no assistant text.")
    return messages[-1]


def _call_copilot(system, user):
    if any(os.environ.get(key) for key in ("COPILOT_PROVIDER_BASE_URL", "COPILOT_PROVIDER_API_KEY")):
        raise CopilotError("Copilot BYOK overrides are forbidden; use authenticated GitHub Copilot access.")
    token = os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
    if not token:
        raise CopilotError("COPILOT_GITHUB_TOKEN is required for the Copilot text provider.")
    executable = shutil.which(os.environ.get("COPILOT_CLI_PATH") or "copilot")
    if not executable:
        raise CopilotError("Copilot CLI is missing; install @github/copilot@1.0.105.")
    args = [
        executable, "--silent", "--output-format", "json", "--no-custom-instructions",
        "--disable-builtin-mcps", "--available-tools=", "--no-ask-user",
    ]
    model = os.environ.get("COPILOT_MODEL", "").strip()
    if model:
        args.extend(["--model", model])
    environment = os.environ.copy()
    for key in (
        "GITHUB_TOKEN", "GH_TOKEN", "GH_PAT", "GITHUB_PAT", "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN", "OPENAI_API_KEY", "OPENAI_KEY", "GROQ_API_KEY",
        "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GITHUB_PERSONAL_ACCESS_TOKEN",
    ):
        environment.pop(key, None)
    environment["COPILOT_GITHUB_TOKEN"] = token
    prompt = f"## SYSTEM\n\n{system}\n\n## USER\n\n{user}"
    try:
        with tempfile.TemporaryDirectory(prefix="decode-copilot-") as directory:
            result = subprocess.run(
                args, input=prompt, text=True, encoding="utf-8", capture_output=True,
                timeout=300, cwd=directory, env=environment, check=False,
            )
    except subprocess.TimeoutExpired:
        raise CopilotError("Copilot CLI timed out after 300 seconds; publication is blocked.") from None
    except OSError:
        raise CopilotError("Copilot CLI could not start; check the pinned installation.") from None
    except UnicodeError:
        raise CopilotError("Copilot CLI returned invalid UTF-8 output.") from None
    if result.returncode != 0:
        # Never echo stdout/stderr: either can contain credentials or source material.
        raise CopilotError(
            f"Copilot CLI exited with code {result.returncode}; "
            "check token access, model availability, and Copilot usage limits."
        )
    return parse_copilot_output(result.stdout)
