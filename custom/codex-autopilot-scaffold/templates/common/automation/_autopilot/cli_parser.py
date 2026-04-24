from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CliParserSupport:
    default_profile_name: str
    default_config_path: str
    default_state_path: str
    default_runtime_path: str
    run_start: Callable[..., int]
    run_watch: Callable[..., int]
    run_status: Callable[..., int]
    run_health: Callable[..., int]
    run_doctor: Callable[..., int]
    run_version: Callable[..., int]
    run_restart_after_next_commit: Callable[..., int]
    run_bootstrap_and_daemonize: Callable[..., int]


def add_start_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    start_parser = subparsers.add_parser("start", help="Run unattended autopilot rounds.")
    start_parser.add_argument("--profile", default=support.default_profile_name, help="Profile name under automation/profiles.")
    start_parser.add_argument("--profile-path", help="Explicit profile JSON path.")
    start_parser.add_argument("--config-path", default=support.default_config_path, help="Base config JSON path.")
    start_parser.add_argument("--state-path", default=support.default_state_path, help="State JSON path.")
    start_parser.add_argument("--max-rounds-this-run", type=int, default=0, help="Limit rounds for this process only.")
    start_parser.add_argument("--single-round", action="store_true", help="Run exactly one unattended round.")
    start_parser.add_argument("--dry-run", action="store_true", help="Render the next prompt only.")
    start_parser.add_argument("--no-branch-guard", action="store_true", help="Skip allowed-branch validation.")
    start_parser.add_argument("--allow-dirty-worktree", action="store_true", help="Skip clean-worktree validation.")
    start_parser.add_argument("--force-lock", action="store_true", help="Override an existing autopilot lock.")
    start_parser.set_defaults(handler=support.run_start)


def add_watch_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    watch_parser = subparsers.add_parser("watch", help="Watch the latest round progress log.")
    watch_parser.add_argument("--runtime-path", default=support.default_runtime_path, help="Runtime directory path.")
    watch_parser.add_argument("--state-path", default="", help="Optional explicit state JSON path.")
    watch_parser.add_argument("--tail", type=int, default=20, help="How many lines to show when switching logs.")
    watch_parser.add_argument("--refresh-seconds", type=int, default=2, help="Polling interval.")
    watch_parser.add_argument(
        "--stale-seconds",
        type=int,
        default=600,
        help="Health threshold for considering the active run stale.",
    )
    watch_parser.add_argument(
        "--prefix-format",
        choices=["long", "short"],
        default="long",
        help="Prefix style for streamed progress.log lines.",
    )
    watch_parser.add_argument("--once", action="store_true", help="Print current status once and exit.")
    watch_parser.set_defaults(handler=support.run_watch)


def add_status_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    status_parser = subparsers.add_parser("status", help="Show current autopilot state.")
    status_parser.add_argument("--state-path", default=support.default_state_path, help="State JSON path.")
    status_parser.set_defaults(handler=support.run_status)


def add_health_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    health_parser = subparsers.add_parser("health", help="Check whether the watched autopilot run is actually alive.")
    health_parser.add_argument("--runtime-path", default=support.default_runtime_path, help="Runtime directory path.")
    health_parser.add_argument("--state-path", default="", help="Optional explicit state JSON path.")
    health_parser.add_argument(
        "--stale-seconds",
        type=int,
        default=600,
        help="Mark active runs stale when progress artifacts stop updating for longer than this.",
    )
    health_parser.add_argument("--json", action="store_true", help="Print the health report as JSON.")
    health_parser.set_defaults(handler=support.run_health)


def add_doctor_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    doctor_parser = subparsers.add_parser("doctor", help="Check environment and profile readiness.")
    doctor_parser.add_argument("--profile", default=support.default_profile_name, help="Profile name under automation/profiles.")
    doctor_parser.add_argument("--profile-path", help="Explicit profile JSON path.")
    doctor_parser.add_argument("--config-path", default=support.default_config_path, help="Base config JSON path.")
    doctor_parser.add_argument("--runtime-path", default=support.default_runtime_path, help="Runtime directory path.")
    doctor_parser.set_defaults(handler=support.run_doctor)


def add_version_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    version_parser = subparsers.add_parser("version", help="Print the deployed scaffold version.")
    version_parser.set_defaults(handler=support.run_version)


def add_restart_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    restart_parser = subparsers.add_parser(
        "restart-after-next-commit",
        help="Wait for the next successful commit, then restart autopilot with replacement settings.",
    )
    restart_parser.add_argument("--profile", default=support.default_profile_name, help="Current profile name under automation/profiles.")
    restart_parser.add_argument("--profile-path", help="Current explicit profile JSON path.")
    restart_parser.add_argument("--config-path", default=support.default_config_path, help="Current base config JSON path.")
    restart_parser.add_argument("--state-path", default=support.default_state_path, help="State JSON path to watch.")
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
    restart_parser.set_defaults(handler=support.run_restart_after_next_commit)


def add_bootstrap_subcommand(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], *, support: CliParserSupport) -> None:
    bootstrap_parser = subparsers.add_parser(
        "bootstrap-and-daemonize",
        help="Run one foreground bootstrap round, then continue in the background if the run is still active.",
    )
    bootstrap_parser.add_argument("--profile", default=support.default_profile_name, help="Profile name under automation/profiles.")
    bootstrap_parser.add_argument("--profile-path", help="Explicit profile JSON path.")
    bootstrap_parser.add_argument("--config-path", default=support.default_config_path, help="Base config JSON path.")
    bootstrap_parser.add_argument("--state-path", default=support.default_state_path, help="State JSON path.")
    bootstrap_parser.add_argument("--no-branch-guard", action="store_true", help="Skip allowed-branch validation.")
    bootstrap_parser.add_argument("--allow-dirty-worktree", action="store_true", help="Skip clean-worktree validation.")
    bootstrap_parser.add_argument("--force-lock", action="store_true", help="Override an existing autopilot lock.")
    bootstrap_parser.add_argument(
        "--daemon-output-path",
        default="automation/runtime/autopilot-daemon.out",
        help="Combined stdout/stderr file for the background continuation process.",
    )
    bootstrap_parser.add_argument(
        "--daemon-pid-path",
        default="automation/runtime/autopilot.pid",
        help="PID file for the background continuation process.",
    )
    bootstrap_parser.set_defaults(handler=support.run_bootstrap_and_daemonize)


def build_parser(*, support: CliParserSupport) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform repository autopilot.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_start_subcommand(subparsers, support=support)
    add_watch_subcommand(subparsers, support=support)
    add_status_subcommand(subparsers, support=support)
    add_health_subcommand(subparsers, support=support)
    add_doctor_subcommand(subparsers, support=support)
    add_version_subcommand(subparsers, support=support)
    add_restart_subcommand(subparsers, support=support)
    add_bootstrap_subcommand(subparsers, support=support)

    return parser
