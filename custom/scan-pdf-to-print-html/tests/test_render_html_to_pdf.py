from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "render_html_to_pdf.py"


def load_module():
    spec = importlib.util.spec_from_file_location("render_html_to_pdf", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_parser_accepts_required_and_optional_args() -> None:
    module = load_module()
    parser = module.build_parser()

    # Required args only — defaults must be set.
    ns = parser.parse_args(["--html", "handout.html", "--pdf", "output.pdf"])
    assert ns.html == "handout.html"
    assert ns.pdf == "output.pdf"
    assert ns.screenshot is None
    assert ns.wait_ms == 1200
    assert ns.viewport_width == 794
    assert ns.viewport_height == 1123

    # All args supplied.
    ns = parser.parse_args(
        [
            "--html",
            "handout.html",
            "--pdf",
            "output.pdf",
            "--screenshot",
            "shot.png",
            "--wait-ms",
            "2000",
            "--viewport-width",
            "800",
            "--viewport-height",
            "1200",
        ]
    )
    assert ns.screenshot == "shot.png"
    assert ns.wait_ms == 2000
    assert ns.viewport_width == 800
    assert ns.viewport_height == 1200


def test_main_errors_when_html_missing(tmp_path: Path) -> None:
    html_path = tmp_path / "nonexistent.html"
    pdf_path = tmp_path / "output.pdf"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html_path),
            "--pdf",
            str(pdf_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    combined_output = (result.stdout + result.stderr).lower()
    assert "not found" in combined_output
    assert "html" in combined_output


def test_playwright_render_skips_when_browser_not_available() -> None:
    """Smoke guard — only runs if Playwright+browser are actually installed."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        import pytest

        pytest.skip("Playwright not installed — skipping real render test")
        return

    # Verify the browser binary is reachable.
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:
        import pytest

        pytest.skip("Chromium browser not available — skipping real render test")
        return

    # The environment is ready; run a minimal render test.
    module = load_module()
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_path = tmp_path / "handout.html"
        html_path.write_text(
            "<!DOCTYPE html>\n"
            '<html data-handout-ready="true">\n'
            "<body><p>Hello render test.</p></body>\n"
            "</html>\n",
            encoding="utf-8",
        )

        pdf_path = tmp_path / "handout.pdf"
        try:
            module.main(
                [
                    "--html",
                    str(html_path),
                    "--pdf",
                    str(pdf_path),
                    "--screenshot",
                    str(tmp_path / "screenshot.png"),
                    "--wait-ms",
                    "500",
                ]
            )
        except SystemExit as exc:
            assert exc.code == 0, f"Render failed with exit code {exc.code}"

        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0
