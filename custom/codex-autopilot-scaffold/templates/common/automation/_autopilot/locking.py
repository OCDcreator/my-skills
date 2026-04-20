from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class LockingSupport:
    lock_filename: str
    error_type: type[Exception]
    clean_string: Callable[..., str]
    parse_int: Callable[..., int]
    now_timestamp: Callable[..., str]
    info: Callable[..., None]
    pid_exists: Callable[..., bool]
    read_json: Callable[..., Any]
    write_json: Callable[..., None]


def read_lock(lock_path: Path, *, support: LockingSupport) -> dict[str, Any] | None:
    if not lock_path.exists():
        return None
    try:
        return support.read_json(lock_path)
    except json.JSONDecodeError:
        return {"invalid": True, "raw_path": str(lock_path)}


def acquire_lock(
    runtime_directory: Path,
    *,
    branch: str,
    head_sha: str,
    profile_name: str,
    force_lock: bool,
    support: LockingSupport,
) -> dict[str, Any]:
    lock_path = runtime_directory / support.lock_filename
    existing_lock = read_lock(lock_path, support=support)
    hostname = socket.gethostname()
    current_pid = os.getpid()

    if existing_lock:
        existing_host = support.clean_string(existing_lock.get("hostname"))
        existing_pid = support.parse_int(existing_lock.get("pid"), -1)

        if existing_host and existing_host != hostname:
            if not force_lock:
                raise support.error_type(
                    f"Lock file is owned by host '{existing_host}' (pid {existing_pid}). "
                    "Stop the other machine first or rerun with --force-lock."
                )
            support.info(f"Overriding lock owned by host '{existing_host}' (pid {existing_pid}).")
        elif existing_pid > 0 and existing_pid != current_pid and support.pid_exists(existing_pid):
            if not force_lock:
                raise support.error_type(
                    f"Another autopilot is already running on this host (pid {existing_pid}). "
                    "Stop it first or rerun with --force-lock."
                )
            support.info(f"Overriding running local lock owned by pid {existing_pid}.")
        elif existing_lock.get("invalid"):
            support.info(f"Replacing unreadable lock file at {lock_path}.")
        else:
            support.info("Replacing stale lock file.")

    lock_data = {
        "hostname": hostname,
        "pid": current_pid,
        "started_at": support.now_timestamp(),
        "branch": branch,
        "head": head_sha,
        "profile": profile_name,
    }
    support.write_json(lock_path, lock_data)
    return lock_data


def release_lock(runtime_directory: Path, lock_data: dict[str, Any] | None, *, support: LockingSupport) -> None:
    if not lock_data:
        return
    lock_path = runtime_directory / support.lock_filename
    if not lock_path.exists():
        return
    try:
        current_lock = support.read_json(lock_path)
    except json.JSONDecodeError:
        lock_path.unlink(missing_ok=True)
        return
    if (
        support.clean_string(current_lock.get("hostname")) == support.clean_string(lock_data.get("hostname"))
        and support.parse_int(current_lock.get("pid"), -1) == support.parse_int(lock_data.get("pid"), -1)
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
    support: LockingSupport,
) -> Any:
    lock_data = acquire_lock(
        runtime_directory,
        branch=branch,
        head_sha=head_sha,
        profile_name=profile_name,
        force_lock=force_lock,
        support=support,
    )
    try:
        yield lock_data
    finally:
        release_lock(runtime_directory, lock_data, support=support)
