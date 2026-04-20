from __future__ import annotations

import glob
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

def run_bootstrap_command(command: list[str]) -> None:
    subprocess.run(command, check=True)

def ensure_python_package(
    import_name: str,
    *,
    pip_name: str,
    auto_install: bool,
) -> Any:
    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        if not auto_install:
            raise RuntimeError(
                f"Missing Python dependency `{pip_name}`. "
                f"Install it with: {' '.join([sys.executable, '-m', 'pip', 'install', pip_name])}"
            ) from exc

    run_bootstrap_command([sys.executable, "-m", "pip", "install", pip_name])

    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Automatic installation finished, but `{pip_name}` still could not be imported."
        ) from exc

def try_install_system_browser() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.extend(
            [
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Microsoft.Edge",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Google.Chrome",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.extend(
            [
                ["brew", "install", "--cask", "microsoft-edge"],
                ["brew", "install", "--cask", "google-chrome"],
            ]
        )
    elif shutil.which("apt-get"):
        commands.extend(
            [
                ["apt-get", "install", "-y", "chromium-browser"],
                ["apt-get", "install", "-y", "chromium"],
            ]
        )

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        browser_path = resolve_browser_path(None)
        if browser_path:
            return browser_path

    return None

def resolve_qpdf_path() -> str | None:
    candidates = [
        shutil.which("qpdf"),
        r"C:\Program Files\qpdf\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf\bin\qpdf.exe",
        "/opt/homebrew/bin/qpdf",
        "/usr/local/bin/qpdf",
        "/usr/bin/qpdf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    glob_patterns = [
        r"C:\Program Files\qpdf*\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf*\bin\qpdf.exe",
        str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/QPDF.QPDF_*" / "*" / "qpdf.exe"),
    ]
    for pattern in glob_patterns:
        matches = sorted(glob.glob(pattern))
        for match in matches:
            if Path(match).exists():
                return str(Path(match))
    return None

def try_install_qpdf() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.append(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "QPDF.QPDF",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.append(["brew", "install", "qpdf"])
    elif shutil.which("apt-get"):
        commands.append(["apt-get", "install", "-y", "qpdf"])

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        qpdf_path = resolve_qpdf_path()
        if qpdf_path:
            return qpdf_path

    return None

def ensure_playwright_runtime(auto_install: bool) -> None:
    if not auto_install:
        return
    run_bootstrap_command([sys.executable, "-m", "playwright", "install", "chromium"])

def load_playwright(auto_install: bool) -> Any:
    module = ensure_python_package(
        "playwright.sync_api",
        pip_name="playwright",
        auto_install=auto_install,
    )
    return module.sync_playwright

def load_pymupdf(auto_install: bool) -> Any:
    return ensure_python_package(
        "fitz",
        pip_name="pymupdf",
        auto_install=auto_install,
    )

def resolve_browser_path(explicit_path: str | None) -> str | None:
    candidates = [
        explicit_path,
        os.environ.get("PLAYWRIGHT_CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    return None

def launch_browser(playwright: Any, *, browser_path: str | None, auto_install: bool) -> tuple[Any, str | None]:
    launch_kwargs: dict[str, Any] = {"headless": True}
    if browser_path:
        launch_kwargs["executable_path"] = browser_path

    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as first_error:
        if not auto_install:
            raise

    ensure_playwright_runtime(auto_install=True)
    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as second_error:
        fallback_browser_path = resolve_browser_path(None) or try_install_system_browser()
        if fallback_browser_path:
            return (
                playwright.chromium.launch(
                    headless=True,
                    executable_path=fallback_browser_path,
                ),
                fallback_browser_path,
            )
        raise RuntimeError(
            "Unable to launch Chromium even after automatic Playwright/browser provisioning."
        ) from second_error
