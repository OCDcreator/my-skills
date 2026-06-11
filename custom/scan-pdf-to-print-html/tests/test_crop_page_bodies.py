from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "crop_page_bodies.py"


def load_module():
    spec = importlib.util.spec_from_file_location("crop_page_bodies", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_synthetic_page(path: Path) -> None:
    image = Image.new("L", (1000, 1400), color=255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((120, 30, 880, 70), fill=0)
    draw.rectangle((100, 180, 900, 1180), fill=0)
    draw.rectangle((180, 1320, 820, 1360), fill=0)
    image.save(path)


def test_detect_body_bbox_excludes_header_and_footer_noise(tmp_path: Path) -> None:
    module = load_module()
    page_path = tmp_path / "page-001.png"
    make_synthetic_page(page_path)
    image = Image.open(page_path)

    left, top, right, bottom = module.detect_body_bbox(image)

    assert left <= 120
    assert top >= 120
    assert right >= 880
    assert bottom <= 1260


def test_cli_writes_cropped_pages_and_manifest(tmp_path: Path) -> None:
    pages_dir = tmp_path / "pages"
    out_dir = tmp_path / "body-pages"
    pages_dir.mkdir()
    page_path = pages_dir / "page-001.png"
    make_synthetic_page(page_path)

    manifest = {
        "source_pdf": "synthetic.pdf",
        "page_count": 1,
        "rendered_page_count": 1,
        "dpi": 220,
        "pages": [
            {
                "page_number": 1,
                "image_path": str(page_path),
                "width": 1000,
                "height": 1400,
                "dpi": 220,
            }
        ],
    }
    manifest_path = pages_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--manifest",
            str(manifest_path),
            "--out-dir",
            str(out_dir),
            "--out-pdf",
            str(tmp_path / "body-only.pdf"),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    cropped_manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    cropped_image = out_dir / "page-001.body.png"

    assert cropped_image.exists()
    assert (tmp_path / "body-only.pdf").exists()
    assert cropped_manifest["cropped_page_count"] == 1
    assert cropped_manifest["pages"][0]["body_image_path"].endswith("page-001.body.png")
