#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from typing import TYPE_CHECKING, Any, cast

sys.dont_write_bytecode = True

from _autopilot.cli_parser import build_parser as build_parser_command
from _autopilot.bootstrap_runtime import run_bootstrap_and_daemonize as run_bootstrap_and_daemonize_command
from _autopilot.controller_builders import (
    build_bootstrap_runtime_support,
    build_cli_parser_support as build_cli_parser_support_command,
    build_doctor_support,
    build_health_runtime_support,
    build_lane_support,
    build_locking_support,
    build_process_control_support,
    build_round_flow_support,
    build_runner_support,
    build_start_runtime_support,
    build_state_runtime_support,
    build_status_view_support,
    build_validation_support,
    build_watch_runtime_support,
)
from _autopilot.controller_runtime import (
    AutopilotError,
    CommandResult,
    DEFAULT_CONFIG_PATH,
    DEFAULT_PROFILE_NAME,
    DEFAULT_RUNTIME_PATH,
    DEFAULT_STATE_PATH,
    LOCK_FILENAME,
    REPO_ROOT,
    append_controller_requirements,
    append_history_entry,
    append_jsonl,
    build_history_entry,
    clean_string,
    compact_text,
    ensure_console_streams,
    ensure_path_within_repo,
    get_codex_event_summary,
    get_codex_item_summary,
    get_current_branch,
    get_head_sha,
    infer_roadmap_path_text_from_phase_doc,
    infer_round_roadmap_path_from_phase_doc,
    info,
    is_working_tree_dirty,
    load_config,
    load_profile,
    normalize_path_text,
    now_timestamp,
    parse_int,
    pid_exists,
    preserve_worktree_before_reset,
    progress,
    read_json,
    read_text,
    read_vulture_snapshot,
    refresh_vulture_metrics,
    render_template,
    reset_worktree_to_head,
    resolve_repo_path,
    resolve_shell_command_args,
    run_command,
    run_git,
    run_git_no_capture,
    run_shell_command,
    save_state,
    test_branch_allowed,
    write_json,
)
from _autopilot.doctor import run_doctor as run_doctor_command
from _autopilot.health_runtime import build_health_report, run_health as run_health_command
from _autopilot.locking import (
    acquire_lock as acquire_lock_command,
    autopilot_lock as autopilot_lock_command,
    read_lock as read_lock_command,
    release_lock as release_lock_command,
)
from _autopilot.process_control import run_restart_after_next_commit as run_restart_after_next_commit_command
from _autopilot.start_runtime import run_start as run_start_command
from _autopilot.state_runtime import (
    new_state as new_state_command,
    resume_state_if_threshold_allows as resume_state_if_threshold_allows_command,
)
from _autopilot.status_views import print_state_summary
from _autopilot.watch_runtime import run_watch as run_watch_command


if TYPE_CHECKING:
    SCAFFOLD_NAME_JSON = ""
    SCAFFOLD_VERSION_JSON = ""


ensure_console_streams()

AUTOPILOT_SCAFFOLD_NAME = cast(str, "codex-autopilot-scaffold")
AUTOPILOT_SCAFFOLD_VERSION = cast(str, "1.1.9")


def new_state(config: dict[str, Any]) -> dict[str, Any]:
    return new_state_command(config, support=build_state_runtime_support())


def resume_state_if_threshold_allows(
    state: dict[str, Any],
    config: dict[str, Any],
    state_path,
) -> dict[str, Any]:
    return resume_state_if_threshold_allows_command(
        state,
        config,
        state_path,
        support=build_state_runtime_support(),
    )


def read_lock(lock_path):
    return read_lock_command(lock_path, support=build_locking_support())


def acquire_lock(
    runtime_directory,
    *,
    branch: str,
    head_sha: str,
    profile_name: str,
    force_lock: bool,
):
    return acquire_lock_command(
        runtime_directory,
        branch=branch,
        head_sha=head_sha,
        profile_name=profile_name,
        force_lock=force_lock,
        support=build_locking_support(),
    )


def release_lock(runtime_directory, lock_data):
    return release_lock_command(runtime_directory, lock_data, support=build_locking_support())


def autopilot_lock(
    runtime_directory,
    *,
    branch: str,
    head_sha: str,
    profile_name: str,
    force_lock: bool,
):
    return autopilot_lock_command(
        runtime_directory,
        branch=branch,
        head_sha=head_sha,
        profile_name=profile_name,
        force_lock=force_lock,
        support=build_locking_support(),
    )


def run_start(args: argparse.Namespace) -> int:
    return run_start_command(
        args,
        support=build_start_runtime_support(),
        runner_support=build_runner_support(),
        validation_support=build_validation_support(),
        round_flow_support=build_round_flow_support(),
    )


def run_status(args: argparse.Namespace) -> int:
    state_path = resolve_repo_path(args.state_path)
    if not state_path.exists():
        print(f"[status] state file not found: {state_path}")
        return 1
    state = read_json(state_path)
    print_state_summary(
        state,
        runtime_directory=state_path.parent,
        health_report=build_health_report(
            runtime_directory=state_path.parent,
            explicit_state_path=args.state_path,
            stale_seconds=600,
            support=build_health_runtime_support(),
            status_view_support=build_status_view_support(),
        ),
        support=build_status_view_support(),
        read_lock=read_lock,
    )
    return 0


def run_health(args: argparse.Namespace) -> int:
    return run_health_command(args, support=build_health_runtime_support(), status_view_support=build_status_view_support())


def run_watch(args: argparse.Namespace) -> int:
    return run_watch_command(args, support=build_watch_runtime_support(), status_view_support=build_status_view_support())


def run_restart_after_next_commit(args: argparse.Namespace) -> int:
    return run_restart_after_next_commit_command(args, support=build_process_control_support())


def run_bootstrap_and_daemonize(args: argparse.Namespace) -> int:
    return run_bootstrap_and_daemonize_command(args, support=build_bootstrap_runtime_support(run_start=run_start))


def run_doctor(args: argparse.Namespace) -> int:
    return run_doctor_command(args, support=build_doctor_support())


def run_version(args: argparse.Namespace) -> int:
    print(f"{AUTOPILOT_SCAFFOLD_NAME} {AUTOPILOT_SCAFFOLD_VERSION}")
    return 0


def build_cli_parser_support():
    return build_cli_parser_support_command(
        run_start=run_start,
        run_watch=run_watch,
        run_status=run_status,
        run_health=run_health,
        run_doctor=run_doctor,
        run_version=run_version,
        run_restart_after_next_commit=run_restart_after_next_commit,
        run_bootstrap_and_daemonize=run_bootstrap_and_daemonize,
    )


def build_parser() -> argparse.ArgumentParser:
    return build_parser_command(support=build_cli_parser_support())


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
