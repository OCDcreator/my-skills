#!/usr/bin/env python3
"""Focused regression tests for write_pdf_outline.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fitz


SCRIPT = Path(__file__).with_name("write_pdf_outline.py")


class WritePdfOutlineTests(unittest.TestCase):
    def test_toc_page_bookmark_is_inserted_before_content_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            pdf = temp / "book.pdf"
            toc_json = temp / "toc_items.json"
            out_pdf = temp / "book.with-toc.pdf"

            doc = fitz.open()
            for _ in range(6):
                doc.new_page()
            doc.save(pdf)
            doc.close()

            toc_json.write_text(
                json.dumps([{"title": "第一章", "level": 1, "page": 1}], ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--pdf",
                    str(pdf),
                    "--toc-json",
                    str(toc_json),
                    "--printed-page-1-pdf-page",
                    "3",
                    "--toc-page",
                    "2",
                    "--out",
                    str(out_pdf),
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            verify = fitz.open(out_pdf)
            try:
                self.assertEqual(verify.get_toc(), [[1, "目录", 2], [1, "第一章", 3]])
            finally:
                verify.close()


if __name__ == "__main__":
    unittest.main()
