from __future__ import annotations

import re
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class StatusViewSupport:
    repo_root: Path
    default_state_path: str
    lock_filename: str
    round_directory_re: re.Pattern[str]


@dataclass(frozen=True)
class HumanWatchEvent:
    category: str
    message: str
    signature: str


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_log_text(text: str | None, *, max_length: int = 180) -> str:
    if not text:
        return ""
    normalized = re.sub(r"\\+[nrt]", " ", text)
    normalized = normalized.replace('\\"', '"').replace("\\'", "'")
    normalized = re.sub(r"\\+$", "", normalized)
    return compact_text(normalized, max_length=max_length)


def resolve_repo_path(path_value: str, support: StatusViewSupport) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return (support.repo_root / path).resolve()


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


def parse_round_directory_number(path: Path | None, support: StatusViewSupport) -> int | None:
    if path is None:
        return None
    match = support.round_directory_re.fullmatch(path.name)
    if not match:
        return None
    return int(match.group(1))


def parse_progress_log_line(raw_line: str) -> tuple[str, str, str]:
    match = re.match(r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<channel>[^\]]+)\]\s*(?P<message>.*)$", raw_line.strip())
    if not match:
        return "", "", normalize_log_text(raw_line, max_length=220)
    return match.group("timestamp"), match.group("channel"), match.group("message").strip()


def extract_command_title(command_text: str) -> str:
    for pattern in (r"printf '([^']+)'", r'printf "([^"]+)"'):
        match = re.search(pattern, command_text)
        if match:
            title = normalize_log_text(match.group(1), max_length=140)
            if title:
                return title

    normalized_command = normalize_log_text(command_text, max_length=140)
    if "automation/run_opencode_implementation.py" in command_text:
        return "Starting OpenCode implementation pass"
    return normalized_command


def build_human_command_event(command_text: str) -> HumanWatchEvent:
    title = extract_command_title(command_text) or "Running command"
    lowered = f"{command_text}\n{title}".lower()

    if "automation/run_opencode_implementation.py" in lowered:
        return HumanWatchEvent("impl", "Starting OpenCode implementation pass", "impl:opencode")
    if (
        "opencode" in lowered
        and any(
            token in lowered
            for token in (
                "still running",
                "still chewing",
                "still waiting",
                "parking on the live opencode wrapper",
                "wrapper state",
                "wait loop",
                "without interrupting",
                "log is still advancing",
            )
        )
    ) or ("wrapper" in lowered and " ps " in f" {lowered} "):
        return HumanWatchEvent("wait", "Waiting on OpenCode implementation wrapper", "wait:opencode")
    if any(token in lowered for token in ("phase doc", "write phase", "write the phase", "phase-")) and any(
        token in lowered for token in ("write", "writing")
    ):
        return HumanWatchEvent("phase", title, f"phase:{title.lower()}")
    if any(
        token in lowered
        for token in ("vitest", "jest", "pytest", "cargo test", "npm test", "pnpm test", "yarn test", "targeted tests")
    ):
        return HumanWatchEvent("test", title, f"test:{title.lower()}")
    if any(
        token in lowered
        for token in (
            "npm run verify",
            " verify",
            "lint",
            "typecheck",
            "pyright",
            "tsc",
            "check:module-docs",
            "module-docs",
            "cargo check",
            "cargo clippy",
            "ruff",
        )
    ):
        return HumanWatchEvent("verify", title, f"verify:{title.lower()}")
    if any(
        token in lowered
        for token in ("build_id", "build id", "deploy", "test vault", "plugin:reload", "manifest.json", "styles.css")
    ):
        return HumanWatchEvent("deploy", title, f"deploy:{title.lower()}")
    if any(
        token in lowered
        for token in (
            "reading",
            "checking",
            "read ",
            "check ",
            " spec",
            "docs/",
            "module docs",
            "roadmap",
            "reference",
            "graph snapshot",
            "phase doc",
        )
    ):
        return HumanWatchEvent("docs", title, f"docs:{title.lower()}")
    return HumanWatchEvent("cmd", title, f"cmd:{title.lower()}")


def build_human_watch_event(raw_line: str) -> HumanWatchEvent | None:
    _, channel, message = parse_progress_log_line(raw_line)
    if not message:
        return None

    if channel == "runner":
        if message.startswith("Spawned codex exec subprocess pid="):
            pid_text = clean_string(message.split("pid=", 1)[1])
            return HumanWatchEvent("runner", f"Codex exec started (pid {pid_text})", f"runner:pid:{pid_text}")
        if "first execution event" in message:
            return HumanWatchEvent("runner", "Codex exec began producing events", "runner:exec-confirmed")
        return HumanWatchEvent("runner", normalize_log_text(message, max_length=140), f"runner:{message.lower()}")

    if message.startswith("Session started:"):
        return HumanWatchEvent("session", "Codex session started", "session:started")
    if message == "Turn started":
        return HumanWatchEvent("turn", "Turn started", "turn:started")
    if message.startswith("Turn completed"):
        return HumanWatchEvent("turn", normalize_log_text(message, max_length=140), f"turn:{message.lower()}")
    if message.startswith("Agent: "):
        return HumanWatchEvent("agent", normalize_log_text(message[7:], max_length=160), f"agent:{message.lower()}")
    if message.startswith("Running command: "):
        return build_human_command_event(message.split("Running command: ", 1)[1])
    if message.startswith("Command finished (exit "):
        match = re.match(r"^Command finished \(exit (?P<code>[^)]+)\):\s*(?P<command>.*)$", message)
        if not match:
            return HumanWatchEvent("fail", normalize_log_text(message, max_length=160), f"finish:{message.lower()}")
        exit_code = clean_string(match.group("code"))
        if exit_code in {"0", ""}:
            return None
        title = extract_command_title(match.group("command")) or "Command"
        return HumanWatchEvent("fail", f"{title} failed (exit {exit_code})", f"fail:{title.lower()}:{exit_code}")
    if message.startswith("item.started: todo_list"):
        return HumanWatchEvent("plan", "Updating todo list", "plan:todo")
    if message.startswith("item.started: file_change"):
        return HumanWatchEvent("edit", "Applying file changes", "edit:file-change")
    if message.startswith("item.completed: file_change"):
        return HumanWatchEvent("edit", "File changes recorded", "edit:file-change-complete")
    if message.startswith("Event: item.updated"):
        return None
    return HumanWatchEvent("note", normalize_log_text(message, max_length=160), f"note:{message.lower()}")


def render_human_watch_event(event: HumanWatchEvent) -> str:
    return f"{event.category}: {event.message}"


def get_watch_terminal_width(default_columns: int = 120) -> int:
    try:
        columns = shutil.get_terminal_size((default_columns, 24)).columns
    except OSError:
        columns = default_columns
    return max(40, int(columns))


def format_human_watch_render_lines(prefix: str, message: str) -> list[str]:
    indent = " " * (len(prefix) + 1)
    terminal_width = get_watch_terminal_width()
    content_width = max(20, terminal_width - len(prefix) - 1)
    logical_lines = message.splitlines() or [""]
    rendered_lines: list[str] = []

    for logical_line in logical_lines:
        wrapped_parts = textwrap.wrap(
            logical_line,
            width=content_width,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not wrapped_parts:
            wrapped_parts = [""]
        for index, wrapped_part in enumerate(wrapped_parts):
            if not rendered_lines and index == 0:
                rendered_lines.append(f"{prefix} {wrapped_part}".rstrip())
            else:
                rendered_lines.append(f"{indent}{wrapped_part}".rstrip())

    return rendered_lines or [prefix]


def build_watch_activity_summary(
    *,
    state: dict[str, Any] | None,
    progress_path: Path | None,
) -> str:
    if progress_path is None or not progress_path.exists():
        if state and clean_string(state.get("last_next_focus")):
            return f"queued focus: {compact_text(clean_string(state.get('last_next_focus')), max_length=120)}"
        return ""

    try:
        recent_lines = read_text(progress_path).splitlines()[-80:]
    except OSError:
        return ""

    recent_events = [event for event in (build_human_watch_event(line) for line in recent_lines) if event is not None]
    for event in reversed(recent_events):
        if event.category == "wait":
            return "waiting on OpenCode implementation wrapper"
        if event.category == "impl":
            return "running OpenCode implementation"
        if event.category == "phase":
            return "writing phase doc"
        if event.category == "docs":
            return "reading docs / spec"
        if event.category == "test":
            return "running targeted tests"
        if event.category == "verify":
            return "running verify / validation"
        if event.category == "deploy":
            return "deploying / checking BUILD_ID"
        if event.category == "edit":
            return "writing files"
        if event.category == "fail":
            return event.message
    if state and clean_string(state.get("last_next_focus")):
        return f"queued focus: {compact_text(clean_string(state.get('last_next_focus')), max_length=120)}"
    return ""


def build_watch_liveness_note(
    *,
    health_report: dict[str, Any] | None,
    activity_summary: str,
) -> str:
    if not health_report or clean_string(health_report.get("verdict")) != "healthy":
        return ""
    age_seconds = health_report.get("freshest_artifact_age_seconds")
    try:
        age_value = int(float(age_seconds))
    except (TypeError, ValueError):
        return ""
    if age_value < 90:
        return ""
    if "waiting on opencode implementation wrapper" in activity_summary.lower():
        return (
            f"quiet for {age_value}s, but the parent/runner pids and progress freshness still look healthy; "
            "this usually means a long-running external wrapper is still busy."
        )
    return f"quiet for {age_value}s, but the run still looks alive."


def resolve_watch_state_path(
    runtime_directory: Path,
    explicit_state_path: str | None,
    *,
    support: StatusViewSupport,
) -> Path:
    explicit_path = clean_string(explicit_state_path)
    if explicit_path:
        return resolve_repo_path(explicit_path, support)

    default_state_path = runtime_directory / Path(support.default_state_path).name
    if default_state_path.exists():
        return default_state_path

    candidate_paths = sorted(
        (
            path
            for path in runtime_directory.glob("*state*.json")
            if path.is_file() and path.name != support.lock_filename
        ),
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    if candidate_paths:
        return candidate_paths[-1]

    return default_state_path


def latest_round_directory(runtime_directory: Path, support: StatusViewSupport) -> Path | None:
    round_directories = sorted(
        (
            path
            for path in runtime_directory.iterdir()
            if path.is_dir() and support.round_directory_re.fullmatch(path.name)
        ),
        key=lambda path: parse_round_directory_number(path, support) or -1,
    )
    return round_directories[-1] if round_directories else None


def infer_watch_roadmap_path(state: dict[str, Any] | None, support: StatusViewSupport) -> Path | None:
    if state is None:
        return None

    phase_doc_path = clean_string(state.get("last_phase_doc"))
    if not phase_doc_path:
        return None

    normalized_phase_doc = phase_doc_path.replace("\\", "/")
    match = re.match(r"^(?P<prefix>.+?)phase-\d+\.md$", normalized_phase_doc)
    if not match:
        return None

    roadmap_path = resolve_repo_path(f"{match.group('prefix')}round-roadmap.md", support)
    if roadmap_path.exists():
        return roadmap_path
    return None


def read_watch_queue_progress(
    state: dict[str, Any] | None,
    *,
    support: StatusViewSupport,
) -> dict[str, Any] | None:
    roadmap_path = infer_watch_roadmap_path(state, support)
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
        clean_string(state.get("last_blocking_reason")),
        clean_string(state.get("last_plan_review_verdict")),
        clean_string(state.get("last_code_review_verdict")),
    )


def print_watch_snapshot(
    *,
    state: dict[str, Any] | None,
    state_path: Path,
    progress_path: Path | None,
    health_report: dict[str, Any] | None,
    support: StatusViewSupport,
) -> None:
    state_round = clean_string(state.get("current_round")) if state else ""
    watched_round_number = parse_round_directory_number(progress_path.parent, support) if progress_path else None
    phase_number = clean_string(state.get("next_phase_number")) if state else ""
    lane_id = clean_string(state.get("active_lane_id")) if state else ""
    status_value = clean_string(state.get("status")) if state else ""
    failures_value = clean_string(state.get("consecutive_failures")) if state else ""
    queue_progress = read_watch_queue_progress(state, support=support)
    activity_summary = build_watch_activity_summary(state=state, progress_path=progress_path)
    liveness_note = build_watch_liveness_note(health_report=health_report, activity_summary=activity_summary)
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
    if health_report and clean_string(health_report.get("verdict")):
        heading_parts.append(f"health={health_report.get('verdict')}")
        runner_state = clean_string(health_report.get("runner_status"))
        if runner_state:
            heading_parts.append(f"runner={runner_state}")
        if health_report.get("runner_exec_confirmed") is not None:
            heading_parts.append(
                "exec=confirmed" if bool(health_report.get("runner_exec_confirmed")) else "exec=waiting"
            )
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
        if activity_summary:
            print(f"[watch] activity: {activity_summary}")
        if state.get("last_commit_sha"):
            print(f"[watch] last commit: {state.get('last_commit_sha')}")
        if state.get("last_plan_review_verdict"):
            print(f"[watch] plan review: {state.get('last_plan_review_verdict')}")
        if state.get("last_code_review_verdict"):
            print(f"[watch] code review: {state.get('last_code_review_verdict')}")
        if state.get("last_blocking_reason"):
            print(f"[watch] blocker: {compact_text(clean_string(state.get('last_blocking_reason')), max_length=220)}")
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
    if health_report:
        freshest_path = clean_string(health_report.get("freshest_artifact_path"))
        freshest_age = health_report.get("freshest_artifact_age_seconds")
        if health_report.get("autopilot_pid") is not None:
            print(
                "[watch] autopilot pid: "
                f"{health_report.get('autopilot_pid')} alive={health_report.get('autopilot_pid_alive')}"
            )
        if health_report.get("runner_pid") is not None:
            print(
                "[watch] runner pid: "
                f"{health_report.get('runner_pid')} alive={health_report.get('runner_pid_alive')} "
                f"exec_confirmed={health_report.get('runner_exec_confirmed')}"
            )
        if freshest_path and freshest_age is not None:
            print(f"[watch] health: {health_report.get('verdict')} via {freshest_path} ({int(freshest_age)}s old)")
        else:
            print(f"[watch] health: {health_report.get('verdict')} ({health_report.get('reason')})")
        if liveness_note:
            print(f"[watch] note: {liveness_note}")
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


def watched_round_directory(runtime_directory: Path, state: dict[str, Any] | None, support: StatusViewSupport) -> Path | None:
    expected_round_number = expected_round_number_for_state(state)
    if expected_round_number is not None:
        return runtime_directory / f"round-{expected_round_number:03d}"
    return latest_round_directory(runtime_directory, support)


def build_watch_detail_prefix(
    *,
    state: dict[str, Any] | None,
    progress_path: Path | None,
    prefix_format: str = "long",
    support: StatusViewSupport,
) -> str:
    watched_round_number = parse_round_directory_number(progress_path.parent, support) if progress_path else None
    if watched_round_number is None:
        watched_round_number = expected_round_number_for_state(state)

    round_value = format_watch_detail_counter(watched_round_number, width=3)
    phase_value = format_watch_detail_counter(state.get("next_phase_number") if state else None, width=3)
    failure_value = format_watch_detail_counter(
        state.get("consecutive_failures") if state else None,
        width=1,
    )
    lane_token = clean_string(state.get("active_lane_id")) if state else ""
    queue_progress = read_watch_queue_progress(state, support=support)
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
    view: str = "human",
    support: StatusViewSupport,
) -> None:
    if not lines:
        return
    prefix = build_watch_detail_prefix(
        state=state,
        progress_path=progress_path,
        prefix_format=prefix_format,
        support=support,
    )
    view_mode = clean_string(view).lower() or "human"
    if view_mode == "raw":
        for line in lines:
            if line:
                print(f"{prefix} {line}")
            else:
                print(prefix)
        return

    last_rendered_signature = ""
    for line in lines:
        event = build_human_watch_event(line)
        if event is None:
            continue
        if event.signature == last_rendered_signature:
            continue
        for rendered_line in format_human_watch_render_lines(prefix, render_human_watch_event(event)):
            print(rendered_line)
        last_rendered_signature = event.signature


def print_state_summary(
    state: dict[str, Any],
    *,
    runtime_directory: Path | None = None,
    health_report: dict[str, Any] | None = None,
    support: StatusViewSupport,
    read_lock: Callable[[Path], dict[str, Any] | None],
) -> None:
    queue_progress = read_watch_queue_progress(state, support=support)
    lane_id = clean_string(state.get("active_lane_id")) or "legacy"
    progress_path = None
    if runtime_directory is not None:
        round_directory = watched_round_directory(runtime_directory, state, support)
        progress_path = round_directory / "progress.log" if round_directory is not None else None
    activity_summary = build_watch_activity_summary(state=state, progress_path=progress_path)
    liveness_note = build_watch_liveness_note(health_report=health_report, activity_summary=activity_summary)
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
    if activity_summary:
        print(f"[status] activity: {activity_summary}")
    if state.get("last_commit_sha"):
        print(f"[status] last commit: {state.get('last_commit_sha')}")
    if state.get("last_plan_review_verdict"):
        print(f"[status] plan review: {state.get('last_plan_review_verdict')}")
    if state.get("last_code_review_verdict"):
        print(f"[status] code review: {state.get('last_code_review_verdict')}")
    if state.get("last_blocking_reason"):
        print(f"[status] blocker: {compact_text(clean_string(state.get('last_blocking_reason')), max_length=220)}")
    if health_report:
        print(f"[status] health: {health_report.get('verdict')} ({health_report.get('reason')})")
        if liveness_note:
            print(f"[status] note: {liveness_note}")
        if health_report.get("autopilot_pid") is not None:
            print(
                "[status] autopilot pid: "
                f"{health_report.get('autopilot_pid')} alive={health_report.get('autopilot_pid_alive')}"
            )
        if health_report.get("runner_pid") is not None:
            print(
                "[status] runner pid: "
                f"{health_report.get('runner_pid')} alive={health_report.get('runner_pid_alive')} "
                f"exec_confirmed={health_report.get('runner_exec_confirmed')}"
            )
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
        lock_path = runtime_directory / support.lock_filename
        lock_data = read_lock(lock_path)
        if lock_data:
            print(
                "[status] lock: "
                f"host={lock_data.get('hostname')} pid={lock_data.get('pid')} "
                f"profile={lock_data.get('profile')} started_at={lock_data.get('started_at')}"
            )
        else:
            print("[status] lock: none")
