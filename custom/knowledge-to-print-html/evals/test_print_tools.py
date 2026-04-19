from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
import struct


SKILL_DIR = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_DIR / "scripts" / "validate_print_layout.py"
ROOT_VALIDATOR_WRAPPER = SKILL_DIR / "validate_print_layout.py"
ROOT_REVIEW_WRAPPER = SKILL_DIR / "review_print_pages.py"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))


MINIMAL_HANDOUT = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Minimal handout</title>
  <style>
    @page { size: A4; margin: 0; }
    @media print { body { margin: 0; } }
    * { box-sizing: border-box; print-color-adjust: exact; }
    body { margin: 0; background: #eee; font-family: Arial, sans-serif; }
    .sheet {
      width: 210mm;
      height: 297mm;
      margin: 0 auto 12px;
      padding: 18mm;
      background: white;
      break-inside: avoid;
      overflow: hidden;
    }
    figure, .callout { border: 1px solid #ccc; padding: 12px; }
  </style>
</head>
<body>
  <article class="sheet" data-page="1"><h1>Page one</h1><p>Enough text for page one.</p><figure>Readable figure one</figure></article>
  <article class="sheet" data-page="2"><h1>Page two</h1><p>Enough text for page two.</p><figure>Readable figure two</figure></article>
  <article class="sheet" data-page="3"><h1>Page three</h1><p>Enough text for page three.</p><figure>Readable figure three</figure></article>
</body>
</html>
"""

TALL_HANDOUT = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Tall handout</title>
  <style>
    @page { size: A4; margin: 0; }
    @media print { body { margin: 0; } }
    * { box-sizing: border-box; print-color-adjust: exact; }
    body { margin: 0; background: #eee; font-family: Arial, sans-serif; }
    .sheet {
      width: 210mm;
      min-height: 297mm;
      margin: 0;
      padding: 18mm;
      background: white;
      break-inside: avoid;
      overflow: hidden;
    }
    p { font-size: 24px; line-height: 1.7; }
  </style>
</head>
<body>
  <article class="sheet" data-page="1">
    <h1>Too tall</h1>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
    <p>This paragraph is intentionally large to make the sheet grow beyond A4.</p>
  </article>
</body>
</html>
"""

CARD_GRID_HANDOUT = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Card grid handout</title>
  <style>
    @page { size: A4; margin: 0; }
    @media print { body { margin: 0; } }
    * { box-sizing: border-box; print-color-adjust: exact; }
    body { margin: 0; background: #eee; font-family: Arial, sans-serif; }
    .sheet {
      width: 210mm;
      height: 297mm;
      margin: 0;
      padding: 16mm;
      background: white;
      break-inside: avoid;
      overflow: hidden;
    }
    .card-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6mm;
      margin-top: 8mm;
    }
    .card {
      border: 1px solid #cbd5e1;
      padding: 4mm;
      background: #f8fafc;
      font-size: 9px;
      line-height: 1.12;
      min-height: 40mm;
    }
    .card h2 { margin: 0 0 2mm; font-size: 10px; }
    p { margin: 0; }
  </style>
</head>
<body>
  <article class="sheet" data-page="1">
    <h1>OAuth 2.0 + PKCE</h1>
    <p>Based on user-provided notes, this handout summarizes the workflow.</p>
    <div class="card-grid">
      <section class="card"><h2>Client</h2><p>Stores verifier, redirects, exchanges code, retries, and explains every branch in tiny text.</p></section>
      <section class="card"><h2>Browser</h2><p>Handles redirect hops, state checks, callback parsing, and error handling in tiny text.</p></section>
      <section class="card"><h2>Auth Server</h2><p>Validates challenge, issues code, checks verifier, creates tokens, and emits edge-case notes.</p></section>
      <section class="card"><h2>API</h2><p>Consumes bearer tokens, renews sessions, and lists additional implementation caveats in tiny text.</p></section>
    </div>
  </article>
</body>
</html>
"""

SINGLE_CALLOUT_HANDOUT = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Single callout handout</title>
  <style>
    @page { size: A4; margin: 0; }
    @media print { body { margin: 0; } }
    * { box-sizing: border-box; print-color-adjust: exact; }
    body { margin: 0; background: #eee; font-family: Arial, sans-serif; }
    .sheet {
      width: 210mm;
      height: 297mm;
      margin: 0;
      padding: 16mm;
      background: white;
      break-inside: avoid;
      overflow: hidden;
    }
    h1 { margin: 0 0 5mm; }
    p { margin: 0 0 4mm; font-size: 13px; line-height: 1.5; }
    .callout {
      margin: 6mm 0;
      padding: 5mm;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      font-size: 13px;
      line-height: 1.45;
    }
    figure {
      margin: 6mm 0;
      border: 1px solid #ccc;
      padding: 4mm;
      min-height: 52mm;
    }
  </style>
</head>
<body>
  <article class="sheet" data-page="1">
    <h1>PKCE core mental model</h1>
    <p>PKCE prevents stolen authorization codes from being redeemed without the original verifier.</p>
    <div class="callout">A single teaching callout is acceptable when it enlarges one key warning instead of turning the page into a dashboard of micro-cards.</div>
    <p>The browser only carries the code challenge. The verifier stays with the client until the token request.</p>
    <figure>Large readable figure placeholder for the code-challenge to verifier flow.</figure>
    <p>Use the final section to reinforce the attack model and the protection mechanism with normal reading rhythm.</p>
  </article>
</body>
</html>
"""


class PrintToolTests(unittest.TestCase):
    def test_canonical_scripts_directory_and_root_wrappers_exist(self) -> None:
        self.assertTrue((SKILL_DIR / "scripts" / "validate_print_layout.py").exists())
        self.assertTrue((SKILL_DIR / "scripts" / "review_print_pages.py").exists())
        self.assertTrue(ROOT_VALIDATOR_WRAPPER.exists())
        self.assertTrue(ROOT_REVIEW_WRAPPER.exists())

    def test_root_wrappers_only_import_main(self) -> None:
        validator_wrapper = ROOT_VALIDATOR_WRAPPER.read_text(encoding="utf-8")
        review_wrapper = ROOT_REVIEW_WRAPPER.read_text(encoding="utf-8")

        self.assertIn("from scripts.validate_print_layout import main", validator_wrapper)
        self.assertIn("from scripts.review_print_pages import main", review_wrapper)
        self.assertNotIn("import *", validator_wrapper)
        self.assertNotIn("import *", review_wrapper)

    def test_evals_include_machine_checkable_assertions(self) -> None:
        evals = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        for item in evals["evals"]:
            self.assertIn("assertions", item)
            self.assertGreaterEqual(len(item["assertions"]), 3)

    def test_skill_text_defaults_to_comprehensive_research(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("Research every core knowledge point by default", skill_text)
        self.assertIn("Each core knowledge point should usually be researched", skill_text)
        self.assertIn("When comprehensive external research is not possible", skill_text)
        self.assertIn("source support for each core knowledge point", skill_text)
        self.assertNotIn("Use search only for:", skill_text)
        self.assertNotIn("Research fills gaps. It does not replace the user's voice.", skill_text)

    def test_output_contract_requires_research_mode_and_per_point_research_notes(self) -> None:
        contract_text = (SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8")

        self.assertIn("Record the research mode in `brief.md`", contract_text)
        self.assertIn("`comprehensive`", contract_text)
        self.assertIn("`constrained`", contract_text)
        self.assertIn("For each core knowledge point", contract_text)
        self.assertIn("authoritative explanation", contract_text)
        self.assertIn("example, application, or counterexample", contract_text)

    def test_evals_pressure_comprehensive_and_constrained_research_paths(self) -> None:
        evals = json.loads((SKILL_DIR / "evals" / "evals.json").read_text(encoding="utf-8"))
        prompts = [item["prompt"] for item in evals["evals"]]
        expected_outputs = [item["expected_output"] for item in evals["evals"]]

        self.assertTrue(
            any("每条知识点" in prompt or "每个核心知识点" in prompt for prompt in prompts)
        )
        self.assertTrue(
            any("不要联网" in prompt or "只用我给的资料" in prompt for prompt in prompts)
        )
        self.assertTrue(
            any("research.md" in output and "core knowledge point" in output for output in expected_outputs)
        )

    def test_ensure_python_package_installs_missing_dependency_before_retry(self) -> None:
        from scripts import validate_print_layout as validator

        imported_module = object()
        real_import_module = importlib.import_module
        call_names: list[str] = []

        def fake_import_module(name: str, package: str | None = None) -> object:
            if name == "playwright.sync_api":
                call_names.append(name)
                if len(call_names) == 1:
                    raise ImportError("missing")
                return imported_module
            return real_import_module(name, package)

        with mock.patch("subprocess.run") as run:
            with mock.patch("importlib.import_module", side_effect=fake_import_module):
                result = validator.ensure_python_package(
                    "playwright.sync_api",
                    pip_name="playwright",
                    auto_install=True,
                )

        self.assertIs(result, imported_module)
        self.assertEqual(call_names, ["playwright.sync_api", "playwright.sync_api"])
        run.assert_called_once_with(
            [sys.executable, "-m", "pip", "install", "playwright"],
            check=True,
        )

    def test_validate_print_layout_isolates_pages_without_html_query_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(MINIMAL_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "isolated",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (out_dir / "isolated-validation-report.json").read_text(encoding="utf-8")
            )
            visible_counts = [
                page["visibleSheetCount"] for page in report["screenshots"]["pages"]
            ]
            self.assertEqual(visible_counts, [1, 1, 1])
            self.assertTrue(report["optionalChecks"]["pageQueryIsolatesSheets"])

    def test_validate_print_layout_exports_page_pngs_with_a4_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(MINIMAL_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "a4",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (out_dir / "a4-validation-report.json").read_text(encoding="utf-8")
            )
            expected_ratio = 210 / 297
            self.assertTrue(report["checks"]["pageScreenshotsUseA4Aspect"])

            for page in report["screenshots"]["pages"]:
                screenshot_path = Path(page["path"])
                png_bytes = screenshot_path.read_bytes()
                self.assertEqual(png_bytes[:8], b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", png_bytes[16:24])
                actual_ratio = width / height

                self.assertAlmostEqual(actual_ratio, expected_ratio, delta=0.02)
                self.assertLess(height, 2200, "A4 page capture should not use the full viewport height.")

    def test_validate_print_layout_exports_pdf_page_pngs_and_parity_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(MINIMAL_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "pdf-parity",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (out_dir / "pdf-parity-validation-report.json").read_text(encoding="utf-8")
            )

            pdf_page_screenshots = report["pdf"]["screenshots"]["pages"]
            parity_pages = report["parity"]["pages"]

            self.assertEqual(len(pdf_page_screenshots), 3)
            self.assertEqual(len(parity_pages), 3)
            self.assertTrue(report["checks"]["pdfScreenshotsUseA4Aspect"])
            self.assertTrue(report["checks"]["pdfOptimizedForFastView"])
            self.assertTrue(report["checks"]["fastViewPdfPageCountMatchesHtml"])
            self.assertTrue(report["checks"]["fastViewPdfOptimizedForFastView"])
            self.assertTrue(report["pdf"]["optimization"]["linearized"])
            self.assertTrue(Path(report["fastViewPdf"]["path"]).exists())
            self.assertEqual(report["fastViewPdf"]["pageCount"], 3)
            self.assertTrue(report["fastViewPdf"]["optimization"]["linearized"])

            for page in pdf_page_screenshots:
                self.assertTrue(Path(page["path"]).exists())
                self.assertTrue(page["usesA4Aspect"])

            for page in parity_pages:
                self.assertIn("htmlScreenshot", page)
                self.assertIn("pdfScreenshot", page)
                self.assertIn("visualDiffScore", page)
                self.assertTrue(Path(page["htmlScreenshot"]).exists())
                self.assertTrue(Path(page["pdfScreenshot"]).exists())

    def test_validate_print_layout_fails_when_sheet_actual_height_exceeds_a4(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(TALL_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "too-tall",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(
                (out_dir / "too-tall-validation-report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["checks"]["sheetsUseA4Aspect"])
            self.assertGreater(report["analysis"]["sheets"][0]["rect"]["height"], report["analysis"]["sheets"][0]["expectedA4Height"])

    def test_optimize_pdf_for_fast_view_runs_qpdf_linearize(self) -> None:
        from scripts import validate_print_layout as validator

        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            raw_pdf = temp_dir / "raw.pdf"
            final_pdf = temp_dir / "final.pdf"
            raw_pdf.write_bytes(b"%PDF-1.7 raw")

            def fake_run(command: list[str]) -> None:
                self.assertEqual(
                    command,
                    [
                        "qpdf",
                        "--linearize",
                        "--object-streams=generate",
                        str(raw_pdf),
                        str(final_pdf),
                    ],
                )
                final_pdf.write_bytes(b"%PDF-1.7\n/Linearized 1\n/ObjStm 1\n")

            with mock.patch.object(validator, "resolve_qpdf_path", return_value="qpdf"):
                with mock.patch.object(validator, "run_bootstrap_command", side_effect=fake_run):
                    info = validator.optimize_pdf_for_fast_view(
                        raw_pdf,
                        final_pdf,
                        auto_install=True,
                    )

            self.assertTrue(final_pdf.exists())
            self.assertTrue(info["linearized"])
            self.assertTrue(info["objectStreams"])
            self.assertEqual(info["tool"], "qpdf")

    def test_build_flags_detect_card_grid_rhythm_and_meta_leakage(self) -> None:
        from scripts.review_print_pages import build_flags

        page = {
            "page": "1",
            "issueCount": 0,
            "density": {
                "bottomGapRatio": 0.08,
                "contentHeightRatio": 0.82,
            },
            "figures": {
                "largest": {
                    "widthRatio": 0.68,
                    "areaRatio": 0.19,
                }
            },
            "cards": {
                "count": 4,
                "gridLikeCount": 4,
                "totalAreaRatio": 0.43,
                "smallTextCount": 4,
                "overflowCount": 0,
            },
            "typography": {
                "minBodyFontSizePx": 10.2,
                "minLineHeightRatio": 1.14,
                "minParagraphSpacingRatio": 0.18,
            },
            "meta": {
                "candidateCount": 1,
                "candidates": [
                    {
                        "kind": "provenance",
                        "text": "Based on user-provided notes",
                    }
                ],
            },
        }
        thresholds = {
            "max_bottom_gap_ratio": 0.22,
            "min_content_height_ratio": 0.58,
            "min_figure_width_ratio": 0.50,
            "min_figure_area_ratio": 0.10,
            "max_card_grid_count": 2,
            "max_card_area_ratio": 0.35,
            "min_card_text_size_px": 11.0,
            "min_body_font_size_px": 11.5,
            "min_body_line_height_ratio": 1.35,
            "min_paragraph_spacing_ratio": 0.45,
        }
        flags = build_flags(
            page=page,
            thresholds=thresholds,
            screenshot={"visibleSheetCount": 1},
            pdf_screenshot={"usesA4Aspect": True},
            parity={"visualDiffScore": 0.01, "sameDimensions": True},
        )

        codes = {flag["code"] for flag in flags}
        self.assertIn("card_grid_antipattern", codes)
        self.assertIn("compressed_typographic_rhythm", codes)
        self.assertIn("meta_leakage_candidate", codes)

    def test_build_flags_do_not_fail_single_large_callout(self) -> None:
        from scripts.review_print_pages import build_flags

        page = {
            "page": "1",
            "issueCount": 0,
            "density": {
                "bottomGapRatio": 0.09,
                "contentHeightRatio": 0.76,
            },
            "figures": {
                "largest": {
                    "widthRatio": 0.73,
                    "areaRatio": 0.20,
                }
            },
            "cards": {
                "count": 1,
                "gridLikeCount": 0,
                "totalAreaRatio": 0.12,
                "smallTextCount": 0,
                "overflowCount": 0,
            },
            "typography": {
                "minBodyFontSizePx": 12.8,
                "minLineHeightRatio": 1.48,
                "minParagraphSpacingRatio": 0.72,
            },
            "meta": {
                "candidateCount": 0,
                "candidates": [],
            },
        }
        thresholds = {
            "max_bottom_gap_ratio": 0.22,
            "min_content_height_ratio": 0.58,
            "min_figure_width_ratio": 0.50,
            "min_figure_area_ratio": 0.10,
            "max_card_grid_count": 2,
            "max_card_area_ratio": 0.35,
            "min_card_text_size_px": 11.0,
            "min_body_font_size_px": 11.5,
            "min_body_line_height_ratio": 1.35,
            "min_paragraph_spacing_ratio": 0.45,
        }
        flags = build_flags(
            page=page,
            thresholds=thresholds,
            screenshot={"visibleSheetCount": 1},
            pdf_screenshot={"usesA4Aspect": True},
            parity={"visualDiffScore": 0.01, "sameDimensions": True},
        )

        codes = {flag["code"] for flag in flags}
        self.assertNotIn("card_grid_antipattern", codes)
        self.assertNotIn("compressed_typographic_rhythm", codes)
        self.assertNotIn("meta_leakage_candidate", codes)

    def test_review_packets_create_explicit_subagent_prompt_files(self) -> None:
        from scripts.review_print_pages import write_review_packets

        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            screenshot = temp_dir / "page-1.png"
            screenshot.write_bytes(b"fake png placeholder")
            pdf_screenshot = temp_dir / "page-1-pdf.png"
            pdf_screenshot.write_bytes(b"fake png placeholder")
            report_path = temp_dir / "report.json"
            report = {
                "htmlPath": str(temp_dir / "handout.html"),
                "validationReport": str(report_path),
                "screenshots": {
                    "pages": [
                        {
                            "page": 1,
                            "path": str(screenshot),
                            "visibleSheetCount": 1,
                        }
                    ]
                },
                "pdf": {
                    "screenshots": {
                        "pages": [
                            {
                                "page": 1,
                                "path": str(pdf_screenshot),
                                "usesA4Aspect": True,
                            }
                        ]
                    }
                },
                "parity": {
                    "pages": [
                        {
                            "page": 1,
                            "htmlScreenshot": str(screenshot),
                            "pdfScreenshot": str(pdf_screenshot),
                            "visualDiffScore": 0.013,
                            "matchSuggested": True,
                        }
                    ]
                },
                "analysis": {
                    "sheets": [
                        {
                            "page": "1",
                            "overflow": {"x": 0, "y": 0},
                            "issueCount": 0,
                            "density": {
                                "bottomGapRatio": 0.12,
                                "contentHeightRatio": 0.72,
                            },
                            "figures": {
                                "largest": {
                                    "widthRatio": 0.72,
                                    "areaRatio": 0.18,
                                }
                            },
                        }
                    ]
                },
            }
            thresholds = {
                "max_bottom_gap_ratio": 0.22,
                "min_content_height_ratio": 0.58,
                "min_figure_width_ratio": 0.50,
                "min_figure_area_ratio": 0.10,
                "max_card_grid_count": 2,
                "max_card_area_ratio": 0.35,
                "min_card_text_size_px": 11.0,
                "min_body_font_size_px": 11.5,
                "min_body_line_height_ratio": 1.35,
                "min_paragraph_spacing_ratio": 0.45,
            }

            manifest_path = write_review_packets(
                report=report,
                report_path=report_path,
                review_dir=temp_dir / "page-review",
                thresholds=thresholds,
                review_language="en",
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            page = manifest["pages"][0]
            prompt_path = Path(page["subagentPromptPath"])

            self.assertTrue(manifest["subagentRequired"])
            self.assertEqual(manifest["nextPageToReview"], 1)
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("REQUIRED: You are a page-review subagent", prompt_text)
            self.assertIn("Do not edit files", prompt_text)
            self.assertIn("Return only JSON", prompt_text)
            self.assertEqual(page["htmlScreenshot"], str(screenshot))
            self.assertEqual(page["pdfScreenshot"], str(pdf_screenshot))
            self.assertEqual(page["parity"]["visualDiffScore"], 0.013)
            self.assertIn("Compare the HTML page screenshot against the PDF page screenshot", prompt_text)
            self.assertIn("Fail if the PDF export changes layout, spacing, scaling, clipping, or missing content", prompt_text)
            self.assertIn("Prefer fixes that rebalance content, merge or split blocks, or enlarge teaching visuals", prompt_text)
            self.assertIn("Do not suggest shrinking font size, line height, or paragraph spacing as the primary fix", prompt_text)

    def test_review_packets_can_emit_chinese_subagent_prompt(self) -> None:
        from scripts.review_print_pages import build_subagent_prompt_with_language

        prompt_text = build_subagent_prompt_with_language(
            {
                "page": 1,
                "htmlScreenshot": "html.png",
                "pdfScreenshot": "pdf.png",
                "parity": {"visualDiffScore": 0.01},
                "heuristicFlags": [],
            },
            review_language="zh",
        )

        self.assertIn("你是逐页审版子代理", prompt_text)
        self.assertIn("只返回 JSON", prompt_text)
        self.assertIn("HTML 截图", prompt_text)
        self.assertIn("优先建议重排内容、合并或拆分区块、放大教学图", prompt_text)
        self.assertIn("不要把缩小字号、压缩行距或段距当作首选修复", prompt_text)

    def test_review_validation_keeps_failed_report_for_packet_generation(self) -> None:
        from argparse import Namespace
        from scripts.review_print_pages import run_validation

        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(MINIMAL_HANDOUT, encoding="utf-8")
            report_path = out_dir / "handout-validation-report.json"
            out_dir.mkdir()
            report_path.write_text('{"pass": false}', encoding="utf-8")

            args = Namespace(
                out_dir=str(out_dir),
                browser_path=None,
            )
            error = subprocess.CalledProcessError(1, ["validator"])
            with mock.patch("subprocess.run", side_effect=error):
                result = run_validation(args, html_path, "handout")

            self.assertEqual(result, report_path)

    def test_validate_print_layout_reports_card_grid_antipattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(CARD_GRID_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "card-grid",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            report = json.loads(
                (out_dir / "card-grid-validation-report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(report["checks"]["avoidsCardGridAntipattern"])
            self.assertFalse(report["checks"]["avoidsMetaLeakageCandidates"])
            self.assertFalse(report["checks"]["maintainsComfortableTypographicRhythm"])
            self.assertGreaterEqual(report["analysis"]["sheets"][0]["cards"]["gridLikeCount"], 4)
            self.assertGreaterEqual(report["analysis"]["sheets"][0]["meta"]["candidateCount"], 1)

    def test_validate_print_layout_allows_single_callout_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            html_path = temp_dir / "handout.html"
            out_dir = temp_dir / "screens"
            html_path.write_text(SINGLE_CALLOUT_HANDOUT, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--html",
                    str(html_path),
                    "--out-dir",
                    str(out_dir),
                    "--prefix",
                    "single-callout",
                    "--settle-ms",
                    "0",
                ],
                cwd=SKILL_DIR,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(
                (out_dir / "single-callout-validation-report.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["checks"]["avoidsCardGridAntipattern"])
            self.assertTrue(report["checks"]["avoidsMetaLeakageCandidates"])
            self.assertTrue(report["checks"]["maintainsComfortableTypographicRhythm"])


if __name__ == "__main__":
    unittest.main()
