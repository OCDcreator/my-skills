#!/usr/bin/env python3
"""Rendered SVG layout checks using browser geometry.

This catches issues that plain XML validation cannot see, such as text glyph
bounds overflowing cards or paths visually crossing text boxes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", type=Path)
    parser.add_argument("--min-edge-pad-mm", type=float, default=10.0)
    parser.add_argument("--min-text-pad-mm", type=float, default=1.0)
    parser.add_argument("--text-cross-pad-mm", type=float, default=0.45)
    parser.add_argument("--max-edge-stroke-mm", type=float, default=0.5)
    parser.add_argument("--max-card-text-center-delta-mm", type=float, default=2.0)
    args = parser.parse_args(argv)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment guard
        raise SystemExit("Playwright is required for rendered layout checks") from exc

    js = r"""
    ({minEdgePad, minTextPad, textCrossPad, maxEdgeStroke, maxCenterDelta}) => {
      const errors = [];
      const svg = document.documentElement;
      const width = 210;
      const height = 297;
      const bbox = (el) => {
        const b = el.getBBox();
        return {x:b.x, y:b.y, width:b.width, height:b.height, right:b.x+b.width, bottom:b.y+b.height};
      };
      const transformedBbox = (el) => {
        const b = el.getBBox();
        const elementMatrix = el.getCTM();
        const rootMatrix = svg.getCTM();
        if (!elementMatrix || !rootMatrix) return {x:b.x, y:b.y, width:b.width, height:b.height, right:b.x+b.width, bottom:b.y+b.height};
        const matrix = rootMatrix.inverse().multiply(elementMatrix);
        const points = [
          new DOMPoint(b.x, b.y).matrixTransform(matrix),
          new DOMPoint(b.x + b.width, b.y).matrixTransform(matrix),
          new DOMPoint(b.x, b.y + b.height).matrixTransform(matrix),
          new DOMPoint(b.x + b.width, b.y + b.height).matrixTransform(matrix),
        ];
        const xs = points.map(p => p.x);
        const ys = points.map(p => p.y);
        const x = Math.min(...xs);
        const y = Math.min(...ys);
        const right = Math.max(...xs);
        const bottom = Math.max(...ys);
        return {x, y, width:right-x, height:bottom-y, right, bottom};
      };
      const intersects = (a, b) => !(a.right <= b.x || b.right <= a.x || a.bottom <= b.y || b.bottom <= a.y);
      const containsWithPad = (outer, inner, pad) => (
        inner.x >= outer.x + pad && inner.right <= outer.right - pad &&
        inner.y >= outer.y + pad && inner.bottom <= outer.bottom - pad
      );
      const pointIn = (p, b) => p.x >= b.x && p.x <= b.right && p.y >= b.y && p.y <= b.bottom;
      const expand = (b, pad) => ({x:b.x-pad, y:b.y-pad, right:b.right+pad, bottom:b.bottom+pad, width:b.width+2*pad, height:b.height+2*pad});

      const shields = [...document.querySelectorAll('rect.label-shield')]
        .map((el, i) => ({el, i, cls: el.getAttribute('class') || '', b: bbox(el)}));
      const cards = [...document.querySelectorAll('rect')]
        .filter(el => !el.classList.contains('bg') && !el.classList.contains('label-shield') && !el.classList.contains('shadow') && !el.closest('g.formula-fit'))
        .map((el, i) => ({el, i, cls: el.getAttribute('class') || '', b: bbox(el)}));
      const texts = [...document.querySelectorAll('text')]
        .map((el, i) => ({el, i, text: el.textContent || '', b: bbox(el)}));
      const formulas = [...document.querySelectorAll('g.formula-fit')]
        .map((el, i) => ({el, i, text: el.getAttribute('data-formula-id') || 'formula', b: transformedBbox(el)}));
      const paths = [...document.querySelectorAll('path.edge,path.edge-strong')]
        .map((el, i) => ({el, i, cls: el.getAttribute('class') || '', b: bbox(el)}));

      for (const card of cards) {
        if (card.b.x < minEdgePad || card.b.y < minEdgePad || card.b.right > width - minEdgePad || card.b.bottom > height - minEdgePad) {
          errors.push(`card too close to SVG edge: ${card.cls} bbox=${JSON.stringify(card.b)}`);
        }
      }

      for (const t of texts) {
        const cx = t.b.x + t.b.width / 2;
        const cy = t.b.y + t.b.height / 2;
        const owner = cards.find(card => pointIn({x: cx, y: cy}, card.b));
        if (!owner) continue;
        t.owner = owner;
        if (!containsWithPad(owner.b, t.b, minTextPad)) {
          errors.push(`text overflows card padding: "${t.text}" text=${JSON.stringify(t.b)} card=${owner.cls} ${JSON.stringify(owner.b)}`);
        }
      }

      for (const f of formulas) {
        const cx = f.b.x + f.b.width / 2;
        const cy = f.b.y + f.b.height / 2;
        const owner = cards.find(card => pointIn({x: cx, y: cy}, card.b));
        if (!owner) continue;
        f.owner = owner;
        if (!containsWithPad(owner.b, f.b, minTextPad)) {
          errors.push(`formula overflows card padding: "${f.text}" formula=${JSON.stringify(f.b)} card=${owner.cls} ${JSON.stringify(owner.b)}`);
        }
      }

      for (const card of cards) {
        const ownedContent = [...texts.filter(t => t.owner === card), ...formulas.filter(f => f.owner === card)];
        if (!ownedContent.length) continue;
        const group = ownedContent.reduce((acc, item) => ({
          x: Math.min(acc.x, item.b.x),
          y: Math.min(acc.y, item.b.y),
          right: Math.max(acc.right, item.b.right),
          bottom: Math.max(acc.bottom, item.b.bottom),
        }), {x: Infinity, y: Infinity, right: -Infinity, bottom: -Infinity});
        group.width = group.right - group.x;
        group.height = group.bottom - group.y;
        const cardCx = card.b.x + card.b.width / 2;
        const cardCy = card.b.y + card.b.height / 2;
        const groupCx = group.x + group.width / 2;
        const groupCy = group.y + group.height / 2;
        const dx = Math.abs(groupCx - cardCx);
        const dy = Math.abs(groupCy - cardCy);
        if (dx > maxCenterDelta || dy > maxCenterDelta) {
          errors.push(`card text group is not centered: ${card.cls} dx=${dx.toFixed(2)} dy=${dy.toFixed(2)} card=${JSON.stringify(card.b)} textGroup=${JSON.stringify(group)}`);
        }
      }

      for (const path of paths) {
        const cs = getComputedStyle(path.el);
        const stroke = parseFloat(cs.strokeWidth || path.el.getAttribute('stroke-width') || '0');
        if (stroke > maxEdgeStroke) {
          errors.push(`edge stroke too heavy: ${path.cls} stroke=${stroke}`);
        }
      }

      const allElements = [...document.querySelectorAll('*')];
      const pathOrder = new Map(paths.map(path => [path.el, allElements.indexOf(path.el)]));
      const textOrder = new Map(texts.map(t => [t.el, allElements.indexOf(t.el)]));
      for (const path of paths) {
        for (const t of texts) {
          if ((pathOrder.get(path.el) || 0) > (textOrder.get(t.el) || 0)) {
            errors.push(`edge is above text in DOM order: path=${path.cls} text="${t.text}"`);
            break;
          }
        }
      }

      for (const path of paths) {
        if (!path.el.getTotalLength) continue;
        const length = path.el.getTotalLength();
        const sampleCount = Math.max(16, Math.ceil(length / 2));
        for (const t of texts) {
          const tb = expand(t.b, textCrossPad);
          let hit = false;
          for (let i = 0; i <= sampleCount; i++) {
            const p = path.el.getPointAtLength(length * i / sampleCount);
            const hiddenByCardOrShield = [...cards, ...shields].some(card => pointIn(p, card.b));
            if (pointIn(p, tb) && !hiddenByCardOrShield) { hit = true; break; }
          }
          if (hit) {
            errors.push(`edge crosses text bbox: path=${path.cls} text="${t.text}"`);
          }
        }
      }

      return {errors, cards: cards.length, texts: texts.length, paths: paths.length};
    }
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=1)
        page.goto(args.svg.resolve().as_uri(), wait_until="domcontentloaded")
        result = page.evaluate(
            js,
            {
                "minEdgePad": args.min_edge_pad_mm,
                "minTextPad": args.min_text_pad_mm,
                "textCrossPad": args.text_cross_pad_mm,
                "maxEdgeStroke": args.max_edge_stroke_mm,
                "maxCenterDelta": args.max_card_text_center_delta_mm,
            },
        )
        browser.close()

    if result["errors"]:
        print("FAIL rendered concept map layout", file=sys.stderr)
        for error in result["errors"]:
            print(f"- {error}", file=sys.stderr)
        print(json.dumps({k: v for k, v in result.items() if k != "errors"}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(
        "PASS rendered concept map layout: "
        f"cards={result['cards']} texts={result['texts']} paths={result['paths']} "
        f"edge_pad_mm={args.min_edge_pad_mm:g} text_pad_mm={args.min_text_pad_mm:g} "
        f"max_edge_stroke_mm={args.max_edge_stroke_mm:g} max_center_delta_mm={args.max_card_text_center_delta_mm:g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
