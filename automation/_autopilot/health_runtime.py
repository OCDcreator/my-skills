from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from _autopilot.status_views import (
    StatusViewSupport,
    clean_string,
    resolve_watch_state_path,
    watched_round_directory,
)


@dataclass(frozen=True)
class HealthRuntimeSupport:
    resolve_repo_path: Callable[..., Path]
    read_json: Callable[..., Any]
    read_lock: Callable[..., dict[str, Any] | None]
    pid_exists: Callable[..., bool]


def parse_pid(value: Any) -> int:
    try:
        return int(clean_string(value))
    except (TypeError, ValueError):
        return -1


def latest_artifact(paths: list[Path]) -> tuple[Path | None, float | None]:
    now = time.time()
    newest_path: Path | None = None
    newest_mtime: float | None = None
    for path in paths:
        if not path.exists():
            continue
        stat = path.stat()
        if newest_mtime is None or stat.st_mtime > newest_mtime:
            newest_path = path
            newest_mtime = stat.st_mtime
    if newest_path is None or newest_mtime is None:
        return None, None
    return newest_path, max(0.0, now - newest_mtime)


def build_health_report(
    *,
    runtime_directory: Path,
    explicit_state_path: str | None,
    stale_seconds: int,
    support: HealthRuntimeSupport,
    status_view_support: StatusViewSupport,
) -> dict[str, Any]:
    state_path = resolve_watch_state_path(runtime_directory, explicit_state_path, support=status_view_support)
    report: dict[str, Any] = {
        "runtime_directory": str(runtime_directory),
        "state_path": str(state_path),
        "verdict": "missing-state",
        "reason": "state file not found",
        "state_status": "",
        "autopilot_pid": None,
        "autopilot_pid_alive": False,
        "runner_pid": None,
        "runner_pid_alive": False,
        "runner_status": "",
        "runner_exec_confirmed": False,
        "runner_exec_confirmed_at": "",
        "lock_path": str(runtime_directory / status_view_support.lock_filename),
        "progress_path": None,
        "progress_age_seconds": None,
        "events_path": None,
        "assistant_output_path": None,
        "runner_status_path": None,
        "freshest_artifact_path": None,
        "freshest_artifact_age_seconds": None,
        "last_commit_sha": "",
        "active_lane_id": "",
        "current_round": "",
        "last_phase_doc": "",
        "last_blocking_reason": "",
        "last_plan_review_verdict": "",
        "last_code_review_verdict": "",
    }
    if not state_path.exists():
        return report

    state = support.read_json(state_path)
    report["state_status"] = clean_string(state.get("status"))
    report["last_commit_sha"] = clean_string(state.get("last_commit_sha"))
    report["active_lane_id"] = clean_string(state.get("active_lane_id"))
    report["current_round"] = clean_string(state.get("current_round"))
    report["last_phase_doc"] = clean_string(state.get("last_phase_doc"))
    report["last_blocking_reason"] = clean_string(state.get("last_blocking_reason"))
    report["last_plan_review_verdict"] = clean_string(state.get("last_plan_review_verdict"))
    report["last_code_review_verdict"] = clean_string(state.get("last_code_review_verdict"))

    round_directory = watched_round_directory(runtime_directory, state, status_view_support)
    progress_path = round_directory / "progress.log" if round_directory is not None else None
    events_path = round_directory / "events.jsonl" if round_directory is not None else None
    assistant_output_path = round_directory / "assistant-output.json" if round_directory is not None else None
    runner_status_path = round_directory / "runner-status.json" if round_directory is not None else None
    report["progress_path"] = str(progress_path) if progress_path is not None else None
    report["events_path"] = str(events_path) if events_path is not None else None
    report["assistant_output_path"] = str(assistant_output_path) if assistant_output_path is not None else None
    report["runner_status_path"] = str(runner_status_path) if runner_status_path is not None else None
    progress_mtime_path, progress_age_seconds = latest_artifact([progress_path] if progress_path is not None else [])
    report["progress_age_seconds"] = progress_age_seconds if progress_mtime_path is not None else None

    lock_path = runtime_directory / status_view_support.lock_filename
    lock_data = support.read_lock(lock_path)
    autopilot_pid = parse_pid(lock_data.get("pid") if lock_data else None)
    autopilot_pid_alive = autopilot_pid > 0 and support.pid_exists(autopilot_pid)
    report["autopilot_pid"] = autopilot_pid if autopilot_pid > 0 else None
    report["autopilot_pid_alive"] = autopilot_pid_alive

    runner_status: dict[str, Any] | None = None
    if runner_status_path is not None and runner_status_path.exists():
        raw_runner_status = support.read_json(runner_status_path)
        if isinstance(raw_runner_status, dict):
            runner_status = raw_runner_status
    runner_pid = parse_pid(runner_status.get("pid") if runner_status else None)
    runner_pid_alive = runner_pid > 0 and support.pid_exists(runner_pid)
    runner_exec_confirmed_at = clean_string(runner_status.get("exec_confirmed_at") if runner_status else None)
    runner_exec_confirmed = bool(runner_exec_confirmed_at)
    report["runner_pid"] = runner_pid if runner_pid > 0 else None
    report["runner_pid_alive"] = runner_pid_alive
    report["runner_status"] = clean_string(runner_status.get("status") if runner_status else None)
    report["runner_exec_confirmed"] = runner_exec_confirmed
    report["runner_exec_confirmed_at"] = runner_exec_confirmed_at

    freshest_path, freshest_age_seconds = latest_artifact(
        [path for path in [progress_path, events_path, assistant_output_path, runner_status_path] if path is not None]
    )
    report["freshest_artifact_path"] = str(freshest_path) if freshest_path is not None else None
    report["freshest_artifact_age_seconds"] = freshest_age_seconds

    status_value = clean_string(state.get("status"))
    if status_value == "active":
        if not lock_data or autopilot_pid <= 0 or not autopilot_pid_alive:
            report["verdict"] = "dead-runner"
            report["reason"] = "state says active but no live autopilot pid is attached to the runtime lock"
            return report
        if runner_status is None:
            report["verdict"] = "starting"
            report["reason"] = "active run has a live autopilot pid but no runner-status.json yet"
            return report
        if runner_pid <= 0 or not runner_pid_alive:
            report["verdict"] = "dead-runner"
            report["reason"] = "state says active but the codex exec child pid is missing or already exited"
            return report
        if not runner_exec_confirmed:
            report["verdict"] = "starting"
            report["reason"] = "codex exec child exists but has not emitted its first execution event yet"
            return report
        if report["progress_age_seconds"] is None:
            report["verdict"] = "stalled"
            report["reason"] = "active run has live pids and confirmed execution, but progress.log has not started updating"
            return report
        if float(report["progress_age_seconds"]) > max(1, stale_seconds):
            report["verdict"] = "stalled"
            report["reason"] = (
                f"active run has live pids but progress.log has not updated in the last {int(float(report['progress_age_seconds']))}s"
            )
            return report
        report["verdict"] = "healthy"
        report["reason"] = (
            "active run has a live autopilot pid, a live codex exec child pid, "
            f"confirmed execution, and a fresh progress.log ({int(float(report['progress_age_seconds']))}s old)"
        )
        return report

    if autopilot_pid_alive or runner_pid_alive:
        report["verdict"] = "inconsistent"
        report["reason"] = (
            f"state is '{status_value or 'unknown'}' but a related process is still alive "
            f"(autopilot={report['autopilot_pid']} runner={report['runner_pid']})"
        )
        return report

    report["verdict"] = "terminal"
    report["reason"] = f"state is '{status_value or 'unknown'}' and no live autopilot or runner pid is attached"
    return report


def print_health_report(report: dict[str, Any]) -> None:
    print(
        "[health] "
        f"verdict={report['verdict']} state={report['state_status'] or 'missing'} "
        f"lane={report['active_lane_id'] or 'n/a'} round={report['current_round'] or 'n/a'}"
    )
    print(f"[health] reason: {report['reason']}")
    print(f"[health] state file: {report['state_path']}")
    if report.get("lock_path"):
        print(f"[health] lock file: {report['lock_path']}")
    if report.get("autopilot_pid") is not None:
        print(f"[health] autopilot pid: {report['autopilot_pid']} alive={report['autopilot_pid_alive']}")
    else:
        print("[health] autopilot pid: none")
    if report.get("runner_pid") is not None:
        print(
            "[health] runner pid: "
            f"{report['runner_pid']} alive={report['runner_pid_alive']} "
            f"exec_confirmed={report['runner_exec_confirmed']}"
        )
    else:
        print("[health] runner pid: none")
    if report.get("freshest_artifact_path"):
        print(
            "[health] freshest artifact: "
            f"{report['freshest_artifact_path']} ({int(report['freshest_artifact_age_seconds'] or 0)}s old)"
        )
    if report.get("runner_status_path"):
        print(f"[health] runner status: {report['runner_status_path']}")
    if report.get("progress_path"):
        print(f"[health] progress log: {report['progress_path']}")
    if report.get("events_path"):
        print(f"[health] events log: {report['events_path']}")
    if report.get("assistant_output_path"):
        print(f"[health] assistant output: {report['assistant_output_path']}")
    if report.get("last_commit_sha"):
        print(f"[health] last commit: {report['last_commit_sha']}")
    if report.get("last_phase_doc"):
        print(f"[health] phase doc: {report['last_phase_doc']}")
    if report.get("last_plan_review_verdict"):
        print(f"[health] plan review: {report['last_plan_review_verdict']}")
    if report.get("last_code_review_verdict"):
        print(f"[health] code review: {report['last_code_review_verdict']}")
    if report.get("last_blocking_reason"):
        print(f"[health] blocker: {report['last_blocking_reason']}")


def run_health(args, *, support: HealthRuntimeSupport, status_view_support: StatusViewSupport) -> int:
    runtime_directory = support.resolve_repo_path(args.runtime_path)
    report = build_health_report(
        runtime_directory=runtime_directory,
        explicit_state_path=getattr(args, "state_path", ""),
        stale_seconds=max(1, int(getattr(args, "stale_seconds", 600))),
        support=support,
        status_view_support=status_view_support,
    )
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_health_report(report)
    return 0 if report["verdict"] in {"healthy", "starting", "terminal"} else 1
