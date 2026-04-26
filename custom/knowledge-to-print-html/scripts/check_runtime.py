from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

try:
    from .runtime_bootstrap import (
        launch_browser,
        load_playwright,
        load_pymupdf,
        resolve_browser_path,
        resolve_qpdf_path,
    )
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    from runtime_bootstrap import (
        launch_browser,
        load_playwright,
        load_pymupdf,
        resolve_browser_path,
        resolve_qpdf_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the local runtime needed by the print HTML validator.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a short text report.",
    )
    parser.add_argument(
        "--browser-path",
        help="Optional Chrome/Chromium executable path to test.",
    )
    return parser.parse_args()


def version_of(module: Any) -> str | None:
    return getattr(module, "__version__", None)


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": {
            "ok": True,
            "executable": sys.executable,
            "version": platform.python_version(),
        },
        "playwright": {"ok": False},
        "pymupdf": {"ok": False},
        "browser": {"ok": False},
        "qpdf": {"ok": False},
    }

    try:
        sync_playwright = load_playwright(auto_install=False)
        playwright_module = sys.modules.get("playwright")
        result["playwright"] = {
            "ok": True,
            "version": version_of(playwright_module),
        }
    except Exception as exc:
        result["playwright"] = {
            "ok": False,
            "error": str(exc),
            "install": f"{sys.executable} -m pip install playwright",
        }
        sync_playwright = None

    try:
        fitz = load_pymupdf(auto_install=False)
        result["pymupdf"] = {
            "ok": True,
            "version": getattr(fitz, "version", None),
        }
    except Exception as exc:
        result["pymupdf"] = {
            "ok": False,
            "error": str(exc),
            "install": f"{sys.executable} -m pip install pymupdf",
        }

    qpdf_path = resolve_qpdf_path()
    result["qpdf"] = {
        "ok": bool(qpdf_path),
        "path": qpdf_path,
        "install": "winget install -e --id QPDF.QPDF"
        if sys.platform == "win32"
        else "install qpdf with your system package manager",
    }

    browser_path = resolve_browser_path(args.browser_path)
    result["browser"]["resolvedPath"] = browser_path

    if sync_playwright:
        try:
            with sync_playwright() as playwright:
                browser, launched_path = launch_browser(
                    playwright,
                    browser_path=browser_path,
                    auto_install=False,
                )
                browser.close()
            result["browser"] = {
                "ok": True,
                "resolvedPath": launched_path,
                "usesBundledBrowser": launched_path is None,
            }
        except Exception as exc:
            result["browser"].update(
                {
                    "ok": False,
                    "error": str(exc),
                    "install": f"{sys.executable} -m playwright install chromium",
                }
            )

    return result


def required_checks_pass(result: dict[str, Any]) -> bool:
    return all(
        bool(result[name]["ok"])
        for name in ("python", "playwright", "pymupdf", "browser", "qpdf")
    )


def print_text_report(result: dict[str, Any]) -> None:
    labels = [
        ("python", "Python"),
        ("playwright", "Playwright"),
        ("pymupdf", "PyMuPDF"),
        ("browser", "Chromium/browser launch"),
        ("qpdf", "qpdf"),
    ]
    for key, label in labels:
        item = result[key]
        status = "ok" if item["ok"] else "missing"
        detail = item.get("version") or item.get("path") or item.get("resolvedPath")
        print(f"{label}: {status}" + (f" ({detail})" if detail else ""))
        if not item["ok"] and item.get("install"):
            print(f"  install: {item['install']}")


def main() -> int:
    args = parse_args()
    result = build_result(args)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print_text_report(result)
    return 0 if required_checks_pass(result) else 1


if __name__ == "__main__":
    raise SystemExit(main())
