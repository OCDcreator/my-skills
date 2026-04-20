from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StatusViewSupport:
    repo_root: Path
    default_state_path: str
    lock_filename: str
    round_directory_re: re.Pattern[str]


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
    )


def print_watch_snapshot(
    *,
    state: dict[str, Any] | None,
    state_path: Path,
    progress_path: Path | None,
    support: StatusViewSupport,
) -> None:
    state_round = clean_string(state.get("current_round")) if state else ""
    watched_round_number = parse_round_directory_number(progress_path.parent, support) if progress_path else None
    phase_number = clean_string(state.get("next_phase_number")) if state else ""
    lane_id = clean_string(state.get("active_lane_id")) if state else ""
    status_value = clean_string(state.get("status")) if state else ""
    failures_value = clean_string(state.get("consecutive_failures")) if state else ""
    queue_progress = read_watch_queue_progress(state, support=support)
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
    for line in lines:
        if line:
            print(f"{prefix} {line}")
        else:
            print(prefix)
