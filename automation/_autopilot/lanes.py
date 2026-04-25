from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


LEGACY_LANE_ID = "legacy-lane"
LANE_ACTIVE_STATUS = "active"
LANE_PENDING_STATUS = "pending"
LANE_COMPLETE_STATUS = "complete"
LANE_OVERRIDE_KEYS = {
    "focus_hint",
    "phase_doc_prefix",
    "starting_phase_doc",
    "roadmap_path",
    "prompt_template",
    "commit_prefix",
}


@dataclass(frozen=True)
class LaneSupport:
    error_type: type[Exception]
    clean_string: Callable[..., str]
    normalize_path_text: Callable[..., str]
    infer_roadmap_path_text_from_phase_doc: Callable[..., str]
    infer_round_roadmap_path_from_phase_doc: Callable[..., Path | None]
    ensure_path_within_repo: Callable[..., Path]
    resolve_repo_path: Callable[..., Path]
    read_text: Callable[..., str]
    parse_int: Callable[..., int]
    queue_item_status_re: re.Pattern[str]


def synthesize_legacy_lane(base_config: dict[str, Any], *, support: LaneSupport) -> dict[str, Any]:
    phase_doc_prefix = support.normalize_path_text(base_config.get("phase_doc_prefix"))
    starting_phase_doc = support.normalize_path_text(base_config.get("starting_phase_doc"))
    if not starting_phase_doc and phase_doc_prefix:
        starting_phase_doc = f"{phase_doc_prefix}0.md"
    roadmap_path = support.normalize_path_text(base_config.get("roadmap_path"))
    if not roadmap_path and starting_phase_doc:
        roadmap_path = support.infer_roadmap_path_text_from_phase_doc(starting_phase_doc)
    return {
        "id": LEGACY_LANE_ID,
        "label": support.clean_string(base_config.get("focus_hint")) or "Legacy lane",
        "focus_hint": support.clean_string(base_config.get("focus_hint")) or "Legacy lane",
        "phase_doc_prefix": phase_doc_prefix,
        "starting_phase_doc": starting_phase_doc,
        "roadmap_path": roadmap_path,
        "prompt_template": support.normalize_path_text(base_config.get("prompt_template")) or "automation/round-prompt.md",
        "commit_prefix": support.clean_string(base_config.get("commit_prefix")),
    }


def normalize_lane_config(
    raw_lane: dict[str, Any],
    *,
    lane_index: int,
    shared_defaults: dict[str, Any],
    support: LaneSupport,
) -> dict[str, Any]:
    lane_id = support.clean_string(raw_lane.get("id"))
    if not lane_id:
        raise support.error_type(f"lanes[{lane_index}] is missing id.")

    phase_doc_prefix = support.normalize_path_text(raw_lane.get("phase_doc_prefix"))
    starting_phase_doc = support.normalize_path_text(raw_lane.get("starting_phase_doc"))
    if not starting_phase_doc and phase_doc_prefix:
        starting_phase_doc = f"{phase_doc_prefix}0.md"

    roadmap_path = support.normalize_path_text(raw_lane.get("roadmap_path"))
    if not roadmap_path and starting_phase_doc:
        roadmap_path = support.infer_roadmap_path_text_from_phase_doc(starting_phase_doc)

    return {
        "id": lane_id,
        "label": support.clean_string(raw_lane.get("label")) or lane_id,
        "focus_hint": support.clean_string(raw_lane.get("focus_hint"))
        or support.clean_string(shared_defaults.get("focus_hint"))
        or lane_id,
        "phase_doc_prefix": phase_doc_prefix,
        "starting_phase_doc": starting_phase_doc,
        "roadmap_path": roadmap_path,
        "prompt_template": support.normalize_path_text(raw_lane.get("prompt_template") or shared_defaults.get("prompt_template"))
        or "automation/round-prompt.md",
        "commit_prefix": support.clean_string(
            raw_lane["commit_prefix"] if "commit_prefix" in raw_lane else shared_defaults.get("commit_prefix")
        ),
    }


def validate_lane_configs(config: dict[str, Any], *, support: LaneSupport) -> None:
    seen_lane_ids: set[str] = set()
    for lane in config["lanes"]:
        lane_id = lane["id"]
        if lane_id in seen_lane_ids:
            raise support.error_type(f"Duplicate lane id '{lane_id}' in autopilot-config.json.")
        seen_lane_ids.add(lane_id)

        prefix_text = support.normalize_path_text(lane.get("phase_doc_prefix"))
        if not prefix_text:
            raise support.error_type(f"Lane '{lane_id}' is missing phase_doc_prefix.")
        starting_phase_doc = support.normalize_path_text(lane.get("starting_phase_doc"))
        roadmap_path = support.normalize_path_text(lane.get("roadmap_path"))
        prompt_template = support.normalize_path_text(lane.get("prompt_template"))

        support.ensure_path_within_repo(f"{prefix_text}0.md", label=f"Lane '{lane_id}' phase_doc_prefix probe")
        support.ensure_path_within_repo(starting_phase_doc, label=f"Lane '{lane_id}' starting_phase_doc", must_exist=True)
        support.ensure_path_within_repo(roadmap_path, label=f"Lane '{lane_id}' roadmap_path", must_exist=True)
        support.ensure_path_within_repo(prompt_template, label=f"Lane '{lane_id}' prompt_template", must_exist=True)

        if not starting_phase_doc.startswith(prefix_text):
            raise support.error_type(
                f"Lane '{lane_id}' starting_phase_doc must stay under phase_doc_prefix: "
                f"{starting_phase_doc} vs {prefix_text}"
            )


def normalize_lanes_config(config: dict[str, Any], *, support: LaneSupport) -> dict[str, Any]:
    normalized = dict(config)
    lanes_raw = normalized.get("lanes")
    lane_entries: list[dict[str, Any]] = []
    if isinstance(lanes_raw, list) and lanes_raw:
        for index, lane in enumerate(lanes_raw):
            if not isinstance(lane, dict):
                raise support.error_type(f"lanes[{index}] must be an object.")
            lane_entries.append(lane)
        legacy_lane_mode = False
    else:
        lane_entries = [synthesize_legacy_lane(normalized, support=support)]
        legacy_lane_mode = True

    shared_defaults = {
        "focus_hint": support.clean_string(normalized.get("focus_hint")),
        "prompt_template": support.normalize_path_text(normalized.get("prompt_template")) or "automation/round-prompt.md",
        "commit_prefix": support.clean_string(normalized.get("commit_prefix")),
    }
    normalized["lanes"] = [
        normalize_lane_config(lane, lane_index=index, shared_defaults=shared_defaults, support=support)
        for index, lane in enumerate(lane_entries)
    ]
    normalized["legacy_lane_mode"] = legacy_lane_mode
    validate_lane_configs(normalized, support=support)
    return normalized


def config_lane_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {lane["id"]: lane for lane in config.get("lanes", [])}


def build_initial_lane_progress(config: dict[str, Any], *, support: LaneSupport) -> dict[str, dict[str, Any]]:
    lane_progress: dict[str, dict[str, Any]] = {}
    initial_phase_number = support.parse_int(config.get("next_phase_number"), 1)
    for index, lane in enumerate(config["lanes"]):
        lane_progress[lane["id"]] = {
            "status": LANE_ACTIVE_STATUS if index == 0 else LANE_PENDING_STATUS,
            "next_phase_number": initial_phase_number if index == 0 else 1,
            "last_phase_doc": lane["starting_phase_doc"],
        }
    return lane_progress


def active_lane_id_for_state(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> str:
    lane_map = config_lane_map(config)
    active_lane_id = support.clean_string(state.get("active_lane_id"))
    if active_lane_id in lane_map:
        return active_lane_id
    if not config.get("lanes"):
        raise support.error_type("No lane configuration is available.")
    return config["lanes"][0]["id"]


def sync_active_lane_mirror_fields(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> None:
    lane_id = active_lane_id_for_state(state, config, support=support)
    lane_progress = state["lane_progress"][lane_id]
    state["active_lane_id"] = lane_id
    state["next_phase_number"] = support.parse_int(lane_progress.get("next_phase_number"), 1)
    state["last_phase_doc"] = support.normalize_path_text(lane_progress.get("last_phase_doc"))


def normalize_state_for_lanes(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> dict[str, Any]:
    normalized_state = dict(state)
    lane_map = config_lane_map(config)
    fallback_active_lane_id = support.clean_string(normalized_state.get("active_lane_id"))
    if fallback_active_lane_id not in lane_map:
        fallback_active_lane_id = config["lanes"][0]["id"]

    raw_lane_progress = normalized_state.get("lane_progress")
    if not isinstance(raw_lane_progress, dict):
        raw_lane_progress = {}

    lane_progress: dict[str, dict[str, Any]] = {}
    fallback_phase_number = support.parse_int(
        normalized_state.get("next_phase_number"),
        support.parse_int(config.get("next_phase_number"), 1),
    )
    fallback_phase_doc = support.normalize_path_text(normalized_state.get("last_phase_doc"))
    for lane in config["lanes"]:
        lane_id = lane["id"]
        raw_progress = raw_lane_progress.get(lane_id)
        if not isinstance(raw_progress, dict):
            raw_progress = {}
        if config.get("legacy_lane_mode") and lane_id == fallback_active_lane_id and not raw_progress:
            lane_progress[lane_id] = {
                "status": support.clean_string(normalized_state.get("status")) or LANE_ACTIVE_STATUS,
                "next_phase_number": fallback_phase_number,
                "last_phase_doc": fallback_phase_doc or lane["starting_phase_doc"],
            }
            continue
        lane_progress[lane_id] = {
            "status": support.clean_string(raw_progress.get("status"))
            or (LANE_ACTIVE_STATUS if lane_id == fallback_active_lane_id else LANE_PENDING_STATUS),
            "next_phase_number": support.parse_int(raw_progress.get("next_phase_number"), 1),
            "last_phase_doc": support.normalize_path_text(raw_progress.get("last_phase_doc")) or lane["starting_phase_doc"],
        }

    normalized_state["active_lane_id"] = fallback_active_lane_id
    normalized_state["lane_progress"] = lane_progress
    sync_active_lane_mirror_fields(normalized_state, config, support=support)
    return normalized_state


def active_lane_config(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> dict[str, Any]:
    return config_lane_map(config)[active_lane_id_for_state(state, config, support=support)]


def active_lane_progress(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> dict[str, Any]:
    return state["lane_progress"][active_lane_id_for_state(state, config, support=support)]


def set_active_lane(state: dict[str, Any], config: dict[str, Any], lane_id: str, *, support: LaneSupport) -> None:
    for lane in config["lanes"]:
        lane_progress = state["lane_progress"][lane["id"]]
        if lane["id"] == lane_id:
            lane_progress["status"] = LANE_ACTIVE_STATUS
        elif support.clean_string(lane_progress.get("status")) != LANE_COMPLETE_STATUS:
            lane_progress["status"] = LANE_PENDING_STATUS
    state["active_lane_id"] = lane_id
    sync_active_lane_mirror_fields(state, config, support=support)


def mark_lane_complete(state: dict[str, Any], lane_id: str) -> None:
    if lane_id in state.get("lane_progress", {}):
        state["lane_progress"][lane_id]["status"] = LANE_COMPLETE_STATUS


def increment_active_lane_phase(state: dict[str, Any], config: dict[str, Any], *, support: LaneSupport) -> None:
    lane_progress = active_lane_progress(state, config, support=support)
    lane_progress["next_phase_number"] = support.parse_int(lane_progress.get("next_phase_number"), 1) + 1
    sync_active_lane_mirror_fields(state, config, support=support)


def lane_runtime_config(config: dict[str, Any], lane: dict[str, Any]) -> dict[str, Any]:
    runtime_config = dict(config)
    for override_key in LANE_OVERRIDE_KEYS:
        runtime_config[override_key] = lane.get(override_key, runtime_config.get(override_key))
    return runtime_config


def read_lane_queue_progress(
    config: dict[str, Any] | None,
    *,
    state: dict[str, Any] | None = None,
    lane_id: str | None = None,
    support: LaneSupport,
) -> dict[str, Any] | None:
    roadmap_path: Path | None = None
    if config and lane_id:
        lane = config_lane_map(config).get(lane_id)
        if lane:
            roadmap_path = support.resolve_repo_path(lane["roadmap_path"])
    if roadmap_path is None and state is not None:
        roadmap_path = support.infer_round_roadmap_path_from_phase_doc(support.clean_string(state.get("last_phase_doc")))
    if roadmap_path is None or not roadmap_path.exists():
        return None

    counts = {"DONE": 0, "NEXT": 0, "QUEUED": 0}
    try:
        roadmap_text = support.read_text(roadmap_path)
    except OSError:
        return None

    for raw_line in roadmap_text.splitlines():
        line = raw_line.strip()
        match = support.queue_item_status_re.match(line)
        if not match:
            continue
        counts[match.group(1)] += 1

    total_count = counts["DONE"] + counts["NEXT"] + counts["QUEUED"]
    remaining_count = counts["NEXT"] + counts["QUEUED"]
    return {
        "roadmap_path": roadmap_path,
        "counts": counts,
        "done_count": counts["DONE"],
        "total_count": total_count,
        "remaining_count": remaining_count,
    }


def has_remaining_lane_work(config: dict[str, Any], state: dict[str, Any], lane_id: str, *, support: LaneSupport) -> bool:
    queue_progress = read_lane_queue_progress(config, state=state, lane_id=lane_id, support=support)
    if queue_progress is None:
        return False
    return int(queue_progress["remaining_count"]) > 0


def next_unfinished_lane_id(
    config: dict[str, Any],
    state: dict[str, Any],
    *,
    after_lane_id: str | None = None,
    support: LaneSupport,
) -> str | None:
    started = after_lane_id is None
    for lane in config["lanes"]:
        lane_id = lane["id"]
        if not started:
            if lane_id == after_lane_id:
                started = True
            continue
        if lane_id == after_lane_id:
            continue
        if has_remaining_lane_work(config, state, lane_id, support=support):
            return lane_id
    return None


def has_any_unfinished_lane_work(config: dict[str, Any], state: dict[str, Any], *, support: LaneSupport) -> bool:
    return any(has_remaining_lane_work(config, state, lane["id"], support=support) for lane in config["lanes"])
