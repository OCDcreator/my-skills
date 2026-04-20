from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from _autopilot.status_views import (
    StatusViewSupport,
    build_watch_state_signature,
    print_watch_detail_lines,
    print_watch_snapshot,
    resolve_watch_state_path,
    watched_round_directory,
)


@dataclass(frozen=True)
class WatchRuntimeSupport:
    resolve_repo_path: Callable[..., Path]
    read_json: Callable[..., Any]


def run_watch(args: argparse.Namespace, *, support: WatchRuntimeSupport, status_view_support: StatusViewSupport) -> int:
    runtime_directory = support.resolve_repo_path(args.runtime_path)
    state_path = resolve_watch_state_path(
        runtime_directory,
        getattr(args, "state_path", ""),
        support=status_view_support,
    )
    last_progress_path: Path | None = None
    last_line_count = 0
    last_state_signature: tuple[str, ...] | None = None

    print(f"[watch] runtime: {runtime_directory}")
    while True:
        state_exists = state_path.exists()
        state = support.read_json(state_path) if state_exists else None
        state_signature = build_watch_state_signature(state, state_path_exists=state_exists)

        round_directory = watched_round_directory(runtime_directory, state, status_view_support)
        progress_path = round_directory / "progress.log" if round_directory is not None else None

        if state_signature != last_state_signature or progress_path != last_progress_path:
            print_watch_snapshot(
                state=state,
                state_path=state_path,
                progress_path=progress_path,
                support=status_view_support,
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
                            support=status_view_support,
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
                        support=status_view_support,
                    )
                    last_line_count = len(current_lines)

        if args.once:
            break
        time.sleep(args.refresh_seconds)
    return 0
