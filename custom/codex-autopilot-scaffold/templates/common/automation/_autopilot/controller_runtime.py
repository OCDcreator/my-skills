from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from _autopilot.lanes import LaneSupport, normalize_lanes_config


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = "automation/autopilot-config.json"
DEFAULT_STATE_PATH = "automation/runtime/autopilot-state.json"
DEFAULT_RUNTIME_PATH = "automation/runtime"
DEFAULT_PROFILE_NAME = "windows"
LOCK_FILENAME = "autopilot.lock.json"
ROUND_DIRECTORY_RE = re.compile(r"^round-(\d+)$")
QUEUE_ITEM_STATUS_RE = re.compile(r"^### \[(DONE|NEXT|QUEUED)\]\s+")
VULTURE_FINDING_RE = re.compile(r"^.+:\d+:\s+")


def ensure_console_streams() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


ensure_console_streams()


class AutopilotError(RuntimeError):
    pass


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def compact_text(text: str | None, max_length: int = 180) -> str:
    if not text or not text.strip():
        return ""
    single_line = " ".join(text.split())
    if len(single_line) <= max_length:
        return single_line
    return f"{single_line[: max_length - 3]}..."


def resolve_repo_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def normalize_path_text(path_value: Any) -> str:
    return clean_string(path_value).replace("\\", "/")


def ensure_path_within_repo(path_value: str, *, label: str, must_exist: bool = False) -> Path:
    normalized = normalize_path_text(path_value)
    if not normalized:
        raise AutopilotError(f"{label} is required.")
    resolved = resolve_repo_path(normalized)
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise AutopilotError(f"{label} must stay within the repository: {normalized}") from exc
    if must_exist and not resolved.exists():
        raise AutopilotError(f"{label} was not found: {normalized}")
    return resolved


def infer_roadmap_path_text_from_phase_doc(phase_doc_path: str) -> str:
    normalized_phase_doc = normalize_path_text(phase_doc_path)
    if not normalized_phase_doc:
        return ""
    match = re.match(r"^(?P<prefix>.+?)phase-\d+\.md$", normalized_phase_doc)
    if not match:
        return ""
    return f"{match.group('prefix')}round-roadmap.md"


def infer_round_roadmap_path_from_phase_doc(phase_doc_path: str) -> Path | None:
    roadmap_path_text = infer_roadmap_path_text_from_phase_doc(phase_doc_path)
    if not roadmap_path_text:
        return None

    roadmap_path = resolve_repo_path(roadmap_path_text)
    if roadmap_path.exists():
        return roadmap_path
    return None


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def save_state(state: dict[str, Any], state_path: Path) -> None:
    state["updated_at"] = now_timestamp()
    write_json(state_path, state)


def info(message: str) -> None:
    print(f"[autopilot] {message}")


def progress(progress_log_path: Path, message: str, channel: str = "codex") -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{channel}] {message}"
    progress_log_path.parent.mkdir(parents=True, exist_ok=True)
    with progress_log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
    print(line)


def render_template(template_text: str, tokens: dict[str, Any]) -> str:
    rendered = template_text
    for token_key, token_value in tokens.items():
        rendered = rendered.replace(f"{{{{{token_key}}}}}", clean_string(token_value))
    return rendered


def append_controller_requirements(prompt_text: str, config: dict[str, Any]) -> str:
    commit_prefix = clean_string(config.get("commit_prefix"))
    lines = [
        "",
        "## Controller-Enforced Requirements",
        "",
        "These requirements are injected by `automation/autopilot.py` and override any looser wording above.",
        "- On `success`, create exactly one final commit for the completed round before returning JSON.",
        "- The final JSON `commit_sha` must equal `git rev-parse HEAD`.",
        "- The final JSON `commit_message` must exactly equal `git log -1 --pretty=%s`.",
        "- If `build_ran` is `true`, set a non-empty `build_id` taken from the actual build artifact, hash, or generated build marker.",
        "- If no reliable build identifier was produced, set `build_ran` to `false` instead of inventing a `build_id`.",
        "- If `deploy_ran` is `true`, only report it when this round actually performed a deploy step required by config.",
        "- If `deploy_ran` is `true`, also set `deploy_verified` to `true` only after the configured deploy verification step really passed.",
        "- Include every real command in `commands_run`; repeated diagnostic Git commands may be reported as controller warnings, but do not hide them.",
    ]
    if commit_prefix:
        lines.append(
            f"- The successful round commit subject must start with `{commit_prefix}:`; "
            "if it does not, amend the commit before returning `success`."
        )
    else:
        lines.append("- This lane does not enforce a commit-message prefix.")
    return f"{prompt_text.rstrip()}\n{chr(10).join(lines)}\n"


def windows_hidden_process_kwargs(
    *,
    detached: bool = False,
    new_process_group: bool = False,
) -> dict[str, Any]:
    if os.name != "nt":
        return {}

    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if detached:
        creationflags |= int(getattr(subprocess, "DETACHED_PROCESS", 0))
    if new_process_group:
        creationflags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

    popen_kwargs: dict[str, Any] = {}
    if creationflags:
        popen_kwargs["creationflags"] = creationflags

    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    startf_use_show_window = int(getattr(subprocess, "STARTF_USESHOWWINDOW", 0))
    sw_hide = int(getattr(subprocess, "SW_HIDE", 0))
    if startupinfo_factory and startf_use_show_window:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= startf_use_show_window
        startupinfo.wShowWindow = sw_hide
        popen_kwargs["startupinfo"] = startupinfo

    return popen_kwargs


def run_command(
    args: list[str],
    *,
    check: bool = True,
    cwd: Path = REPO_ROOT,
) -> CommandResult:
    process = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **windows_hidden_process_kwargs(),
    )
    result = CommandResult(
        stdout=process.stdout.strip(),
        stderr=process.stderr.strip(),
        returncode=process.returncode,
    )
    if check and process.returncode != 0:
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise AutopilotError(f"{' '.join(args)} failed: {combined}")
    return result


def run_git(args: list[str], *, check: bool = True) -> CommandResult:
    return run_command(["git", "-C", str(REPO_ROOT), *args], check=check)


def run_git_no_capture(args: list[str], *, check: bool = True) -> int:
    process = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=False,
        **windows_hidden_process_kwargs(),
    )
    if check and process.returncode != 0:
        raise AutopilotError(f"git {' '.join(args)} failed with exit code {process.returncode}")
    return int(process.returncode)


def resolve_shell_command_args(command_text: str, config: dict[str, Any]) -> list[str]:
    shell_preference = clean_string(config.get("shell_preference")).lower()
    if os.name == "nt":
        candidate_names = [shell_preference] if shell_preference else []
        candidate_names.extend(["pwsh", "powershell", "cmd"])
        seen: set[str] = set()
        for candidate in candidate_names:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate == "cmd":
                cmd_path = shutil.which("cmd") or os.environ.get("COMSPEC") or "cmd"
                return [cmd_path, "/c", command_text]
            resolved = shutil.which(candidate)
            if resolved:
                return [resolved, "-NoLogo", "-NoProfile", "-Command", command_text]
    else:
        candidate_names = [shell_preference] if shell_preference else []
        candidate_names.extend(["zsh", "bash", "sh"])
        seen: set[str] = set()
        for candidate in candidate_names:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolved = shutil.which(candidate)
            if resolved:
                return [resolved, "-lc", command_text]
    raise AutopilotError("No compatible shell was found to run configured text commands.")


def run_shell_command(
    command_text: str,
    *,
    config: dict[str, Any],
    check: bool = True,
    cwd: Path = REPO_ROOT,
) -> CommandResult:
    shell_args = resolve_shell_command_args(command_text, config)
    return run_command(shell_args, check=check, cwd=cwd)


def append_history_entry(runtime_directory: Path, entry: dict[str, Any]) -> None:
    append_jsonl(runtime_directory / "history.jsonl", entry)


def test_branch_allowed(branch_name: str, allowed_prefixes: list[str]) -> bool:
    return any(branch_name.lower().startswith(prefix.lower()) for prefix in allowed_prefixes)


def is_working_tree_dirty() -> bool:
    return bool(run_git(["status", "--porcelain"]).stdout.strip())


def preserve_worktree_before_reset(target_head_sha: str) -> None:
    current_head = get_head_sha()
    snapshot_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    if current_head and current_head != target_head_sha:
        safety_ref = f"refs/autopilot/safety/{snapshot_id}-{current_head[:12]}"
        run_git(["update-ref", safety_ref, current_head])
        info(f"Preserved pre-reset HEAD at {safety_ref}.")

    if is_working_tree_dirty():
        stash_message = f"autopilot safety before reset to {target_head_sha[:12]} at {snapshot_id}"
        stash_result = run_git(["stash", "push", "--include-untracked", "-m", stash_message], check=False)
        combined = "\n".join(part for part in (stash_result.stdout, stash_result.stderr) if clean_string(part))
        if stash_result.returncode != 0:
            raise AutopilotError(f"Failed to preserve dirty worktree before reset: {combined}")
        if "No local changes to save" not in combined:
            info(f"Preserved dirty worktree in git stash: {stash_message}")


def reset_worktree_to_head(head_sha: str) -> None:
    preserve_worktree_before_reset(head_sha)
    run_git(["reset", "--hard", head_sha])
    run_git(["clean", "-fd"])


def count_vulture_findings(output_text: str) -> int:
    lines = [line.strip() for line in output_text.splitlines() if line.strip()]
    if not lines:
        return 0
    finding_lines = [line for line in lines if VULTURE_FINDING_RE.match(line)]
    return len(finding_lines) if finding_lines else len(lines)


def read_vulture_snapshot(config: dict[str, Any]) -> dict[str, Any] | None:
    vulture_command = clean_string(config.get("vulture_command"))
    if not vulture_command:
        return None

    result = run_shell_command(vulture_command, config=config, check=False)
    finding_count = count_vulture_findings(result.stdout)
    if result.returncode not in {0, 3} and not (finding_count > 0 and not clean_string(result.stderr)):
        combined = "\n".join(part for part in (result.stdout, result.stderr) if clean_string(part))
        return {
            "command": vulture_command,
            "count": None,
            "error": combined or f"vulture command exited with code {result.returncode}",
            "returncode": result.returncode,
        }

    return {
        "command": vulture_command,
        "count": finding_count,
        "error": "",
        "returncode": result.returncode,
    }


def refresh_vulture_metrics(state: dict[str, Any], config: dict[str, Any]) -> None:
    snapshot = read_vulture_snapshot(config)
    if snapshot is None:
        state["vulture_command"] = ""
        state["vulture_current_count"] = None
        state["vulture_previous_count"] = None
        state["vulture_delta"] = None
        state["vulture_updated_at"] = None
        state["vulture_last_error"] = None
        return

    state["vulture_command"] = snapshot["command"]
    state["vulture_updated_at"] = now_timestamp()
    if snapshot["error"]:
        state["vulture_last_error"] = snapshot["error"]
        return

    previous_count = state.get("vulture_current_count")
    current_count = int(cast(int, snapshot["count"]))
    state["vulture_previous_count"] = previous_count
    state["vulture_current_count"] = current_count
    state["vulture_delta"] = None if previous_count is None else current_count - int(previous_count)
    state["vulture_last_error"] = None


def pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _lane_support_for_config() -> LaneSupport:
    return LaneSupport(
        error_type=AutopilotError,
        clean_string=clean_string,
        normalize_path_text=normalize_path_text,
        infer_roadmap_path_text_from_phase_doc=infer_roadmap_path_text_from_phase_doc,
        infer_round_roadmap_path_from_phase_doc=infer_round_roadmap_path_from_phase_doc,
        ensure_path_within_repo=ensure_path_within_repo,
        resolve_repo_path=resolve_repo_path,
        read_text=read_text,
        parse_int=parse_int,
        queue_item_status_re=QUEUE_ITEM_STATUS_RE,
    )


def load_profile(profile_name: str, profile_path_override: str | None) -> tuple[str, Path, dict[str, Any]]:
    if profile_path_override:
        profile_path = resolve_repo_path(profile_path_override)
        profile_key = profile_name
    else:
        profile_key = profile_name
        profile_path = resolve_repo_path(f"automation/profiles/{profile_name}.json")
    if not profile_path.exists():
        raise AutopilotError(f"Profile '{profile_key}' was not found at {profile_path}.")
    return profile_key, profile_path, read_json(profile_path)


def load_config(config_path_value: str, profile_name: str, profile_path_override: str | None) -> tuple[dict[str, Any], Path, Path]:
    config_path = resolve_repo_path(config_path_value)
    if not config_path.exists():
        raise AutopilotError(f"Config file not found: {config_path}")
    base_config = read_json(config_path)
    _, profile_path, profile_config = load_profile(profile_name, profile_path_override)
    merged_config = dict(base_config)
    for key, value in profile_config.items():
        if key in merged_config:
            if value is None:
                continue
            if isinstance(value, str) and not clean_string(value):
                continue
            if isinstance(value, (list, dict)) and not value:
                continue
        merged_config[key] = value
    merged_config["profile_name"] = profile_name
    merged_config.setdefault("shell_preference", "pwsh" if os.name == "nt" else "zsh")
    merged_config.setdefault("deploy_policy", "never")
    merged_config.setdefault("deploy_required_paths", [])
    merged_config.setdefault("deploy_verify_path", "")
    merged_config.setdefault("vulture_command", "")
    merged_config.setdefault("prompt_template", "automation/round-prompt.md")
    merged_config.setdefault("commit_prefix", "")
    merged_config.setdefault("focus_hint", "")
    merged_config.setdefault("next_phase_number", 1)
    merged_config = normalize_lanes_config(merged_config, support=_lane_support_for_config())
    return merged_config, config_path, profile_path


def get_codex_item_summary(item: dict[str, Any], event_type: str) -> str | None:
    item_type = clean_string(item.get("type"))
    if item_type == "agent_message" and event_type == "item.completed":
        message_text = compact_text(clean_string(item.get("text")), max_length=220)
        if message_text:
            return f"Agent: {message_text}"

    if item_type == "command_execution":
        command_text = compact_text(clean_string(item.get("command")), max_length=200)
        if event_type == "item.started":
            return f"Running command: {command_text}"
        exit_code = item.get("exit_code")
        exit_code_text = "?" if exit_code is None else str(exit_code)
        return f"Command finished (exit {exit_code_text}): {command_text}"

    if item_type:
        return f"{event_type}: {item_type}"
    return None


def get_codex_event_summary(json_line: str) -> str | None:
    try:
        event_record = json.loads(json_line)
    except json.JSONDecodeError:
        return f"Raw output: {compact_text(json_line, max_length=220)}"

    event_type = clean_string(event_record.get("type"))
    if event_type == "thread.started":
        return f"Session started: {event_record.get('thread_id')}"
    if event_type == "turn.started":
        return "Turn started"
    if event_type == "turn.completed":
        usage = event_record.get("usage") or {}
        if usage:
            return f"Turn completed (input {usage.get('input_tokens')}, output {usage.get('output_tokens')})"
        return "Turn completed"
    if event_type in {"item.started", "item.completed"}:
        item = event_record.get("item")
        if isinstance(item, dict):
            return get_codex_item_summary(item, event_type)
    if event_type:
        return f"Event: {event_type}"
    return None


def build_history_entry(
    *,
    attempt_number: int,
    phase_number: int,
    lane_id: str,
    result: dict[str, Any] | None,
    failure_reason: str | None,
) -> dict[str, Any]:
    return {
        "timestamp": now_timestamp(),
        "round": attempt_number,
        "phase_number": phase_number,
        "lane_id": clean_string(result.get("lane_id") if result else lane_id) or lane_id,
        "status": "failure" if failure_reason else clean_string(result.get("status") if result else ""),
        "phase_doc": result.get("phase_doc_path") if result else None,
        "commit_sha": result.get("commit_sha") if result else None,
        "summary": result.get("summary") if result else None,
        "next_focus": result.get("next_focus") if result else None,
        "blocking_reason": failure_reason if failure_reason else None,
    }


def get_current_branch() -> str:
    return run_git(["branch", "--show-current"]).stdout


def get_head_sha() -> str:
    return run_git(["rev-parse", "HEAD"]).stdout
