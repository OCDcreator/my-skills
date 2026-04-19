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
VALIDATOR = SKILL_DIR / "validate_print_layout.py"
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


class PrintToolTests(unittest.TestCase):
    def test_ensure_python_package_installs_missing_dependency_before_retry(self) -> None:
        import validate_print_layout as validator

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
        import validate_print_layout as validator

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

    def test_review_packets_create_explicit_subagent_prompt_files(self) -> None:
        from review_print_pages import write_review_packets

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
            }

            manifest_path = write_review_packets(
                report=report,
                report_path=report_path,
                review_dir=temp_dir / "page-review",
                thresholds=thresholds,
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

    def test_review_validation_keeps_failed_report_for_packet_generation(self) -> None:
        from argparse import Namespace
        from review_print_pages import run_validation

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


if __name__ == "__main__":
    unittest.main()
