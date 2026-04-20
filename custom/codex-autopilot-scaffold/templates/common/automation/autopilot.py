#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from _autopilot.runner import RunnerSupport, invoke_runner_round, resolve_runner_executable
from _autopilot.validation import ValidationSupport, validate_round_result


if TYPE_CHECKING:
    SCAFFOLD_NAME_JSON = ""
    SCAFFOLD_VERSION_JSON = ""


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = "automation/autopilot-config.json"
DEFAULT_STATE_PATH = "automation/runtime/autopilot-state.json"
DEFAULT_RUNTIME_PATH = "automation/runtime"
AUTOPILOT_SCAFFOLD_NAME = cast(str, [[SCAFFOLD_NAME_JSON]])
AUTOPILOT_SCAFFOLD_VERSION = cast(str, [[SCAFFOLD_VERSION_JSON]])
DEFAULT_PROFILE_NAME = "windows"
LOCK_FILENAME = "autopilot.lock.json"
ROUND_DIRECTORY_RE = re.compile(r"^round-(\d+)$")
QUEUE_ITEM_STATUS_RE = re.compile(r"^### \[(DONE|NEXT|QUEUED)\]\s+")
VULTURE_FINDING_RE = re.compile(r"^.+:\d+:\s+")
LANE_OVERRIDE_KEYS = {
    "focus_hint",
    "phase_doc_prefix",
    "starting_phase_doc",
    "roadmap_path",
    "prompt_template",
    "commit_prefix",
}
LEGACY_LANE_ID = "legacy-lane"
LANE_ACTIVE_STATUS = "active"
LANE_PENDING_STATUS = "pending"
LANE_COMPLETE_STATUS = "complete"


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


def synthesize_legacy_lane(base_config: dict[str, Any]) -> dict[str, Any]:
    phase_doc_prefix = normalize_path_text(base_config.get("phase_doc_prefix"))
    starting_phase_doc = normalize_path_text(base_config.get("starting_phase_doc"))
    if not starting_phase_doc and phase_doc_prefix:
        starting_phase_doc = f"{phase_doc_prefix}0.md"
    roadmap_path = normalize_path_text(base_config.get("roadmap_path"))
    if not roadmap_path and starting_phase_doc:
        roadmap_path = infer_roadmap_path_text_from_phase_doc(starting_phase_doc)
    return {
        "id": LEGACY_LANE_ID,
        "label": clean_string(base_config.get("focus_hint")) or "Legacy lane",
        "focus_hint": clean_string(base_config.get("focus_hint")) or "Legacy lane",
        "phase_doc_prefix": phase_doc_prefix,
        "starting_phase_doc": starting_phase_doc,
        "roadmap_path": roadmap_path,
        "prompt_template": normalize_path_text(base_config.get("prompt_template")) or "automation/round-prompt.md",
        "commit_prefix": clean_string(base_config.get("commit_prefix")),
    }


def normalize_lane_config(raw_lane: dict[str, Any], *, lane_index: int, shared_defaults: dict[str, Any]) -> dict[str, Any]:
    lane_id = clean_string(raw_lane.get("id"))
    if not lane_id:
        raise AutopilotError(f"lanes[{lane_index}] is missing id.")

    phase_doc_prefix = normalize_path_text(raw_lane.get("phase_doc_prefix"))
    starting_phase_doc = normalize_path_text(raw_lane.get("starting_phase_doc"))
    if not starting_phase_doc and phase_doc_prefix:
        starting_phase_doc = f"{phase_doc_prefix}0.md"

    roadmap_path = normalize_path_text(raw_lane.get("roadmap_path"))
    if not roadmap_path and starting_phase_doc:
        roadmap_path = infer_roadmap_path_text_from_phase_doc(starting_phase_doc)

    normalized_lane = {
        "id": lane_id,
        "label": clean_string(raw_lane.get("label")) or lane_id,
        "focus_hint": clean_string(raw_lane.get("focus_hint")) or clean_string(shared_defaults.get("focus_hint")) or lane_id,
        "phase_doc_prefix": phase_doc_prefix,
        "starting_phase_doc": starting_phase_doc,
        "roadmap_path": roadmap_path,
        "prompt_template": normalize_path_text(raw_lane.get("prompt_template") or shared_defaults.get("prompt_template"))
        or "automation/round-prompt.md",
        "commit_prefix": clean_string(
            raw_lane["commit_prefix"] if "commit_prefix" in raw_lane else shared_defaults.get("commit_prefix")
        ),
    }
    return normalized_lane


def validate_lane_configs(config: dict[str, Any]) -> None:
    seen_lane_ids: set[str] = set()
    for lane in config["lanes"]:
        lane_id = lane["id"]
        if lane_id in seen_lane_ids:
            raise AutopilotError(f"Duplicate lane id '{lane_id}' in autopilot-config.json.")
        seen_lane_ids.add(lane_id)

        prefix_text = normalize_path_text(lane.get("phase_doc_prefix"))
        if not prefix_text:
            raise AutopilotError(f"Lane '{lane_id}' is missing phase_doc_prefix.")
        starting_phase_doc = normalize_path_text(lane.get("starting_phase_doc"))
        roadmap_path = normalize_path_text(lane.get("roadmap_path"))
        prompt_template = normalize_path_text(lane.get("prompt_template"))

        ensure_path_within_repo(f"{prefix_text}0.md", label=f"Lane '{lane_id}' phase_doc_prefix probe")
        ensure_path_within_repo(starting_phase_doc, label=f"Lane '{lane_id}' starting_phase_doc", must_exist=True)
        ensure_path_within_repo(roadmap_path, label=f"Lane '{lane_id}' roadmap_path", must_exist=True)
        ensure_path_within_repo(prompt_template, label=f"Lane '{lane_id}' prompt_template", must_exist=True)

        if not starting_phase_doc.startswith(prefix_text):
            raise AutopilotError(
                f"Lane '{lane_id}' starting_phase_doc must stay under phase_doc_prefix: "
                f"{starting_phase_doc} vs {prefix_text}"
            )


def normalize_lanes_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    lanes_raw = normalized.get("lanes")
    lane_entries: list[dict[str, Any]] = []
    if isinstance(lanes_raw, list) and lanes_raw:
        for index, lane in enumerate(lanes_raw):
            if not isinstance(lane, dict):
                raise AutopilotError(f"lanes[{index}] must be an object.")
            lane_entries.append(lane)
        legacy_lane_mode = False
    else:
        lane_entries = [synthesize_legacy_lane(normalized)]
        legacy_lane_mode = True

    shared_defaults = {
        "focus_hint": clean_string(normalized.get("focus_hint")),
        "prompt_template": normalize_path_text(normalized.get("prompt_template")) or "automation/round-prompt.md",
        "commit_prefix": clean_string(normalized.get("commit_prefix")),
    }
    normalized["lanes"] = [
        normalize_lane_config(lane, lane_index=index, shared_defaults=shared_defaults)
        for index, lane in enumerate(lane_entries)
    ]
    normalized["legacy_lane_mode"] = legacy_lane_mode
    validate_lane_configs(normalized)
    return normalized


def config_lane_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {lane["id"]: lane for lane in config.get("lanes", [])}


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_initial_lane_progress(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lane_progress: dict[str, dict[str, Any]] = {}
    initial_phase_number = parse_int(config.get("next_phase_number"), 1)
    for index, lane in enumerate(config["lanes"]):
        lane_progress[lane["id"]] = {
            "status": LANE_ACTIVE_STATUS if index == 0 else LANE_PENDING_STATUS,
            "next_phase_number": initial_phase_number if index == 0 else 1,
            "last_phase_doc": lane["starting_phase_doc"],
        }
    return lane_progress


def active_lane_id_for_state(state: dict[str, Any], config: dict[str, Any]) -> str:
    lane_map = config_lane_map(config)
    active_lane_id = clean_string(state.get("active_lane_id"))
    if active_lane_id in lane_map:
        return active_lane_id
    if not config.get("lanes"):
        raise AutopilotError("No lane configuration is available.")
    return config["lanes"][0]["id"]


def normalize_state_for_lanes(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    normalized_state = dict(state)
    lane_map = config_lane_map(config)
    fallback_active_lane_id = clean_string(normalized_state.get("active_lane_id"))
    if fallback_active_lane_id not in lane_map:
        fallback_active_lane_id = config["lanes"][0]["id"]

    raw_lane_progress = normalized_state.get("lane_progress")
    if not isinstance(raw_lane_progress, dict):
        raw_lane_progress = {}

    lane_progress: dict[str, dict[str, Any]] = {}
    fallback_phase_number = parse_int(normalized_state.get("next_phase_number"), parse_int(config.get("next_phase_number"), 1))
    fallback_phase_doc = normalize_path_text(normalized_state.get("last_phase_doc"))
    for lane in config["lanes"]:
        lane_id = lane["id"]
        raw_progress = raw_lane_progress.get(lane_id)
        if not isinstance(raw_progress, dict):
            raw_progress = {}
        if config.get("legacy_lane_mode") and lane_id == fallback_active_lane_id and not raw_progress:
            lane_progress[lane_id] = {
                "status": clean_string(normalized_state.get("status")) or LANE_ACTIVE_STATUS,
                "next_phase_number": fallback_phase_number,
                "last_phase_doc": fallback_phase_doc or lane["starting_phase_doc"],
            }
            continue
        lane_progress[lane_id] = {
            "status": clean_string(raw_progress.get("status")) or (LANE_ACTIVE_STATUS if lane_id == fallback_active_lane_id else LANE_PENDING_STATUS),
            "next_phase_number": parse_int(raw_progress.get("next_phase_number"), 1),
            "last_phase_doc": normalize_path_text(raw_progress.get("last_phase_doc")) or lane["starting_phase_doc"],
        }

    normalized_state["active_lane_id"] = fallback_active_lane_id
    normalized_state["lane_progress"] = lane_progress
    sync_active_lane_mirror_fields(normalized_state, config)
    return normalized_state


def sync_active_lane_mirror_fields(state: dict[str, Any], config: dict[str, Any]) -> None:
    lane_id = active_lane_id_for_state(state, config)
    lane_progress = state["lane_progress"][lane_id]
    state["active_lane_id"] = lane_id
    state["next_phase_number"] = parse_int(lane_progress.get("next_phase_number"), 1)
    state["last_phase_doc"] = normalize_path_text(lane_progress.get("last_phase_doc"))


def active_lane_config(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return config_lane_map(config)[active_lane_id_for_state(state, config)]


def active_lane_progress(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return state["lane_progress"][active_lane_id_for_state(state, config)]


def set_active_lane(state: dict[str, Any], config: dict[str, Any], lane_id: str) -> None:
    for lane in config["lanes"]:
        lane_progress = state["lane_progress"][lane["id"]]
        if lane["id"] == lane_id:
            lane_progress["status"] = LANE_ACTIVE_STATUS
        elif clean_string(lane_progress.get("status")) != LANE_COMPLETE_STATUS:
            lane_progress["status"] = LANE_PENDING_STATUS
    state["active_lane_id"] = lane_id
    sync_active_lane_mirror_fields(state, config)


def mark_lane_complete(state: dict[str, Any], lane_id: str) -> None:
    if lane_id in state.get("lane_progress", {}):
        state["lane_progress"][lane_id]["status"] = LANE_COMPLETE_STATUS


def increment_active_lane_phase(state: dict[str, Any], config: dict[str, Any]) -> None:
    lane_progress = active_lane_progress(state, config)
    lane_progress["next_phase_number"] = parse_int(lane_progress.get("next_phase_number"), 1) + 1
    sync_active_lane_mirror_fields(state, config)


def lane_runtime_config(config: dict[str, Any], lane: dict[str, Any]) -> dict[str, Any]:
    runtime_config = dict(config)
    for override_key in LANE_OVERRIDE_KEYS:
        runtime_config[override_key] = lane.get(override_key, runtime_config.get(override_key))
    return runtime_config


def read_lane_queue_progress(
    config: dict[str, Any] | None,
    *,
    state: dict[str, Any] | None = None,
    lane_id: str | None = None,
) -> dict[str, Any] | None:
    roadmap_path: Path | None = None
    if config and lane_id:
        lane = config_lane_map(config).get(lane_id)
        if lane:
            roadmap_path = resolve_repo_path(lane["roadmap_path"])
    if roadmap_path is None and state is not None:
        roadmap_path = infer_round_roadmap_path_from_phase_doc(clean_string(state.get("last_phase_doc")))
    if roadmap_path is None or not roadmap_path.exists():
        return None

    counts = {"DONE": 0, "NEXT": 0, "QUEUED": 0}
    try:
        roadmap_text = read_text(roadmap_path)
    except OSError:
        return None

    for raw_line in roadmap_text.splitlines():
        line = raw_line.strip()
        match = QUEUE_ITEM_STATUS_RE.match(line)
        if not match:
            continue
        counts[match.group(1)] += 1

    total_count = counts["DONE"] + counts["NEXT"] + counts["QUEUED"]
    remaining_count = counts["NEXT"] + counts["QUEUED"]
    return {
        "roadmap_path": roadmap_path,
        "counts": counts,
        "done_count": counts["DONE"],
        "total_count": total_count,
        "remaining_count": remaining_count,
    }


def has_remaining_lane_work(config: dict[str, Any], state: dict[str, Any], lane_id: str) -> bool:
    queue_progress = read_lane_queue_progress(config, state=state, lane_id=lane_id)
    if queue_progress is None:
        return False
    return int(queue_progress["remaining_count"]) > 0


def next_unfinished_lane_id(config: dict[str, Any], state: dict[str, Any], *, after_lane_id: str | None = None) -> str | None:
    started = after_lane_id is None
    for lane in config["lanes"]:
        lane_id = lane["id"]
        if not started:
            if lane_id == after_lane_id:
                started = True
            continue
        if lane_id == after_lane_id:
            continue
        if has_remaining_lane_work(config, state, lane_id):
            return lane_id
    return None


def has_any_unfinished_lane_work(config: dict[str, Any], state: dict[str, Any]) -> bool:
    return any(has_remaining_lane_work(config, state, lane["id"]) for lane in config["lanes"])


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
        popen_kwargs['creationflags'] = creationflags

    startupinfo_factory = getattr(subprocess, 'STARTUPINFO', None)
    startf_use_show_window = int(getattr(subprocess, 'STARTF_USESHOWWINDOW', 0))
    sw_hide = int(getattr(subprocess, 'SW_HIDE', 0))
    if startupinfo_factory and startf_use_show_window:
        startupinfo = startupinfo_factory()
        startupinfo.dwFlags |= startf_use_show_window
        startupinfo.wShowWindow = sw_hide
        popen_kwargs['startupinfo'] = startupinfo

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


def new_state(config: dict[str, Any]) -> dict[str, Any]:
    timestamp = now_timestamp()
    lane_progress = build_initial_lane_progress(config)
    initial_lane_id = config["lanes"][0]["id"]
    return {
        "status": "active",
        "current_round": 0,
        "consecutive_failures": 0,
        "active_lane_id": initial_lane_id,
        "lane_progress": lane_progress,
        "next_phase_number": lane_progress[initial_lane_id]["next_phase_number"],
        "last_phase_doc": lane_progress[initial_lane_id]["last_phase_doc"],
        "last_commit_sha": None,
        "last_summary": None,
        "last_next_focus": active_lane_config({"active_lane_id": initial_lane_id, "lane_progress": lane_progress}, config)["focus_hint"],
        "last_result": None,
        "last_blocking_reason": None,
        "vulture_command": clean_string(config.get("vulture_command")),
        "vulture_current_count": None,
        "vulture_previous_count": None,
        "vulture_delta": None,
        "vulture_updated_at": None,
        "vulture_last_error": None,
        "started_at": timestamp,
        "updated_at": timestamp,
    }


def save_state(state: dict[str, Any], state_path: Path) -> None:
    state["updated_at"] = now_timestamp()
    write_json(state_path, state)


def infer_round_roadmap_path_from_phase_doc(phase_doc_path: str) -> Path | None:
    roadmap_path_text = infer_roadmap_path_text_from_phase_doc(phase_doc_path)
    if not roadmap_path_text:
        return None

    roadmap_path = resolve_repo_path(roadmap_path_text)
    if roadmap_path.exists():
        return roadmap_path
    return None


def read_queue_status_counts_from_state(state: dict[str, Any] | None, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if state is None:
        return None
    lane_id = clean_string(state.get("active_lane_id"))
    return read_lane_queue_progress(config, state=state, lane_id=lane_id or None)


def has_unfinished_queue_work(state: dict[str, Any] | None, config: dict[str, Any] | None = None) -> bool:
    queue_status = read_queue_status_counts_from_state(state, config)
    if queue_status is None:
        return False
    return int(queue_status.get("remaining_count", 0)) > 0


def ensure_next_phase_after_completed_round(state: dict[str, Any], config: dict[str, Any]) -> None:
    lane_progress = active_lane_progress(state, config)
    if parse_int(lane_progress.get("next_phase_number"), 0) < 1:
        lane_progress["next_phase_number"] = 1
    sync_active_lane_mirror_fields(state, config)


def resume_state_if_threshold_allows(
    state: dict[str, Any],
    config: dict[str, Any],
    state_path: Path,
) -> dict[str, Any]:
    state = normalize_state_for_lanes(state, config)
    previous_status = clean_string(state.get("status"))
    should_resume = False
    if previous_status == "stopped_max_rounds":
        should_resume = int(state["current_round"]) < int(config["max_rounds"])
    elif previous_status == "stopped_failures":
        should_resume = int(state["consecutive_failures"]) < int(config["max_consecutive_failures"])
    elif previous_status == "complete" and has_any_unfinished_lane_work(config, state):
        if not has_remaining_lane_work(config, state, active_lane_id_for_state(state, config)):
            next_lane_id = next_unfinished_lane_id(config, state)
            if next_lane_id:
                set_active_lane(state, config, next_lane_id)
        ensure_next_phase_after_completed_round(state, config)
        should_resume = True

    if not should_resume:
        return state

    state["status"] = "active"
    save_state(state, state_path)
    info(f"State status '{previous_status}' is resumable with current config; resuming.")
    return state


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
    current_count = int(snapshot["count"])
    state["vulture_previous_count"] = previous_count
    state["vulture_current_count"] = current_count
    state["vulture_delta"] = None if previous_count is None else current_count - int(previous_count)
    state["vulture_last_error"] = None


def build_runner_support() -> RunnerSupport:
    return RunnerSupport(
        repo_root=REPO_ROOT,
        error_type=AutopilotError,
        clean_string=clean_string,
        compact_text=compact_text,
        progress=progress,
        get_codex_event_summary=get_codex_event_summary,
        windows_hidden_process_kwargs=windows_hidden_process_kwargs,
    )


def build_validation_support() -> ValidationSupport:
    return ValidationSupport(
        clean_string=clean_string,
        resolve_repo_path=resolve_repo_path,
        run_git=run_git,
        info=info,
    )


def format_metric_delta(value: Any) -> str:
    if value is None or clean_string(value) == "":
        return "n/a"
    try:
        delta_value = int(value)
    except (TypeError, ValueError):
        return clean_string(value)
    if delta_value > 0:
        return f"+{delta_value}"
    return str(delta_value)


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
    merged_config = normalize_lanes_config(merged_config)
    return merged_config, config_path, profile_path


def read_lock(lock_path: Path) -> dict[str, Any] | None:
    if not lock_path.exists():
        return None
    try:
        return read_json(lock_path)
    except json.JSONDecodeError:
        return {"invalid": True, "raw_path": str(lock_path)}


def acquire_lock(
    runtime_directory: Path,
    *,
    branch: str,
    head_sha: str,
    profile_name: str,
    force_lock: bool,
) -> dict[str, Any]:
    lock_path = runtime_directory / LOCK_FILENAME
    existing_lock = read_lock(lock_path)
    hostname = socket.gethostname()
    current_pid = os.getpid()

    if existing_lock:
        existing_host = clean_string(existing_lock.get("hostname"))
        existing_pid = parse_int(existing_lock.get("pid"), -1)

        if existing_host and existing_host != hostname:
            if not force_lock:
                raise AutopilotError(
                    f"Lock file is owned by host '{existing_host}' (pid {existing_pid}). "
                    "Stop the other machine first or rerun with --force-lock."
                )
            info(f"Overriding lock owned by host '{existing_host}' (pid {existing_pid}).")
        elif existing_pid > 0 and existing_pid != current_pid and pid_exists(existing_pid):
            if not force_lock:
                raise AutopilotError(
                    f"Another autopilot is already running on this host (pid {existing_pid}). "
                    "Stop it first or rerun with --force-lock."
                )
            info(f"Overriding running local lock owned by pid {existing_pid}.")
        elif existing_lock.get("invalid"):
            info(f"Replacing unreadable lock file at {lock_path}.")
        else:
            info("Replacing stale lock file.")

    lock_data = {
        "hostname": hostname,
        "pid": current_pid,
        "started_at": now_timestamp(),
        "branch": branch,
        "head": head_sha,
        "profile": profile_name,
    }
    write_json(lock_path, lock_data)
    return lock_data


def release_lock(runtime_directory: Path, lock_data: dict[str, Any] | None) -> None:
    if not lock_data:
        return
    lock_path = runtime_directory / LOCK_FILENAME
    if not lock_path.exists():
        return
    try:
        current_lock = read_json(lock_path)
    except json.JSONDecodeError:
        lock_path.unlink(missing_ok=True)
        return
    if (
        clean_string(current_lock.get("hostname")) == clean_string(lock_data.get("hostname"))
        and parse_int(current_lock.get("pid"), -1) == parse_int(lock_data.get("pid"), -1)
    ):
        lock_path.unlink(missing_ok=True)


@contextmanager
def autopilot_lock(
    runtime_directory: Path,
    *,
    branch: str,
    head_sha: str,
    profile_name: str,
    force_lock: bool,
) -> Any:
    lock_data = acquire_lock(
        runtime_directory,
        branch=branch,
        head_sha=head_sha,
        profile_name=profile_name,
        force_lock=force_lock,
    )
    try:
        yield lock_data
    finally:
        release_lock(runtime_directory, lock_data)


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


def advance_lane_after_nonfailure(state: dict[str, Any], config: dict[str, Any], *, completed_lane_id: str) -> None:
    increment_active_lane_phase(state, config)
    if has_remaining_lane_work(config, state, completed_lane_id):
        set_active_lane(state, config, completed_lane_id)
        state["status"] = "active"
        return

    mark_lane_complete(state, completed_lane_id)
    next_lane_id = next_unfinished_lane_id(config, state, after_lane_id=completed_lane_id)
    if next_lane_id:
        set_active_lane(state, config, next_lane_id)
        state["status"] = "active"
        state["last_next_focus"] = config_lane_map(config)[next_lane_id]["focus_hint"]
        return

    state["status"] = "complete"


def get_current_branch() -> str:
    return run_git(["branch", "--show-current"]).stdout


def get_head_sha() -> str:
    return run_git(["rev-parse", "HEAD"]).stdout


def ensure_commands_available(command_names: list[str]) -> list[str]:
    missing: list[str] = []
    for command_name in command_names:
        if shutil.which(command_name) is None:
            missing.append(command_name)
    return missing


def run_start(args: argparse.Namespace) -> int:
    config, _, _ = load_config(args.config_path, args.profile, args.profile_path)
    state_path = resolve_repo_path(args.state_path)
    runtime_directory = state_path.parent
    runtime_directory.mkdir(parents=True, exist_ok=True)

    schema_path = resolve_repo_path(str(config["result_schema"]))
    schema = read_json(schema_path)
    runner_support = build_runner_support()
    validation_support = build_validation_support()

    runner_executable = resolve_runner_executable(
        config,
        clean_string=runner_support.clean_string,
        error_type=runner_support.error_type,
    )
    missing_commands = ensure_commands_available(["git"])
    if runner_executable == "codex":
        missing_commands.extend(ensure_commands_available(["codex"]))
    if missing_commands:
        raise AutopilotError(f"Required command(s) not found in PATH: {', '.join(missing_commands)}")

    state = read_json(state_path) if state_path.exists() else new_state(config)
    state = normalize_state_for_lanes(state, config)
    save_state(state, state_path)
    state = resume_state_if_threshold_allows(state, config, state_path)

    current_branch = get_current_branch()
    if not args.no_branch_guard and not test_branch_allowed(current_branch, list(config.get("allowed_branch_prefixes", []))):
        raise AutopilotError(
            "Refusing to run on branch "
            f"'{current_branch}'. Use a dedicated worktree branch with one of these prefixes: "
            f"{', '.join(config.get('allowed_branch_prefixes', []))}."
        )

    if not args.allow_dirty_worktree and is_working_tree_dirty():
        raise AutopilotError("Working tree must be clean before unattended execution.")

    rounds_executed = 0
    head_sha = get_head_sha()

    with autopilot_lock(
        runtime_directory,
        branch=current_branch,
        head_sha=head_sha,
        profile_name=args.profile,
        force_lock=args.force_lock,
    ):
        if clean_string(config.get("vulture_command")):
            refresh_vulture_metrics(state, config)
            save_state(state, state_path)

        while True:
            if args.single_round and rounds_executed >= 1:
                info("Single round requested; stopping.")
                break

            if args.max_rounds_this_run > 0 and rounds_executed >= args.max_rounds_this_run:
                info(f"Reached MaxRoundsThisRun={args.max_rounds_this_run}; stopping.")
                break

            if clean_string(state.get("status")) != "active":
                info(f"State status is '{state.get('status')}'; stopping.")
                break

            if int(state["current_round"]) >= int(config["max_rounds"]):
                state["status"] = "stopped_max_rounds"
                save_state(state, state_path)
                info(f"Reached max_rounds={config['max_rounds']}; stopping.")
                break

            if int(state["consecutive_failures"]) >= int(config["max_consecutive_failures"]):
                state["status"] = "stopped_failures"
                save_state(state, state_path)
                info(f"Reached max_consecutive_failures={config['max_consecutive_failures']}; stopping.")
                break

            attempt_number = int(state["current_round"]) + 1
            current_lane = active_lane_config(state, config)
            current_lane_id = current_lane["id"]
            current_lane_progress = active_lane_progress(state, config)
            round_config = lane_runtime_config(config, current_lane)
            template_path = resolve_repo_path(str(round_config["prompt_template"]))
            template_text = read_text(template_path)
            phase_number = parse_int(current_lane_progress.get("next_phase_number"), 1)
            phase_doc_relative_path = f"{current_lane['phase_doc_prefix']}{phase_number}.md"
            round_directory = runtime_directory / f"round-{attempt_number:03d}"
            round_directory.mkdir(parents=True, exist_ok=True)

            prompt_path = round_directory / "prompt.md"
            assistant_output_path = round_directory / "assistant-output.json"
            events_log_path = round_directory / "events.jsonl"
            progress_log_path = round_directory / "progress.log"

            rendered_prompt = render_template(
                template_text,
                {
                    "objective": config["objective"],
                    "round_attempt": attempt_number,
                    "next_phase_number": phase_number,
                    "next_phase_doc": phase_doc_relative_path,
                    "current_branch": current_branch,
                    "last_phase_doc": clean_string(state.get("last_phase_doc")),
                    "last_commit_sha": clean_string(state.get("last_commit_sha")),
                    "last_summary": clean_string(state.get("last_summary")),
                    "focus_hint": clean_string(state.get("last_next_focus")),
                    "lint_command": clean_string(config.get("lint_command")),
                    "typecheck_command": clean_string(config.get("typecheck_command")),
                    "full_test_command": clean_string(config.get("full_test_command")),
                    "build_command": config["build_command"],
                    "vulture_command": clean_string(config.get("vulture_command")),
                    "runner_kind": clean_string(config.get("runner_kind")),
                    "runner_model": clean_string(config.get("runner_model")),
                    "commit_prefix": round_config["commit_prefix"],
                    "platform_note": config.get("platform_note", ""),
                    "current_lane_id": current_lane_id,
                    "current_lane_label": current_lane["label"],
                    "current_lane_roadmap": current_lane["roadmap_path"],
                },
            )
            rendered_prompt = append_controller_requirements(rendered_prompt, round_config)
            prompt_path.write_bytes(rendered_prompt.encode("utf-8"))

            if args.dry_run:
                info(f"Dry run complete. Prompt written to {prompt_path}")
                break

            starting_head = get_head_sha()
            info(f"Starting round {attempt_number} (phase {phase_number}).")
            codex_exit_code = invoke_runner_round(
                prompt_path=prompt_path,
                schema_path=schema_path,
                assistant_output_path=assistant_output_path,
                events_log_path=events_log_path,
                progress_log_path=progress_log_path,
                config=config,
                support=runner_support,
            )
            rounds_executed += 1

            result: dict[str, Any] | None = None
            parse_error: str | None = None
            stderr_log_path = events_log_path.with_suffix(".stderr.log")
            if assistant_output_path.exists():
                try:
                    parsed_result = read_json(assistant_output_path)
                    if isinstance(parsed_result, dict):
                        result = parsed_result
                    else:
                        parse_error = "Agent output JSON was not an object."
                except json.JSONDecodeError as exc:
                    parse_error = str(exc)

            ending_head = get_head_sha()
            working_tree_dirty = is_working_tree_dirty()
            failure_reason: str | None = None

            if codex_exit_code != 0:
                stderr_text = stderr_log_path.read_text(encoding="utf-8", errors="replace") if stderr_log_path.exists() else ""
                if "input is not valid UTF-8" in stderr_text:
                    failure_reason = "runner could not read the round prompt as UTF-8."
                else:
                    failure_reason = f"runner exited with code {codex_exit_code}."
            elif result is None:
                failure_reason = (
                    f"Could not parse agent output JSON: {parse_error}"
                    if parse_error
                    else "Agent output JSON was not created."
                )

            if not failure_reason and result is not None:
                failure_reason = validate_round_result(
                    attempt_number=attempt_number,
                    result=result,
                    schema=schema,
                    phase_doc_relative_path=phase_doc_relative_path,
                    expected_lane_id=current_lane_id,
                    config=round_config,
                    ending_head=ending_head,
                    working_tree_dirty=working_tree_dirty,
                    support=validation_support,
                )

            state["current_round"] = int(state["current_round"]) + 1
            history_entry = build_history_entry(
                attempt_number=attempt_number,
                phase_number=phase_number,
                lane_id=current_lane_id,
                result=result,
                failure_reason=failure_reason,
            )

            if failure_reason:
                info(f"Round {attempt_number} failed: {failure_reason}")
                if ending_head != starting_head or working_tree_dirty:
                    info(f"Reverting worktree to {starting_head}")
                    reset_worktree_to_head(starting_head)

                state["consecutive_failures"] = int(state["consecutive_failures"]) + 1
                state["last_result"] = "failure"
                state["last_blocking_reason"] = failure_reason
                if result and clean_string(result.get("next_focus")):
                    state["last_next_focus"] = result.get("next_focus")
                append_history_entry(runtime_directory, history_entry)
                save_state(state, state_path)

                if failure_reason == "runner could not read the round prompt as UTF-8.":
                    state["status"] = "stopped_infra_error"
                    save_state(state, state_path)
                    info("Stopping after infrastructure error: prompt encoding.")
                    break

                continue

            assert result is not None
            state["consecutive_failures"] = 0
            state["last_result"] = result["status"]
            state["last_blocking_reason"] = None
            state["last_summary"] = result["summary"]

            if clean_string(result.get("next_focus")):
                state["last_next_focus"] = result["next_focus"]
            if clean_string(result.get("phase_doc_path")):
                state["lane_progress"][current_lane_id]["last_phase_doc"] = result["phase_doc_path"]
            if clean_string(result.get("commit_sha")):
                state["last_commit_sha"] = result["commit_sha"]

            sync_active_lane_mirror_fields(state, config)

            if result["status"] == "success":
                advance_lane_after_nonfailure(state, config, completed_lane_id=current_lane_id)
                info(f"Round {attempt_number} succeeded with commit {result['commit_sha']}.")
            elif result["status"] == "goal_complete":
                advance_lane_after_nonfailure(state, config, completed_lane_id=current_lane_id)
                if clean_string(state.get("status")) == "complete":
                    info("Autopilot objective reported complete.")
                else:
                    info("Round reported goal_complete; controller advanced without wasting an empty discovery round.")

            if clean_string(state.get("status")) != "complete" and active_lane_id_for_state(state, config) != current_lane_id:
                next_lane = active_lane_config(state, config)
                info(f"Switching active lane to {next_lane['id']}.")

            if clean_string(config.get("vulture_command")):
                refresh_vulture_metrics(state, config)
            append_history_entry(runtime_directory, history_entry)
            save_state(state, state_path)

    return 0


def print_state_summary(state: dict[str, Any], *, runtime_directory: Path | None = None) -> None:
    queue_progress = read_watch_queue_progress(state)
    lane_id = clean_string(state.get("active_lane_id")) or "legacy"
    print(
        "[status] "
        f"status={state.get('status')} round={state.get('current_round')} "
        f"lane={lane_id} phase={state.get('next_phase_number')} failures={state.get('consecutive_failures')}"
    )
    if queue_progress and queue_progress.get("total_count") is not None:
        print(f"[status] queue: {queue_progress['done_count']}/{queue_progress['total_count']} done")
    if state.get("last_phase_doc"):
        print(f"[status] last phase doc: {state.get('last_phase_doc')}")
    if state.get("last_next_focus"):
        print(f"[status] next focus: {state.get('last_next_focus')}")
    if state.get("last_commit_sha"):
        print(f"[status] last commit: {state.get('last_commit_sha')}")
    if clean_string(state.get("vulture_command")):
        if clean_string(state.get("vulture_last_error")):
            print(f"[status] vulture: error={compact_text(clean_string(state.get('vulture_last_error')), max_length=220)}")
        else:
            print(
                "[status] vulture: "
                f"count={state.get('vulture_current_count')} "
                f"delta={format_metric_delta(state.get('vulture_delta'))}"
            )
            if state.get("vulture_updated_at"):
                print(f"[status] vulture updated: {state.get('vulture_updated_at')}")
    if runtime_directory:
        lock_path = runtime_directory / LOCK_FILENAME
        lock_data = read_lock(lock_path)
        if lock_data:
            print(
                "[status] lock: "
                f"host={lock_data.get('hostname')} pid={lock_data.get('pid')} "
                f"profile={lock_data.get('profile')} started_at={lock_data.get('started_at')}"
            )
        else:
            print("[status] lock: none")


def run_status(args: argparse.Namespace) -> int:
    state_path = resolve_repo_path(args.state_path)
    if not state_path.exists():
        print(f"[status] state file not found: {state_path}")
        return 1
    state = read_json(state_path)
    print_state_summary(state, runtime_directory=state_path.parent)
    return 0


def parse_round_directory_number(path: Path | None) -> int | None:
    if path is None:
        return None
    match = ROUND_DIRECTORY_RE.fullmatch(path.name)
    if not match:
        return None
    return int(match.group(1))


def resolve_watch_state_path(runtime_directory: Path, explicit_state_path: str | None) -> Path:
    explicit_path = clean_string(explicit_state_path)
    if explicit_path:
        return resolve_repo_path(explicit_path)

    default_state_path = runtime_directory / Path(DEFAULT_STATE_PATH).name
    if default_state_path.exists():
        return default_state_path

    candidate_paths = sorted(
        (
            path
            for path in runtime_directory.glob("*state*.json")
            if path.is_file() and path.name != LOCK_FILENAME
        ),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    if candidate_paths:
        return candidate_paths[-1]

    return default_state_path


def latest_round_directory(runtime_directory: Path) -> Path | None:
    round_directories = sorted(
        (path for path in runtime_directory.iterdir() if path.is_dir() and ROUND_DIRECTORY_RE.fullmatch(path.name)),
        key=lambda path: parse_round_directory_number(path) or -1,
    )
    return round_directories[-1] if round_directories else None


def infer_watch_roadmap_path(state: dict[str, Any] | None) -> Path | None:
    if state is None:
        return None

    phase_doc_path = clean_string(state.get("last_phase_doc"))
    if not phase_doc_path:
        return None

    normalized_phase_doc = phase_doc_path.replace("\\", "/")
    match = re.match(r"^(?P<prefix>.+?)phase-\d+\.md$", normalized_phase_doc)
    if not match:
        return None

    roadmap_path = resolve_repo_path(f"{match.group('prefix')}round-roadmap.md")
    if roadmap_path.exists():
        return roadmap_path
    return None


def read_watch_queue_progress(state: dict[str, Any] | None) -> dict[str, Any] | None:
    roadmap_path = infer_watch_roadmap_path(state)
    if roadmap_path is None:
        return None

    counts = {"DONE": 0, "NEXT": 0, "QUEUED": 0}
    try:
        roadmap_text = read_text(roadmap_path)
    except OSError:
        return None

    for raw_line in roadmap_text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^### \[(DONE|NEXT|QUEUED)\]\s+", line)
        if not match:
            continue
        counts[match.group(1)] += 1

    total = counts["DONE"] + counts["NEXT"] + counts["QUEUED"]
    return {
        "done_count": counts["DONE"],
        "total_count": total,
        "remaining_count": counts["NEXT"] + counts["QUEUED"],
        "roadmap_path": roadmap_path,
    }


def build_watch_state_signature(state: dict[str, Any] | None, *, state_path_exists: bool) -> tuple[str, ...]:
    if not state_path_exists or state is None:
        return ("missing",)
    return (
        clean_string(state.get("status")),
        clean_string(state.get("active_lane_id")),
        clean_string(state.get("current_round")),
        clean_string(state.get("consecutive_failures")),
        clean_string(state.get("next_phase_number")),
        clean_string(state.get("last_phase_doc")),
        clean_string(state.get("last_next_focus")),
        clean_string(state.get("last_commit_sha")),
    )


def print_watch_snapshot(
    *,
    state: dict[str, Any] | None,
    state_path: Path,
    progress_path: Path | None,
) -> None:
    state_round = clean_string(state.get("current_round")) if state else ""
    watched_round_number = parse_round_directory_number(progress_path.parent) if progress_path else None
    phase_number = clean_string(state.get("next_phase_number")) if state else ""
    lane_id = clean_string(state.get("active_lane_id")) if state else ""
    status_value = clean_string(state.get("status")) if state else ""
    failures_value = clean_string(state.get("consecutive_failures")) if state else ""
    queue_progress = read_watch_queue_progress(state)
    heading_parts: list[str] = []

    if watched_round_number is not None and state_round and state_round == str(watched_round_number):
        heading_parts.append(f"round={watched_round_number}")
    else:
        if watched_round_number is not None:
            heading_parts.append(f"watch_round={watched_round_number}")
        if state_round:
            heading_parts.append(f"state_round={state_round}")
    if phase_number:
        heading_parts.append(f"phase={phase_number}")
    if lane_id:
        heading_parts.append(f"lane={lane_id}")
    if queue_progress and queue_progress.get("total_count") is not None:
        heading_parts.append(f"queue={queue_progress['done_count']}/{queue_progress['total_count']}")
    if state and state.get("vulture_current_count") is not None:
        heading_parts.append(f"vulture={state.get('vulture_current_count')}")
    if state and state.get("vulture_delta") is not None:
        heading_parts.append(f"vdelta={format_metric_delta(state.get('vulture_delta'))}")
    heading_parts.append(f"status={status_value or 'unknown'}")
    heading_parts.append(f"failures={failures_value or '0'}")

    print()
    print("[watch] " + "=" * 72)
    print(f"[watch] {' '.join(heading_parts)}")
    if state is None:
        print(f"[watch] state file: {state_path} (not created yet)")
    else:
        print(f"[watch] state file: {state_path}")
        if state.get("last_phase_doc"):
            print(f"[watch] phase doc: {state.get('last_phase_doc')}")
        if state.get("last_next_focus"):
            print(f"[watch] focus: {compact_text(clean_string(state.get('last_next_focus')), max_length=220)}")
        if state.get("last_commit_sha"):
            print(f"[watch] last commit: {state.get('last_commit_sha')}")
        if clean_string(state.get("vulture_command")):
            if clean_string(state.get("vulture_last_error")):
                print(f"[watch] vulture error: {compact_text(clean_string(state.get('vulture_last_error')), max_length=220)}")
            else:
                print(
                    "[watch] vulture: "
                    f"count={state.get('vulture_current_count')} "
                    f"delta={format_metric_delta(state.get('vulture_delta'))}"
                )
        if queue_progress and queue_progress.get("total_count") is not None:
            print(
                "[watch] queue progress: "
                f"{queue_progress['done_count']}/{queue_progress['total_count']} done "
                f"({queue_progress['remaining_count']} remaining)"
            )
    if progress_path is not None:
        print(f"[watch] progress log: {progress_path}")
    print("[watch] " + "=" * 72)


def format_watch_detail_counter(value: Any, *, prefix: str = "", width: int = 3) -> str:
    text = clean_string(value)
    if not text:
        return f"{prefix}{'?' * width}" if prefix else "?"
    try:
        rendered = f"{int(text):0{width}d}"
    except (TypeError, ValueError):
        rendered = text
    return f"{prefix}{rendered}" if prefix else rendered


def format_watch_completion_percent(value: Any) -> str:
    text = clean_string(value)
    if not text:
        return "??%"
    try:
        clamped_value = max(0, min(100, int(text)))
    except (TypeError, ValueError):
        return f"{text}%"
    return f"{clamped_value}%"


def expected_round_number_for_state(state: dict[str, Any] | None) -> int | None:
    if state is None:
        return None
    try:
        completed_round = int(state.get("current_round", 0))
    except (TypeError, ValueError):
        return None
    if clean_string(state.get("status")) == "active":
        return completed_round + 1
    return completed_round if completed_round > 0 else None


def watched_round_directory(runtime_directory: Path, state: dict[str, Any] | None) -> Path | None:
    expected_round_number = expected_round_number_for_state(state)
    if expected_round_number is not None:
        return runtime_directory / f"round-{expected_round_number:03d}"
    return latest_round_directory(runtime_directory)


def build_watch_detail_prefix(
    *,
    state: dict[str, Any] | None,
    progress_path: Path | None,
    prefix_format: str = "long",
) -> str:
    watched_round_number = parse_round_directory_number(progress_path.parent) if progress_path else None
    if watched_round_number is None:
        watched_round_number = expected_round_number_for_state(state)

    round_value = format_watch_detail_counter(watched_round_number, width=3)
    phase_value = format_watch_detail_counter(state.get("next_phase_number") if state else None, width=3)
    failure_value = format_watch_detail_counter(
        state.get("consecutive_failures") if state else None,
        width=1,
    )
    lane_token = clean_string(state.get("active_lane_id")) if state else ""
    queue_progress = read_watch_queue_progress(state)
    queue_value = "q?/?"
    if queue_progress and queue_progress.get("total_count") is not None:
        queue_value = f"q{queue_progress['done_count']}/{queue_progress['total_count']}"
    status_token = clean_string(state.get("status")) if state else ""
    if clean_string(prefix_format).lower() == "short":
        lane_short = lane_token or "lane?"
        return f"[{lane_short} {queue_value} r{round_value} p{phase_value} {status_token or 'unknown'} f{failure_value}]"
    return (
        f"[lane={lane_token or 'unknown'} queue={queue_value[1:]} round={round_value} phase={phase_value} "
        f"status={status_token or 'unknown'} failures={failure_value}]"
    )


def print_watch_detail_lines(
    lines: list[str],
    *,
    state: dict[str, Any] | None,
    progress_path: Path | None,
    prefix_format: str = "long",
) -> None:
    if not lines:
        return
    prefix = build_watch_detail_prefix(
        state=state,
        progress_path=progress_path,
        prefix_format=prefix_format,
    )
    for line in lines:
        if line:
            print(f"{prefix} {line}")
        else:
            print(prefix)


def stop_process(pid: int, *, graceful_timeout_seconds: int = 30) -> None:
    if pid <= 0:
        return
    if not pid_exists(pid):
        info(f"Process {pid} already exited.")
        return

    info(f"Stopping process {pid}.")
    if os.name == "nt":
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + graceful_timeout_seconds
        while time.time() < deadline:
            if not pid_exists(pid):
                info(f"Process {pid} stopped cleanly.")
                return
            time.sleep(1)

        taskkill_result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **windows_hidden_process_kwargs(),
        )
        if taskkill_result.returncode != 0 and pid_exists(pid):
            combined = "\n".join(part for part in (taskkill_result.stdout, taskkill_result.stderr) if part.strip())
            raise AutopilotError(f"Failed to force-stop pid {pid}: {combined}")
    else:
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + graceful_timeout_seconds
        while time.time() < deadline:
            if not pid_exists(pid):
                info(f"Process {pid} stopped cleanly.")
                return
            time.sleep(1)

        os.kill(pid, signal.SIGKILL)
        deadline = time.time() + 10
        while time.time() < deadline:
            if not pid_exists(pid):
                info(f"Process {pid} force-stopped.")
                return
            time.sleep(1)

    if pid_exists(pid):
        raise AutopilotError(f"Failed to stop pid {pid}.")


def remove_stale_lock(runtime_directory: Path, *, expected_pid: int | None = None) -> None:
    lock_path = runtime_directory / LOCK_FILENAME
    lock_data = read_lock(lock_path)
    if not lock_data:
        return

    lock_pid = parse_int(lock_data.get("pid"), -1)

    if expected_pid is not None and lock_pid not in (-1, expected_pid):
        return

    if lock_pid > 0 and pid_exists(lock_pid):
        raise AutopilotError(f"Refusing to remove active lock owned by pid {lock_pid}.")

    lock_path.unlink(missing_ok=True)
    info(f"Removed stale lock file at {lock_path}.")


def build_restart_start_args(args: argparse.Namespace) -> list[str]:
    restart_profile = clean_string(args.restart_profile) or clean_string(args.profile) or DEFAULT_PROFILE_NAME
    restart_config_path = clean_string(args.restart_config_path) or clean_string(args.config_path) or DEFAULT_CONFIG_PATH
    restart_state_path = clean_string(args.restart_state_path) or clean_string(args.state_path) or DEFAULT_STATE_PATH
    restart_profile_path = clean_string(args.restart_profile_path) or clean_string(args.profile_path)

    start_args = [
        sys.executable,
        str(resolve_repo_path("automation/autopilot.py")),
        "start",
        "--profile",
        restart_profile,
        "--config-path",
        restart_config_path,
        "--state-path",
        restart_state_path,
    ]
    if restart_profile_path:
        start_args.extend(["--profile-path", restart_profile_path])
    return start_args


def git_ref_exists(ref_name: str) -> bool:
    return run_git(["rev-parse", "--verify", f"{ref_name}^{{commit}}"], check=False).returncode == 0


def git_is_ancestor(ancestor_ref: str, descendant_ref: str) -> bool:
    return run_git(["merge-base", "--is-ancestor", ancestor_ref, descendant_ref], check=False).returncode == 0


def sync_repo_to_restart_ref(
    *,
    restart_sync_ref: str,
    stopped_head: str,
    timeout_seconds: int,
    refresh_seconds: int,
) -> None:
    started_monotonic = time.monotonic()
    while True:
        run_git_no_capture(["fetch", "--all", "--prune"], check=True)

        if git_ref_exists(restart_sync_ref):
            if git_is_ancestor(stopped_head, restart_sync_ref):
                info(f"Fast-forwarding repo to cutover ref {restart_sync_ref}.")
                run_git_no_capture(["merge", "--ff-only", restart_sync_ref], check=True)
                return
            info(f"Ref {restart_sync_ref} exists but is not a fast-forward successor of stopped HEAD {stopped_head}.")
        else:
            info(f"Waiting for cutover ref {restart_sync_ref} to appear.")

        if timeout_seconds > 0 and time.monotonic() - started_monotonic >= timeout_seconds:
            raise AutopilotError(
                f"Timed out waiting for cutover ref '{restart_sync_ref}' to become a fast-forward successor of {stopped_head}."
            )

        time.sleep(refresh_seconds)


def spawn_background_autopilot(command_args: list[str], *, output_path: Path, pid_path: Path | None = None) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_handle = output_path.open("ab")
    popen_kwargs: dict[str, Any] = {
        "args": command_args,
        "cwd": str(REPO_ROOT),
        "stdin": subprocess.DEVNULL,
        "stdout": output_handle,
        "stderr": subprocess.STDOUT,
    }

    if os.name == "nt":
        popen_kwargs.update(
            windows_hidden_process_kwargs(
                detached=True,
                new_process_group=True,
            )
        )
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(**popen_kwargs)
    finally:
        output_handle.close()

    if pid_path:
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    return int(process.pid)


def run_watch(args: argparse.Namespace) -> int:
    runtime_directory = resolve_repo_path(args.runtime_path)
    state_path = resolve_watch_state_path(runtime_directory, getattr(args, "state_path", ""))
    last_progress_path: Path | None = None
    last_line_count = 0
    last_state_signature: tuple[str, ...] | None = None

    print(f"[watch] runtime: {runtime_directory}")
    while True:
        state_exists = state_path.exists()
        state = read_json(state_path) if state_exists else None
        state_signature = build_watch_state_signature(state, state_path_exists=state_exists)

        round_directory = watched_round_directory(runtime_directory, state)
        progress_path = round_directory / "progress.log" if round_directory is not None else None

        if state_signature != last_state_signature or progress_path != last_progress_path:
            print_watch_snapshot(
                state=state,
                state_path=state_path,
                progress_path=progress_path,
            )
            last_state_signature = state_signature

        if progress_path is not None:
            if progress_path != last_progress_path:
                last_progress_path = progress_path
                last_line_count = 0
                if progress_path.exists():
                    existing_lines = progress_path.read_text(encoding="utf-8", errors="replace").splitlines()
                    if existing_lines:
                        tail_lines = existing_lines[-args.tail :]
                        print_watch_detail_lines(
                            tail_lines,
                            state=state,
                            progress_path=progress_path,
                            prefix_format=args.prefix_format,
                        )
                        last_line_count = len(existing_lines)

            if last_progress_path and last_progress_path.exists():
                current_lines = last_progress_path.read_text(encoding="utf-8", errors="replace").splitlines()
                if len(current_lines) > last_line_count:
                    print_watch_detail_lines(
                        current_lines[last_line_count:],
                        state=state,
                        progress_path=last_progress_path,
                        prefix_format=args.prefix_format,
                    )
                    last_line_count = len(current_lines)

        if args.once:
            break
        time.sleep(args.refresh_seconds)
    return 0


def run_restart_after_next_commit(args: argparse.Namespace) -> int:
    state_path = resolve_repo_path(args.state_path)
    runtime_directory = state_path.parent
    if not state_path.exists():
        raise AutopilotError(f"State file not found: {state_path}")

    state = read_json(state_path)
    target_commit_sha = clean_string(state.get("last_commit_sha"))
    if not target_commit_sha:
        raise AutopilotError("State file does not have last_commit_sha; nothing to watch yet.")

    lock_path = runtime_directory / LOCK_FILENAME
    lock_data = read_lock(lock_path)
    current_pid = -1
    if lock_data:
        try:
            current_pid = int(lock_data.get("pid", -1))
        except (TypeError, ValueError):
            current_pid = -1

    info(
        "Watching for the next successful commit after "
        f"{target_commit_sha} (current pid {current_pid if current_pid > 0 else 'unknown'})."
    )

    refresh_seconds = max(1, int(args.refresh_seconds))
    while True:
        time.sleep(refresh_seconds)
        state = read_json(state_path)
        latest_commit_sha = clean_string(state.get("last_commit_sha"))
        current_round = state.get("current_round")
        current_status = clean_string(state.get("status"))

        if latest_commit_sha and latest_commit_sha != target_commit_sha:
            info(
                "Detected new commit "
                f"{latest_commit_sha} at round {current_round} with status {current_status or '<empty>'}."
            )
            break

        if current_status and current_status != "active" and args.stop_if_status_changes:
            raise AutopilotError(f"State changed to '{current_status}' before a new commit was detected.")

    if current_pid > 0:
        stop_process(current_pid, graceful_timeout_seconds=max(1, int(args.stop_timeout_seconds)))
    else:
        info("No active pid was captured from the lock file; skipping process stop step.")

    remove_stale_lock(runtime_directory, expected_pid=current_pid if current_pid > 0 else None)

    stopped_head = get_head_sha()

    if args.hard_reset:
        run_git_no_capture(["reset", "--hard", "HEAD"], check=True)

    restart_sync_ref = clean_string(args.restart_sync_ref)
    if restart_sync_ref:
        sync_repo_to_restart_ref(
            restart_sync_ref=restart_sync_ref,
            stopped_head=stopped_head,
            timeout_seconds=max(0, int(args.restart_sync_timeout_seconds)),
            refresh_seconds=max(1, int(args.restart_sync_refresh_seconds)),
        )

    restart_args = build_restart_start_args(args)
    restart_output_path = resolve_repo_path(args.restart_output_path)
    restart_pid_path = resolve_repo_path(args.restart_pid_path) if clean_string(args.restart_pid_path) else None
    new_pid = spawn_background_autopilot(restart_args, output_path=restart_output_path, pid_path=restart_pid_path)
    info(f"Started replacement autopilot pid {new_pid}.")
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    config, config_path, profile_path = load_config(args.config_path, args.profile, args.profile_path)
    failures = 0

    print(f"[doctor] repo: {REPO_ROOT}")
    print(f"[doctor] config: {config_path}")
    print(f"[doctor] profile: {profile_path}")

    git_path = shutil.which("git")
    if git_path:
        print(f"[doctor] ok   command git: {git_path}")
    else:
        print("[doctor] fail command git: not found in PATH")
        failures += 1

    try:
        runner_support = build_runner_support()
        runner_path = resolve_runner_executable(
            config,
            clean_string=runner_support.clean_string,
            error_type=runner_support.error_type,
        )
        print(f"[doctor] ok   runner command: {runner_path}")
    except AutopilotError as exc:
        print(f"[doctor] fail runner command: {exc}")
        failures += 1

    for extra_directory in config.get("runner_additional_dirs", []):
        extra_directory_text = clean_string(extra_directory)
        if not extra_directory_text:
            continue
        if Path(extra_directory_text).exists():
            print(f"[doctor] ok   runner add-dir: {extra_directory_text}")
        else:
            print(f"[doctor] fail runner add-dir: {extra_directory_text}")
            failures += 1

    deploy_verify_path = clean_string(config.get("deploy_verify_path"))
    if deploy_verify_path:
        if Path(deploy_verify_path).exists():
            print(f"[doctor] ok   deploy verify path: {deploy_verify_path}")
        else:
            print(f"[doctor] fail deploy verify path: {deploy_verify_path}")
            failures += 1
    else:
        print("[doctor] ok   deploy verify path: <not configured>")

    vulture_command = clean_string(config.get("vulture_command"))
    if vulture_command:
        snapshot = read_vulture_snapshot(config)
        if snapshot and not snapshot["error"]:
            print(
                "[doctor] ok   vulture command: "
                f"{vulture_command} (findings={snapshot['count']}, exit={snapshot['returncode']})"
            )
        else:
            error_text = snapshot["error"] if snapshot else "vulture snapshot unavailable"
            print(f"[doctor] fail vulture command: {compact_text(clean_string(error_text), max_length=220)}")
            failures += 1
    else:
        print("[doctor] info vulture command: <not configured>")

    print(f"[doctor] info lanes: {len(config.get('lanes', []))}")
    for lane in config.get("lanes", []):
        lane_id = lane["id"]
        try:
            ensure_path_within_repo(f"{lane['phase_doc_prefix']}0.md", label=f"Lane '{lane_id}' phase_doc_prefix probe")
            print(f"[doctor] ok   lane {lane_id} phase prefix: {lane['phase_doc_prefix']}")
        except AutopilotError as exc:
            print(f"[doctor] fail lane {lane_id} phase prefix: {exc}")
            failures += 1

        for label, path_value in [
            ("starting phase", lane["starting_phase_doc"]),
            ("roadmap", lane["roadmap_path"]),
            ("prompt", lane["prompt_template"]),
        ]:
            try:
                ensure_path_within_repo(path_value, label=f"Lane '{lane_id}' {label}", must_exist=True)
                print(f"[doctor] ok   lane {lane_id} {label}: {path_value}")
            except AutopilotError as exc:
                print(f"[doctor] fail lane {lane_id} {label}: {exc}")
                failures += 1

    branch_name = get_current_branch()
    allowed_prefixes = list(config.get("allowed_branch_prefixes", []))
    if test_branch_allowed(branch_name, allowed_prefixes):
        print(f"[doctor] ok   branch '{branch_name}' matches allowed prefixes")
    else:
        print(f"[doctor] fail branch '{branch_name}' does not match allowed prefixes: {', '.join(allowed_prefixes)}")
        failures += 1

    if is_working_tree_dirty():
        print("[doctor] fail working tree is dirty")
        failures += 1
    else:
        print("[doctor] ok   working tree is clean")

    runtime_directory = resolve_repo_path(args.runtime_path)
    print(f"[doctor] info runtime directory: {runtime_directory}")
    lock_path = runtime_directory / LOCK_FILENAME
    lock_data = read_lock(lock_path)
    if lock_data:
        print(
            "[doctor] warn lock present: "
            f"host={lock_data.get('hostname')} pid={lock_data.get('pid')} profile={lock_data.get('profile')}"
        )
    else:
        print("[doctor] ok   no autopilot lock present")

    return 1 if failures else 0


def run_version(args: argparse.Namespace) -> int:
    print(f"{AUTOPILOT_SCAFFOLD_NAME} {AUTOPILOT_SCAFFOLD_VERSION}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform repository autopilot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Run unattended autopilot rounds.")
    start_parser.add_argument("--profile", default=DEFAULT_PROFILE_NAME, help="Profile name under automation/profiles.")
    start_parser.add_argument("--profile-path", help="Explicit profile JSON path.")
    start_parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH, help="Base config JSON path.")
    start_parser.add_argument("--state-path", default=DEFAULT_STATE_PATH, help="State JSON path.")
    start_parser.add_argument("--max-rounds-this-run", type=int, default=0, help="Limit rounds for this process only.")
    start_parser.add_argument("--single-round", action="store_true", help="Run exactly one unattended round.")
    start_parser.add_argument("--dry-run", action="store_true", help="Render the next prompt only.")
    start_parser.add_argument("--no-branch-guard", action="store_true", help="Skip allowed-branch validation.")
    start_parser.add_argument("--allow-dirty-worktree", action="store_true", help="Skip clean-worktree validation.")
    start_parser.add_argument("--force-lock", action="store_true", help="Override an existing autopilot lock.")
    start_parser.set_defaults(handler=run_start)

    watch_parser = subparsers.add_parser("watch", help="Watch the latest round progress log.")
    watch_parser.add_argument("--runtime-path", default=DEFAULT_RUNTIME_PATH, help="Runtime directory path.")
    watch_parser.add_argument("--state-path", default="", help="Optional explicit state JSON path.")
    watch_parser.add_argument("--tail", type=int, default=20, help="How many lines to show when switching logs.")
    watch_parser.add_argument("--refresh-seconds", type=int, default=2, help="Polling interval.")
    watch_parser.add_argument(
        "--prefix-format",
        choices=["long", "short"],
        default="long",
        help="Prefix style for streamed progress.log lines.",
    )
    watch_parser.add_argument("--once", action="store_true", help="Print current status once and exit.")
    watch_parser.set_defaults(handler=run_watch)

    status_parser = subparsers.add_parser("status", help="Show current autopilot state.")
    status_parser.add_argument("--state-path", default=DEFAULT_STATE_PATH, help="State JSON path.")
    status_parser.set_defaults(handler=run_status)

    doctor_parser = subparsers.add_parser("doctor", help="Check environment and profile readiness.")
    doctor_parser.add_argument("--profile", default=DEFAULT_PROFILE_NAME, help="Profile name under automation/profiles.")
    doctor_parser.add_argument("--profile-path", help="Explicit profile JSON path.")
    doctor_parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH, help="Base config JSON path.")
    doctor_parser.add_argument("--runtime-path", default=DEFAULT_RUNTIME_PATH, help="Runtime directory path.")
    doctor_parser.set_defaults(handler=run_doctor)

    version_parser = subparsers.add_parser("version", help="Print the deployed scaffold version.")
    version_parser.set_defaults(handler=run_version)

    restart_parser = subparsers.add_parser(
        "restart-after-next-commit",
        help="Wait for the next successful commit, then restart autopilot with replacement settings.",
    )
    restart_parser.add_argument("--profile", default=DEFAULT_PROFILE_NAME, help="Current profile name under automation/profiles.")
    restart_parser.add_argument("--profile-path", help="Current explicit profile JSON path.")
    restart_parser.add_argument("--config-path", default=DEFAULT_CONFIG_PATH, help="Current base config JSON path.")
    restart_parser.add_argument("--state-path", default=DEFAULT_STATE_PATH, help="State JSON path to watch.")
    restart_parser.add_argument("--restart-profile", help="Profile name to use for the replacement start command.")
    restart_parser.add_argument("--restart-profile-path", help="Explicit profile JSON path for the replacement start command.")
    restart_parser.add_argument("--restart-config-path", help="Config JSON path for the replacement start command.")
    restart_parser.add_argument("--restart-state-path", help="State JSON path for the replacement start command.")
    restart_parser.add_argument(
        "--restart-output-path",
        default="automation/runtime/autopilot-restart.out",
        help="Where to write the replacement autopilot stdout/stderr stream.",
    )
    restart_parser.add_argument(
        "--restart-pid-path",
        default="automation/runtime/autopilot.pid",
        help="Where to write the replacement autopilot pid.",
    )
    restart_parser.add_argument("--refresh-seconds", type=int, default=5, help="Polling interval while waiting.")
    restart_parser.add_argument(
        "--stop-timeout-seconds",
        type=int,
        default=30,
        help="How long to wait for the current autopilot to stop before forcing it.",
    )
    restart_parser.add_argument(
        "--hard-reset",
        action="store_true",
        default=True,
        help="Run `git reset --hard HEAD` before launching the replacement process.",
    )
    restart_parser.add_argument(
        "--no-hard-reset",
        dest="hard_reset",
        action="store_false",
        help="Skip `git reset --hard HEAD` before relaunching.",
    )
    restart_parser.add_argument(
        "--stop-if-status-changes",
        action="store_true",
        help="Abort instead of waiting forever if the watched state leaves `active` before a new commit appears.",
    )
    restart_parser.add_argument(
        "--restart-sync-ref",
        help="After stopping the current autopilot, wait for this git ref and fast-forward merge it before relaunching.",
    )
    restart_parser.add_argument(
        "--restart-sync-timeout-seconds",
        type=int,
        default=0,
        help="How long to wait for the cutover ref to become a fast-forward successor; 0 waits forever.",
    )
    restart_parser.add_argument(
        "--restart-sync-refresh-seconds",
        type=int,
        default=5,
        help="Polling interval while waiting for the cutover ref.",
    )
    restart_parser.set_defaults(handler=run_restart_after_next_commit)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except KeyboardInterrupt:
        info("Interrupted.")
        return 130
    except AutopilotError as exc:
        print(f"[autopilot] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
