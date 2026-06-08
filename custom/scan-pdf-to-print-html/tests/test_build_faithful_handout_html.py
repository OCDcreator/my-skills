from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_faithful_handout_html.py"


def test_builds_a4_html_with_page_split_and_tables(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "# Source Transcript",
                "",
                "## Page 274",
                "",
                "知识盒二 线面平行与面面平行",
                "",
                "一、线面平行判定定理",
                "",
                "| 列 | 内容 |",
                "| --- | --- |",
                "| 1 | 平面外一条直线与此平面内一条直线平行 |",
                "",
                "![图 1](./diagrams/theorem-1.png)",
                "",
                "## Page 275",
                "",
                "二、线面平行性质定理",
                "",
                "文字语言：一条直线与一个平面平行，如果过该直线的平面与此平面相交，那么该直线与交线平行。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
            "--title",
            "测试讲义",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "@page" in html
    assert 'class="sheet"' in html
    assert html.count('class="sheet"') == 2
    assert "源页 274" in html
    assert "源页 275" in html
    assert "<table>" in html
    assert './diagrams/theorem-1.png' in html
    assert "为什么重要" not in html
    assert "Preset:" not in html


def test_includes_mathjax_for_doc2x_latex(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## 知识点二 线面平行与面面平行",
                "",
                r"符号语言：\( a // \alpha , a \subset \beta , \alpha \cap \beta = b \Rightarrow a // b \)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "MathJax" in html
    assert "tex-svg.js" in html
    assert "tex-mml-chtml.js" not in html


def test_images_do_not_get_default_border_frame(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "![图 1](./images/example.png)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "border: none;" in html
    assert "background: transparent;" in html


def test_centers_table_cells_for_text_formula_and_media(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "| 类型 | 内容 |",
                "| --- | --- |",
                r"| 符号语言 | \( a // b \) |",
                "| 图形语言 | ![图 1](./images/example.png) |",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "text-align: center;" in html
    assert "vertical-align: middle;" in html
    assert ".transcript-body td img," in html
    assert 'mjx-container[display="true"][jax="SVG"]' in html


def test_limits_block_centering_to_display_math_in_table_cells(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "| 类型 | 内容 |",
                "| --- | --- |",
                r"| 混合内容 | 设 \( a // b \)，则可得结论。 |",
                r"| 展示公式 | $$a // b$$ |",
                "| 图形语言 | ![图 1](./images/example.png) |",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert '.transcript-body td mjx-container[jax="SVG"] {' not in html
    assert '.transcript-body td .mjx-container[jax="SVG"] {' not in html
    assert ".transcript-body td img," in html
    assert '.transcript-body td mjx-container[display="true"][jax="SVG"]' in html
    assert '.transcript-body td .mjx-container[display="true"][jax="SVG"]' in html


def test_uses_kami_default_paper_tokens(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\nKami token smoke test\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "--bg: #f5f4ed;" in html
    assert "--accent: #1b365d;" in html
    assert "Charter" in html


def test_defines_legacy_ocr_css_variables_in_final_html(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\nLegacy OCR CSS token coverage\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "--desk:" in html
    assert "--ink:" in html
    assert "--paper:" in html
    assert "--line:" in html
    assert "--surface-soft:" in html
    assert "--line-strong:" in html
