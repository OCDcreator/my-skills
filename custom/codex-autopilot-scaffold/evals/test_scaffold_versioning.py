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
    module_parent = str(path.parent)
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


def run_scaffold(repo_root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCAFFOLD_SCRIPT),
            "--target-repo",
            str(repo_root),
            "--preset",
            "maintainability",
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
                self.assertTrue((repo_root / "automation" / "_autopilot" / "doctor.py").exists())
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
                        str(repo_root / "automation" / "_autopilot" / "doctor.py"),
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

    def test_older_scaffold_auto_upgrades_common_files_without_overwriting_queue_config(self) -> None:
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
            config["objective"] = "Preserve this project-specific queue objective."
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            upgrade_result = run_scaffold(repo_root)

            self.assertEqual(upgrade_result.returncode, 0, upgrade_result.stderr)
            self.assertIn("auto-upgrade", upgrade_result.stdout)
            upgraded_marker = read_version_marker(repo_root)
            self.assertNotEqual(upgraded_marker["scaffold_version"], "0.0.1")
            self.assertNotIn("stale controller", autopilot_path.read_text(encoding="utf-8"))
            preserved_config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(preserved_config["objective"], "Preserve this project-specific queue objective.")

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
