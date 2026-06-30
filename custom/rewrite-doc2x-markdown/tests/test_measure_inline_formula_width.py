"""Integration tests for measure_inline_formula_width.py.

These render real formulas via headless Chromium + KaTeX, so they need:
  - Python Playwright + Chromium installed (the scan-pdf-to-print-html skill
    depends on the same; this skill reuses it)
  - Network access for the KaTeX CDN (katex@0.16.11)

If Playwright is missing or the browser cannot launch, the whole module is
skipped (not failed) — this keeps `pytest` green on minimal environments while
exercising the measurement on full environments. Mark with `-m integration`
once a marker is registered; for now the import-skip is the gate.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Skip the whole module if Playwright is unavailable.
if importlib.util.find_spec("playwright") is None:
    pytest.skip("playwright not installed — skipping measure_inline_formula_width integration tests",
                allow_module_level=True)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import measure_inline_formula_width as mif  # noqa: E402


def _can_launch_chromium() -> bool:
    """Probe whether Chromium actually launches in this environment."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
        return True
    except Exception:
        return False


# If the browser binary is missing (e.g. `playwright install chromium` not run),
# skip rather than fail every test.
pytestmark = pytest.mark.skipif(
    not _can_launch_chromium(),
    reason="Chromium could not launch — run `playwright install chromium`",
)


# --- pure-logic tests (no browser) ----------------------------------------

def test_classify_band_three_zones() -> None:
    assert mif.classify_band(50) == "short"
    assert mif.classify_band(464) == "short"        # boundary: exactly 2/3 → short
    assert mif.classify_band(464.1) == "medium"
    assert mif.classify_band(625) == "medium"       # boundary: exactly 90% → medium
    assert mif.classify_band(625.1) == "long"
    assert mif.classify_band(700) == "long"


def test_extract_inline_skips_display_math() -> None:
    md = "inline $a = b$ and display\n$$x = y$$\nmore $c = d$"
    bodies = [b for _, b in mif.extract_inline_formulas(md)]
    assert bodies == ["a = b", "c = d"]   # the $$x = y$$ body must NOT appear


def test_extract_inline_dedup_is_callers_job() -> None:
    # extractor returns per-occurrence; dedup is a CLI flag, not extractor behavior
    md = "$a=1$\n$a=1$"
    bodies = [b for _, b in mif.extract_inline_formulas(md)]
    assert bodies == ["a=1", "a=1"]


# --- browser-backed tests (the real value) --------------------------------

def test_short_formula_measures_short_band() -> None:
    """A trivial chain $a = b = c$ renders well under the 2/3 line — short."""
    widths = mif.measure_widths(["a = b = c"])
    assert widths[0] > 0
    assert mif.classify_band(widths[0]) == "short"


def test_sin_beta_chain_is_short_not_long() -> None:
    """The sin β chain that the old source-char lint false-flagged as 'long'
    (275 source chars) actually renders ~360px — solidly in the SHORT band.
    This is the regression the measurement tool exists to catch."""
    body = (
        r"\sin \beta = \lvert {\cos \langle \mathbf{n}, \overrightarrow{CM}\rangle }\rvert "
        r"= \dfrac{\lvert \mathbf{n} \cdot \overrightarrow{CM}\rvert }{\lvert \mathbf{n}\rvert "
        r"\cdot \lvert \overrightarrow{CM}\rvert } = \dfrac{2}{\sqrt{2} \cdot \sqrt{2 + {k}^{2}}} "
        r"= \dfrac{\sqrt{6}}{3}"
    )
    widths = mif.measure_widths([body])
    assert widths[0] > 0
    band = mif.classify_band(widths[0])
    assert band == "short", f"sin β chain should be SHORT, got {band} ({widths[0]:.1f}px)"


def test_long_vector_decomposition_is_not_short() -> None:
    """A genuine multi-step vector decomposition chain (the full B₁M expansion
    with coordinate substitution) renders wide enough to land in medium or long
    — NOT short. This confirms the tool does flag real long chains (it isn't
    just permissive). Uses the FULL chain from 例2 (renders ~617px)."""
    body = (
        r"\overrightarrow{{B}_{1}M} = \overrightarrow{{B}_{1}B} + \overrightarrow{BM} "
        r"= \overrightarrow{{B}_{1}{A}_{1}} + \overrightarrow{{A}_{1}A} + \overrightarrow{AB} "
        r"+ \dfrac{1}{2}\overrightarrow{BD} = - \dfrac{2}{3}\overrightarrow{AB} "
        r"+ \overrightarrow{{A}_{1}A} + \overrightarrow{AB} + \dfrac{1}{2}\left( "
        r"-\overrightarrow{AB} + \dfrac{3}{2}\overrightarrow{{A}_{1}{D}_{1}}\right)"
    )
    widths = mif.measure_widths([body])
    assert widths[0] > 0
    band = mif.classify_band(widths[0])
    assert band in ("medium", "long"), f"long chain should be medium/long, got {band} ({widths[0]:.1f}px)"
