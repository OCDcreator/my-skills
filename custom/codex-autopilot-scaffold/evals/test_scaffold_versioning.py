from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD_SCRIPT = SKILL_ROOT / "scripts" / "scaffold_repo.py"


def run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "-c",
            "user.name=Autopilot Test",
            "-c",
            "user.email=autopilot-test@example.invalid",
            *args,
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module_parent_path = path.parent.parent if path.parent.name == "_autopilot" else path.parent
    module_parent = str(module_parent_path)
    inserted_path = False
    stale_package_modules = [name for name in sys.modules if name == "_autopilot" or name.startswith("_autopilot.")]
    for stale_module_name in stale_package_modules:
        sys.modules.pop(stale_module_name, None)
    if module_parent not in sys.path:
        sys.path.insert(0, module_parent)
        inserted_path = True
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
        if inserted_path and sys.path and sys.path[0] == module_parent:
            sys.path.pop(0)
    return module


def load_scaffold_module():
    return load_module_from_path(SCAFFOLD_SCRIPT, "_scaffold_repo_under_test")


def write_files(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        target_path = root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")


def create_repo_with_files(tmp_path: Path, files: dict[str, str]) -> Path:
    repo_root = tmp_path / "target"
    repo_root.mkdir()
    write_files(repo_root, files)
    return repo_root


def detect_commands_for_files(files: dict[str, str]):
    scaffold_module = load_scaffold_module()
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = create_repo_with_files(Path(temp_dir), files)
        return scaffold_module.detect_commands(repo_root)


def create_target_repo(tmp_path: Path) -> Path:
    repo_root = create_repo_with_files(tmp_path, {"package.json": '{"scripts":{"test":"vitest"}}\n'})
    assert run_git(repo_root, "init").returncode == 0
    assert run_git(repo_root, "checkout", "-b", "autopilot/version-smoke").returncode == 0
    assert run_git(repo_root, "add", ".").returncode == 0
    assert run_git(repo_root, "commit", "-m", "seed").returncode == 0
    return repo_root


def run_scaffold(repo_root: Path, *extra_args: str, preset: str = "maintainability") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCAFFOLD_SCRIPT),
            "--target-repo",
            str(repo_root),
            "--preset",
            preset,
            *extra_args,
        ],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def read_version_marker(repo_root: Path) -> dict[str, str]:
    return json.loads((repo_root / "automation" / "autopilot-scaffold-version.json").read_text(encoding="utf-8"))


def write_missing_output_runner(repo_root: Path) -> Path:
    runner_dir = repo_root / ".fake-runner"
    runner_dir.mkdir(parents=True, exist_ok=True)
    runner_script = runner_dir / "fake_codex_missing_output.py"
    runner_script.write_text(
        "from __future__ import annotations\n"
        "import sys\n"
        "sys.stdin.buffer.read()\n"
        "print('{\"type\":\"session.started\"}', flush=True)\n"
        "print('{\"type\":\"agent.finished\"}', flush=True)\n",
        encoding="utf-8",
        newline="\n",
    )
    if os.name == "nt":
        runner_command = runner_dir / "fake-codex.cmd"
        runner_command.write_text(
            f'@echo off\r\n"{sys.executable}" "{runner_script}" %*\r\n',
            encoding="utf-8",
        )
        return runner_command

    runner_command = runner_dir / "fake-codex"
    runner_command.write_text(
        f"#!/usr/bin/env sh\nexec \"{sys.executable}\" \"{runner_script}\" \"$@\"\n",
        encoding="utf-8",
        newline="\n",
    )
    runner_command.chmod(0o755)
    return runner_command


class ScaffoldVersioningTests(unittest.TestCase):
    def test_fresh_scaffold_records_current_scaffold_version(self) -> None:
        with self.subTest("fresh scaffold"):
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_root = create_target_repo(Path(temp_dir))

                result = run_scaffold(repo_root)

                self.assertEqual(result.returncode, 0, result.stderr)
                marker = read_version_marker(repo_root)
                self.assertEqual(marker["scaffold_name"], "codex-autopilot-scaffold")
                self.assertTrue(marker["scaffold_version"])
                autopilot_text = (repo_root / "automation" / "autopilot.py").read_text(encoding="utf-8")
                self.assertIn("AUTOPILOT_SCAFFOLD_VERSION", autopilot_text)
                self.assertLess(len(autopilot_text.splitlines()), 600)
                self.assertTrue((repo_root / "automation" / "_autopilot" / "__init__.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "cli_parser.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "controller_builders.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "controller_runtime.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "bootstrap_runtime.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "doctor.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "health_runtime.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "lanes.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "locking.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "process_control.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "round_flow.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "runner.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "start_runtime.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "state_runtime.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "status_views.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "validation.py").exists())
                self.assertTrue((repo_root / "automation" / "_autopilot" / "watch_runtime.py").exists())
                version_result = subprocess.run(
                    [sys.executable, str(repo_root / "automation" / "autopilot.py"), "version"],
                    cwd=repo_root,
                    text=True,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(version_result.returncode, 0, version_result.stderr)
                self.assertIn(marker["scaffold_version"], version_result.stdout)
                self.assertFalse((repo_root / "automation" / "__pycache__").exists())
                self.assertFalse((repo_root / "automation" / "_autopilot" / "__pycache__").exists())
                gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
                self.assertIn("automation/runtime/", gitignore_text)
                self.assertIn("automation/**/__pycache__/", gitignore_text)
                self.assertIn("automation/**/*.pyc", gitignore_text)
                readme_text = (repo_root / "automation" / "README.md").read_text(encoding="utf-8")
                self.assertIn("bash ./automation/start-autopilot.sh", readme_text)
                self.assertIn("bash ./automation/watch-autopilot.sh", readme_text)
                self.assertIn("--prefix-format short", readme_text)
                self.assertIn("Default operator handoff should use `watch ... --prefix-format short`", readme_text)
                self.assertIn("ssh mac 'cd \"/Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot\"", readme_text)
                self.assertIn("python3 -u ./automation/autopilot.py watch", readme_text)
                compile_result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "py_compile",
                        str(repo_root / "automation" / "autopilot.py"),
                        str(repo_root / "automation" / "_autopilot" / "__init__.py"),
                        str(repo_root / "automation" / "_autopilot" / "cli_parser.py"),
                        str(repo_root / "automation" / "_autopilot" / "controller_builders.py"),
                        str(repo_root / "automation" / "_autopilot" / "controller_runtime.py"),
                        str(repo_root / "automation" / "_autopilot" / "bootstrap_runtime.py"),
                        str(repo_root / "automation" / "_autopilot" / "doctor.py"),
                        str(repo_root / "automation" / "_autopilot" / "health_runtime.py"),
                        str(repo_root / "automation" / "_autopilot" / "lanes.py"),
                        str(repo_root / "automation" / "_autopilot" / "locking.py"),
                        str(repo_root / "automation" / "_autopilot" / "process_control.py"),
                        str(repo_root / "automation" / "_autopilot" / "round_flow.py"),
                        str(repo_root / "automation" / "_autopilot" / "runner.py"),
                        str(repo_root / "automation" / "_autopilot" / "start_runtime.py"),
                        str(repo_root / "automation" / "_autopilot" / "state_runtime.py"),
                        str(repo_root / "automation" / "_autopilot" / "status_views.py"),
                        str(repo_root / "automation" / "_autopilot" / "validation.py"),
                        str(repo_root / "automation" / "_autopilot" / "watch_runtime.py"),
                    ],
                    cwd=repo_root,
                    text=True,
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(compile_result.returncode, 0, compile_result.stderr)

    def test_scaffold_next_steps_use_bash_wrappers_for_mac_shell_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))

            result = run_scaffold(repo_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("bash ./automation/start-autopilot.sh -- --profile mac --dry-run --single-round", result.stdout)
            self.assertIn("git switch -c autopilot/<topic>", result.stdout)
            self.assertIn("remote mac rollout template", result.stdout)
            self.assertIn("python automation/autopilot.py version", result.stdout)
            self.assertIn("python automation/autopilot.py health", result.stdout)
            self.assertIn("bootstrap-and-daemonize", result.stdout)
            self.assertIn(
                "python automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short",
                result.stdout,
            )
            self.assertIn(
                "python3 ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short",
                result.stdout,
            )
            self.assertIn(
                "ssh mac 'cd \"/Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot\" && python3 -u ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short'",
                result.stdout,
            )

    def test_scaffold_next_steps_distinguish_preview_single_round_and_keep_running(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))

            result = run_scaffold(repo_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("choose exactly one startup intent before launch", result.stdout)
            self.assertIn("preview-only", result.stdout)
            self.assertIn("single real round", result.stdout)
            self.assertIn("keep-running", result.stdout)
            self.assertIn("smoke is an intermediate checkpoint for keep-running", result.stdout)
            self.assertIn("do not report success for keep-running until health passes", result.stdout)

    def test_generated_readme_states_that_keep_running_cannot_end_at_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))

            result = run_scaffold(repo_root)

            self.assertEqual(result.returncode, 0, result.stderr)
            readme_text = (repo_root / "automation" / "README.md").read_text(encoding="utf-8")
            self.assertIn("Startup intent confirmation", readme_text)
            self.assertIn("If the operator intent is keep-running", readme_text)
            self.assertIn("A dry-run preview cannot count as success", readme_text)
            self.assertIn("A single foreground round cannot count as success by itself", readme_text)
            self.assertIn("the run is incomplete until `health` proves the target state line is live", readme_text)

    def test_seed_plan_copies_source_and_overrides_lane_queue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            repo_root = create_target_repo(temp_root)
            seed_plan = temp_root / "approved-plan.md"
            seed_plan.write_text(
                "# Approved implementation plan\n\n"
                "- [ ] B1: Replace stale parser\n"
                "- [ ] B2: Add regression tests\n",
                encoding="utf-8",
            )

            result = run_scaffold(repo_root, "--seed-plan", str(seed_plan))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("seeded plan", result.stdout)
            copied_seed = repo_root / "docs" / "status" / "autopilot-seed-plan.md"
            self.assertTrue(copied_seed.exists())
            self.assertIn("Approved implementation plan", copied_seed.read_text(encoding="utf-8"))
            roadmap_text = (
                repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-round-roadmap.md"
            ).read_text(encoding="utf-8")
            self.assertLess(
                roadmap_text.index("### [NEXT] Execute the next approved plan slice"),
                roadmap_text.index("### [NEXT] R1 - First maintainability / refactor slice"),
            )

    def test_dry_run_marks_preview_state_instead_of_dead_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: scaffold").returncode, 0)

            autopilot_path = repo_root / "automation" / "autopilot.py"
            state_path = repo_root / "automation" / "runtime" / "autopilot-state.json"
            prompt_path = repo_root / "automation" / "runtime" / "round-001" / "prompt.md"

            first_dry_run = subprocess.run(
                [
                    sys.executable,
                    str(autopilot_path),
                    "start",
                    "--profile",
                    "windows",
                    "--dry-run",
                    "--single-round",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(first_dry_run.returncode, 0, first_dry_run.stderr)
            self.assertIn("Dry run complete. Prompt written to", first_dry_run.stdout)
            self.assertTrue(prompt_path.exists())
            preview_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(preview_state["status"], "stopped_dry_run")

            status_result = subprocess.run(
                [
                    sys.executable,
                    str(autopilot_path),
                    "status",
                    "--state-path",
                    "automation/runtime/autopilot-state.json",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(status_result.returncode, 0, status_result.stderr)
            self.assertIn("status=stopped_dry_run", status_result.stdout)
            self.assertIn("health: terminal", status_result.stdout)
            self.assertNotIn("dead-runner", status_result.stdout)

            health_result = subprocess.run(
                [
                    sys.executable,
                    str(autopilot_path),
                    "health",
                    "--state-path",
                    "automation/runtime/autopilot-state.json",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(health_result.returncode, 0, health_result.stderr)
            self.assertIn("verdict=terminal", health_result.stdout)
            self.assertIn("state=stopped_dry_run", health_result.stdout)

            second_dry_run = subprocess.run(
                [
                    sys.executable,
                    str(autopilot_path),
                    "start",
                    "--profile",
                    "windows",
                    "--dry-run",
                    "--single-round",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(second_dry_run.returncode, 0, second_dry_run.stderr)
            self.assertIn("Dry run complete. Prompt written to", second_dry_run.stdout)
            self.assertNotIn("State status is 'stopped_dry_run'; stopping.", second_dry_run.stdout)

    def test_command_budget_defaults_to_warning_not_success_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            phase_doc_path = repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-phase-1.md"
            phase_doc_path.parent.mkdir(parents=True, exist_ok=True)
            phase_doc_path.write_text("# phase 1\n", encoding="utf-8")
            (repo_root / "src").mkdir()
            (repo_root / "src" / "demo.py").write_text("print('ok')\n", encoding="utf-8")
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: round 1 - demo").returncode, 0)
            commit_sha = run_git(repo_root, "rev-parse", "HEAD").stdout.strip()
            commit_message = run_git(repo_root, "log", "-1", "--pretty=%s", commit_sha).stdout

            validation_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
                "_template_validation_under_test",
            )
            warnings: list[str] = []
            support = validation_module.ValidationSupport(
                clean_string=lambda value: "" if value is None else str(value).strip(),
                resolve_repo_path=lambda value: repo_root / str(value),
                run_git=lambda args: run_git(repo_root, *args),
                info=warnings.append,
            )
            result = {
                "status": "success",
                "lane_id": "m1-hotspot-slice",
                "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                "commit_sha": commit_sha,
                "commit_message": commit_message,
                "summary": "demo",
                "next_focus": "",
                "tests_run": [],
                "commands_run": ["git status --short", "git status --short", "git diff --stat", "git diff --stat"],
                "build_ran": False,
                "build_id": "",
                "deploy_ran": False,
                "deploy_verified": False,
                "background_tasks_used": False,
                "background_tasks_completed": True,
                "repo_visible_work_landed": True,
                "final_artifacts_written": True,
            }
            config = {
                "commit_prefix": "autopilot",
                "build_command": "",
                "deploy_policy": "never",
                "max_git_status_per_round": 1,
                "max_git_diff_stat_per_round": 1,
                "command_budget_policy": "warn",
            }

            failure_reason = validation_module.validate_round_result(
                attempt_number=1,
                result=result,
                schema={},
                phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                expected_lane_id="m1-hotspot-slice",
                config=config,
                ending_head=commit_sha,
                working_tree_dirty=False,
                support=support,
            )

            self.assertIsNone(failure_reason)
            self.assertTrue(any("Command budget warning" in warning for warning in warnings))

    def test_review_gated_preset_scaffolds_cross_platform_review_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))

            result = run_scaffold(repo_root, preset="review-gated")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((repo_root / "automation" / "opencode-review.sh").exists())
            self.assertTrue((repo_root / "automation" / "Invoke-OpencodeReview.ps1").exists())
            self.assertTrue((repo_root / ".opencode" / "commands" / "review-plan.md").exists())
            self.assertTrue((repo_root / ".opencode" / "commands" / "review-code.md").exists())
            gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("!.opencode/", gitignore_text)
            self.assertIn("!.opencode/commands/review-plan.md", gitignore_text)
            config = json.loads((repo_root / "automation" / "autopilot-config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["review_poll_seconds"], 60)
            self.assertEqual(config["review_timeout_seconds"], 1800)
            self.assertIn("automation/opencode-review.sh", config["prerequisite_paths"])
            self.assertIn("automation/Invoke-OpencodeReview.ps1", config["prerequisite_paths"])
            self.assertIn(".opencode/commands/review-plan.md", config["prerequisite_paths"])
            master_plan_text = (repo_root / "docs" / "status" / "autopilot-master-plan.md").read_text(encoding="utf-8")
            self.assertIn(
                "Do not abort an OpenCode pass early only because it is still reading references or the repo diff is empty",
                master_plan_text,
            )
            self.assertIn(
                "If an implementation helper uses background tasks or detached sub-work, the round is not complete until those tasks finish",
                master_plan_text,
            )

    def test_round_result_schema_requires_every_property_for_codex_output(self) -> None:
        schema = json.loads(
            (SKILL_ROOT / "templates" / "common" / "automation" / "round-result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        property_names = set(schema.get("properties", {}).keys())
        required_names = set(schema.get("required", []))

        self.assertEqual(set(), property_names - required_names)

    def test_schema_requires_background_completion_contract_fields(self) -> None:
        schema = json.loads(
            (SKILL_ROOT / "templates" / "common" / "automation" / "round-result.schema.json").read_text(
                encoding="utf-8"
            )
        )
        required_names = set(schema.get("required", []))

        self.assertIn("background_tasks_used", required_names)
        self.assertIn("background_tasks_completed", required_names)
        self.assertIn("repo_visible_work_landed", required_names)
        self.assertIn("final_artifacts_written", required_names)
        self.assertEqual(schema["properties"]["background_tasks_used"]["type"], "boolean")
        self.assertEqual(schema["properties"]["background_tasks_completed"]["type"], "boolean")
        self.assertEqual(schema["properties"]["repo_visible_work_landed"]["type"], "boolean")
        self.assertEqual(schema["properties"]["final_artifacts_written"]["type"], "boolean")

    def test_success_result_fails_when_background_tasks_have_not_completed(self) -> None:
        validation_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
            "_template_validation_background_completion_test",
        )
        result = {
            "status": "success",
            "lane_id": "m1-hotspot-slice",
            "summary": "main pass exited early",
            "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
            "tests_run": [],
            "commands_run": [],
            "build_ran": False,
            "deploy_ran": False,
            "deploy_verified": False,
            "build_id": "",
            "commit_sha": "abc123",
            "commit_message": "autopilot: round 1 - demo",
            "next_focus": "",
            "blocking_reason": "",
            "plan_review_verdict": "",
            "code_review_verdict": "",
            "changed_files": ["src/demo.py"],
            "background_tasks_used": True,
            "background_tasks_completed": False,
            "repo_visible_work_landed": True,
            "final_artifacts_written": True,
        }

        failure_reason = validation_module.validate_round_result(
            attempt_number=1,
            result=result,
            schema=json.loads(
                (SKILL_ROOT / "templates" / "common" / "automation" / "round-result.schema.json").read_text(
                    encoding="utf-8"
                )
            ),
            phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
            expected_lane_id="m1-hotspot-slice",
            config={"commit_prefix": "autopilot", "build_command": "", "deploy_policy": "never"},
            ending_head="abc123",
            working_tree_dirty=False,
            support=validation_module.ValidationSupport(
                clean_string=lambda value: "" if value is None else str(value).strip(),
                resolve_repo_path=lambda value: Path("unused") / str(value),
                run_git=lambda args: run_git(SKILL_ROOT, *args),
                info=lambda message: None,
            ),
        )

        self.assertIsNotNone(failure_reason)
        self.assertIn("background tasks were used but background_tasks_completed=false", failure_reason)

    def test_success_result_requires_repo_visible_work_and_final_artifacts(self) -> None:
        validation_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
            "_template_validation_final_artifacts_test",
        )
        result = {
            "status": "success",
            "lane_id": "m1-hotspot-slice",
            "summary": "claimed success before artifacts landed",
            "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
            "tests_run": [],
            "commands_run": [],
            "build_ran": False,
            "deploy_ran": False,
            "deploy_verified": False,
            "build_id": "",
            "commit_sha": "abc123",
            "commit_message": "autopilot: round 1 - demo",
            "next_focus": "",
            "blocking_reason": "",
            "plan_review_verdict": "",
            "code_review_verdict": "",
            "changed_files": ["src/demo.py"],
            "background_tasks_used": True,
            "background_tasks_completed": True,
            "repo_visible_work_landed": False,
            "final_artifacts_written": False,
        }

        failure_reason = validation_module.validate_round_result(
            attempt_number=1,
            result=result,
            schema=json.loads(
                (SKILL_ROOT / "templates" / "common" / "automation" / "round-result.schema.json").read_text(
                    encoding="utf-8"
                )
            ),
            phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
            expected_lane_id="m1-hotspot-slice",
            config={"commit_prefix": "autopilot", "build_command": "", "deploy_policy": "never"},
            ending_head="abc123",
            working_tree_dirty=False,
            support=validation_module.ValidationSupport(
                clean_string=lambda value: "" if value is None else str(value).strip(),
                resolve_repo_path=lambda value: Path("unused") / str(value),
                run_git=lambda args: run_git(SKILL_ROOT, *args),
                info=lambda message: None,
            ),
        )

        self.assertIsNotNone(failure_reason)
        self.assertIn("repo_visible_work_landed=false", failure_reason)
        self.assertIn("final_artifacts_written=false", failure_reason)

    def test_missing_agent_output_is_reported_as_background_aware_completion_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir) / "round-001"
            round_dir.mkdir()
            round_flow_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "round_flow.py",
                "_template_round_flow_missing_output_test",
            )
            context = round_flow_module.RoundContext(
                attempt_number=1,
                lane_id="m1-hotspot-slice",
                lane_label="R1",
                round_config={},
                phase_number=1,
                phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                round_directory=round_dir,
                prompt_path=round_dir / "prompt.md",
                assistant_output_path=round_dir / "assistant-output.json",
                events_log_path=round_dir / "events.jsonl",
                progress_log_path=round_dir / "progress.log",
            )

            evaluation = round_flow_module.evaluate_round_execution(
                round_context=context,
                codex_exit_code=0,
                schema={},
                validation_support=None,
                support=round_flow_module.RoundFlowSupport(
                    clean_string=lambda value: "" if value is None else str(value).strip(),
                    parse_int=lambda value, default: default,
                    resolve_repo_path=lambda value: Path(value),
                    read_text=lambda path: Path(path).read_text(encoding="utf-8"),
                    read_json=lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
                    render_template=lambda text, tokens: text,
                    append_controller_requirements=lambda text, config: text,
                    active_lane_config=lambda state, config: {},
                    active_lane_progress=lambda state, config: {},
                    lane_runtime_config=lambda config, lane: {},
                    get_head_sha=lambda: "abc123",
                    is_working_tree_dirty=lambda: False,
                    validate_round_result=lambda **kwargs: None,
                ),
            )

            self.assertIsNotNone(evaluation.failure_reason)
            self.assertIn("Agent output JSON was not created.", evaluation.failure_reason)
            self.assertIn("background-task-aware completion contract", evaluation.failure_reason)

    def test_start_can_return_nonzero_when_round_failure_flag_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            config_path = repo_root / "automation" / "autopilot-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["runner_command"] = str(write_missing_output_runner(repo_root))
            config["lint_command"] = ""
            config["typecheck_command"] = ""
            config["full_test_command"] = ""
            config["build_command"] = ""
            config["targeted_test_required"] = False
            config["full_test_cadence_rounds"] = 0
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: scaffold").returncode, 0)

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "automation" / "autopilot.py"),
                    "start",
                    "--profile",
                    "windows",
                    "--single-round",
                    "--fail-on-round-failure",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Agent output JSON was not created.", result.stdout)
            state = json.loads((repo_root / "automation" / "runtime" / "autopilot-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["last_result"], "failure")
            self.assertIn("background-task-aware completion contract", state["last_blocking_reason"])

    def test_all_preset_prompts_include_background_completion_contract(self) -> None:
        for prompt_path in sorted((SKILL_ROOT / "templates" / "presets").glob("*/automation/round-prompt.md")):
            with self.subTest(prompt_path=prompt_path):
                prompt_text = prompt_path.read_text(encoding="utf-8")
                self.assertIn("background tasks", prompt_text)
                self.assertIn("main pass", prompt_text)
                self.assertIn("final round artifacts", prompt_text)

    def test_review_gated_dry_run_writes_prompt_with_schema_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))

            scaffold_result = run_scaffold(repo_root, preset="review-gated")
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: scaffold").returncode, 0)

            autopilot_path = repo_root / "automation" / "autopilot.py"
            prompt_path = repo_root / "automation" / "runtime" / "round-001" / "prompt.md"
            dry_run_result = subprocess.run(
                [
                    sys.executable,
                    str(autopilot_path),
                    "start",
                    "--profile",
                    "windows",
                    "--dry-run",
                    "--single-round",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(dry_run_result.returncode, 0, dry_run_result.stderr)
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn(
                "do not kill it early just because the repo diff is still empty or the pass is still reading files",
                prompt_text,
            )
            self.assertIn(
                "Treat a still-growing implementation log or a still-live child PID as proof that the pass is still working",
                prompt_text,
            )
            self.assertIn(
                "If the implementation path uses background tasks, do not treat the main pass as complete until those background tasks finish",
                prompt_text,
            )
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("plan_review_verdict", prompt_text)
            self.assertIn("code_review_verdict", prompt_text)

    def test_review_gated_python_test_script_does_not_require_node_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_repo_with_files(
                Path(temp_dir),
                {"package.json": '{"scripts":{"test":"python -m unittest"}}\n'},
            )
            self.assertEqual(run_git(repo_root, "init").returncode, 0)
            self.assertEqual(run_git(repo_root, "checkout", "-b", "autopilot/python-smoke").returncode, 0)
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "seed").returncode, 0)

            result = run_scaffold(repo_root, preset="review-gated")

            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads((repo_root / "automation" / "autopilot-config.json").read_text(encoding="utf-8"))
            self.assertNotIn("node_modules", config["prerequisite_paths"])

    def test_health_runtime_flags_active_state_without_live_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            runtime_directory = repo_root / "automation" / "runtime"
            runtime_directory.mkdir(parents=True, exist_ok=True)
            state_path = runtime_directory / "autopilot-state.json"
            state = {
                "status": "active",
                "current_round": 3,
                "active_lane_id": "m1-hotspot-slice",
                "last_commit_sha": "abc123",
                "last_phase_doc": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-2.md",
                "last_blocking_reason": "",
                "last_plan_review_verdict": "APPROVED",
                "last_code_review_verdict": "APPROVED",
            }
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            (runtime_directory / "autopilot.lock.json").write_text(
                json.dumps({"pid": 999999, "hostname": "test-host"}, indent=2) + "\n",
                encoding="utf-8",
            )

            health_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "health_runtime.py",
                "_template_health_runtime_under_test",
            )
            status_views_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "status_views.py",
                "_template_status_views_under_test",
            )
            report = health_module.build_health_report(
                runtime_directory=runtime_directory,
                explicit_state_path=str(state_path),
                stale_seconds=600,
                support=health_module.HealthRuntimeSupport(
                    resolve_repo_path=lambda value: Path(value).resolve() if Path(value).is_absolute() else (repo_root / str(value)),
                    read_json=lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
                    read_lock=lambda lock_path: json.loads(Path(lock_path).read_text(encoding="utf-8")),
                    pid_exists=lambda pid: False,
                ),
                status_view_support=status_views_module.StatusViewSupport(
                    repo_root=repo_root,
                    default_state_path="automation/runtime/autopilot-state.json",
                    lock_filename="autopilot.lock.json",
                    round_directory_re=status_views_module.re.compile(r"round-(\d+)$"),
                ),
            )

            self.assertEqual(report["verdict"], "dead-runner")
            self.assertIn("no live autopilot pid", report["reason"])

    def test_health_runtime_requires_exec_confirmation_before_claiming_round_is_running(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            runtime_directory = repo_root / "automation" / "runtime"
            round_directory = runtime_directory / "round-004"
            round_directory.mkdir(parents=True, exist_ok=True)
            state_path = runtime_directory / "autopilot-state.json"
            state = {
                "status": "active",
                "current_round": 3,
                "active_lane_id": "m1-hotspot-slice",
                "last_commit_sha": "abc123",
            }
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            (runtime_directory / "autopilot.lock.json").write_text(
                json.dumps({"pid": 12345, "hostname": "test-host"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (round_directory / "runner-status.json").write_text(
                json.dumps(
                    {
                        "pid": 67890,
                        "status": "spawned",
                        "started_at": "2026-04-24T10:00:00",
                        "exec_confirmed_at": None,
                        "last_output_at": None,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            health_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "health_runtime.py",
                "_template_health_runtime_exec_gate_test",
            )
            status_views_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "status_views.py",
                "_template_status_views_exec_gate_test",
            )
            report = health_module.build_health_report(
                runtime_directory=runtime_directory,
                explicit_state_path=str(state_path),
                stale_seconds=600,
                support=health_module.HealthRuntimeSupport(
                    resolve_repo_path=lambda value: Path(value).resolve() if Path(value).is_absolute() else (repo_root / str(value)),
                    read_json=lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
                    read_lock=lambda lock_path: json.loads(Path(lock_path).read_text(encoding="utf-8")),
                    pid_exists=lambda pid: pid in {12345, 67890},
                ),
                status_view_support=status_views_module.StatusViewSupport(
                    repo_root=repo_root,
                    default_state_path="automation/runtime/autopilot-state.json",
                    lock_filename="autopilot.lock.json",
                    round_directory_re=status_views_module.re.compile(r"round-(\d+)$"),
                ),
            )

            self.assertEqual(report["verdict"], "starting")
            self.assertFalse(report["runner_exec_confirmed"])
            self.assertIn("has not emitted its first execution event", report["reason"])

    def test_health_runtime_requires_progress_log_updates_even_after_exec_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            runtime_directory = repo_root / "automation" / "runtime"
            round_directory = runtime_directory / "round-005"
            round_directory.mkdir(parents=True, exist_ok=True)
            state_path = runtime_directory / "autopilot-state.json"
            state_path.write_text(
                json.dumps({"status": "active", "current_round": 4, "active_lane_id": "m1-hotspot-slice"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (runtime_directory / "autopilot.lock.json").write_text(
                json.dumps({"pid": 12345, "hostname": "test-host"}, indent=2) + "\n",
                encoding="utf-8",
            )
            (round_directory / "runner-status.json").write_text(
                json.dumps(
                    {
                        "pid": 67890,
                        "status": "running",
                        "started_at": "2026-04-24T10:00:00",
                        "exec_confirmed_at": "2026-04-24T10:00:05",
                        "last_output_at": "2026-04-24T10:00:05",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            health_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "health_runtime.py",
                "_template_health_runtime_progress_gate_test",
            )
            status_views_module = load_module_from_path(
                SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "status_views.py",
                "_template_status_views_progress_gate_test",
            )
            report = health_module.build_health_report(
                runtime_directory=runtime_directory,
                explicit_state_path=str(state_path),
                stale_seconds=600,
                support=health_module.HealthRuntimeSupport(
                    resolve_repo_path=lambda value: Path(value).resolve() if Path(value).is_absolute() else (repo_root / str(value)),
                    read_json=lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
                    read_lock=lambda lock_path: json.loads(Path(lock_path).read_text(encoding="utf-8")),
                    pid_exists=lambda pid: pid in {12345, 67890},
                ),
                status_view_support=status_views_module.StatusViewSupport(
                    repo_root=repo_root,
                    default_state_path="automation/runtime/autopilot-state.json",
                    lock_filename="autopilot.lock.json",
                    round_directory_re=status_views_module.re.compile(r"round-(\d+)$"),
                ),
            )

            self.assertEqual(report["verdict"], "stalled")
            self.assertIn("progress.log has not started updating", report["reason"])

    def test_watch_detail_lines_default_to_human_friendly_summary_and_preserve_raw_view(self) -> None:
        status_views_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "status_views.py",
            "_template_status_views_human_watch_test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            progress_path = repo_root / "automation" / "runtime" / "round-013" / "progress.log"
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "active_lane_id": "a2-mcp-settings",
                "current_round": 12,
                "next_phase_number": 2,
                "status": "active",
                "consecutive_failures": 0,
            }
            support = status_views_module.StatusViewSupport(
                repo_root=repo_root,
                default_state_path="automation/runtime/autopilot-state.json",
                lock_filename="autopilot.lock.json",
                round_directory_re=status_views_module.re.compile(r"round-(\d+)$"),
            )
            lines = [
                "[15:49:23] [codex] Running command: /bin/zsh -lc \"printf 'Using superpowers + planning skills, then reading the queued lane docs.\\\\n' && sed -n '1,220p' foo\"",
                "[15:49:23] [codex] Command finished (exit 0): /bin/zsh -lc \"printf 'Using superpowers + planning skills, then reading the queued lane docs.\\\\n' && sed -n '1,220p' foo\"",
                "[15:50:34] [codex] Command finished (exit 1): /bin/zsh -lc \"printf 'I’ve got the current owner. Now pulling the remaining spec bits and MCP type details.\\\\n' && sed -n '317,420p' bar\"",
                "[15:52:25] [codex] Running command: /bin/zsh -lc 'python3 automation/run_opencode_implementation.py --timeout-seconds 3600 --dir . --agent build'",
                "[15:53:42] [codex] Running command: /bin/zsh -lc \"printf 'Still waiting on OpenCode. I’m peeking at the newest log lines and current worktree diff.\\\\n' && tail -n 60 baz\"",
            ]

            human_stdout = StringIO()
            with redirect_stdout(human_stdout):
                status_views_module.print_watch_detail_lines(
                    lines,
                    state=state,
                    progress_path=progress_path,
                    prefix_format="short",
                    view="human",
                    support=support,
                )
            human_output = human_stdout.getvalue()
            self.assertIn("docs: Using superpowers + planning skills, then reading the queued lane docs.", human_output)
            self.assertIn("fail: I’ve got the current owner. Now pulling the remaining spec bits and MCP type details. failed (exit 1)", human_output)
            self.assertIn("impl: Starting OpenCode implementation pass", human_output)
            self.assertIn("wait: Waiting on OpenCode implementation wrapper", human_output)
            self.assertNotIn("Command finished (exit 0)", human_output)
            self.assertNotIn("run_opencode_implementation.py --timeout-seconds 3600", human_output)

            raw_stdout = StringIO()
            with redirect_stdout(raw_stdout):
                status_views_module.print_watch_detail_lines(
                    lines,
                    state=state,
                    progress_path=progress_path,
                    prefix_format="short",
                    view="raw",
                    support=support,
                )
            raw_output = raw_stdout.getvalue()
            self.assertIn("Command finished (exit 0)", raw_output)
            self.assertIn("run_opencode_implementation.py --timeout-seconds 3600", raw_output)

    def test_status_summary_surfaces_activity_and_healthy_but_quiet_note(self) -> None:
        status_views_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "status_views.py",
            "_template_status_views_activity_summary_test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            round_dir = repo_root / "automation" / "runtime" / "round-013"
            round_dir.mkdir(parents=True, exist_ok=True)
            (round_dir / "progress.log").write_text(
                "\n".join(
                    [
                        "[15:52:25] [codex] Running command: /bin/zsh -lc 'python3 automation/run_opencode_implementation.py --timeout-seconds 3600 --dir . --agent build'",
                        "[15:56:16] [codex] Running command: /bin/zsh -lc \"printf 'I’m parking on the live OpenCode wrapper until it exits, rather than interrupting it mid-pass.\\\\n' && while ps -p 13122 >/dev/null 2>&1; do sleep 30; done\"",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            state = {
                "status": "active",
                "current_round": 12,
                "active_lane_id": "a2-mcp-settings",
                "next_phase_number": 2,
                "consecutive_failures": 0,
                "last_phase_doc": "docs/status/lanes/a2-mcp-settings/autopilot-phase-1.md",
                "last_next_focus": "M2 - Implement MCP server operations and add-server forms",
            }
            health_report = {
                "verdict": "healthy",
                "reason": "active run has a live autopilot pid, a live codex exec child pid, confirmed execution, and a fresh progress.log (190s old)",
                "freshest_artifact_age_seconds": 190,
                "autopilot_pid": 7745,
                "autopilot_pid_alive": True,
                "runner_pid": 10346,
                "runner_pid_alive": True,
                "runner_exec_confirmed": True,
            }
            support = status_views_module.StatusViewSupport(
                repo_root=repo_root,
                default_state_path="automation/runtime/autopilot-state.json",
                lock_filename="autopilot.lock.json",
                round_directory_re=status_views_module.re.compile(r"round-(\d+)$"),
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                status_views_module.print_state_summary(
                    state,
                    runtime_directory=repo_root / "automation" / "runtime",
                    health_report=health_report,
                    support=support,
                    read_lock=lambda _path: None,
                )
            output = stdout.getvalue()
            self.assertIn("[status] activity: waiting on OpenCode implementation wrapper", output)
            self.assertIn("[status] note: quiet for 190s", output)

    def test_older_scaffold_auto_upgrades_common_files_and_refreshes_preset_automation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            first_result = run_scaffold(repo_root)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)

            version_path = repo_root / "automation" / "autopilot-scaffold-version.json"
            version_path.write_text(
                json.dumps(
                    {
                        "scaffold_name": "codex-autopilot-scaffold",
                        "scaffold_version": "0.0.1",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            autopilot_path = repo_root / "automation" / "autopilot.py"
            autopilot_path.write_text("# stale controller from old scaffold\n", encoding="utf-8")
            config_path = repo_root / "automation" / "autopilot-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["objective"] = "Stale project-specific queue objective."
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            upgrade_result = run_scaffold(repo_root)

            self.assertEqual(upgrade_result.returncode, 0, upgrade_result.stderr)
            self.assertIn("auto-upgrade", upgrade_result.stdout)
            upgraded_marker = read_version_marker(repo_root)
            self.assertNotEqual(upgraded_marker["scaffold_version"], "0.0.1")
            self.assertNotIn("stale controller", autopilot_path.read_text(encoding="utf-8"))
            refreshed_config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(
                refreshed_config["objective"],
                "Reduce ownership concentration and maintainability hotspots one queued slice at a time while keeping configured validation commands green.",
            )

    def test_older_scaffold_auto_upgrade_refreshes_preset_automation_but_preserves_lane_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            first_result = run_scaffold(repo_root)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)

            version_path = repo_root / "automation" / "autopilot-scaffold-version.json"
            version_path.write_text(
                json.dumps(
                    {
                        "scaffold_name": "codex-autopilot-scaffold",
                        "scaffold_version": "0.0.1",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            prompt_path = repo_root / "automation" / "round-prompt.md"
            stale_prompt = "# stale top-level prompt\nRead docs/status/maintainability-round-roadmap.md only.\n"
            prompt_path.write_text(stale_prompt, encoding="utf-8")

            config_path = repo_root / "automation" / "autopilot-config.json"
            stale_config = json.loads(config_path.read_text(encoding="utf-8"))
            stale_config["focus_hint"] = "Stale focus hint that should be refreshed."
            stale_config["targeted_test_prefixes"] = []
            config_path.write_text(json.dumps(stale_config, indent=2) + "\n", encoding="utf-8")

            lane_roadmap_path = repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-round-roadmap.md"
            preserved_lane_marker = "<!-- preserve lane roadmap edits -->\n"
            lane_roadmap_path.write_text(preserved_lane_marker + lane_roadmap_path.read_text(encoding="utf-8"), encoding="utf-8")

            upgrade_result = run_scaffold(repo_root)

            self.assertEqual(upgrade_result.returncode, 0, upgrade_result.stderr)
            self.assertIn("refreshed common assets plus preset automation files", upgrade_result.stdout)

            refreshed_prompt = prompt_path.read_text(encoding="utf-8")
            self.assertNotIn(stale_prompt.strip(), refreshed_prompt)
            self.assertIn("{{current_lane_roadmap}}", refreshed_prompt)
            self.assertIn("Stay inside lane `{{current_lane_id}}`", refreshed_prompt)

            refreshed_config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(refreshed_config["focus_hint"], "R1 - First maintainability / refactor slice")
            self.assertEqual(
                refreshed_config["targeted_test_prefixes"],
                [
                    "npm test --",
                    "npm run test --",
                    "npx jest ",
                    "npx vitest ",
                    "pnpm test --",
                    "pnpm exec jest ",
                    "pnpm exec vitest ",
                    "yarn test ",
                    "yarn jest ",
                    "yarn vitest ",
                ],
            )

            preserved_lane_text = lane_roadmap_path.read_text(encoding="utf-8")
            self.assertTrue(preserved_lane_text.startswith(preserved_lane_marker))

    def test_release_lock_removes_matching_lock_even_when_pid_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            autopilot_module = load_module_from_path(
                repo_root / "automation" / "autopilot.py",
                "_generated_autopilot_under_test",
            )
            runtime_directory = repo_root / "automation" / "runtime"
            runtime_directory.mkdir(parents=True, exist_ok=True)
            lock_path = runtime_directory / autopilot_module.LOCK_FILENAME
            lock_path.write_text(json.dumps({"hostname": socket.gethostname()}, indent=2) + "\n", encoding="utf-8")

            autopilot_module.release_lock(runtime_directory, {"hostname": socket.gethostname()})

            self.assertFalse(lock_path.exists(), "Matching lock file should be removed even without pid fields.")

    def test_start_runtime_support_wraps_state_runtime_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            scaffold_result = run_scaffold(repo_root)
            self.assertEqual(scaffold_result.returncode, 0, scaffold_result.stderr)

            autopilot_module = load_module_from_path(
                repo_root / "automation" / "autopilot.py",
                "_generated_autopilot_support_under_test",
            )
            config, _, _ = autopilot_module.load_config(
                autopilot_module.DEFAULT_CONFIG_PATH,
                autopilot_module.DEFAULT_PROFILE_NAME,
                None,
            )
            runtime_directory = repo_root / "automation" / "runtime"
            runtime_directory.mkdir(parents=True, exist_ok=True)
            state_path = runtime_directory / "autopilot-state.json"

            support = autopilot_module.build_start_runtime_support()
            state = support.new_state(config)
            normalized_state = support.normalize_state_for_lanes(state, config)
            self.assertEqual(normalized_state["active_lane_id"], state["active_lane_id"])

            normalized_state["status"] = "stopped_max_rounds"
            normalized_state["current_round"] = max(int(config["max_rounds"]) - 1, 0)
            resumed_state = support.resume_state_if_threshold_allows(normalized_state, config, state_path)

            self.assertEqual(resumed_state["status"], "active")
            self.assertTrue(state_path.exists())

    def test_no_auto_upgrade_leaves_existing_common_files_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            first_result = run_scaffold(repo_root)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)

            version_path = repo_root / "automation" / "autopilot-scaffold-version.json"
            version_path.write_text(
                json.dumps(
                    {
                        "scaffold_name": "codex-autopilot-scaffold",
                        "scaffold_version": "0.0.1",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            autopilot_path = repo_root / "automation" / "autopilot.py"
            autopilot_path.write_text("# stale controller from old scaffold\n", encoding="utf-8")

            no_upgrade_result = run_scaffold(repo_root, "--no-auto-upgrade")

            self.assertNotEqual(no_upgrade_result.returncode, 0)
            self.assertIn("Refusing to overwrite existing file without --force", no_upgrade_result.stderr)
            self.assertIn("stale controller", autopilot_path.read_text(encoding="utf-8"))
            self.assertEqual(read_version_marker(repo_root)["scaffold_version"], "0.0.1")

    def test_parse_semver_supports_short_forms_and_rejects_invalid_versions(self) -> None:
        scaffold_module = load_scaffold_module()

        self.assertEqual(scaffold_module.parse_semver(""), (0, 0, 0))
        self.assertEqual(scaffold_module.parse_semver("1"), (1, 0, 0))
        self.assertEqual(scaffold_module.parse_semver("1.2"), (1, 2, 0))
        self.assertEqual(scaffold_module.parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(scaffold_module.parse_semver(" 2.4 "), (2, 4, 0))

        with self.assertRaises(scaffold_module.ScaffoldError):
            scaffold_module.parse_semver("1.2.3.4")
        with self.assertRaises(scaffold_module.ScaffoldError):
            scaffold_module.parse_semver("v1.2.3")
        with self.assertRaises(scaffold_module.ScaffoldError):
            scaffold_module.parse_semver("1.two.3")

    def test_detect_commands_from_package_json_scripts(self) -> None:
        result = detect_commands_for_files(
            {
                "package.json": json.dumps(
                    {
                        "scripts": {
                            "lint": "eslint .",
                            "typecheck": "tsc --noEmit",
                            "test": "vitest run",
                            "build": "tsc -p tsconfig.json",
                            "vulture": "vulture src",
                        }
                    },
                    indent=2,
                )
                + "\n",
                "src/index.ts": "export const value = 1;\n",
                "tests/sample.test.ts": "export {};\n",
            }
        )

        self.assertEqual(result.lint_command, "npm run lint")
        self.assertEqual(result.typecheck_command, "npm run typecheck")
        self.assertEqual(result.full_test_command, "npm test")
        self.assertEqual(result.build_command, "npm run build")
        self.assertEqual(result.vulture_command, "npm run vulture")
        self.assertEqual(
            result.targeted_test_prefixes,
            [
                "npm test --",
                "npm run test --",
                "npx jest ",
                "npx vitest ",
                "pnpm test --",
                "pnpm exec jest ",
                "pnpm exec vitest ",
                "yarn test ",
                "yarn jest ",
                "yarn vitest ",
            ],
        )
        self.assertEqual(result.command_sources["lint_command"], "package.json:scripts.lint")
        self.assertEqual(result.command_sources["typecheck_command"], "package.json:scripts.typecheck")
        self.assertEqual(result.command_sources["full_test_command"], "package.json:scripts.test")
        self.assertEqual(result.command_sources["build_command"], "package.json:scripts.build")
        self.assertEqual(result.command_sources["vulture_command"], "package.json:scripts.vulture")

    def test_success_result_with_npx_jest_targeted_tests_is_not_misclassified(self) -> None:
        validation_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
            "_template_validation_targeted_jest_success_test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            phase_doc_path = repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-phase-1.md"
            phase_doc_path.parent.mkdir(parents=True, exist_ok=True)
            phase_doc_path.write_text("# phase 1\n", encoding="utf-8")
            (repo_root / "src").mkdir(exist_ok=True)
            (repo_root / "src" / "demo.ts").write_text("export const demo = 1;\n", encoding="utf-8")
            (repo_root / "tests").mkdir(exist_ok=True)
            (repo_root / "tests" / "demo.test.ts").write_text("export {};\n", encoding="utf-8")
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: round 1 - demo").returncode, 0)
            commit_sha = run_git(repo_root, "rev-parse", "HEAD").stdout.strip()
            commit_message = run_git(repo_root, "log", "-1", "--pretty=%s", commit_sha).stdout.strip()

            warnings: list[str] = []
            result = {
                "status": "success",
                "lane_id": "m1-hotspot-slice",
                "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                "commit_sha": commit_sha,
                "commit_message": commit_message,
                "summary": "demo",
                "next_focus": "",
                "tests_run": ["npx jest --runInBand tests/demo.test.ts"],
                "commands_run": [],
                "build_ran": False,
                "build_id": "",
                "deploy_ran": False,
                "deploy_verified": False,
                "background_tasks_used": False,
                "background_tasks_completed": True,
                "repo_visible_work_landed": True,
                "final_artifacts_written": True,
            }
            config = {
                "commit_prefix": "autopilot",
                "build_command": "",
                "deploy_policy": "never",
                "targeted_test_required": True,
                "targeted_test_required_paths": ["src/", "tests/"],
                "targeted_test_prefixes": ["npm test --", "npm run test --"],
                "full_test_cadence_rounds": 0,
                "full_test_required_paths": [],
            }

            failure_reason = validation_module.validate_round_result(
                attempt_number=1,
                result=result,
                schema={},
                phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                expected_lane_id="m1-hotspot-slice",
                config=config,
                ending_head=commit_sha,
                working_tree_dirty=False,
                support=validation_module.ValidationSupport(
                    clean_string=lambda value: "" if value is None else str(value).strip(),
                    resolve_repo_path=lambda value: repo_root / str(value),
                    run_git=lambda args: run_git(repo_root, *args),
                    info=warnings.append,
                ),
            )

            self.assertIsNone(failure_reason)
            self.assertTrue(any("targeted test warning" in warning.lower() for warning in warnings))

    def test_success_result_still_fails_when_targeted_tests_are_truly_missing(self) -> None:
        validation_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
            "_template_validation_targeted_missing_test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            phase_doc_path = repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-phase-1.md"
            phase_doc_path.parent.mkdir(parents=True, exist_ok=True)
            phase_doc_path.write_text("# phase 1\n", encoding="utf-8")
            (repo_root / "src").mkdir(exist_ok=True)
            (repo_root / "src" / "demo.ts").write_text("export const demo = 1;\n", encoding="utf-8")
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: round 1 - demo").returncode, 0)
            commit_sha = run_git(repo_root, "rev-parse", "HEAD").stdout.strip()
            commit_message = run_git(repo_root, "log", "-1", "--pretty=%s", commit_sha).stdout.strip()

            result = {
                "status": "success",
                "lane_id": "m1-hotspot-slice",
                "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                "commit_sha": commit_sha,
                "commit_message": commit_message,
                "summary": "demo",
                "next_focus": "",
                "tests_run": [],
                "commands_run": [],
                "build_ran": False,
                "build_id": "",
                "deploy_ran": False,
                "deploy_verified": False,
                "background_tasks_used": False,
                "background_tasks_completed": True,
                "repo_visible_work_landed": True,
                "final_artifacts_written": True,
            }
            config = {
                "commit_prefix": "autopilot",
                "build_command": "",
                "deploy_policy": "never",
                "targeted_test_required": True,
                "targeted_test_required_paths": ["src/", "tests/"],
                "targeted_test_prefixes": ["npm test --", "npm run test --"],
                "full_test_cadence_rounds": 0,
                "full_test_required_paths": [],
            }

            failure_reason = validation_module.validate_round_result(
                attempt_number=1,
                result=result,
                schema={},
                phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                expected_lane_id="m1-hotspot-slice",
                config=config,
                ending_head=commit_sha,
                working_tree_dirty=False,
                support=validation_module.ValidationSupport(
                    clean_string=lambda value: "" if value is None else str(value).strip(),
                    resolve_repo_path=lambda value: repo_root / str(value),
                    run_git=lambda args: run_git(repo_root, *args),
                    info=lambda message: None,
                ),
            )

            self.assertIsNotNone(failure_reason)
            self.assertIn("did not report targeted tests", failure_reason)

    def test_success_result_with_pnpm_vitest_targeted_tests_is_not_misclassified(self) -> None:
        validation_module = load_module_from_path(
            SKILL_ROOT / "templates" / "common" / "automation" / "_autopilot" / "validation.py",
            "_template_validation_targeted_pnpm_vitest_success_test",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            phase_doc_path = repo_root / "docs" / "status" / "lanes" / "m1-hotspot-slice" / "autopilot-phase-1.md"
            phase_doc_path.parent.mkdir(parents=True, exist_ok=True)
            phase_doc_path.write_text("# phase 1\n", encoding="utf-8")
            (repo_root / "src").mkdir(exist_ok=True)
            (repo_root / "src" / "demo.ts").write_text("export const demo = 1;\n", encoding="utf-8")
            (repo_root / "tests").mkdir(exist_ok=True)
            (repo_root / "tests" / "demo.test.ts").write_text("export {};\n", encoding="utf-8")
            self.assertEqual(run_git(repo_root, "add", ".").returncode, 0)
            self.assertEqual(run_git(repo_root, "commit", "-m", "autopilot: round 1 - demo").returncode, 0)
            commit_sha = run_git(repo_root, "rev-parse", "HEAD").stdout.strip()
            commit_message = run_git(repo_root, "log", "-1", "--pretty=%s", commit_sha).stdout.strip()

            warnings: list[str] = []
            result = {
                "status": "success",
                "lane_id": "m1-hotspot-slice",
                "phase_doc_path": "docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                "commit_sha": commit_sha,
                "commit_message": commit_message,
                "summary": "demo",
                "next_focus": "",
                "tests_run": ["pnpm exec vitest run tests/demo.test.ts"],
                "commands_run": [],
                "build_ran": False,
                "build_id": "",
                "deploy_ran": False,
                "deploy_verified": False,
                "background_tasks_used": False,
                "background_tasks_completed": True,
                "repo_visible_work_landed": True,
                "final_artifacts_written": True,
            }
            config = {
                "commit_prefix": "autopilot",
                "build_command": "",
                "deploy_policy": "never",
                "targeted_test_required": True,
                "targeted_test_required_paths": ["src/", "tests/"],
                "targeted_test_prefixes": ["npm test --", "npm run test --"],
                "full_test_cadence_rounds": 0,
                "full_test_required_paths": [],
            }

            failure_reason = validation_module.validate_round_result(
                attempt_number=1,
                result=result,
                schema={},
                phase_doc_relative_path="docs/status/lanes/m1-hotspot-slice/autopilot-phase-1.md",
                expected_lane_id="m1-hotspot-slice",
                config=config,
                ending_head=commit_sha,
                working_tree_dirty=False,
                support=validation_module.ValidationSupport(
                    clean_string=lambda value: "" if value is None else str(value).strip(),
                    resolve_repo_path=lambda value: repo_root / str(value),
                    run_git=lambda args: run_git(repo_root, *args),
                    info=warnings.append,
                ),
            )

            self.assertIsNone(failure_reason)
            self.assertTrue(any("targeted test warning" in warning.lower() for warning in warnings))

    def test_detect_commands_from_pyproject_tooling(self) -> None:
        result = detect_commands_for_files(
            {
                "pyproject.toml": """
[tool.ruff]
line-length = 100

[tool.mypy]
python_version = "3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.vulture]
paths = ["src"]
""".strip()
                + "\n",
                "tests/test_sample.py": "def test_ok() -> None:\n    assert True\n",
                "src/app.py": "VALUE = 1\n",
            }
        )

        self.assertEqual(result.lint_command, "ruff check .")
        self.assertEqual(result.typecheck_command, "python -m mypy .")
        self.assertEqual(result.full_test_command, "pytest")
        self.assertEqual(result.vulture_command, "python -m vulture .")
        self.assertEqual(result.targeted_test_prefixes, ["pytest ", "python -m pytest "])
        self.assertEqual(result.command_sources["lint_command"], "pyproject.toml:tool.ruff")
        self.assertEqual(result.command_sources["typecheck_command"], "pyproject.toml:tool.mypy")
        self.assertEqual(result.command_sources["full_test_command"], "pyproject.toml / tests/")
        self.assertEqual(result.command_sources["vulture_command"], "pyproject.toml:tool.vulture")

    def test_detect_commands_from_cargo_toml(self) -> None:
        result = detect_commands_for_files(
            {
                "Cargo.toml": """
[package]
name = "demo"
version = "0.1.0"
edition = "2021"
""".strip()
                + "\n",
                "src/main.rs": "fn main() {}\n",
            }
        )

        self.assertEqual(result.lint_command, "cargo clippy --all-targets --all-features -- -D warnings")
        self.assertEqual(result.typecheck_command, "cargo check")
        self.assertEqual(result.full_test_command, "cargo test")
        self.assertEqual(result.build_command, "cargo build")
        self.assertEqual(result.targeted_test_prefixes, ["cargo test "])
        self.assertEqual(result.command_sources["lint_command"], "Cargo.toml")
        self.assertEqual(result.command_sources["typecheck_command"], "Cargo.toml")
        self.assertEqual(result.command_sources["full_test_command"], "Cargo.toml")
        self.assertEqual(result.command_sources["build_command"], "Cargo.toml")

    def test_detect_commands_from_go_mod(self) -> None:
        result = detect_commands_for_files(
            {
                "go.mod": "module example.com/demo\n\ngo 1.22\n",
                "main.go": "package main\n\nfunc main() {}\n",
            }
        )

        self.assertEqual(result.full_test_command, "go test ./...")
        self.assertEqual(result.build_command, "go build ./...")
        self.assertEqual(result.targeted_test_prefixes, ["go test "])
        self.assertEqual(result.command_sources["full_test_command"], "go.mod")
        self.assertEqual(result.command_sources["build_command"], "go.mod")

    def test_detect_commands_from_makefile_targets(self) -> None:
        result = detect_commands_for_files(
            {
                "Makefile": """
lint:
\t@echo lint

typecheck:
\t@echo typecheck

test:
\t@echo test

build:
\t@echo build
""".strip()
                + "\n",
                "src/app.py": "VALUE = 1\n",
            }
        )

        self.assertEqual(result.lint_command, "make lint")
        self.assertEqual(result.typecheck_command, "make typecheck")
        self.assertEqual(result.full_test_command, "make test")
        self.assertEqual(result.build_command, "make build")
        self.assertEqual(result.command_sources["lint_command"], "Makefile:lint")
        self.assertEqual(result.command_sources["typecheck_command"], "Makefile:typecheck")
        self.assertEqual(result.command_sources["full_test_command"], "Makefile:test")
        self.assertEqual(result.command_sources["build_command"], "Makefile:build")

    def test_detect_commands_from_justfile_targets(self) -> None:
        result = detect_commands_for_files(
            {
                "justfile": """
lint:
    @echo lint

typecheck:
    @echo typecheck

test:
    @echo test

build:
    @echo build
""".strip()
                + "\n",
                "src/app.py": "VALUE = 1\n",
            }
        )

        self.assertEqual(result.lint_command, "just lint")
        self.assertEqual(result.typecheck_command, "just typecheck")
        self.assertEqual(result.full_test_command, "just test")
        self.assertEqual(result.build_command, "just build")
        self.assertEqual(result.command_sources["lint_command"], "justfile:lint")
        self.assertEqual(result.command_sources["typecheck_command"], "justfile:typecheck")
        self.assertEqual(result.command_sources["full_test_command"], "justfile:test")
        self.assertEqual(result.command_sources["build_command"], "justfile:build")

    def test_force_overwrites_existing_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = create_target_repo(Path(temp_dir))
            first_result = run_scaffold(repo_root)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)

            round_prompt_path = repo_root / "automation" / "round-prompt.md"
            round_prompt_path.write_text("# stale prompt that should be replaced\n", encoding="utf-8")

            force_result = run_scaffold(repo_root, "--force")

            self.assertEqual(force_result.returncode, 0, force_result.stderr)
            self.assertNotIn("stale prompt", round_prompt_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
