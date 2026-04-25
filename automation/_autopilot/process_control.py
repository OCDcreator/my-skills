from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ProcessControlSupport:
    repo_root: Path
    default_profile_name: str
    default_config_path: str
    default_state_path: str
    lock_filename: str
    error_type: type[Exception]
    info: Callable[..., None]
    pid_exists: Callable[..., bool]
    parse_int: Callable[..., int]
    clean_string: Callable[..., str]
    resolve_repo_path: Callable[..., Path]
    read_json: Callable[..., Any]
    read_lock: Callable[..., dict[str, Any] | None]
    get_head_sha: Callable[..., str]
    run_git: Callable[..., Any]
    run_git_no_capture: Callable[..., int]
    windows_hidden_process_kwargs: Callable[..., dict[str, Any]]


def stop_process(pid: int, *, graceful_timeout_seconds: int = 30, support: ProcessControlSupport) -> None:
    if pid <= 0:
        return
    if not support.pid_exists(pid):
        support.info(f"Process {pid} already exited.")
        return

    support.info(f"Stopping process {pid}.")
    if os.name == "nt":
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + graceful_timeout_seconds
        while time.time() < deadline:
            if not support.pid_exists(pid):
                support.info(f"Process {pid} stopped cleanly.")
                return
            time.sleep(1)

        taskkill_result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **support.windows_hidden_process_kwargs(),
        )
        if taskkill_result.returncode != 0 and support.pid_exists(pid):
            combined = "\n".join(part for part in (taskkill_result.stdout, taskkill_result.stderr) if part.strip())
            raise support.error_type(f"Failed to force-stop pid {pid}: {combined}")
    else:
        os.kill(pid, signal.SIGTERM)
        deadline = time.time() + graceful_timeout_seconds
        while time.time() < deadline:
            if not support.pid_exists(pid):
                support.info(f"Process {pid} stopped cleanly.")
                return
            time.sleep(1)

        os.kill(pid, signal.SIGKILL)
        deadline = time.time() + 10
        while time.time() < deadline:
            if not support.pid_exists(pid):
                support.info(f"Process {pid} force-stopped.")
                return
            time.sleep(1)

    if support.pid_exists(pid):
        raise support.error_type(f"Failed to stop pid {pid}.")


def remove_stale_lock(
    runtime_directory: Path,
    *,
    support: ProcessControlSupport,
    expected_pid: int | None = None,
) -> None:
    lock_path = runtime_directory / support.lock_filename
    lock_data = support.read_lock(lock_path)
    if not lock_data:
        return

    lock_pid = support.parse_int(lock_data.get("pid"), -1)

    if expected_pid is not None and lock_pid not in (-1, expected_pid):
        return

    if lock_pid > 0 and support.pid_exists(lock_pid):
        raise support.error_type(f"Refusing to remove active lock owned by pid {lock_pid}.")

    lock_path.unlink(missing_ok=True)
    support.info(f"Removed stale lock file at {lock_path}.")


def build_restart_start_args(args: argparse.Namespace, *, support: ProcessControlSupport) -> list[str]:
    restart_profile = (
        support.clean_string(args.restart_profile)
        or support.clean_string(args.profile)
        or support.default_profile_name
    )
    restart_config_path = (
        support.clean_string(args.restart_config_path)
        or support.clean_string(args.config_path)
        or support.default_config_path
    )
    restart_state_path = (
        support.clean_string(args.restart_state_path)
        or support.clean_string(args.state_path)
        or support.default_state_path
    )
    restart_profile_path = support.clean_string(args.restart_profile_path) or support.clean_string(args.profile_path)

    start_args = [
        sys.executable,
        str(support.resolve_repo_path("automation/autopilot.py")),
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


def git_ref_exists(ref_name: str, *, support: ProcessControlSupport) -> bool:
    return support.run_git(["rev-parse", "--verify", f"{ref_name}^{{commit}}"], check=False).returncode == 0


def git_is_ancestor(ancestor_ref: str, descendant_ref: str, *, support: ProcessControlSupport) -> bool:
    return support.run_git(["merge-base", "--is-ancestor", ancestor_ref, descendant_ref], check=False).returncode == 0


def sync_repo_to_restart_ref(
    *,
    restart_sync_ref: str,
    stopped_head: str,
    timeout_seconds: int,
    refresh_seconds: int,
    support: ProcessControlSupport,
) -> None:
    started_monotonic = time.monotonic()
    while True:
        support.run_git_no_capture(["fetch", "--all", "--prune"], check=True)

        if git_ref_exists(restart_sync_ref, support=support):
            if git_is_ancestor(stopped_head, restart_sync_ref, support=support):
                support.info(f"Fast-forwarding repo to cutover ref {restart_sync_ref}.")
                support.run_git_no_capture(["merge", "--ff-only", restart_sync_ref], check=True)
                return
            support.info(f"Ref {restart_sync_ref} exists but is not a fast-forward successor of stopped HEAD {stopped_head}.")
        else:
            support.info(f"Waiting for cutover ref {restart_sync_ref} to appear.")

        if timeout_seconds > 0 and time.monotonic() - started_monotonic >= timeout_seconds:
            raise support.error_type(
                f"Timed out waiting for cutover ref '{restart_sync_ref}' to become a fast-forward successor of {stopped_head}."
            )

        time.sleep(refresh_seconds)


def spawn_background_autopilot(
    command_args: list[str],
    *,
    output_path: Path,
    pid_path: Path | None = None,
    support: ProcessControlSupport,
) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_handle = output_path.open("ab")
    popen_kwargs: dict[str, Any] = {
        "args": command_args,
        "cwd": str(support.repo_root),
        "stdin": subprocess.DEVNULL,
        "stdout": output_handle,
        "stderr": subprocess.STDOUT,
    }

    if os.name == "nt":
        popen_kwargs.update(
            support.windows_hidden_process_kwargs(
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


def run_restart_after_next_commit(args: argparse.Namespace, *, support: ProcessControlSupport) -> int:
    state_path = support.resolve_repo_path(args.state_path)
    runtime_directory = state_path.parent
    if not state_path.exists():
        raise support.error_type(f"State file not found: {state_path}")

    state = support.read_json(state_path)
    target_commit_sha = support.clean_string(state.get("last_commit_sha"))
    if not target_commit_sha:
        raise support.error_type("State file does not have last_commit_sha; nothing to watch yet.")

    lock_path = runtime_directory / support.lock_filename
    lock_data = support.read_lock(lock_path)
    current_pid = support.parse_int(lock_data.get("pid") if lock_data else None, -1)

    support.info(
        "Watching for the next successful commit after "
        f"{target_commit_sha} (current pid {current_pid if current_pid > 0 else 'unknown'})."
    )

    refresh_seconds = max(1, int(args.refresh_seconds))
    while True:
        time.sleep(refresh_seconds)
        state = support.read_json(state_path)
        latest_commit_sha = support.clean_string(state.get("last_commit_sha"))
        current_round = state.get("current_round")
        current_status = support.clean_string(state.get("status"))

        if latest_commit_sha and latest_commit_sha != target_commit_sha:
            support.info(
                "Detected new commit "
                f"{latest_commit_sha} at round {current_round} with status {current_status or '<empty>'}."
            )
            break

        if current_status and current_status != "active" and args.stop_if_status_changes:
            raise support.error_type(f"State changed to '{current_status}' before a new commit was detected.")

    if current_pid > 0:
        stop_process(current_pid, graceful_timeout_seconds=max(1, int(args.stop_timeout_seconds)), support=support)
    else:
        support.info("No active pid was captured from the lock file; skipping process stop step.")

    remove_stale_lock(runtime_directory, expected_pid=current_pid if current_pid > 0 else None, support=support)

    stopped_head = support.get_head_sha()

    if args.hard_reset:
        support.run_git_no_capture(["reset", "--hard", "HEAD"], check=True)

    restart_sync_ref = support.clean_string(args.restart_sync_ref)
    if restart_sync_ref:
        sync_repo_to_restart_ref(
            restart_sync_ref=restart_sync_ref,
            stopped_head=stopped_head,
            timeout_seconds=max(0, int(args.restart_sync_timeout_seconds)),
            refresh_seconds=max(1, int(args.restart_sync_refresh_seconds)),
            support=support,
        )

    restart_args = build_restart_start_args(args, support=support)
    restart_output_path = support.resolve_repo_path(args.restart_output_path)
    restart_pid_path = (
        support.resolve_repo_path(args.restart_pid_path) if support.clean_string(args.restart_pid_path) else None
    )
    new_pid = spawn_background_autopilot(
        restart_args,
        output_path=restart_output_path,
        pid_path=restart_pid_path,
        support=support,
    )
    support.info(f"Started replacement autopilot pid {new_pid}.")
    return 0
