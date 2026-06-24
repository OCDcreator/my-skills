#!/usr/bin/env python3
"""渲染 HTML 流派 A4 封面 -> 截图 + PDF。

复用项目内 scan-pdf-to-print-html 技能的 render_html_to_pdf.py。
HTML 封面的 drawEdges/autoFitFormula 会在 data-handout-ready 置位前完成，
render_html_to_pdf.py 的等待链路 (networkidle -> handoutReady -> fonts -> grace)
正好契合这个时序。

用法:
    py -3 render_cover.py <cover.html> [--pdf out.pdf] [--png out.png] [--wait-ms 2500]

默认产物与输入 html 同目录、同文件名换扩展名。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

def find_renderer() -> Path:
    """向上查找项目根（含 .git 的目录），再在 .kimi-code/.codex/.zcode 下找
    scan-pdf-to-print-html 技能的 render_html_to_pdf.py。
    不硬编码层级号，避免技能目录移动后失效。
    """
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            project_root = parent
            break
    else:
        # 兜底：往上找第一个含 skills 目录的祖先
        project_root = here.parents[3] if len(here.parents) > 3 else here.root
    for dir_name in (".kimi-code", ".codex", ".zcode"):
        cand = project_root / dir_name / "skills" / "scan-pdf-to-print-html" / "scripts" / "render_html_to_pdf.py"
        if cand.exists():
            return cand
    raise SystemExit(
        "找不到渲染器 render_html_to_pdf.py（scan-pdf-to-print-html 技能）。"
        f"已搜索项目根: {project_root}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path, help="输入封面 HTML 路径")
    ap.add_argument("--pdf", type=Path, default=None, help="输出 PDF（默认同目录换扩展名）")
    ap.add_argument("--png", type=Path, default=None, help="输出 PNG（默认同目录换扩展名）")
    ap.add_argument("--wait-ms", type=int, default=2500,
                    help="KaTeX 渲染 + autoFit + drawEdges 后的 grace 毫秒（默认 2500）")
    args = ap.parse_args()

    html = args.html.resolve()
    if not html.exists():
        raise SystemExit(f"HTML 不存在: {html}")

    renderer = find_renderer()

    pdf = (args.pdf or html.with_suffix(".pdf")).resolve()
    png = (args.png or html.with_suffix(".png")).resolve()

    cmd = [
        sys.executable, str(renderer),
        "--html", str(html),
        "--pdf", str(pdf),
        "--screenshot", str(png),
        "--wait-ms", str(args.wait_ms),
    ]
    print("run:", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"渲染失败 (exit {r.returncode})", file=sys.stderr)
        return r.returncode

    print(f"\n产物:")
    print(f"  HTML -> {html}")
    print(f"  PNG  -> {png} ({png.stat().st_size if png.exists() else 0} bytes)")
    print(f"  PDF  -> {pdf} ({pdf.stat().st_size if pdf.exists() else 0} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
