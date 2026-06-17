from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_faithful_handout_html.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_faithful_handout_html", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert 'id="handout-source"' in html
    assert 'id="handout-print-root"' in html
    assert html.count('class="source-fragment"') == 2
    assert "源页 274" not in html
    assert "源页 275" not in html
    assert "<table>" in html
    assert './diagrams/theorem-1.png' in html
    assert "为什么重要" not in html
    assert "Preset:" not in html


def test_strips_repeated_margin_header_and_footer_noise_from_pages(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "# Source Transcript",
                "",
                "## Page 274",
                "",
                "MST高中基础知识与二级结论",
                "",
                "真正正文甲",
                "",
                "老唐说题",
                "",
                "## Page 275",
                "",
                "MST高中基础知识与二级结论",
                "",
                "真正正文乙",
                "",
                "老唐说题",
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

    assert "真正正文甲" in html
    assert "真正正文乙" in html
    assert "MST高中基础知识与二级结论" not in html
    assert "老唐说题" not in html


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


def test_mathjax_is_manually_typeset_after_startup(tmp_path: Path) -> None:
    """Pagination must not race MathJax's startup auto-typeset.

    The handout first measures source blocks, paginates them into A4 sheets,
    then exports. If MathJax auto-typesets the source tree while pagination is
    moving nodes, formulas can remain as raw ``$...$`` in the final print root.
    Disable startup auto-typesetting and wait for startup before the explicit
    ``typesetPromise`` call.
    """
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("# T\n\n公式 $x^2+1$。\n", encoding="utf-8")

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

    assert "typeset: false" in html
    assert "MathJax.startup.promise" in html
    assert "await window.MathJax.startup.promise" in html


def test_preserves_inline_latex_from_plain_markdown_paragraphs(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 276",
                "",
                r"（3）记作： \( \alpha \bot \beta \) 。",
                "",
                r"若 \( m // \alpha \)，则 \( \alpha \bot \beta \) 。",
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

    assert r"$ \alpha \bot \beta $" in html
    assert r"$ m // \alpha $" in html
    assert r"( \alpha \bot \beta )" not in html


def test_escapes_angle_brackets_inside_restored_math_segments(tmp_path: Path) -> None:
    """Raw ``<`` inside TeX must not become browser HTML tags.

    Expressions like ``$0<a<2$`` are common in math handouts. The builder
    protects math before MarkdownIt and restores it afterward; restored math
    must be HTML-escaped so the browser gives MathJax a text node instead of
    parsing ``<a``/``<b`` as malformed tags.
    """
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("# T\n\n范围 $0<a<2$，且 $b<\\dfrac{4}{e^2}$。\n", encoding="utf-8")

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

    assert "$0&lt;a&lt;2$" in html
    assert "$b&lt;\\dfrac{4}{e^2}$" in html
    assert "$0<a<2$" not in html


def test_does_not_apply_markdown_emphasis_inside_math_segments(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 278",
                "",
                r"例 5 在正方体 \( {ABCD} - {A}_{1}{B}_{1}{C}_{1}{D}_{1} \) 中, \( E,F \) 分别为 \( {AB},{BC} \) 的中点。",
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

    assert r"{A}_{1}{B}_{1}{C}_{1}{D}_{1}" in html
    assert "<em>" not in html


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
    assert ".transcript-flow td img," in html
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

    assert '.transcript-flow td mjx-container[jax="SVG"] {' not in html
    assert '.transcript-flow td .mjx-container[jax="SVG"] {' not in html
    assert ".transcript-flow td img," in html
    assert '.transcript-flow td mjx-container[display="true"][jax="SVG"]' in html
    assert '.transcript-flow td .mjx-container[display="true"][jax="SVG"]' in html


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

    assert "Vendored Kami tokens define the document language." in html
    assert "--font-body:" in html
    assert "--font-display:" in html
    assert "--paper:" in html


def test_clean_markdown_preserves_tex_delimiters_inside_fenced_code() -> None:
    module = load_module()

    cleaned = module.clean_markdown(
        "\n".join(
            [
                "示例：",
                "",
                "```tex",
                r"\( a // b \)",
                r"\[ x + y \]",
                "```",
                "",
                r"正文里有 \( m // n \) 和 \[ p + q \]",
            ]
        )
    )

    assert "```tex" in cleaned
    assert r"\( a // b \)" in cleaned
    assert r"\[ x + y \]" in cleaned
    assert r"$ m // n $" in cleaned
    assert r"$$ p + q $$" in cleaned


def test_clean_markdown_preserves_tex_delimiters_inside_inline_code_spans() -> None:
    module = load_module()

    cleaned = module.clean_markdown(
        "\n".join(
            [
                r"示例 `\( a // b \)` 和 `\[ x + y \]`",
                "",
                r"正文 \( m // n \) 与 \[ p + q \]",
            ]
        )
    )

    assert r"`\( a // b \)`" in cleaned
    assert r"`\[ x + y \]`" in cleaned
    assert r"$ m // n $" in cleaned
    assert r"$$ p + q $$" in cleaned


def test_clean_markdown_preserves_literal_html_comments_inside_code_examples() -> None:
    module = load_module()

    cleaned = module.clean_markdown(
        "\n".join(
            [
                "正文 <!-- 注释应移除 --> 保留文字",
                "",
                "```html",
                "<!-- code block comment -->",
                "```",
                "",
                "`<!-- inline code comment -->`",
            ]
        )
    )

    assert "<!-- 注释应移除 -->" not in cleaned
    assert "<!-- code block comment -->" in cleaned
    assert "`<!-- inline code comment -->`" in cleaned


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


def test_build_html_document_from_fragments_rejects_full_document_markup() -> None:
    module = load_module()

    try:
        module.build_html_document_from_fragments(
            [
                ("1", "<p>Safe fragment</p>"),
                ("2", "<body><p>Not allowed</p></body>"),
            ],
            title="Fragment Gate",
            source_label="OCR Transcript",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected fragment validation to reject body/html markup")

    assert "page 2" in message.lower()
    assert "<body>" in message


def test_validate_fragment_html_rejects_empty_fragment() -> None:
    module = load_module()

    try:
        module.validate_fragment_html("3", "   \n\t  ")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected empty fragment to be rejected")

    assert "page 3" in message.lower()
    assert "empty" in message.lower()


def test_validate_fragment_html_rejects_raw_markdown_fragment() -> None:
    module = load_module()

    try:
        module.validate_fragment_html("4", "## Raw Markdown Heading")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected raw Markdown fragment to be rejected")

    assert "page 4" in message.lower()
    assert "html" in message.lower()


def test_validate_fragment_html_accepts_rendered_html_fragment() -> None:
    module = load_module()

    fragment = module.validate_fragment_html("5", "  <p>Rendered HTML</p>\n")

    assert fragment == "<p>Rendered HTML</p>"


def test_build_html_document_groups_adjacent_doc2x_images_into_cluster() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "279",
                "\n".join(
                    [
                        '<img src="https://cdn.noedgeai.com/example.jpg?x=465&y=118&w=157&h=170&r=0"/>',
                        '<img src="https://cdn.noedgeai.com/example.jpg?x=741&y=106&w=164&h=186&r=0"/>',
                        '<img src="https://cdn.noedgeai.com/example.jpg?x=1018&y=117&w=155&h=159&r=0"/>',
                    ]
                ),
            )
        ],
        title="Image Cluster",
        source_label="OCR Transcript",
    )

    assert 'class="ocr-image-cluster ocr-image-cluster--3"' in html
    assert html.count('class="ocr-crop-image ocr-crop-image--small"') == 3


def test_build_html_document_groups_split_images_inside_table_cells() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "274",
                '<table><tr><td>图形语言</td><td><img src="https://cdn.noedgeai.com/example.jpg?x=905&y=1533&w=178&h=82&r=0"/> <br>  <img src="https://cdn.noedgeai.com/example.jpg?x=904&y=1626&w=182&h=87&r=0"/></td></tr></table>',
            )
        ],
        title="Table Split Image",
        source_label="OCR Transcript",
    )

    assert 'class="ocr-image-cluster ocr-image-cluster--2"' in html
    assert "<br>" not in html


def test_build_html_document_caps_small_doc2x_crop_images() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "280",
                '<p><img src="https://cdn.noedgeai.com/example.jpg?x=559&y=1102&w=198&h=217&r=0"/></p>',
            )
        ],
        title="Small Crop",
        source_label="OCR Transcript",
    )

    assert ".ocr-crop-image--small {" in html
    assert "max-width: min(100%, 34mm);" in html
    assert 'class="ocr-crop-image ocr-crop-image--small"' in html


def test_build_html_document_emits_flow_pagination_scaffold() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            ("274", "<p>第一页</p>"),
            ("275", "<p>第二页</p>"),
        ],
        title="Fit Shell",
        source_label="OCR Transcript",
    )

    assert 'data-source-page="274"' in html
    assert 'data-source-page="275"' in html
    assert 'id="handout-source"' in html
    assert 'id="handout-print-root"' in html
    assert 'class="source-fragment"' in html


def test_build_html_document_includes_flow_pagination_script_and_css_contract() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [("279", "<p>长页内容</p>")],
        title="Adaptive Fit",
        source_label="OCR Transcript",
    )

    assert "#handout-source {" in html
    assert ".flow-block {" in html
    assert "@media print {" in html
    assert "box-shadow: none;" in html
    assert "#handout-print-root {\n    padding: 0;" in html
    assert "async function paginateHandout()" in html
    assert "collectFlowBlocks" in html
    assert "document.documentElement.dataset.handoutReady" in html


def test_build_html_document_from_fragments_wraps_body_only_fragments() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            ("7", "<h2>第一页片段</h2><p>只允许 body 内容。</p>"),
            ("8", "<div class='note'>第二页片段</div>"),
        ],
        title="Fragment Assembly",
        source_label="Subagent Fragments",
    )

    assert html.startswith("<!DOCTYPE html>")
    assert html.count('class="source-fragment"') == 2
    assert "Subagent Fragments" in html
    assert 'data-title="Fragment Assembly"' in html
    assert 'data-source-label="Subagent Fragments"' in html
    assert "第一页片段" in html
    assert "第二页片段" in html


def test_build_html_document_from_fragments_unwraps_page_level_fragment_wrappers() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "281",
                '<section class="source-page-fragment" data-source-page="281"><h4>例 12</h4><p>正文</p></section>',
            ),
        ],
        title="Fragment Assembly",
        source_label="Subagent Fragments",
    )

    assert html.count('class="source-fragment"') == 1
    assert 'class="source-page-fragment"' not in html
    assert html.count('data-source-page="281"') == 1
    assert "<h4>例 12</h4><p>正文</p>" in html


def test_build_html_document_does_not_render_header_label_or_footer_title_text() -> None:
    module = load_module()

    html = module.build_html_document_from_fragments(
        [("7", "<p>第一页片段</p>")],
        title="Fragment Assembly",
        source_label="Subagent Fragments",
    )

    assert 'class="sheet-header"' not in html
    assert "Subagent Fragments</span>" not in html
    assert "Fragment Assembly</span>" not in html


def test_promotes_fraction_display_style_for_simple_and_nested_math(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                r"简单分式：\( \frac{1}{2} \)",
                "",
                r"复杂分式：\( \frac{a+b}{c} \)",
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

    assert r"\dfrac{1}{2}" in html
    assert r"\tfrac{a+b}{c}" in html
    assert r"\frac{1}{2}" not in html
    assert r"\frac{a+b}{c}" not in html


def test_renders_choice_blockquotes_with_phycat_template_and_even_option_grid(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "> 例 1 已知直线与平面关系，判断正确选项。",
                ">",
                "> - A. 第一项",
                "> - B. 第二项",
                "> - C. 第三项",
                "> - D. 第四项",
                "",
                "解析：利用线面平行判定。",
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

    assert ".phycat-blockquote {" in html
    assert '<blockquote class="phycat-blockquote">' in html
    assert 'class="choice-options"' in html
    assert 'class="choice-option"' in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in html


def test_marks_analysis_paragraphs_and_normalizes_fill_in_blanks(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "填空：直线与平面平行的判定是____。",
                "",
                "解析：先在平面内找到与该直线平行的直线。",
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

    assert "判定是__________。" in html
    assert 'class="lead-para"' in html
    assert 'class="lead-tag">解析</span>' in html


def test_code_blocks_use_centered_preformatted_layout(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "```python",
                "print('line 1')",
                "print('line 2')",
                "```",
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

    assert ".transcript-flow pre code {" in html
    assert "margin: 3mm auto 4mm;" in html
    assert "width: fit-content;" in html


# --- v3 regression tests (problems exposed by the yinlingdian-wenti job) ---


def test_does_not_cluster_images_already_inside_an_author_figure() -> None:
    """Author <figure> elements carry explicit layout (flex, max-width %) and
    must not be collapsed into the 92mm OCR-crop cluster, which shrinks each
    image to ~20mm. Figures are passed through untouched."""
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "1",
                '<figure style="display:flex;justify-content:center;">'
                '<img src="https://example.com/a.webp" alt="图1" style="max-width:45%;height:auto;"/>'
                '<img src="https://example.com/b.webp" alt="图2" style="max-width:45%;height:auto;"/>'
                "</figure>",
            )
        ],
        title="Figure Test",
        source_label="OCR Transcript",
    )

    assert '<span class="ocr-image-cluster' not in html  # no cluster span around the figure
    assert "<figure" in html
    assert html.count("<img") == 2


def test_still_clusters_bare_adjacent_crop_images_not_in_a_figure() -> None:
    """Figure protection must not disable clustering for genuine side-by-side
    Doc2X crops (the original purpose per references/figure-policy.md)."""
    module = load_module()

    html = module.build_html_document_from_fragments(
        [
            (
                "1",
                '<img src="https://cdn.noedgeai.com/example.jpg?x=465&y=118&w=157&h=170&r=0"/>'
                '<img src="https://cdn.noedgeai.com/example.jpg?x=741&y=106&w=164&h=186&r=0"/>',
            )
        ],
        title="Crop Cluster",
        source_label="OCR Transcript",
    )

    assert 'class="ocr-image-cluster ocr-image-cluster--2"' in html


def test_marks_bold_label_analysis_paragraphs(tmp_path: Path) -> None:
    """Hand-authored markdown writes the solution lead-in as '**解析** ...'
    (bold label + space). The detector must catch this, not only '解析：'."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\n**解析** 由题意可知 $a > 0$。\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert 'class="lead-para"' in html
    assert 'class="lead-tag">解析</span>' in html


def test_marks_analysis_and_answer_labels_as_lead_tags(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\n**分析** 先设切点。\n\n**解答** 由题意可得。\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert 'class="lead-tag">分析</span>' in html
    assert 'class="lead-tag">解答</span>' in html


def test_does_not_style_words_that_only_start_with_a_label_prefix(tmp_path: Path) -> None:
    """'解析几何' starts with '解析' but is a noun, not a solution label.
    The boundary check must reject word-continuation false positives."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\n解析几何是高中数学的重要内容。\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert 'class="lead-para"' not in html
    assert 'class="lead-tag"' not in html


def test_dedupes_content_h1_when_it_equals_the_explicit_title(tmp_path: Path) -> None:
    """When --title is passed AND the content opens with a matching '# Title',
    the content H1 must be dropped so the doc-title page header is not
    duplicated (the observed bug: title rendered on two lines)."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("# 隐零点问题\n\n正文开始。\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
            "--title",
            "隐零点问题",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "<h1>隐零点问题</h1>" not in html  # content H1 dropped
    assert 'data-title="隐零点问题"' in html  # still in the page header
    assert "正文开始。" in html


def test_keeps_title_heading_when_it_is_the_only_page_content(tmp_path: Path) -> None:
    """If '# Title' is the ONLY page-1 content, dropping it would leave an
    empty fragment that fails validation. Keep the heading instead."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("# 只有标题\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
            "--title",
            "只有标题",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "<h1>只有标题</h1>" in html  # heading kept so the fragment is non-empty
    assert 'data-title="只有标题"' in html


def test_styles_numbered_method_labels(tmp_path: Path) -> None:
    """Method lead-ins like '**方案一**' / '**法二（…）**' are solution labels
    and should get the analysis styling."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "## Page 1\n\n**方案一**（朗博构造）由此可得结论。\n", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert 'class="lead-para"' in html
    assert 'class="lead-tag">方案一</span>' in html


def test_does_not_style_words_after_method_prefix_without_a_numeral(tmp_path: Path) -> None:
    """'方案设计' / '法案' share the prefix but are not method labels; the
    numeral guard must reject them."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\n方案设计需要考虑多个方面。\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert 'class="lead-para"' not in html
    assert 'class="lead-tag"' not in html


def test_phycat_blockquote_rule_is_scoped_higher_than_base_blockquote_css(tmp_path: Path) -> None:
    """The base print CSS ships `.transcript-flow blockquote` (specificity
    0,1,1). The phycat styling must use a higher-specificity selector
    (`.transcript-flow .phycat-blockquote`, 0,2,0) or its accent border /
    warm surface get overridden and the visual fix silently no-ops."""
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\n> 这是一个题干。\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(source_md), "--out-html", str(out_html)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert ".transcript-flow .phycat-blockquote {" in html
    assert "border-left: 3px solid #1b365d;" in html
