from __future__ import annotations

from typing import Any, Callable

from _autopilot import controller_runtime as runtime
from _autopilot.baseline import BaselineSupport
from _autopilot.cli_parser import CliParserSupport
from _autopilot.bootstrap_runtime import BootstrapRuntimeSupport
from _autopilot.doctor import DoctorSupport
from _autopilot.health_runtime import HealthRuntimeSupport, build_health_report
from _autopilot.lanes import (
    LaneSupport,
    active_lane_config,
    active_lane_id_for_state,
    active_lane_progress,
    config_lane_map,
    has_remaining_lane_work,
    increment_active_lane_phase,
    lane_runtime_config,
    mark_lane_complete,
    next_unfinished_lane_id,
    normalize_state_for_lanes,
    set_active_lane,
    sync_active_lane_mirror_fields,
)
from _autopilot.locking import LockingSupport, autopilot_lock as autopilot_lock_command, read_lock as read_lock_command
from _autopilot.process_control import ProcessControlSupport, spawn_background_autopilot
from _autopilot.round_flow import RoundFlowSupport
from _autopilot.runner import RunnerSupport, resolve_runner_executable
from _autopilot.start_runtime import StartRuntimeSupport
from _autopilot.state_runtime import (
    StateRuntimeSupport,
    new_state as new_state_command,
    resume_state_if_threshold_allows as resume_state_if_threshold_allows_command,
)
from _autopilot.status_views import StatusViewSupport
from _autopilot.validation import ValidationSupport, validate_round_result
from _autopilot.watch_runtime import WatchRuntimeSupport


def build_validation_support() -> ValidationSupport:
    return ValidationSupport(
        clean_string=runtime.clean_string,
        resolve_repo_path=runtime.resolve_repo_path,
        run_git=runtime.run_git,
        info=runtime.info,
    )


def build_baseline_support() -> BaselineSupport:
    return BaselineSupport(
        clean_string=runtime.clean_string,
        compact_text=runtime.compact_text,
        run_shell_command=runtime.run_shell_command,
    )


def build_status_view_support() -> StatusViewSupport:
    return StatusViewSupport(
        repo_root=runtime.REPO_ROOT,
        default_state_path=runtime.DEFAULT_STATE_PATH,
        lock_filename=runtime.LOCK_FILENAME,
        round_directory_re=runtime.ROUND_DIRECTORY_RE,
    )


def build_lane_support() -> LaneSupport:
    return LaneSupport(
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        normalize_path_text=runtime.normalize_path_text,
        infer_roadmap_path_text_from_phase_doc=runtime.infer_roadmap_path_text_from_phase_doc,
        infer_round_roadmap_path_from_phase_doc=runtime.infer_round_roadmap_path_from_phase_doc,
        ensure_path_within_repo=runtime.ensure_path_within_repo,
        resolve_repo_path=runtime.resolve_repo_path,
        read_text=runtime.read_text,
        parse_int=runtime.parse_int,
        queue_item_status_re=runtime.QUEUE_ITEM_STATUS_RE,
    )


def build_state_runtime_support(*, lane_support: LaneSupport | None = None) -> StateRuntimeSupport:
    return StateRuntimeSupport(
        clean_string=runtime.clean_string,
        parse_int=runtime.parse_int,
        now_timestamp=runtime.now_timestamp,
        info=runtime.info,
        save_state=runtime.save_state,
        lane_support=lane_support or build_lane_support(),
    )


def build_locking_support() -> LockingSupport:
    return LockingSupport(
        lock_filename=runtime.LOCK_FILENAME,
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        parse_int=runtime.parse_int,
        now_timestamp=runtime.now_timestamp,
        info=runtime.info,
        pid_exists=runtime.pid_exists,
        read_json=runtime.read_json,
        write_json=runtime.write_json,
    )


def build_runner_support() -> RunnerSupport:
    return RunnerSupport(
        repo_root=runtime.REPO_ROOT,
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        compact_text=runtime.compact_text,
        progress=runtime.progress,
        get_codex_event_summary=runtime.get_codex_event_summary,
        now_timestamp=runtime.now_timestamp,
        write_json=runtime.write_json,
        windows_hidden_process_kwargs=runtime.windows_hidden_process_kwargs,
    )


def build_process_control_support() -> ProcessControlSupport:
    return ProcessControlSupport(
        repo_root=runtime.REPO_ROOT,
        default_profile_name=runtime.DEFAULT_PROFILE_NAME,
        default_config_path=runtime.DEFAULT_CONFIG_PATH,
        default_state_path=runtime.DEFAULT_STATE_PATH,
        lock_filename=runtime.LOCK_FILENAME,
        error_type=runtime.AutopilotError,
        info=runtime.info,
        pid_exists=runtime.pid_exists,
        parse_int=runtime.parse_int,
        clean_string=runtime.clean_string,
        resolve_repo_path=runtime.resolve_repo_path,
        read_json=runtime.read_json,
        read_lock=lambda lock_path: read_lock_command(lock_path, support=build_locking_support()),
        get_head_sha=runtime.get_head_sha,
        run_git=runtime.run_git,
        run_git_no_capture=runtime.run_git_no_capture,
        windows_hidden_process_kwargs=runtime.windows_hidden_process_kwargs,
    )


def build_health_runtime_support() -> HealthRuntimeSupport:
    return HealthRuntimeSupport(
        resolve_repo_path=runtime.resolve_repo_path,
        read_json=runtime.read_json,
        read_lock=lambda lock_path: read_lock_command(lock_path, support=build_locking_support()),
        pid_exists=runtime.pid_exists,
    )


def build_doctor_support() -> DoctorSupport:
    return DoctorSupport(
        repo_root=runtime.REPO_ROOT,
        lock_filename=runtime.LOCK_FILENAME,
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        compact_text=runtime.compact_text,
        load_config=runtime.load_config,
        build_runner_support=build_runner_support,
        resolve_runner_executable=resolve_runner_executable,
        read_vulture_snapshot=runtime.read_vulture_snapshot,
        ensure_path_within_repo=runtime.ensure_path_within_repo,
        get_current_branch=runtime.get_current_branch,
        test_branch_allowed=runtime.test_branch_allowed,
        is_working_tree_dirty=runtime.is_working_tree_dirty,
        resolve_repo_path=runtime.resolve_repo_path,
        read_lock=lambda lock_path: read_lock_command(lock_path, support=build_locking_support()),
        baseline_support=build_baseline_support(),
    )


def build_bootstrap_runtime_support(*, run_start: Callable[..., int]) -> BootstrapRuntimeSupport:
    return BootstrapRuntimeSupport(
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        info=runtime.info,
        read_json=runtime.read_json,
        resolve_repo_path=runtime.resolve_repo_path,
        run_start=run_start,
        spawn_background_autopilot=lambda command_args, output_path, pid_path=None: spawn_background_autopilot(
            command_args,
            output_path=output_path,
            pid_path=pid_path,
            support=build_process_control_support(),
        ),
    )


def build_round_flow_support(*, lane_support: LaneSupport | None = None) -> RoundFlowSupport:
    resolved_lane_support = lane_support or build_lane_support()
    return RoundFlowSupport(
        clean_string=runtime.clean_string,
        parse_int=runtime.parse_int,
        resolve_repo_path=runtime.resolve_repo_path,
        read_text=runtime.read_text,
        read_json=runtime.read_json,
        render_template=runtime.render_template,
        append_controller_requirements=runtime.append_controller_requirements,
        active_lane_config=lambda state, config: active_lane_config(state, config, support=resolved_lane_support),
        active_lane_progress=lambda state, config: active_lane_progress(state, config, support=resolved_lane_support),
        lane_runtime_config=lane_runtime_config,
        get_head_sha=runtime.get_head_sha,
        is_working_tree_dirty=runtime.is_working_tree_dirty,
        validate_round_result=validate_round_result,
    )


def build_start_runtime_support() -> StartRuntimeSupport:
    lane_support = build_lane_support()
    state_runtime_support = build_state_runtime_support(lane_support=lane_support)
    return StartRuntimeSupport(
        error_type=runtime.AutopilotError,
        clean_string=runtime.clean_string,
        compact_text=runtime.compact_text,
        info=runtime.info,
        load_config=runtime.load_config,
        resolve_repo_path=runtime.resolve_repo_path,
        read_json=runtime.read_json,
        save_state=runtime.save_state,
        new_state=lambda config: new_state_command(config, support=state_runtime_support),
        normalize_state_for_lanes=lambda state, config: normalize_state_for_lanes(
            state,
            config,
            support=lane_support,
        ),
        resume_state_if_threshold_allows=lambda state, config, state_path: resume_state_if_threshold_allows_command(
            state,
            config,
            state_path,
            support=state_runtime_support,
        ),
        get_current_branch=runtime.get_current_branch,
        test_branch_allowed=runtime.test_branch_allowed,
        is_working_tree_dirty=runtime.is_working_tree_dirty,
        get_head_sha=runtime.get_head_sha,
        autopilot_lock=lambda runtime_directory, *, branch, head_sha, profile_name, force_lock: autopilot_lock_command(
            runtime_directory,
            branch=branch,
            head_sha=head_sha,
            profile_name=profile_name,
            force_lock=force_lock,
            support=build_locking_support(),
        ),
        refresh_vulture_metrics=runtime.refresh_vulture_metrics,
        reset_worktree_to_head=runtime.reset_worktree_to_head,
        append_history_entry=runtime.append_history_entry,
        increment_active_lane_phase=lambda state, config: increment_active_lane_phase(
            state,
            config,
            support=lane_support,
        ),
        has_remaining_lane_work=lambda config, state, lane_id: has_remaining_lane_work(
            config,
            state,
            lane_id,
            support=lane_support,
        ),
        set_active_lane=lambda state, config, lane_id: set_active_lane(state, config, lane_id, support=lane_support),
        mark_lane_complete=mark_lane_complete,
        next_unfinished_lane_id=lambda config, state, after_lane_id=None: next_unfinished_lane_id(
            config,
            state,
            after_lane_id=after_lane_id,
            support=lane_support,
        ),
        config_lane_map=config_lane_map,
        active_lane_id_for_state=lambda state, config: active_lane_id_for_state(state, config, support=lane_support),
        active_lane_config=lambda state, config: active_lane_config(state, config, support=lane_support),
        sync_active_lane_mirror_fields=lambda state, config: sync_active_lane_mirror_fields(
            state,
            config,
            support=lane_support,
        ),
        baseline_support=build_baseline_support(),
    )


def build_cli_parser_support(
    *,
    run_start: Callable[..., int],
    run_watch: Callable[..., int],
    run_status: Callable[..., int],
    run_health: Callable[..., int],
    run_doctor: Callable[..., int],
    run_version: Callable[..., int],
    run_restart_after_next_commit: Callable[..., int],
    run_bootstrap_and_daemonize: Callable[..., int],
) -> CliParserSupport:
    return CliParserSupport(
        default_profile_name=runtime.DEFAULT_PROFILE_NAME,
        default_config_path=runtime.DEFAULT_CONFIG_PATH,
        default_state_path=runtime.DEFAULT_STATE_PATH,
        default_runtime_path=runtime.DEFAULT_RUNTIME_PATH,
        run_start=run_start,
        run_watch=run_watch,
        run_status=run_status,
        run_health=run_health,
        run_doctor=run_doctor,
        run_version=run_version,
        run_restart_after_next_commit=run_restart_after_next_commit,
        run_bootstrap_and_daemonize=run_bootstrap_and_daemonize,
    )


def build_watch_runtime_support() -> WatchRuntimeSupport:
    return WatchRuntimeSupport(
        resolve_repo_path=runtime.resolve_repo_path,
        read_json=runtime.read_json,
        build_health_report=lambda *, runtime_directory, explicit_state_path, stale_seconds, status_view_support: build_health_report(
            runtime_directory=runtime_directory,
            explicit_state_path=explicit_state_path,
            stale_seconds=stale_seconds,
            support=build_health_runtime_support(),
            status_view_support=status_view_support,
        ),
    )
