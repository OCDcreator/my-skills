#!/usr/bin/env python3
"""验证 HTML 流派 A4 封面的公式布局：溢出量 + 左偏量。

这是 a4-novak-html-cover 技能的硬合同验证器。任何公式 [溢出] 或 [左偏]
超过阈值即判失败，封面不算完成。

测量原理（不依赖图像分析，直接读 DOM）:
  溢出量 = 公式宽 - 卡片可用内宽   (>0 即真溢出)
  左偏量 = 公式中心 - 卡片中心     (绝对值大即未居中)

退出码:
  0 = 全部通过
  1 = 存在溢出或左偏超阈值（会打印失败明细）

用法:
    py -3 validate_cover_formulas.py <cover.html> [--over 0.5] [--drift 3]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

MEASURE_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('.card').forEach(card => {
    const formulaEl = card.querySelector('.formula');
    if (!formulaEl) return;
    const inner = formulaEl.querySelector('.katex') || formulaEl.querySelector('mjx-container');
    const target = inner || formulaEl;
    const cR = card.getBoundingClientRect();
    const cs = getComputedStyle(card);
    const availW = cR.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const fR = target.getBoundingClientRect();
    const cardCx = cR.left + cR.width / 2;
    const formCx = fR.left + fR.width / 2;
    const title = (card.querySelector('.title')||{}).textContent || '?';
    out.push({
      title, availW: +availW.toFixed(1), formW: +fR.width.toFixed(1),
      over: +(fR.width - availW).toFixed(1),
      drift: +(formCx - cardCx).toFixed(1),
    });
  });
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html", type=Path)
    ap.add_argument("--over", type=float, default=0.5, help="溢出阈值 px（默认 0.5）")
    ap.add_argument("--drift", type=float, default=3.0, help="左偏阈值 px（默认 3）")
    args = ap.parse_args()

    html = args.html.resolve()
    if not html.exists():
        raise SystemExit(f"HTML 不存在: {html}")

    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 794, "height": 1123})
        page = ctx.new_page()
        page.goto(html.as_uri(), wait_until="networkidle")
        try:
            page.wait_for_function(
                "document.documentElement.dataset.handoutReady==='true'", timeout=60_000
            )
        except Exception:
            print("警告: data-handout-ready 未置位，JS 可能报错", file=sys.stderr)
        page.wait_for_function(
            "document.fonts && document.fonts.status==='loaded'", timeout=60_000
        )
        page.wait_for_timeout(2000)
        rows = page.evaluate(MEASURE_JS)
        browser.close()

    if not rows:
        print("未发现任何含公式的卡片（无 .formula 元素）", file=sys.stderr)
        return 0

    print(f"{'卡片':<12}{'可用宽':>8}{'公式宽':>8}{'溢出':>8}{'左偏':>8}  状态")
    n_formulas = 0
    for r in rows:
        n_formulas += 1
        over_bad = r["over"] > args.over
        drift_bad = abs(r["drift"]) > args.drift
        tags = [s for s, b in [("溢出", over_bad), ("偏移", drift_bad)] if b]
        flag = ("  ❌" + "/".join(tags)) if tags else "  OK"
        if over_bad or drift_bad:
            failures.append(r)
        print(f"{r['title']:<12}{r['availW']:>8}{r['formW']:>8}{r['over']:>8}{r['drift']:>8}{flag}")

    print(f"\n公式卡片: {n_formulas}  失败: {len(failures)}")
    if failures:
        print(f"\n验证失败：阈值 溢出>{args.over}px 或 左偏>{args.drift}px")
        return 1
    print("验证通过：无溢出、无左偏超阈值。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
