from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
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
            self.assertEqual(refreshed_config["targeted_test_prefixes"], ["npm test --", "npm run test --"])

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
        self.assertEqual(result.targeted_test_prefixes, ["npm test --", "npm run test --"])
        self.assertEqual(result.command_sources["lint_command"], "package.json:scripts.lint")
        self.assertEqual(result.command_sources["typecheck_command"], "package.json:scripts.typecheck")
        self.assertEqual(result.command_sources["full_test_command"], "package.json:scripts.test")
        self.assertEqual(result.command_sources["build_command"], "package.json:scripts.build")
        self.assertEqual(result.command_sources["vulture_command"], "package.json:scripts.vulture")

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
