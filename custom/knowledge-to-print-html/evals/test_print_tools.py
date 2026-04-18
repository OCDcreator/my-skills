from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
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


class PrintToolTests(unittest.TestCase):
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

    def test_review_packets_create_explicit_subagent_prompt_files(self) -> None:
        from review_print_pages import write_review_packets

        with tempfile.TemporaryDirectory() as temp_name:
            temp_dir = Path(temp_name)
            screenshot = temp_dir / "page-1.png"
            screenshot.write_bytes(b"fake png placeholder")
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


if __name__ == "__main__":
    unittest.main()
