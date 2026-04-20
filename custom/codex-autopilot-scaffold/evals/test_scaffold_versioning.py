from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
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
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def load_scaffold_module():
    return load_module_from_path(SCAFFOLD_SCRIPT, "_scaffold_repo_under_test")


def create_target_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "target"
    repo_root.mkdir()
    (repo_root / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
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
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                repo_root = create_target_repo(Path(temp_dir))

                result = run_scaffold(repo_root)

                self.assertEqual(result.returncode, 0, result.stderr)
                marker = read_version_marker(repo_root)
                self.assertEqual(marker["scaffold_name"], "codex-autopilot-scaffold")
                self.assertTrue(marker["scaffold_version"])
                autopilot_text = (repo_root / "automation" / "autopilot.py").read_text(encoding="utf-8")
                self.assertIn("AUTOPILOT_SCAFFOLD_VERSION", autopilot_text)
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

    def test_older_scaffold_auto_upgrades_common_files_without_overwriting_queue_config(self) -> None:
        import tempfile

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
        import tempfile

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

    def test_no_auto_upgrade_leaves_existing_common_files_untouched(self) -> None:
        import tempfile

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

        self.assertEqual(scaffold_module.parse_semver("1"), (1, 0, 0))
        self.assertEqual(scaffold_module.parse_semver("1.2"), (1, 2, 0))
        self.assertEqual(scaffold_module.parse_semver("1.2.3"), (1, 2, 3))

        with self.assertRaises(scaffold_module.ScaffoldError):
            scaffold_module.parse_semver("1.2.3.4")
        with self.assertRaises(scaffold_module.ScaffoldError):
            scaffold_module.parse_semver("v1.2.3")


if __name__ == "__main__":
    unittest.main()
