from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class DoctorSupport:
    repo_root: Path
    lock_filename: str
    error_type: type[Exception]
    clean_string: Callable[..., str]
    compact_text: Callable[..., str]
    load_config: Callable[..., tuple[dict[str, Any], Path, Path]]
    build_runner_support: Callable[..., Any]
    resolve_runner_executable: Callable[..., str]
    read_vulture_snapshot: Callable[..., dict[str, Any] | None]
    ensure_path_within_repo: Callable[..., Path]
    get_current_branch: Callable[..., str]
    test_branch_allowed: Callable[..., bool]
    is_working_tree_dirty: Callable[..., bool]
    resolve_repo_path: Callable[..., Path]
    read_lock: Callable[..., dict[str, Any] | None]


def run_doctor(args: argparse.Namespace, *, support: DoctorSupport) -> int:
    config, config_path, profile_path = support.load_config(args.config_path, args.profile, args.profile_path)
    failures = 0

    print(f"[doctor] repo: {support.repo_root}")
    print(f"[doctor] config: {config_path}")
    print(f"[doctor] profile: {profile_path}")

    git_path = shutil.which("git")
    if git_path:
        print(f"[doctor] ok   command git: {git_path}")
    else:
        print("[doctor] fail command git: not found in PATH")
        failures += 1

    try:
        runner_support = support.build_runner_support()
        runner_path = support.resolve_runner_executable(
            config,
            clean_string=runner_support.clean_string,
            error_type=runner_support.error_type,
        )
        print(f"[doctor] ok   runner command: {runner_path}")
    except support.error_type as exc:
        print(f"[doctor] fail runner command: {exc}")
        failures += 1

    for extra_directory in config.get("runner_additional_dirs", []):
        extra_directory_text = support.clean_string(extra_directory)
        if not extra_directory_text:
            continue
        if Path(extra_directory_text).exists():
            print(f"[doctor] ok   runner add-dir: {extra_directory_text}")
        else:
            print(f"[doctor] fail runner add-dir: {extra_directory_text}")
            failures += 1

    deploy_verify_path = support.clean_string(config.get("deploy_verify_path"))
    if deploy_verify_path:
        if Path(deploy_verify_path).exists():
            print(f"[doctor] ok   deploy verify path: {deploy_verify_path}")
        else:
            print(f"[doctor] fail deploy verify path: {deploy_verify_path}")
            failures += 1
    else:
        print("[doctor] ok   deploy verify path: <not configured>")

    vulture_command = support.clean_string(config.get("vulture_command"))
    if vulture_command:
        snapshot = support.read_vulture_snapshot(config)
        if snapshot and not snapshot["error"]:
            print(
                "[doctor] ok   vulture command: "
                f"{vulture_command} (findings={snapshot['count']}, exit={snapshot['returncode']})"
            )
        else:
            error_text = snapshot["error"] if snapshot else "vulture snapshot unavailable"
            print(f"[doctor] fail vulture command: {support.compact_text(support.clean_string(error_text), max_length=220)}")
            failures += 1
    else:
        print("[doctor] info vulture command: <not configured>")

    print(f"[doctor] info lanes: {len(config.get('lanes', []))}")
    for lane in config.get("lanes", []):
        lane_id = lane["id"]
        try:
            support.ensure_path_within_repo(
                f"{lane['phase_doc_prefix']}0.md",
                label=f"Lane '{lane_id}' phase_doc_prefix probe",
            )
            print(f"[doctor] ok   lane {lane_id} phase prefix: {lane['phase_doc_prefix']}")
        except support.error_type as exc:
            print(f"[doctor] fail lane {lane_id} phase prefix: {exc}")
            failures += 1

        for label, path_value in [
            ("starting phase", lane["starting_phase_doc"]),
            ("roadmap", lane["roadmap_path"]),
            ("prompt", lane["prompt_template"]),
        ]:
            try:
                support.ensure_path_within_repo(path_value, label=f"Lane '{lane_id}' {label}", must_exist=True)
                print(f"[doctor] ok   lane {lane_id} {label}: {path_value}")
            except support.error_type as exc:
                print(f"[doctor] fail lane {lane_id} {label}: {exc}")
                failures += 1

    branch_name = support.get_current_branch()
    allowed_prefixes = list(config.get("allowed_branch_prefixes", []))
    if support.test_branch_allowed(branch_name, allowed_prefixes):
        print(f"[doctor] ok   branch '{branch_name}' matches allowed prefixes")
    else:
        print(f"[doctor] fail branch '{branch_name}' does not match allowed prefixes: {', '.join(allowed_prefixes)}")
        failures += 1

    if support.is_working_tree_dirty():
        print("[doctor] fail working tree is dirty")
        failures += 1
    else:
        print("[doctor] ok   working tree is clean")

    runtime_directory = support.resolve_repo_path(args.runtime_path)
    print(f"[doctor] info runtime directory: {runtime_directory}")
    lock_path = runtime_directory / support.lock_filename
    lock_data = support.read_lock(lock_path)
    if lock_data:
        print(
            "[doctor] warn lock present: "
            f"host={lock_data.get('hostname')} pid={lock_data.get('pid')} profile={lock_data.get('profile')}"
        )
    else:
        print("[doctor] ok   no autopilot lock present")

    return 1 if failures else 0
