from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class BootstrapRuntimeSupport:
    error_type: type[Exception]
    clean_string: Callable[..., str]
    info: Callable[..., None]
    read_json: Callable[..., Any]
    resolve_repo_path: Callable[..., Path]
    run_start: Callable[..., int]
    spawn_background_autopilot: Callable[..., int]


def build_start_command_args(args: argparse.Namespace, *, support: BootstrapRuntimeSupport) -> list[str]:
    start_args = [
        sys.executable,
        str(support.resolve_repo_path("automation/autopilot.py")),
        "start",
        "--profile",
        support.clean_string(getattr(args, "profile", "")) or "default",
        "--config-path",
        support.clean_string(getattr(args, "config_path", "")) or "automation/autopilot-config.json",
        "--state-path",
        support.clean_string(getattr(args, "state_path", "")) or "automation/runtime/autopilot-state.json",
    ]
    profile_path = support.clean_string(getattr(args, "profile_path", ""))
    if profile_path:
        start_args.extend(["--profile-path", profile_path])
    return start_args


def run_bootstrap_and_daemonize(args: argparse.Namespace, *, support: BootstrapRuntimeSupport) -> int:
    bootstrap_args = argparse.Namespace(**vars(args))
    bootstrap_args.single_round = True
    bootstrap_args.max_rounds_this_run = 0
    bootstrap_args.dry_run = False

    support.info("Running one foreground bootstrap round before background continuation.")
    result = support.run_start(bootstrap_args)
    if result != 0:
        return result

    state_path = support.resolve_repo_path(args.state_path)
    if not state_path.exists():
        raise support.error_type(f"Bootstrap finished but state file is missing: {state_path}")

    state = support.read_json(state_path)
    status_value = support.clean_string(state.get("status"))
    last_commit_sha = support.clean_string(state.get("last_commit_sha"))
    if not last_commit_sha:
        raise support.error_type(
            "Bootstrap round finished without last_commit_sha; use foreground debugging until the first successful commit exists."
        )

    if status_value != "active":
        support.info(
            f"Bootstrap round ended with state '{status_value or 'unknown'}'; no background continuation was needed."
        )
        return 0

    daemon_output_path = support.resolve_repo_path(args.daemon_output_path)
    daemon_pid_path = support.resolve_repo_path(args.daemon_pid_path)
    new_pid = support.spawn_background_autopilot(
        build_start_command_args(args, support=support),
        output_path=daemon_output_path,
        pid_path=daemon_pid_path,
    )
    support.info(
        "Bootstrap succeeded; background continuation started with "
        f"pid {new_pid}, output {daemon_output_path}, pid file {daemon_pid_path}."
    )
    return 0
