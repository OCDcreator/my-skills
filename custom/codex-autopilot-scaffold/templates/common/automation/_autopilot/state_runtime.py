from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from _autopilot.lanes import (
    LaneSupport,
    active_lane_config,
    active_lane_id_for_state,
    active_lane_progress,
    build_initial_lane_progress,
    has_any_unfinished_lane_work,
    has_remaining_lane_work,
    next_unfinished_lane_id,
    normalize_state_for_lanes,
    set_active_lane,
    sync_active_lane_mirror_fields,
)


@dataclass(frozen=True)
class StateRuntimeSupport:
    clean_string: Callable[..., str]
    parse_int: Callable[..., int]
    now_timestamp: Callable[..., str]
    info: Callable[..., None]
    save_state: Callable[..., None]
    lane_support: LaneSupport


def new_state(config: dict[str, Any], *, support: StateRuntimeSupport) -> dict[str, Any]:
    timestamp = support.now_timestamp()
    lane_progress = build_initial_lane_progress(config, support=support.lane_support)
    initial_lane_id = config["lanes"][0]["id"]
    return {
        "status": "active",
        "current_round": 0,
        "consecutive_failures": 0,
        "active_lane_id": initial_lane_id,
        "lane_progress": lane_progress,
        "next_phase_number": lane_progress[initial_lane_id]["next_phase_number"],
        "last_phase_doc": lane_progress[initial_lane_id]["last_phase_doc"],
        "last_commit_sha": None,
        "last_summary": None,
        "last_next_focus": active_lane_config(
            {"active_lane_id": initial_lane_id, "lane_progress": lane_progress},
            config,
            support=support.lane_support,
        )["focus_hint"],
        "last_result": None,
        "last_blocking_reason": None,
        "vulture_command": support.clean_string(config.get("vulture_command")),
        "vulture_current_count": None,
        "vulture_previous_count": None,
        "vulture_delta": None,
        "vulture_updated_at": None,
        "vulture_last_error": None,
        "started_at": timestamp,
        "updated_at": timestamp,
    }


def ensure_next_phase_after_completed_round(
    state: dict[str, Any],
    config: dict[str, Any],
    *,
    support: StateRuntimeSupport,
) -> None:
    lane_progress = active_lane_progress(state, config, support=support.lane_support)
    if support.parse_int(lane_progress.get("next_phase_number"), 0) < 1:
        lane_progress["next_phase_number"] = 1
    sync_active_lane_mirror_fields(state, config, support=support.lane_support)


def resume_state_if_threshold_allows(
    state: dict[str, Any],
    config: dict[str, Any],
    state_path,
    *,
    support: StateRuntimeSupport,
) -> dict[str, Any]:
    state = normalize_state_for_lanes(state, config, support=support.lane_support)
    previous_status = support.clean_string(state.get("status"))
    should_resume = False
    if previous_status == "stopped_max_rounds":
        should_resume = int(state["current_round"]) < int(config["max_rounds"])
    elif previous_status == "stopped_failures":
        should_resume = int(state["consecutive_failures"]) < int(config["max_consecutive_failures"])
    elif previous_status == "complete" and has_any_unfinished_lane_work(config, state, support=support.lane_support):
        current_lane_id = active_lane_id_for_state(state, config, support=support.lane_support)
        if not has_remaining_lane_work(config, state, current_lane_id, support=support.lane_support):
            next_lane_id = next_unfinished_lane_id(config, state, support=support.lane_support)
            if next_lane_id:
                set_active_lane(state, config, next_lane_id, support=support.lane_support)
        ensure_next_phase_after_completed_round(state, config, support=support)
        should_resume = True

    if not should_resume:
        return state

    state["status"] = "active"
    support.save_state(state, state_path)
    support.info(f"State status '{previous_status}' is resumable with current config; resuming.")
    return state
