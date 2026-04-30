from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from _autopilot.baseline import (
    BaselineSupport,
    baseline_failures,
    format_baseline_result,
    run_validation_baseline,
)
from _autopilot.round_flow import RoundFlowSupport, evaluate_round_execution, prepare_round_context
from _autopilot.runner import RunnerSupport, invoke_runner_round, resolve_runner_executable
from _autopilot.state_runtime import DRY_RUN_STOP_STATUS
from _autopilot.validation import ValidationSupport


@dataclass(frozen=True)
class StartRuntimeSupport:
    error_type: type[Exception]
    clean_string: Callable[..., str]
    compact_text: Callable[..., str]
    info: Callable[..., None]
    load_config: Callable[..., tuple[dict[str, Any], Path, Path]]
    resolve_repo_path: Callable[..., Path]
    read_json: Callable[..., Any]
    save_state: Callable[..., None]
    new_state: Callable[..., dict[str, Any]]
    normalize_state_for_lanes: Callable[..., dict[str, Any]]
    resume_state_if_threshold_allows: Callable[..., dict[str, Any]]
    get_current_branch: Callable[..., str]
    test_branch_allowed: Callable[..., bool]
    is_working_tree_dirty: Callable[..., bool]
    get_head_sha: Callable[..., str]
    autopilot_lock: Callable[..., Any]
    refresh_vulture_metrics: Callable[..., None]
    reset_worktree_to_head: Callable[..., None]
    append_history_entry: Callable[..., None]
    increment_active_lane_phase: Callable[..., None]
    has_remaining_lane_work: Callable[..., bool]
    set_active_lane: Callable[..., None]
    mark_lane_complete: Callable[..., None]
    next_unfinished_lane_id: Callable[..., str | None]
    config_lane_map: Callable[..., dict[str, dict[str, Any]]]
    active_lane_id_for_state: Callable[..., str]
    active_lane_config: Callable[..., dict[str, Any]]
    sync_active_lane_mirror_fields: Callable[..., None]
    baseline_support: BaselineSupport


def ensure_required_commands(config: dict[str, Any], runner_support: RunnerSupport, *, support: StartRuntimeSupport) -> None:
    runner_executable = resolve_runner_executable(
        config,
        clean_string=runner_support.clean_string,
        error_type=runner_support.error_type,
    )
    command_names = ["git"]
    if runner_executable == "codex":
        command_names.append("codex")

    missing = [command_name for command_name in command_names if shutil.which(command_name) is None]
    if missing:
        raise support.error_type(f"Required command(s) not found in PATH: {', '.join(missing)}")


def require_green_baseline_before_start(config: dict[str, Any], *, support: StartRuntimeSupport) -> bool:
    baseline_results = run_validation_baseline(config, support=support.baseline_support)
    for result in baseline_results:
        rendered = format_baseline_result(result, support=support.baseline_support)
        if result.status == "not_configured":
            support.info(f"Validation baseline {result.command_key}: {rendered}")
        elif result.status == "success":
            support.info(f"Validation baseline {result.command_key}: {rendered}")
        else:
            support.info(f"Validation baseline {result.command_key} failed: {rendered}")

    failures = baseline_failures(baseline_results)
    if failures:
        failed_names = ", ".join(result.command_key for result in failures)
        support.info(
            "Configured validation baseline failed before start "
            f"({failed_names}). Fix the repo first or rerun without --require-green-baseline."
        )
        return False
    return True


def build_history_entry(
    *,
    attempt_number: int,
    phase_number: int,
    lane_id: str,
    result: dict[str, Any] | None,
    failure_reason: str | None,
    support: StartRuntimeSupport,
) -> dict[str, Any]:
    return {
        "round": attempt_number,
        "phase_number": phase_number,
        "lane_id": support.clean_string(result.get("lane_id") if result else lane_id) or lane_id,
        "status": "failure" if failure_reason else support.clean_string(result.get("status") if result else ""),
        "phase_doc": result.get("phase_doc_path") if result else None,
        "commit_sha": result.get("commit_sha") if result else None,
        "summary": result.get("summary") if result else None,
        "next_focus": result.get("next_focus") if result else None,
        "blocking_reason": failure_reason if failure_reason else None,
    }


def advance_lane_after_nonfailure(
    state: dict[str, Any],
    config: dict[str, Any],
    *,
    completed_lane_id: str,
    support: StartRuntimeSupport,
) -> None:
    support.increment_active_lane_phase(state, config)
    if support.has_remaining_lane_work(config, state, completed_lane_id):
        support.set_active_lane(state, config, completed_lane_id)
        state["status"] = "active"
        return

    support.mark_lane_complete(state, completed_lane_id)
    next_lane_id = support.next_unfinished_lane_id(config, state, after_lane_id=completed_lane_id)
    if next_lane_id:
        support.set_active_lane(state, config, next_lane_id)
        state["status"] = "active"
        state["last_next_focus"] = support.config_lane_map(config)[next_lane_id]["focus_hint"]
        return

    state["status"] = "complete"


def should_stop_before_round(
    *,
    args: argparse.Namespace,
    rounds_executed: int,
    state: dict[str, Any],
    config: dict[str, Any],
    state_path: Path,
    support: StartRuntimeSupport,
) -> bool:
    if args.single_round and rounds_executed >= 1:
        support.info("Single round requested; stopping.")
        return True

    if args.max_rounds_this_run > 0 and rounds_executed >= args.max_rounds_this_run:
        support.info(f"Reached MaxRoundsThisRun={args.max_rounds_this_run}; stopping.")
        return True

    status_value = support.clean_string(state.get("status"))
    if status_value != "active":
        support.info(f"State status is '{state.get('status')}'; stopping.")
        return True

    if int(state["current_round"]) >= int(config["max_rounds"]):
        state["status"] = "stopped_max_rounds"
        support.save_state(state, state_path)
        support.info(f"Reached max_rounds={config['max_rounds']}; stopping.")
        return True

    if int(state["consecutive_failures"]) >= int(config["max_consecutive_failures"]):
        state["status"] = "stopped_failures"
        support.save_state(state, state_path)
        support.info(f"Reached max_consecutive_failures={config['max_consecutive_failures']}; stopping.")
        return True

    return False


def is_runner_start_failure(
    *,
    failure_reason: str,
    result: dict[str, Any] | None,
    starting_head: str,
    ending_head: str,
    working_tree_dirty: bool,
    support: StartRuntimeSupport,
) -> bool:
    if ending_head != starting_head or working_tree_dirty or not isinstance(result, dict):
        return False

    if support.clean_string(result.get("status")) != "failure":
        return False

    if result.get("changed_files") or result.get("tests_run") or result.get("repo_visible_work_landed"):
        return False

    reason_text = " ".join(
        support.clean_string(value).lower()
        for value in (
            failure_reason,
            result.get("blocking_reason"),
            result.get("summary"),
        )
    )
    return any(
        marker in reason_text
        for marker in (
            "before repository work began",
            "premature schema",
            "schema-only",
            "final json schema was emitted prematurely",
            "final response was requested in schema-only format",
            "no files were changed, no commands were run",
            "no repository commands",
            "repository workflow",
        )
    )


def record_failed_round(
    *,
    state: dict[str, Any],
    config: dict[str, Any],
    state_path: Path,
    runtime_directory: Path,
    starting_head: str,
    ending_head: str,
    working_tree_dirty: bool,
    attempt_number: int,
    failure_reason: str,
    result: dict[str, Any] | None,
    history_entry: dict[str, Any],
    support: StartRuntimeSupport,
) -> bool:
    support.info(f"Round {attempt_number} failed: {failure_reason}")
    if ending_head != starting_head or working_tree_dirty:
        support.info(f"Reverting worktree to {starting_head}")
        support.reset_worktree_to_head(starting_head)

    if is_runner_start_failure(
        failure_reason=failure_reason,
        result=result,
        starting_head=starting_head,
        ending_head=ending_head,
        working_tree_dirty=working_tree_dirty,
        support=support,
    ):
        state["consecutive_runner_start_failures"] = int(state.get("consecutive_runner_start_failures") or 0) + 1
        state["last_result"] = "runner_start_failure"
        state["last_blocking_reason"] = f"runner_start_failure: {failure_reason}"
        if result and support.clean_string(result.get("next_focus")):
            state["last_next_focus"] = result.get("next_focus")

        support.append_history_entry(runtime_directory, history_entry)
        support.save_state(state, state_path)

        runner_start_limit = int(config.get("max_consecutive_runner_start_failures") or 8)
        if int(state["consecutive_runner_start_failures"]) >= runner_start_limit:
            state["status"] = "stopped_infra_error"
            support.save_state(state, state_path)
            support.info(
                "Stopping after repeated runner-start failures: "
                f"{state['consecutive_runner_start_failures']}/{runner_start_limit}."
            )
            return True

        support.info(
            "Treating this as a runner-start failure; preserving business failure budget "
            f"({state.get('consecutive_failures', 0)}/{config.get('max_consecutive_failures')})."
        )
        return False

    state["consecutive_runner_start_failures"] = 0
    state["consecutive_failures"] = int(state["consecutive_failures"]) + 1
    state["last_result"] = "failure"
    state["last_blocking_reason"] = failure_reason
    if result and support.clean_string(result.get("next_focus")):
        state["last_next_focus"] = result.get("next_focus")

    support.append_history_entry(runtime_directory, history_entry)
    support.save_state(state, state_path)

    if failure_reason == "runner could not read the round prompt as UTF-8.":
        state["status"] = "stopped_infra_error"
        support.save_state(state, state_path)
        support.info("Stopping after infrastructure error: prompt encoding.")
        return True

    return False


def record_successful_round(
    *,
    state: dict[str, Any],
    config: dict[str, Any],
    state_path: Path,
    runtime_directory: Path,
    current_lane_id: str,
    attempt_number: int,
    result: dict[str, Any],
    history_entry: dict[str, Any],
    support: StartRuntimeSupport,
) -> None:
    state["consecutive_failures"] = 0
    state["consecutive_runner_start_failures"] = 0
    state["last_result"] = result["status"]
    state["last_blocking_reason"] = None
    state["last_summary"] = result["summary"]

    if support.clean_string(result.get("next_focus")):
        state["last_next_focus"] = result["next_focus"]
    state["last_plan_review_verdict"] = result.get("plan_review_verdict")
    state["last_code_review_verdict"] = result.get("code_review_verdict")
    if support.clean_string(result.get("phase_doc_path")):
        state["lane_progress"][current_lane_id]["last_phase_doc"] = result["phase_doc_path"]
    if support.clean_string(result.get("commit_sha")):
        state["last_commit_sha"] = result["commit_sha"]

    support.sync_active_lane_mirror_fields(state, config)

    if result["status"] == "success":
        advance_lane_after_nonfailure(state, config, completed_lane_id=current_lane_id, support=support)
        support.info(f"Round {attempt_number} succeeded with commit {result['commit_sha']}.")
    elif result["status"] == "goal_complete":
        advance_lane_after_nonfailure(state, config, completed_lane_id=current_lane_id, support=support)
        if support.clean_string(state.get("status")) == "complete":
            support.info("Autopilot objective reported complete.")
        else:
            support.info("Round reported goal_complete; controller advanced without wasting an empty discovery round.")

    if support.clean_string(state.get("status")) != "complete" and support.active_lane_id_for_state(state, config) != current_lane_id:
        next_lane = support.active_lane_config(state, config)
        support.info(f"Switching active lane to {next_lane['id']}.")

    if support.clean_string(config.get("vulture_command")):
        support.refresh_vulture_metrics(state, config)
    support.append_history_entry(runtime_directory, history_entry)
    support.save_state(state, state_path)


def run_start(
    args: argparse.Namespace,
    *,
    support: StartRuntimeSupport,
    runner_support: RunnerSupport,
    validation_support: ValidationSupport,
    round_flow_support: RoundFlowSupport,
) -> int:
    config, _, _ = support.load_config(args.config_path, args.profile, args.profile_path)
    state_path = support.resolve_repo_path(args.state_path)
    runtime_directory = state_path.parent
    runtime_directory.mkdir(parents=True, exist_ok=True)

    schema_path = support.resolve_repo_path(str(config["result_schema"]))
    schema = support.read_json(schema_path)
    ensure_required_commands(config, runner_support, support=support)

    state = support.read_json(state_path) if state_path.exists() else support.new_state(config)
    state = support.normalize_state_for_lanes(state, config)
    support.save_state(state, state_path)
    state = support.resume_state_if_threshold_allows(state, config, state_path)

    current_branch = support.get_current_branch()
    if not args.no_branch_guard and not support.test_branch_allowed(current_branch, list(config.get("allowed_branch_prefixes", []))):
        raise support.error_type(
            "Refusing to run on branch "
            f"'{current_branch}'. Use a dedicated worktree branch with one of these prefixes: "
            f"{', '.join(config.get('allowed_branch_prefixes', []))}."
        )

    if not args.allow_dirty_worktree and support.is_working_tree_dirty():
        raise support.error_type("Working tree must be clean before unattended execution.")

    if getattr(args, "require_green_baseline", False) and not require_green_baseline_before_start(config, support=support):
        return 1

    rounds_executed = 0
    saw_round_failure = False
    head_sha = support.get_head_sha()

    with support.autopilot_lock(
        runtime_directory,
        branch=current_branch,
        head_sha=head_sha,
        profile_name=args.profile,
        force_lock=args.force_lock,
    ):
        if support.clean_string(config.get("vulture_command")):
            support.refresh_vulture_metrics(state, config)
            support.save_state(state, state_path)

        while True:
            if should_stop_before_round(
                args=args,
                rounds_executed=rounds_executed,
                state=state,
                config=config,
                state_path=state_path,
                support=support,
            ):
                break

            round_context = prepare_round_context(
                state=state,
                config=config,
                runtime_directory=runtime_directory,
                current_branch=current_branch,
                support=round_flow_support,
            )

            if args.dry_run:
                state["status"] = DRY_RUN_STOP_STATUS
                state["last_result"] = "dry_run"
                state["last_blocking_reason"] = None
                support.save_state(state, state_path)
                support.info(f"Dry run complete. Prompt written to {round_context.prompt_path}")
                break

            starting_head = support.get_head_sha()
            support.info(f"Starting round {round_context.attempt_number} (phase {round_context.phase_number}).")
            codex_exit_code = invoke_runner_round(
                prompt_path=round_context.prompt_path,
                schema_path=schema_path,
                assistant_output_path=round_context.assistant_output_path,
                events_log_path=round_context.events_log_path,
                progress_log_path=round_context.progress_log_path,
                config=config,
                support=runner_support,
            )
            rounds_executed += 1

            round_evaluation = evaluate_round_execution(
                round_context=round_context,
                codex_exit_code=codex_exit_code,
                schema=schema,
                validation_support=validation_support,
                support=round_flow_support,
            )
            state["current_round"] = int(state["current_round"]) + 1
            history_entry = build_history_entry(
                attempt_number=round_context.attempt_number,
                phase_number=round_context.phase_number,
                lane_id=round_context.lane_id,
                result=round_evaluation.result,
                failure_reason=round_evaluation.failure_reason,
                support=support,
            )

            if round_evaluation.failure_reason:
                saw_round_failure = True
                should_stop = record_failed_round(
                    state=state,
                    config=config,
                    state_path=state_path,
                    runtime_directory=runtime_directory,
                    starting_head=starting_head,
                    ending_head=round_evaluation.ending_head,
                    working_tree_dirty=round_evaluation.working_tree_dirty,
                    attempt_number=round_context.attempt_number,
                    failure_reason=round_evaluation.failure_reason,
                    result=round_evaluation.result,
                    history_entry=history_entry,
                    support=support,
                )
                if should_stop:
                    break
                if args.fail_on_round_failure:
                    support.info("Round failure encountered; exiting non-zero because --fail-on-round-failure is set.")
                    break
                continue

            assert round_evaluation.result is not None
            record_successful_round(
                state=state,
                config=config,
                state_path=state_path,
                runtime_directory=runtime_directory,
                current_lane_id=round_context.lane_id,
                attempt_number=round_context.attempt_number,
                result=round_evaluation.result,
                history_entry=history_entry,
                support=support,
            )

    return 1 if saw_round_failure and args.fail_on_round_failure else 0
