from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class RoundContext:
    attempt_number: int
    lane_id: str
    lane_label: str
    round_config: dict[str, Any]
    phase_number: int
    phase_doc_relative_path: str
    round_directory: Path
    prompt_path: Path
    assistant_output_path: Path
    events_log_path: Path
    progress_log_path: Path


@dataclass(frozen=True)
class RoundEvaluation:
    result: dict[str, Any] | None
    failure_reason: str | None
    ending_head: str
    working_tree_dirty: bool


@dataclass(frozen=True)
class RoundFlowSupport:
    clean_string: Callable[..., str]
    parse_int: Callable[..., int]
    resolve_repo_path: Callable[..., Path]
    read_text: Callable[..., str]
    read_json: Callable[..., Any]
    render_template: Callable[..., str]
    append_controller_requirements: Callable[..., str]
    active_lane_config: Callable[..., dict[str, Any]]
    active_lane_progress: Callable[..., dict[str, Any]]
    lane_runtime_config: Callable[..., dict[str, Any]]
    get_head_sha: Callable[..., str]
    is_working_tree_dirty: Callable[..., bool]
    validate_round_result: Callable[..., str | None]


def prepare_round_context(
    *,
    state: dict[str, Any],
    config: dict[str, Any],
    runtime_directory: Path,
    current_branch: str,
    support: RoundFlowSupport,
) -> RoundContext:
    attempt_number = int(state["current_round"]) + 1
    current_lane = support.active_lane_config(state, config)
    lane_id = current_lane["id"]
    current_lane_progress = support.active_lane_progress(state, config)
    round_config = support.lane_runtime_config(config, current_lane)
    template_path = support.resolve_repo_path(str(round_config["prompt_template"]))
    template_text = support.read_text(template_path)
    phase_number = support.parse_int(current_lane_progress.get("next_phase_number"), 1)
    phase_doc_relative_path = f"{current_lane['phase_doc_prefix']}{phase_number}.md"
    round_directory = runtime_directory / f"round-{attempt_number:03d}"
    round_directory.mkdir(parents=True, exist_ok=True)

    prompt_path = round_directory / "prompt.md"
    assistant_output_path = round_directory / "assistant-output.json"
    events_log_path = round_directory / "events.jsonl"
    progress_log_path = round_directory / "progress.log"

    rendered_prompt = support.render_template(
        template_text,
        {
            "objective": config["objective"],
            "round_attempt": attempt_number,
            "next_phase_number": phase_number,
            "next_phase_doc": phase_doc_relative_path,
            "current_branch": current_branch,
            "last_phase_doc": support.clean_string(state.get("last_phase_doc")),
            "last_commit_sha": support.clean_string(state.get("last_commit_sha")),
            "last_summary": support.clean_string(state.get("last_summary")),
            "focus_hint": support.clean_string(state.get("last_next_focus")),
            "lint_command": support.clean_string(config.get("lint_command")),
            "typecheck_command": support.clean_string(config.get("typecheck_command")),
            "full_test_command": support.clean_string(config.get("full_test_command")),
            "build_command": config["build_command"],
            "vulture_command": support.clean_string(config.get("vulture_command")),
            "runner_kind": support.clean_string(config.get("runner_kind")),
            "runner_model": support.clean_string(config.get("runner_model")),
            "commit_prefix": round_config["commit_prefix"],
            "platform_note": config.get("platform_note", ""),
            "current_lane_id": lane_id,
            "current_lane_label": current_lane["label"],
            "current_lane_roadmap": current_lane["roadmap_path"],
        },
    )
    rendered_prompt = support.append_controller_requirements(rendered_prompt, round_config)
    prompt_path.write_bytes(rendered_prompt.encode("utf-8"))

    return RoundContext(
        attempt_number=attempt_number,
        lane_id=lane_id,
        lane_label=current_lane["label"],
        round_config=round_config,
        phase_number=phase_number,
        phase_doc_relative_path=phase_doc_relative_path,
        round_directory=round_directory,
        prompt_path=prompt_path,
        assistant_output_path=assistant_output_path,
        events_log_path=events_log_path,
        progress_log_path=progress_log_path,
    )


def evaluate_round_execution(
    *,
    round_context: RoundContext,
    codex_exit_code: int,
    schema: dict[str, Any],
    validation_support: Any,
    support: RoundFlowSupport,
) -> RoundEvaluation:
    result: dict[str, Any] | None = None
    parse_error: str | None = None
    stderr_log_path = round_context.events_log_path.with_suffix(".stderr.log")

    if round_context.assistant_output_path.exists():
        try:
            parsed_result = support.read_json(round_context.assistant_output_path)
            if isinstance(parsed_result, dict):
                result = parsed_result
            else:
                parse_error = "Agent output JSON was not an object."
        except json.JSONDecodeError as exc:
            parse_error = str(exc)

    ending_head = support.get_head_sha()
    working_tree_dirty = support.is_working_tree_dirty()
    failure_reason: str | None = None

    if codex_exit_code != 0:
        stderr_text = stderr_log_path.read_text(encoding="utf-8", errors="replace") if stderr_log_path.exists() else ""
        if "input is not valid UTF-8" in stderr_text:
            failure_reason = "runner could not read the round prompt as UTF-8."
        else:
            failure_reason = f"runner exited with code {codex_exit_code}."
    elif result is None:
        failure_reason = (
            f"Could not parse agent output JSON: {parse_error}" if parse_error else "Agent output JSON was not created."
        )

    if not failure_reason and result is not None:
        failure_reason = support.validate_round_result(
            attempt_number=round_context.attempt_number,
            result=result,
            schema=schema,
            phase_doc_relative_path=round_context.phase_doc_relative_path,
            expected_lane_id=round_context.lane_id,
            config=round_context.round_config,
            ending_head=ending_head,
            working_tree_dirty=working_tree_dirty,
            support=validation_support,
        )

    return RoundEvaluation(
        result=result,
        failure_reason=failure_reason,
        ending_head=ending_head,
        working_tree_dirty=working_tree_dirty,
    )
