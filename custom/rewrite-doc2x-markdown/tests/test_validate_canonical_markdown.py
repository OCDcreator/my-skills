from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_canonical_markdown.py"


def run_validator(tmp_path: Path, markdown: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text(markdown, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


def run_job_validator(tmp_path: Path, source_markdown: str, doc2x_markdown: str, plan: str | None = None) -> subprocess.CompletedProcess[str]:
    job_dir = tmp_path / "job"
    export_dir = job_dir / "doc2x" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "source-transcript.md").write_text(source_markdown, encoding="utf-8")
    (export_dir / "export.md").write_text(doc2x_markdown, encoding="utf-8")
    (job_dir / "job.json").write_text("{}\n", encoding="utf-8")
    if plan is not None:
        (job_dir / "markdown-rewrite-plan.md").write_text(plan, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--job-dir", str(job_dir)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_accepts_continuous_question_callout_and_compact_html_analysis_block(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何基础知识与二级结论

## 线面平行与面面平行

> [!question] 题干
> 已知 $a \\parallel \\alpha$，求下列结论。
>
> <div class="choice-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.2rem 0.8rem;">
> <span>A. <math><mi>a</mi><mo>∥</mo><mi>b</mi></math></span><span>B. <math><mi>a</mi><mo>⊥</mo><mi>b</mi></math></span>
> </div>

<div class="analysis-block" style="border:1px solid #d0d7de;border-left:4px solid #57606a;border-radius:6px;padding:0.7rem 0.85rem;margin:0.8rem 0;background:#f6f8fa;">
  <div style="font-weight:600;margin-bottom:0.35rem;">解析</div>
  <p style="margin:0.35rem 0;">先由线面平行得到辅助平面内的平行关系，再结合交线性质推出结论。</p>
  <p style="margin:0.35rem 0;">因此应选择 A。</p>
</div>

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr><td style="vertical-align:middle;">文字语言</td><td style="vertical-align:middle;">内容</td></tr>
</table>

<figure style="text-align:center;">
  <img src="doc2x/export/images/example.jpg" alt="例题图" style="max-width:72%;height:auto;display:block;margin:0 auto;" />
</figure>

公式：$\\dfrac{1}{2} + \\dfrac{\\tfrac{1}{2}}{3}$
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK:" in result.stdout


def test_rejects_callout_or_quote_split_by_bare_blank_line(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> [!question] 题干
> 第一行

> 第二行仍然想属于同一个题干
""",
    )

    assert result.returncode == 1
    assert "bare blank line splits a blockquote or callout" in result.stdout


def test_rejects_analysis_outside_html_analysis_block(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

### 例 1

解析：Doc2X 把解析直接输出成普通段落。
""",
    )

    assert result.returncode == 1
    assert "question analysis must use an HTML analysis-block" in result.stdout


def test_rejects_analysis_markdown_quote(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> 解析：旧格式使用引用块。
""",
    )

    assert result.returncode == 1
    assert "not a Markdown blockquote" in result.stdout


def test_rejects_analysis_block_with_too_many_scattered_paragraphs(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<div class="analysis-block" style="border:1px solid #d0d7de;border-left:4px solid #57606a;border-radius:6px;padding:0.7rem 0.85rem;margin:0.8rem 0;background:#f6f8fa;">
  <div style="font-weight:600;margin-bottom:0.35rem;">解析</div>
  <p>第一行。</p>
  <p>第二行。</p>
  <p>第三行。</p>
  <p>第四行。</p>
  <p>第五行。</p>
  <p>第六行。</p>
  <p>第七行。</p>
  <p>第八行。</p>
  <p>第九行。</p>
  <p>第十行。</p>
  <p>第十一行。</p>
  <p>第十二行。</p>
  <p>第十三行。</p>
</div>
""",
    )

    assert result.returncode == 1
    assert "analysis block is too scattered" in result.stdout


def test_rejects_analysis_block_without_visible_border_style(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<div class="analysis-block" style="padding:0.7rem 0.85rem;">
  <div>解析</div>
  <p>缺少边框。</p>
</div>
""",
    )

    assert result.returncode == 1
    assert "analysis block must include a visible border style" in result.stdout


def test_rejects_choice_options_outside_question_callout(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

### 例 1

已知条件如下，选择正确答案。

- A. 选项一
- B. 选项二
""",
    )

    assert result.returncode == 1
    assert "choice option must stay inside a question callout" in result.stdout


def test_rejects_generic_title_page_headings_mst_headers_and_numbered_headings(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# Source Transcript

## Page 274

### 1. 线面平行

### 1.1 线面平行判定

### 1.1.1 线面平行

MST 高中基础知识与二级结论
""",
    )

    assert result.returncode == 1
    assert "top title must describe the document" in result.stdout
    assert "page markers must not be visible headings" in result.stdout
    assert "dotted numeric heading labels are not allowed" in result.stdout
    assert "print header/footer noise must be removed" in result.stdout


def test_rejects_numeric_outline_labels_in_body_text(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

构造方式：1. 重垂线构造法；2. 水平线构造法；3. 侧平线构造法。

1.1 线面平行判定定理

> [!question] 例题
> (1) 证明线面平行。
>
> (2) 求二面角。

> 解析：题干中的小问编号可以保留，但正文大纲编号不能保留。
""",
    )

    assert result.returncode == 1
    assert "numeric outline labels are not allowed" in result.stdout


def test_rejects_markdown_tables_and_requires_centered_html_tables(tmp_path: Path) -> None:
    markdown_table = run_validator(
        tmp_path,
        """# 空间几何

| | 内容 |
|---|---|
| 文字语言 | 内容 |
""",
    )
    assert markdown_table.returncode == 1
    assert "Markdown tables are not allowed outside question callouts" in markdown_table.stdout

    uncentered_html_table = run_validator(
        tmp_path,
        """# 空间几何

<table>
  <tr><td>文字语言</td><td>内容</td></tr>
</table>
""",
    )
    assert uncentered_html_table.returncode == 1
    assert "HTML tables must declare centered horizontal and vertical alignment" in uncentered_html_table.stdout


def test_allows_markdown_choice_tables_inside_question_callouts(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 导数与三次函数

> [!question] 例题
> 若函数在区间上有最小值，则实数 $a$ 的取值范围是（ ）
>
> | A. $(-1,2]$ | B. $(1,2)$ | C. $(-1,4)$ | D. $(-1,\\sqrt{11})$ |
> | :---: | :---: | :---: | :---: |

**解答**

由题可得 $f'(x)=0$，故选 A。
""",
    )

    assert result.returncode == 0


def test_fix_preserves_callout_prefixes_and_choice_table_separators(tmp_path: Path) -> None:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text(
        """# 导数与三次函数

> [!question] 例题
> 若函数在区间上有最小值，则实数 $a$ 的取值范围是（ ）
>
> | A. $(-1,2]$ | B. $(1,2)$ | C. $(-1,4)$ | D. $(-1,\\sqrt{11})$ |
> | :---: | :---: | :---: | :---: |

**解答**

由题可得 $f'(x)=0$，故选 A。
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), "--fix"],
        check=False,
        capture_output=True,
        text=True,
    )
    fixed = md_path.read_text(encoding="utf-8")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "> [!question] 例题" in fixed
    assert "> | A. $(-1,2]$ | B. $(1,2)$ | C. $(-1,4)$ | D. $(-1,\\sqrt{11})$ |" in fixed
    assert "$| B.$" not in fixed
    assert "> | :---: | :---: | :---: | :---: |" in fixed
    assert ":__________:" not in fixed


def test_rejects_markdown_images_and_uncontrolled_html_images(tmp_path: Path) -> None:
    markdown_image = run_validator(
        tmp_path,
        """# 空间几何

![例6图1](../doc2x/export/images/example.jpg)
""",
    )
    assert markdown_image.returncode == 1
    assert "Markdown image syntax is not allowed" in markdown_image.stdout

    uncontrolled_html_image = run_validator(
        tmp_path,
        """# 空间几何

<img src="../doc2x/export/images/example.jpg" alt="例6图1">
""",
    )
    assert uncontrolled_html_image.returncode == 1
    assert "HTML images must include sizing and centering styles" in uncontrolled_html_image.stdout


def test_rejects_multi_image_figure_without_horizontal_flex_layout(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="text-align:center;">
  <img src="doc2x/export/images/a.jpg" alt="图1" style="max-width:45%;height:auto;display:block;margin:0 auto;" />
  <img src="doc2x/export/images/b.jpg" alt="图2" style="max-width:45%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )

    assert result.returncode == 1
    assert "multi-image figures must use horizontal flex layout" in result.stdout

    flex_result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="display:flex;justify-content:center;align-items:center;gap:0.8rem;flex-wrap:nowrap;text-align:center;">
  <img src="doc2x/export/images/a.jpg" alt="图1" style="max-width:45%;height:auto;display:block;margin:0 auto;" />
  <img src="doc2x/export/images/b.jpg" alt="图2" style="max-width:45%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )

    assert flex_result.returncode == 0, flex_result.stdout + flex_result.stderr


def test_rejects_adjacent_single_image_figures_that_should_merge(tmp_path: Path) -> None:
    """Two or more single-image figures separated only by blank lines must be
    merged into one side-by-side figure; emitting each crop as its own figure
    stacks them vertically. (Regression: 2026-06-23 session.)"""
    result = run_validator(
        tmp_path,
        """# 对偶性质

<figure style="text-align:center;"><img src="doc2x/export/images/a.jpg" alt="对偶性质图1" style="max-width:20%;height:auto;display:block;margin:0 auto;"/></figure>

<figure style="text-align:center;"><img src="doc2x/export/images/b.jpg" alt="对偶性质图2" style="max-width:20%;height:auto;display:block;margin:0 auto;"/></figure>

<figure style="text-align:center;"><img src="doc2x/export/images/c.jpg" alt="对偶性质图3" style="max-width:20%;height:auto;display:block;margin:0 auto;"/></figure>

**证明**
""",
    )

    assert result.returncode == 1
    assert "adjacent single-image figures must be merged" in result.stdout

    # Prose-separated single-image figures are independent and NOT flagged.
    ok_result = run_validator(
        tmp_path,
        """# 独立情形

<figure style="text-align:center;"><img src="doc2x/export/images/a.jpg" alt="情形1" style="max-width:32%;height:auto;display:block;margin:0 auto;"/></figure>

情形 1 的说明文字。

<figure style="text-align:center;"><img src="doc2x/export/images/b.jpg" alt="情形2" style="max-width:32%;height:auto;display:block;margin:0 auto;"/></figure>
""",
    )
    assert ok_result.returncode == 0, ok_result.stdout + ok_result.stderr


def test_accepts_choice_grid_with_multiple_single_image_figures_on_one_line(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> [!question] 题干
> <div class="choice-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.5rem 0.8rem;align-items:start;">
> <span>A. <figure style="text-align:center;margin:0;"><img src="doc2x/export/images/a.jpg" alt="A" style="max-width:70%;height:auto;display:block;margin:0 auto;" /></figure></span><span>B. <figure style="text-align:center;margin:0;"><img src="doc2x/export/images/b.jpg" alt="B" style="max-width:70%;height:auto;display:block;margin:0 auto;" /></figure></span>
> </div>
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_plain_frac_and_vertical_choice_lists(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> [!question] 题干
> 计算 \\( \\frac{1}{2} \\)。
>
> - A. \\( \\frac{1}{2} \\)
> - B. \\( \\dfrac{1}{2} \\)

> 解析：应使用规范分式。
""",
    )

    assert result.returncode == 1
    assert "plain \\frac is not allowed" in result.stdout
    assert "choice options must use a horizontal HTML choice grid" in result.stdout


def test_rejects_non_obsidian_math_delimiters_and_fragile_katex_macros(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

这里使用了 \\( a \\mathbin{/ \\mspace{-4mu}/} b \\)。

\\[
\\left. \\begin{array}{l} a \\subset \\alpha \\\\ b \\subset \\alpha \\end{array}\\right\\}
\\]
""",
    )

    assert result.returncode == 1
    assert "use Obsidian math delimiters" in result.stdout
    assert "fragile or unsupported KaTeX macro" in result.stdout


def test_accepts_obsidian_math_delimiters_and_katex_safe_parallel(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

若 $a \\parallel b$，则可继续推导。

$$
\\begin{cases}
a \\subset \\alpha \\\\
b \\subset \\alpha
\\end{cases}
\\Rightarrow a \\parallel b
$$
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_dense_analysis_paragraph(tmp_path: Path) -> None:
    long_sentence = "由题意可知" + "，继续推导" * 80 + "。"
    result = run_validator(
        tmp_path,
        f"""# 空间几何

<div class="analysis-block" style="border:1px solid #d0d7de;border-left:4px solid #57606a;border-radius:6px;padding:0.7rem 0.85rem;margin:0.8rem 0;background:#f6f8fa;">
  <div style="font-weight:600;margin-bottom:0.35rem;">解析</div>
  <p>{long_sentence}</p>
</div>
""",
    )

    assert result.returncode == 1
    assert "analysis paragraph is too dense" in result.stdout


def test_rejects_markdown_math_inside_html_content(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr><td style="vertical-align:middle;">符号语言</td><td style="vertical-align:middle;">$x$</td></tr>
</table>

> [!question] 题干
> <div class="choice-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.2rem 0.8rem;">
> <span>A. $x$</span><span>B. 文本</span>
> </div>
""",
    )

    assert result.returncode == 1
    assert "HTML content must use MathML" in result.stdout


def test_rejects_non_obsidian_delimiters_inside_html_content(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<div class="analysis-block" style="border:1px solid #d0d7de;">
  <div>解析</div>
  <p>这里错误使用 \\(x\\)。</p>
</div>
""",
    )

    assert result.returncode == 1
    assert "HTML content must use MathML" in result.stdout


def test_rejects_inline_math_boundary_spaces(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

普通正文中的 $ x $ 应被清理。
""",
    )

    assert result.returncode == 1
    assert "inline math must not have boundary spaces" in result.stdout


def test_accepts_markdown_math_and_html_mathml(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

普通正文中的 $x$ 可以渲染。

$$
x = 1
$$

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr><td style="vertical-align:middle;">符号语言</td><td style="vertical-align:middle;"><math><mi>x</mi><mo>=</mo><mn>1</mn></math></td></tr>
</table>
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_accepts_html_inline_svg_math(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">符号语言</td>
    <td style="vertical-align:middle;">
      <span class="math-svg-wrap" style="display:inline-block;color:inherit;line-height:1;vertical-align:middle;"><svg class="math-svg" xmlns="http://www.w3.org/2000/svg" width="12ex" height="4ex" role="img" aria-label="a 平行 b" focusable="false" viewBox="0 0 120 40"><path d="M10 10H110M10 30H110" /></svg></span>
    </td>
  </tr>
</table>
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_html_inline_svg_math_without_accessible_label(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">符号语言</td>
    <td style="vertical-align:middle;">
      <span class="math-svg-wrap" style="display:inline-block;"><svg class="math-svg" xmlns="http://www.w3.org/2000/svg" width="12ex" height="4ex" viewBox="0 0 120 40"><path d="M10 10H110M10 30H110" /></svg></span>
    </td>
  </tr>
</table>
""",
    )

    assert result.returncode == 1
    assert "inline SVG math must include role=\"img\" and a non-empty aria-label" in result.stdout


def test_rejects_mathml_condition_group_without_explicit_stretchy_brace(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr><td style="vertical-align:middle;">符号语言</td><td style="vertical-align:middle;"><math><mrow><mo>{</mo><mtable><mtr><mtd><mi>a</mi></mtd></mtr></mtable></mrow></math></td></tr>
</table>
""",
    )

    assert result.returncode == 1
    assert "HTML MathML condition groups must use an explicit stretchy left brace" in result.stdout


def test_accepts_mathml_condition_group_with_explicit_stretchy_brace(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">符号语言</td>
    <td style="vertical-align:middle;">
      <math display="block">
        <mrow>
          <mo stretchy="true" symmetric="true" minsize="2.4em">{</mo>
          <mtable>
            <mtr><mtd><mi>a</mi></mtd></mtr>
          </mtable>
          <mo>⇒</mo><mi>b</mi>
        </mrow>
      </math>
    </td>
  </tr>
</table>
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_accepts_html_forced_multiline_math_cases_layout(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">符号语言</td>
    <td style="vertical-align:middle;">
      <span class="math-cases" style="display:inline-flex;align-items:center;justify-content:center;gap:0.35em;line-height:1.2;">
        <math><mo>{</mo></math>
        <span class="case-lines" style="display:inline-flex;flex-direction:column;align-items:flex-start;gap:0.12em;">
          <math><mi>a</mi></math>
          <math><mi>b</mi></math>
        </span>
        <math><mo>⇒</mo><mi>c</mi></math>
      </span>
    </td>
  </tr>
</table>
""",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_math_cases_without_vertical_case_lines(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">符号语言</td>
    <td style="vertical-align:middle;">
      <span class="math-cases" style="display:inline-flex;">
        <span class="case-lines" style="display:inline-flex;">
          <math><mi>a</mi></math>
        </span>
      </span>
    </td>
  </tr>
</table>
""",
    )

    assert result.returncode == 1
    assert "math-cases must include case-lines" in result.stdout


def test_requires_mathml_for_formula_like_html_table_or_choice_grid(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr><td style="vertical-align:middle;">符号语言</td><td style="vertical-align:middle;">\\alpha \\parallel \\beta</td></tr>
</table>

> [!question] 题干
> <div class="choice-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.2rem 0.8rem;">
> <span>A. \\alpha</span><span>B. 文本</span>
> </div>
""",
    )

    assert result.returncode == 1
    assert "HTML formula content must be rendered as MathML" in result.stdout


def test_long_doc2x_markdown_requires_completed_chunk_plan(tmp_path: Path) -> None:
    valid_source = """# 空间几何

> [!question] 题干
> 内容。

<div class="analysis-block" style="border:1px solid #d0d7de;border-left:4px solid #57606a;border-radius:6px;padding:0.7rem 0.85rem;margin:0.8rem 0;background:#f6f8fa;">
  <div style="font-weight:600;margin-bottom:0.35rem;">解析</div>
  <p>简洁解析。</p>
</div>
"""
    long_doc2x_export = "\n".join(f"### 标题 {index}\n正文 {index}" for index in range(180))

    missing_plan = run_job_validator(tmp_path, valid_source, long_doc2x_export)
    assert missing_plan.returncode == 1
    assert "long Doc2X markdown requires markdown-rewrite-plan.md" in missing_plan.stdout

    unfinished_plan = run_job_validator(
        tmp_path,
        valid_source,
        long_doc2x_export,
        plan="# Markdown Rewrite Plan\n\n- [x] Chunk 1: Page 1\n- [ ] Chunk 2: Page 2\n",
    )
    assert unfinished_plan.returncode == 1
    assert "markdown-rewrite-plan.md has unfinished chunks" in unfinished_plan.stdout

    completed_plan = run_job_validator(
        tmp_path,
        valid_source,
        long_doc2x_export,
        plan="# Markdown Rewrite Plan\n\n- [x] Chunk 1: Page 1\n- [x] Chunk 2: Page 2\n",
    )
    assert completed_plan.returncode == 0, completed_plan.stdout + completed_plan.stderr


def test_md_mode_checks_sibling_rewrite_plan_when_present(tmp_path: Path) -> None:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text("# 空间几何\n\n正文。\n", encoding="utf-8")
    (tmp_path / "markdown-rewrite-plan.md").write_text(
        "# Markdown Rewrite Plan\n\n- [x] Chunk 1: A\n- [ ] Chunk 2: B\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "markdown-rewrite-plan.md has unfinished chunks" in result.stdout


# --- auto-fix mode tests ---

def run_fix(tmp_path: Path, markdown: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text(markdown, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), "--fix", *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_fix_removes_leading_orphan_punctuation(tmp_path: Path) -> None:
    result = run_fix(tmp_path, """# 空间几何

）例题
））例题2
。文本开头
""")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "例题" in fixed
    assert "）例题" not in fixed
    assert "））例题" not in fixed
    assert "removed" not in result.stdout.lower() or "issue" in result.stdout.lower()


def test_fix_normalizes_inline_math_spacing(tmp_path: Path) -> None:
    result = run_fix(tmp_path, "# 空间几何\n\n已知 $ x $ 和 $ y $。\n")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "$x$" in fixed
    assert "$ x $" not in fixed


def test_fix_normalizes_math_delimiters(tmp_path: Path) -> None:
    result = run_fix(tmp_path, "# 空间几何\n\n这里用 \\(a\\) 和 \\[b\\]。\n")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "$a$" in fixed
    assert "\\(a\\)" not in fixed


def test_fix_standardizes_fractions(tmp_path: Path) -> None:
    result = run_fix(tmp_path, "# 空间几何\n\n公式：\\frac{1}{2}\n")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "\\dfrac" in fixed
    assert "\\frac" not in fixed


def test_fix_normalizes_fill_in_blanks(tmp_path: Path) -> None:
    result = run_fix(tmp_path, "# 空间几何\n\n填空：____ 和 ----。\n")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "__________" in fixed


def test_fix_removes_print_noise(tmp_path: Path) -> None:
    result = run_fix(tmp_path, "# 空间几何\n\nMST 高中基础知识与二级结论\n")
    assert result.returncode == 0
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert "MST" not in fixed


def test_fix_dry_run_does_not_modify_file(tmp_path: Path) -> None:
    original = "# 空间几何\n\n$ x $\n"
    result = run_fix(tmp_path, original, "--dry-run")
    assert result.returncode == 0
    assert "DRY RUN" in result.stdout
    fixed = (tmp_path / "source-transcript.md").read_text(encoding="utf-8")
    assert fixed == original


# --- proofreading mode tests ---

def run_proof(tmp_path: Path, markdown: str) -> subprocess.CompletedProcess[str]:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text(markdown, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), "--check-proofreading"],
        check=False,
        capture_output=True,
        text=True,
    )


def test_proofread_detects_unclosed_math_delimiter(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n$ x\n")
    assert result.returncode == 1
    assert "unclosed" in result.stdout


def test_proofread_detects_heading_jump(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n## 第一章\n\n#### 跳级了\n")
    assert result.returncode == 1
    assert "heading jump" in result.stdout


def test_proofread_detects_suspicious_characters(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n己经知道了。\n")
    assert result.returncode == 1
    assert "suspicious character" in result.stdout


def test_proofread_detects_to_verify_markers(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n正文。[TO VERIFY: something]\n")
    assert result.returncode == 1
    assert "TO VERIFY" in result.stdout


def test_proofread_detects_empty_image_references(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n![]( )\n")
    assert result.returncode == 1
    assert "empty image reference" in result.stdout


def test_proofread_passes_clean_document(tmp_path: Path) -> None:
    result = run_proof(tmp_path, """# 空间几何基础知识

## 第一章

### 第一节

正文内容正常。

$x$ 和 $y$ 都是变量。
""")
    assert result.returncode == 0
    assert "OK:" in result.stdout


def test_proofread_detects_malformed_triple_dollar(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n$$$ x $$\n")
    assert result.returncode == 1
    assert "malformed math delimiter" in result.stdout


def test_proofread_detects_garbled_lines(tmp_path: Path) -> None:
    result = run_proof(tmp_path, "# 空间几何\n\n###ERROR###\n")
    assert result.returncode == 1
    assert "garbled" in result.stdout


def test_accepts_consistent_comma_style(tmp_path: Path) -> None:
    # Regression fixture for Punctuation Consistency (canonical-markdown-rules.md):
    # clean, consistent, properly-spaced commas must be accepted. The validator
    # does NOT enforce comma style by regex (it is model-enforced per Forbidden
    # Pattern F1); this fixture pins the expected clean style so future validator
    # changes do not break it. Paragraph 1 uses English ", " between formulas;
    # paragraph 2 uses Chinese "，" in prose — each block is internally consistent.
    result = run_validator(
        tmp_path,
        """# 函数与导数

## 导数的应用

已知函数 $f(x) = x^2$, 求其在 $x = 1$ 处的导数。

由题意可知，$f'(x) = 2x$，因此 $f'(1) = 2$。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- fraction nesting and QA ordering tests ---

def test_dfrac_in_exponent_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：${e}^{\\dfrac{2}{e}}$\n",
    )
    assert result.returncode == 1
    assert "should be \\tfrac" in result.stdout


def test_dfrac_in_numerator_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：$\\dfrac{\\dfrac{1}{2}x}{e}$\n",
    )
    assert result.returncode == 1
    assert "should be \\tfrac" in result.stdout


def test_dfrac_in_denominator_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：$\\dfrac{1}{\\ln(1+\\dfrac{1}{n})}$\n",
    )
    assert result.returncode == 1
    assert "should be \\tfrac" in result.stdout


def test_tfrac_nested_behind_intervening_braces_ok(tmp_path: Path) -> None:
    """\\tfrac inside \\dfrac numerator with intervening {..} groups is correctly nested."""
    result = run_validator(
        tmp_path,
        "# Test\n\n$\\dfrac{-a^2\\left({x + \\tfrac{1}{a}}\\right)}{ax^2}$\n",
    )
    assert result.returncode == 0


def test_tfrac_in_nested_denominator_behind_braces_ok(tmp_path: Path) -> None:
    """\\tfrac inside \\dfrac denominator with intervening braces is nested."""
    result = run_validator(
        tmp_path,
        "# Test\n\n$a \\leq \\dfrac{1}{\\ln\\left({1 + \\tfrac{1}{n}}\\right)} - n$\n",
    )
    assert result.returncode == 0


def test_tfrac_in_ln_argument_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：$\\ln(\\tfrac{1}{x})$\n",
    )
    assert result.returncode == 1
    assert "non-nested context" in result.stdout


def test_standalone_dfrac_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：$\\dfrac{1}{2}$\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_correct_tfrac_in_exponent_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        "# 空间几何\n\n公式：${e}^{\\tfrac{2}{e}}$\n",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_consecutive_questions_no_analysis_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> [!question] 第一题
> 题干内容

> [!question] 第二题
> 题干内容

**解析**

统一放到后面讲，这是错误结构。
""",
    )
    assert result.returncode == 1
    assert "no analysis before next question" in result.stdout


def test_question_with_analysis_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

> [!question] 第一题
> 题干内容

**解析** 答案。

> [!question] 第二题
> 题干内容
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_rejects_bare_example_stem_outside_question_callout(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 圆锥曲线

【例题 1】已知椭圆 $C : \\dfrac{x^2}{4} + \\dfrac{y^2}{3} = 1$。

(1) 求方程；

(2) 证明直线过定点。
""",
    )
    assert result.returncode == 1
    assert "example/exercise stem must be wrapped in a `> [!question]` callout" in result.stdout


def test_allows_consecutive_question_callouts_when_interstitial_content_exists(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 圆锥曲线

> [!question] 例题 1
> 已知点 $A$ 在曲线上。

提示：本题解析见后文一题多解部分。

> [!question] 例题 2
> 已知点 $B$ 在曲线上。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_image_path_images_prefix_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="text-align:center;">
  <img src="images/foo.jpg" alt="图" style="max-width:72%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )
    assert result.returncode == 1
    assert "image path 'images/...' is likely wrong" in result.stdout


def test_image_path_correct_prefix_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="text-align:center;">
  <img src="doc2x/export/images/foo.jpg" alt="图" style="max-width:72%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_image_path_https_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="text-align:center;">
  <img src="https://example.com/foo.jpg" alt="图" style="max-width:72%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_image_path_markdown_syntax_flagged(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

![alt](images/foo.jpg)
""",
    )
    assert result.returncode == 1
    assert "image path 'images/...' is likely wrong" in result.stdout


def test_image_path_data_uri_ok(tmp_path: Path) -> None:
    result = run_validator(
        tmp_path,
        """# 空间几何

<figure style="text-align:center;">
  <img src="data:image/png;base64,iVBORw0KGgo=" alt="图" style="max-width:72%;height:auto;display:block;margin:0 auto;" />
</figure>
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- question callout title-line lint (Step 2.7 structural evidence) ---
# A question callout's title line must hold only the label + source tag; the
# stem body must start on its own `>` line. The lint anchors on the universal
# label (例题N/例N/练习N), strips a loose source suffix, then flags a glued
# stem. See validate_canonical_markdown.py:lint_question_callout_title_attached.


def test_callout_title_with_bracketed_source_and_split_stem_ok(tmp_path: Path) -> None:
    """GOOD: label + `(2017・新课标 I )` source, stem on the next `>` line."""
    result = run_validator(
        tmp_path,
        """# 椭圆

> [!question] 例题 1 (2017・新课标 I )
> 已知椭圆 $C : \\dfrac{x^2}{a^2} + \\dfrac{y^2}{b^2} = 1$，四点 $P_1(1,1)$。
>
> (1)求 $C$ 的方程。

**解析**

由题意可得。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_callout_title_bare_label_ok(tmp_path: Path) -> None:
    """GOOD: label with no source tag at all."""
    result = run_validator(
        tmp_path,
        """# 数列

> [!question] 例题 1
> 设等差数列 $\\{a_n\\}$ 的前 $n$ 项和为 $S_n$。

**解析**

略。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_callout_title_angle_bracket_source_ok(tmp_path: Path) -> None:
    """GOOD: 【...】 source tag shape."""
    result = run_validator(
        tmp_path,
        """# 函数

> [!question] 练习 2 【2018全国I】
> 设函数 $f(x) = x^3$。

**解析**

略。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_callout_title_stem_glued_with_source_flagged(tmp_path: Path) -> None:
    """BAD: stem body glued after label + source on the SAME title line."""
    result = run_validator(
        tmp_path,
        """# 椭圆

> [!question] 例题 1 (2017・新课标 I ) 已知椭圆 $C : \\dfrac{x^2}{a^2} + \\dfrac{y^2}{b^2} = 1$。

**解析**

略。
""",
    )
    assert result.returncode == 1
    assert "title line has the stem body glued" in result.stdout


def test_callout_title_stem_glued_no_source_flagged(tmp_path: Path) -> None:
    """BAD: label directly followed by a stem-start signal word, no source."""
    result = run_validator(
        tmp_path,
        """# 函数

> [!question] 例题 1 设函数 $f(x) = x^3$。

**解析**

略。
""",
    )
    assert result.returncode == 1
    assert "title line has the stem body glued" in result.stdout


def test_callout_title_long_non_stem_tail_ok(tmp_path: Path) -> None:
    """GOOD: a short non-stem tail (如 选填题) after the source is not flagged."""
    result = run_validator(
        tmp_path,
        """# 集合

> [!question] 例题 1 (2017) 选填题
> 已知集合 $A = \\{1, 2\\}$。

**解析**

略。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_callout_title_non_label_not_in_scope(tmp_path: Path) -> None:
    """GOOD: a `[!question] 题干` title (no 例题N label) is out of scope."""
    result = run_validator(
        tmp_path,
        """# 立体几何

> [!question] 题干
> 已知 $a \\parallel \\alpha$，求结论。

**解析**

略。
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr

