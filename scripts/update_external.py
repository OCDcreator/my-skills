#!/usr/bin/env python3
"""Unified external source updater for my-skills.

Reads config/sources.yaml as the single source of truth,
clones repos, copies skills, and commits/pushes changes.

This replaces the duplicated logic in update.sh and update.ps1.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
SOURCES_YAML = ROOT / "config" / "sources.yaml"
TMP_DIR = ROOT / ".tmp-skills"

# Paths that the updater is allowed to stage for commit (P0-1)
ALLOWED_COMMIT_PATHS = ["external/", "SKILLS.md", "docs/full-catalog.md", "README.md"]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def read_sources() -> tuple[list[dict], list[dict], list[str]]:
    """Read sources.yaml and return (skill_sources, reference_sources, exclude_names)."""
    if not SOURCES_YAML.exists():
        print(f"ERROR: {SOURCES_YAML} not found.")
        sys.exit(1)
    data = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    return (
        data.get("skill_sources", []),
        data.get("reference_sources", []),
        data.get("exclude_names", []),
    )


def clone_repo(url: str, branch: str, dest: Path) -> bool:
    """Clone a git repo. Returns True on success."""
    if dest.exists():
        shutil.rmtree(dest)
    try:
        run(["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)])
        return True
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Clone failed: {e.stderr.strip()}")
        return False


def remove_git_dir(path: Path) -> None:
    """Remove .git directory from cloned repo."""
    git_dir = path / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)


def should_exclude(name: str, exclude_names: list[str]) -> bool:
    """Check if a skill name matches any exclude pattern."""
    for ex in exclude_names:
        if name.startswith(ex):
            return True
    return False


def copy_skills(source_dir: Path, target_dir: Path, exclude_names: list[str], mode: str = "flatten") -> int:
    """Copy skill directories containing SKILL.md from source to target.

    Uses atomic swap via a staging directory: if copy succeeds and produces
    content, the old target is replaced atomically. If copy fails or produces
    zero skills, the existing target is left untouched.

    Returns number of skills copied.
    """
    if not source_dir.exists():
        return 0

    # P0-2: Copy to staging directory first for atomic swap
    staging_dir = target_dir.parent / f"{target_dir.name}.staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    if mode == "preserve":
        # Preserve relative path structure
        preserved_dir = staging_dir / source_dir.name
        preserved_dir.mkdir(parents=True)
        for item in source_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, preserved_dir / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, preserved_dir / item.name)

        # Also copy support files from clone root
        clone_root = source_dir.parent
        for support_dir in ["agents", "agents-codex", "scripts"]:
            src = clone_root / support_dir
            if src.exists():
                shutil.copytree(src, staging_dir / support_dir, dirs_exist_ok=True)
        for support_file in ["README.md", "README.zh.md", "LICENSE", "workflow.png"]:
            src = clone_root / support_file
            if src.exists():
                shutil.copy2(src, staging_dir / support_file)

        copied = len(list(source_dir.rglob("SKILL.md")))
    else:
        # Standard flatten mode
        copied = 0
        for skill_md in sorted(source_dir.rglob("SKILL.md")):
            skill_dir = skill_md.parent
            skill_name = skill_dir.name

            if should_exclude(skill_name, exclude_names):
                continue

            if skill_dir == source_dir or skill_name == ".":
                # Root-level skills: copy contents directly
                for item in skill_dir.iterdir():
                    if item.name == ".git":
                        continue
                    dest = staging_dir / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
                copied += 1
            else:
                # Nested skills: copy the directory
                dest = staging_dir / skill_name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(skill_dir, dest)
                copied += 1

    # P0-2: Atomic swap — only replace target if we have content
    if copied > 0:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        staging_dir.rename(target_dir)
    else:
        shutil.rmtree(staging_dir)

    return copied


def copy_reference(source_dir: Path, target_dir: Path) -> int:
    """Copy reference directories (non-skill sources).

    Uses atomic swap via a staging directory: if copy succeeds and produces
    content, the old target is replaced atomically. If copy fails or produces
    zero references, the existing target is left untouched.

    Returns number of reference directories copied.
    """
    if not source_dir.exists():
        return 0

    # P0-2: Copy to staging directory first for atomic swap
    staging_dir = target_dir.parent / f"{target_dir.name}.staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    copied = 0
    for ref_dir in sorted(source_dir.iterdir()):
        if ref_dir.is_dir():
            dest = staging_dir / ref_dir.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(ref_dir, dest)
            copied += 1

    # P0-2: Atomic swap — only replace target if we have content
    if copied > 0:
        if target_dir.exists():
            shutil.rmtree(target_dir)
        staging_dir.rename(target_dir)
    else:
        shutil.rmtree(staging_dir)

    return copied


def git_commit_and_push() -> tuple[str, str]:
    """Stage, commit, and push changes. Returns (status, detail).

    P0-1: Only stages allowed paths (external/, SKILLS.md, docs/full-catalog.md,
    README.md). Unrelated uncommitted changes are detected and warned about but
    are never staged.
    """
    # P0-1: Preflight — detect unrelated uncommitted changes
    try:
        result = run(["git", "status", "--porcelain"], cwd=ROOT, check=False)
        unrelated = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # git status --porcelain format: XY filename (3 chars of status + space, then path)
            if len(line) > 3 and line[2] == " ":
                filepath = line[3:].strip()
                # Handle renamed files: "R  old -> new"
                if " -> " in filepath:
                    filepath = filepath.split(" -> ")[-1]
                # Check if file is under any allowed path
                is_allowed = any(
                    filepath == allowed.rstrip("/")
                    or filepath.startswith(allowed)
                    for allowed in ALLOWED_COMMIT_PATHS
                )
                if not is_allowed:
                    unrelated.append(filepath)
        if unrelated:
            print("[WARN] Unrelated uncommitted changes detected outside allowed paths:")
            for f in unrelated:
                print(f"       {f}")
            print("[WARN] These changes will NOT be committed. Only "
                  "external/, SKILLS.md, docs/full-catalog.md, README.md are staged.")
            print()
    except subprocess.CalledProcessError:
        pass

    # P0-1: Stage only allowed paths (not git add -A)
    for path in ALLOWED_COMMIT_PATHS:
        try:
            run(["git", "add", path], cwd=ROOT, check=False)
        except subprocess.CalledProcessError:
            pass  # Path may not exist yet (e.g., first run)

    # Check if there are any staged changes
    result = run(["git", "diff", "--cached", "--quiet"], cwd=ROOT, check=False)
    if result.returncode == 0:
        return "NO_CHANGES", "No changes to commit."

    # Commit
    commit_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"sync external resources {commit_ts}"
    try:
        run(["git", "commit", "-m", commit_msg], cwd=ROOT)
    except subprocess.CalledProcessError as e:
        return "ERROR", f"git commit failed: {e.stderr.strip()}"

    # Push
    try:
        branch = run(["git", "branch", "--show-current"], cwd=ROOT).stdout.strip() or "main"
        run(["git", "push", "origin", branch], cwd=ROOT)
        return "SUCCESS", f"Committed and pushed: {commit_msg}"
    except subprocess.CalledProcessError as e:
        return "ERROR", f"git push failed: {e.stderr.strip()}"


def run_validation() -> tuple[bool, str]:
    """Run structure verification and catalog generation before commit.
    
    Returns (success, error_message).
    """
    print("\n[Validate] Running structure verification...")
    try:
        result = subprocess.run(
            ["python3", "scripts/verify_structure.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False, f"verify_structure.py failed:\n{result.stdout}\n{result.stderr}"
        print("[Validate] Structure verification passed.")
    except Exception as e:
        return False, f"verify_structure.py could not run: {e}"
    
    print("[Validate] Running catalog generation...")
    try:
        result = subprocess.run(
            ["python3", "scripts/generate_skills_catalog.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False, f"generate_skills_catalog.py failed:\n{result.stdout}\n{result.stderr}"
        print("[Validate] Catalog generation passed.")
    except Exception as e:
        return False, f"generate_skills_catalog.py could not run: {e}"
    
    return True, ""


def main() -> int:
    print("=" * 60)
    print("my-skills external resource updater (Python)")
    print("=" * 60)
    print()

    # Check git
    try:
        run(["git", "--version"])
    except subprocess.CalledProcessError:
        print("ERROR: Git not found.")
        return 1

    # Check we're in a git repo
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT)
    except subprocess.CalledProcessError:
        print("ERROR: Not inside a git repository.")
        return 1

    # Read config
    skill_sources, reference_sources, exclude_names = read_sources()
    print(f"Loaded {len(skill_sources)} skill sources and {len(reference_sources)} reference sources from {SOURCES_YAML}")
    print(f"Exclude patterns: {exclude_names}")
    print()

    # Clean temp dir
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    source_errors = 0
    total_skills = 0
    processing_error = False

    # P2-1: try/finally ensures TMP_DIR is always cleaned up
    try:
        # Process skill sources
        print("[Skill Sources]")
        for i, src in enumerate(skill_sources, 1):
            name = src["name"]
            url = src["repo"]
            branch = src.get("branch", "main")
            subdir = src.get("subdir", ".")
            mode = src.get("mode", "flatten")

            print(f"\n[{i}/{len(skill_sources)}] {name}")
            clone_dir = TMP_DIR / name

            if not clone_repo(url, branch, clone_dir):
                source_errors += 1
                continue

            remove_git_dir(clone_dir)

            source_path = clone_dir / subdir if subdir != "." else clone_dir
            if not source_path.exists():
                print(f"[WARN] Source subdir not found: {source_path}")
                source_errors += 1
                continue

            target_dir = ROOT / "external" / name
            copied = copy_skills(source_path, target_dir, exclude_names, mode)
            total_skills += copied
            print(f"[OK] Copied {copied} skills to external/{name}/")

        # Process reference sources
        if reference_sources:
            print("\n[Reference Sources]")
            for i, src in enumerate(reference_sources, 1):
                name = src["name"]
                url = src["repo"]
                branch = src.get("branch", "main")
                subdir = src.get("subdir", ".")

                print(f"\n[{i}/{len(reference_sources)}] {name}")
                clone_dir = TMP_DIR / name

                if not clone_repo(url, branch, clone_dir):
                    source_errors += 1
                    continue

                remove_git_dir(clone_dir)

                source_path = clone_dir / subdir if subdir != "." else clone_dir
                if not source_path.exists():
                    print(f"[WARN] Source subdir not found: {source_path}")
                    source_errors += 1
                    continue

                target_dir = ROOT / "external" / name
                copied = copy_reference(source_path, target_dir)
                print(f"[OK] Copied {copied} reference directories to external/{name}/")

    except Exception as e:
        print(f"\n[ERROR] Unexpected error during processing: {e}")
        import traceback
        traceback.print_exc()
        processing_error = True
    finally:
        # P2-1: Always clean up temp directory
        if TMP_DIR.exists():
            shutil.rmtree(TMP_DIR)
        print("\n[OK] Temporary directory cleaned")

    if processing_error:
        return 1

    # Run validation before committing
    valid, error = run_validation()
    if not valid:
        print(f"\n[ERROR] Validation failed: {error}")
        print("[ERROR] Commit aborted due to validation failure.")
        return 1

    # Commit and push
    print("\n[Git] Committing and pushing...")
    status, detail = git_commit_and_push()

    print()
    print("=" * 60)
    print(f"Status: {status}")
    print(f"Detail: {detail}")
    if source_errors:
        print(f"Source errors: {source_errors}")
    print("=" * 60)

    # P0-3: source_errors must affect exit code
    return 0 if (status in ("SUCCESS", "NO_CHANGES") and source_errors == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
