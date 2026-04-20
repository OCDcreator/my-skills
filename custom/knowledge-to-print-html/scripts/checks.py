from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from .svg_enclosure import attach_svg_visual_enclosure_issues
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    from svg_enclosure import attach_svg_visual_enclosure_issues

DEFAULT_PARITY_DIFF_THRESHOLD = 0.035

DEFAULT_MAX_CARD_GRID_COUNT = 2

DEFAULT_MAX_CARD_AREA_RATIO = 0.35

DEFAULT_MIN_CARD_TEXT_SIZE_PX = 11.0

DEFAULT_MIN_BODY_FONT_SIZE_PX = 11.5

DEFAULT_MIN_BODY_LINE_HEIGHT_RATIO = 1.35

DEFAULT_MIN_PARAGRAPH_SPACING_RATIO = 0.45

IMAGE_EVAL_JS = r"""
elements => elements.map((image) => ({
  src: image.getAttribute("src"),
  alt: image.getAttribute("alt"),
  page: image.closest(".sheet") ? image.closest(".sheet").dataset.page || null : null,
  complete: image.complete,
  naturalWidth: image.naturalWidth,
  naturalHeight: image.naturalHeight,
}))
"""

SHEET_EVAL_JS = r"""
elements => {
  const watchedSelectors = [
    "figure",
    ".callout",
    ".case-study",
    ".note-box",
    ".mistakes",
    ".print-note",
    "pre",
    "table",
    ".card",
    ".mini",
    ".ref-item",
    ".summary-points > div",
    ".hero-panel",
    ".tags",
    ".table-like",
  ].join(",");
  const cardSelectors = [
    ".card",
    ".mini",
    ".callout",
    ".case-study",
    ".note-box",
    ".mistakes",
    ".summary-points > div",
    ".hero-panel",
    ".table-like",
  ].join(",");
  const textSelectors = [
    "p",
    "li",
    "blockquote p",
    "figcaption",
    "td",
    "th",
    ".callout",
    ".case-study",
    ".note-box",
    ".card",
    ".mini",
  ].join(",");
  const paragraphSelectors = [
    "p",
    "li",
    "blockquote p",
  ].join(",");
  const metaPatterns = [
    { kind: "provenance", pattern: /\bbased on user[- ]provided\b/i },
    { kind: "provenance", pattern: /\bfrom user[- ]provided\b/i },
    { kind: "provenance", pattern: /\busing user[- ]provided\b/i },
    { kind: "provenance", pattern: /\bcompiled from (?:the )?user(?:'s)? (?:notes|draft|outline|materials?)\b/i },
    { kind: "provenance", pattern: /\breorganized from (?:the )?user(?:'s)? (?:notes|draft|outline|materials?)\b/i },
    { kind: "process", pattern: /\bthis handout (?:was )?generated from\b/i },
    { kind: "process", pattern: /\bthis page (?:was )?generated from\b/i },
    { kind: "process", pattern: /\bthis handout will answer\b/i },
    { kind: "provenance", pattern: /基于用户提供(?:的)?(?:笔记|资料|草稿|提纲)/ },
    { kind: "provenance", pattern: /参考了用户提供(?:的)?(?:笔记|资料|草稿|提纲)/ },
    { kind: "provenance", pattern: /由用户提供(?:的)?(?:笔记|资料|草稿|提纲)整理/ },
  ];
  const round = value => Math.round(value * 100) / 100;
  const roundRatio = value => Math.round(value * 1000) / 1000;
  const isVisible = node => {
    const style = window.getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  };
  const parsePx = (value, fallbackFontSize) => {
    if (!value || value === "normal") {
      return fallbackFontSize * 1.2;
    }
    const numeric = Number.parseFloat(value);
    return Number.isFinite(numeric) ? numeric : fallbackFontSize * 1.2;
  };
  const parseLength = value => {
    const numeric = Number.parseFloat(value || "");
    return Number.isFinite(numeric) ? numeric : 0;
  };
  const selectorLabel = node => {
    const className = typeof node.className === "string"
      ? node.className
      : (node.className && typeof node.className.baseVal === "string" ? node.className.baseVal : "");
    return className || node.tagName.toLowerCase();
  };
  const textSnippet = node => (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
  const hasContainerChrome = style => {
    const padding = (
      parseLength(style.paddingTop) +
      parseLength(style.paddingRight) +
      parseLength(style.paddingBottom) +
      parseLength(style.paddingLeft)
    );
    const hasBorder = (
      parseLength(style.borderTopWidth) +
      parseLength(style.borderRightWidth) +
      parseLength(style.borderBottomWidth) +
      parseLength(style.borderLeftWidth)
    ) > 0;
    const background = style.backgroundColor || "";
    const hasBackground = background && background !== "rgba(0, 0, 0, 0)" && background !== "transparent";
    return padding > 0 || hasBorder || hasBackground;
  };
  const hasClipOrScrollStyle = style => {
    return ["hidden", "clip", "scroll", "auto"].includes(style.overflowX)
      || ["hidden", "clip", "scroll", "auto"].includes(style.overflowY)
      || style.whiteSpace === "nowrap";
  };
  const isLikelyTextContainer = (node, style) => {
    const tag = node.tagName.toLowerCase();
    const label = selectorLabel(node);
    return ["td", "th", "pre", "code", "figcaption"].includes(tag)
      || style.display === "table-cell"
      || hasClipOrScrollStyle(style)
      || hasContainerChrome(style)
      || /(callout|case-study|note-box|mistakes|print-note|card|mini|ref-item|hero-panel|table-like|panel|insight|memory-strip|chip|pill|tag|badge|definition)/i.test(label);
  };
  const smallestFontSize = node => {
    const descendants = [node, ...Array.from(node.querySelectorAll("*"))];
    let smallest = null;
    for (const element of descendants) {
      const fontSize = Number.parseFloat(window.getComputedStyle(element).fontSize || "");
      if (Number.isFinite(fontSize)) {
        smallest = smallest === null ? fontSize : Math.min(smallest, fontSize);
      }
    }
    return smallest;
  };

  return elements.map((sheet) => {
    const rect = sheet.getBoundingClientRect();
    const expectedA4Height = rect.width / (210 / 297);
    const issues = [];
    const directChildren = Array.from(sheet.children).filter((node) => {
      return !node.classList.contains("page-no") && !node.hidden && isVisible(node);
    });

    let contentTop = rect.bottom;
    let contentBottom = rect.top;
    let contentLeft = rect.right;
    let contentRight = rect.left;

    for (const node of sheet.querySelectorAll(watchedSelectors)) {
      if (!isVisible(node)) {
        continue;
      }
      const box = node.getBoundingClientRect();
      const rightOverflow = round(box.right - rect.right);
      const bottomOverflow = round(box.bottom - rect.bottom);

      if (rightOverflow > 1) {
        issues.push({
          kind: "right-overflow",
          selector: node.className || node.tagName.toLowerCase(),
          amount: rightOverflow,
        });
      }

      if (bottomOverflow > 1) {
        issues.push({
          kind: "bottom-overflow",
          selector: node.className || node.tagName.toLowerCase(),
          amount: bottomOverflow,
        });
      }
    }

    for (const node of directChildren) {
      const box = node.getBoundingClientRect();
      contentTop = Math.min(contentTop, box.top);
      contentBottom = Math.max(contentBottom, box.bottom);
      contentLeft = Math.min(contentLeft, box.left);
      contentRight = Math.max(contentRight, box.right);
    }

    const hasVisibleContent = directChildren.length > 0;
    const contentBounds = hasVisibleContent ? {
      top: round(contentTop - rect.top),
      bottom: round(contentBottom - rect.top),
      left: round(contentLeft - rect.left),
      right: round(contentRight - rect.left),
      width: round(contentRight - contentLeft),
      height: round(contentBottom - contentTop),
    } : null;

    const figures = Array.from(sheet.querySelectorAll("figure, .figure, img")).filter(isVisible).map((node) => {
      const box = node.getBoundingClientRect();
      return {
        selector: node.className || node.tagName.toLowerCase(),
        width: round(box.width),
        height: round(box.height),
        widthRatio: roundRatio(box.width / rect.width),
        heightRatio: roundRatio(box.height / rect.height),
        areaRatio: roundRatio((box.width * box.height) / (rect.width * rect.height)),
      };
    });

    const largestFigure = figures.reduce((largest, current) => {
      if (!largest || current.areaRatio > largest.areaRatio) return current;
      return largest;
    }, null);

    const cards = Array.from(sheet.querySelectorAll(cardSelectors)).filter(isVisible).map((node) => {
      const box = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      const fontSizePx = Number.parseFloat(style.fontSize || "");
      const smallestTextPx = smallestFontSize(node);
      return {
        selector: node.className || node.tagName.toLowerCase(),
        widthRatio: roundRatio(box.width / rect.width),
        areaRatio: roundRatio((box.width * box.height) / (rect.width * rect.height)),
        fontSizePx: Number.isFinite(fontSizePx) ? round(fontSizePx) : null,
        smallestFontSizePx: smallestTextPx === null ? null : round(smallestTextPx),
        overflowX: Math.max(0, node.scrollWidth - node.clientWidth),
        overflowY: Math.max(0, node.scrollHeight - node.clientHeight),
      };
    });
    const containerTextOverflowItems = Array.from(sheet.querySelectorAll("*")).filter((node) => {
      if (!isVisible(node) || node === sheet) {
        return false;
      }
      const text = textSnippet(node);
      if (text.length < 18) {
        return false;
      }
      const style = window.getComputedStyle(node);
      if (!isLikelyTextContainer(node, style)) {
        return false;
      }
      return Math.max(0, node.scrollWidth - node.clientWidth) > 1
        || Math.max(0, node.scrollHeight - node.clientHeight) > 1;
    }).map((node) => {
      const box = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      const overflowX = Math.max(0, node.scrollWidth - node.clientWidth);
      const overflowY = Math.max(0, node.scrollHeight - node.clientHeight);
      return {
        selector: selectorLabel(node),
        tag: node.tagName.toLowerCase(),
        overflowX: round(overflowX),
        overflowY: round(overflowY),
        clientWidth: round(node.clientWidth),
        clientHeight: round(node.clientHeight),
        scrollWidth: round(node.scrollWidth),
        scrollHeight: round(node.scrollHeight),
        rectWidth: round(box.width),
        rectHeight: round(box.height),
        whiteSpace: style.whiteSpace,
        overflowWrap: style.overflowWrap,
        wordBreak: style.wordBreak,
        hyphens: style.hyphens,
        text: textSnippet(node).slice(0, 120),
      };
    });
    const paragraphItems = Array.from(sheet.querySelectorAll(paragraphSelectors)).filter(isVisible).filter((node) => {
      return (node.textContent || "").trim().length >= 20;
    }).map((node) => {
      const style = window.getComputedStyle(node);
      const fontSizePx = Number.parseFloat(style.fontSize || "");
      if (!Number.isFinite(fontSizePx)) {
        return null;
      }
      const lineHeightPx = parsePx(style.lineHeight, fontSizePx);
      const marginBottomPx = parsePx(style.marginBottom, fontSizePx);
      return {
        fontSizePx,
        lineHeightRatio: lineHeightPx / fontSizePx,
        paragraphSpacingRatio: marginBottomPx / fontSizePx,
      };
    }).filter(Boolean);
    const textItems = Array.from(sheet.querySelectorAll(textSelectors)).filter(isVisible).filter((node) => {
      return (node.textContent || "").trim().length >= 20;
    }).map((node) => {
      const style = window.getComputedStyle(node);
      const fontSizePx = Number.parseFloat(style.fontSize || "");
      if (!Number.isFinite(fontSizePx)) {
        return null;
      }
      const lineHeightPx = parsePx(style.lineHeight, fontSizePx);
      return {
        fontSizePx,
        lineHeightRatio: lineHeightPx / fontSizePx,
      };
    }).filter(Boolean);
    const cardSmallTextCount = cards.filter((card) => {
      const size = card.smallestFontSizePx ?? card.fontSizePx;
      return size !== null && size < 11;
    }).length;
    const cardOverflowCount = cards.filter((card) => card.overflowX > 1 || card.overflowY > 1).length;
    const metaText = (sheet.innerText || sheet.textContent || "").replace(/\s+/g, " ").trim();
    const metaCandidates = [];
    for (const entry of metaPatterns) {
      const match = metaText.match(entry.pattern);
      if (match && !metaCandidates.some((candidate) => candidate.text === match[0])) {
        metaCandidates.push({
          kind: entry.kind,
          text: match[0],
        });
      }
    }

    return {
      page: sheet.dataset.page || null,
      client: {
        width: sheet.clientWidth,
        height: sheet.clientHeight,
      },
      scroll: {
        width: sheet.scrollWidth,
        height: sheet.scrollHeight,
      },
      overflow: {
        x: Math.max(0, sheet.scrollWidth - sheet.clientWidth),
        y: Math.max(0, sheet.scrollHeight - sheet.clientHeight),
      },
      rect: {
        width: round(rect.width),
        height: round(rect.height),
      },
      expectedA4Height: round(expectedA4Height),
      usesA4Aspect: Math.abs(rect.height - expectedA4Height) <= 2,
      contentBounds,
      density: hasVisibleContent ? {
        contentHeightRatio: roundRatio((contentBottom - contentTop) / rect.height),
        contentWidthRatio: roundRatio((contentRight - contentLeft) / rect.width),
        bottomGap: round(rect.bottom - contentBottom),
        bottomGapRatio: roundRatio((rect.bottom - contentBottom) / rect.height),
        topGap: round(contentTop - rect.top),
        topGapRatio: roundRatio((contentTop - rect.top) / rect.height),
      } : null,
      figures: {
        count: figures.length,
        largest: largestFigure,
        items: figures,
      },
      cards: {
        count: cards.length,
        gridLikeCount: cards.filter((card) => card.widthRatio <= 0.52 && card.areaRatio <= 0.22).length,
        totalAreaRatio: roundRatio(cards.reduce((total, card) => total + card.areaRatio, 0)),
        smallTextCount: cardSmallTextCount,
        minSmallestFontSizePx: cards.length
          ? round(Math.min(...cards.map((card) => card.smallestFontSizePx ?? card.fontSizePx ?? 999)))
          : null,
        overflowCount: cardOverflowCount,
        items: cards,
      },
      containerTextOverflow: {
        count: containerTextOverflowItems.length,
        items: containerTextOverflowItems,
      },
      typography: {
        sampleCount: textItems.length,
        minBodyFontSizePx: textItems.length
          ? round(Math.min(...textItems.map((item) => item.fontSizePx)))
          : null,
        minLineHeightRatio: textItems.length
          ? roundRatio(Math.min(...textItems.map((item) => item.lineHeightRatio)))
          : null,
        minParagraphSpacingRatio: paragraphItems.length
          ? roundRatio(Math.min(...paragraphItems.map((item) => item.paragraphSpacingRatio)))
          : null,
      },
      meta: {
        candidateCount: metaCandidates.length,
        candidates: metaCandidates,
      },
      issueCount: issues.length,
      issues,
    };
  });
}
"""

STYLE_RULES_EVAL_JS = r"""
() => {
  const styleText = Array.from(document.querySelectorAll("style"))
    .map((style) => style.textContent || "")
    .join("\n");

  return {
    a4Page: /@page\s*\{[^}]*size\s*:\s*A4/i.test(styleText),
    breakAvoid: /break-inside\s*:\s*avoid/i.test(styleText),
    printMedia: /@media\s+print/i.test(styleText),
    printColorAdjust: /print-color-adjust\s*:\s*exact/i.test(styleText),
  };
}
"""

def sheet_has_card_grid_antipattern(sheet: dict[str, Any]) -> bool:
    cards = sheet.get("cards") or {}
    count = cards.get("count", 0)
    return (
        cards.get("gridLikeCount", 0) > DEFAULT_MAX_CARD_GRID_COUNT
        or (
            count > DEFAULT_MAX_CARD_GRID_COUNT
            and cards.get("totalAreaRatio", 0) > DEFAULT_MAX_CARD_AREA_RATIO
            and cards.get("smallTextCount", 0) > 0
        )
    )

def sheet_has_compressed_typography(sheet: dict[str, Any]) -> bool:
    typography = sheet.get("typography") or {}
    min_body_font_size = typography.get("minBodyFontSizePx")
    min_line_height_ratio = typography.get("minLineHeightRatio")
    min_paragraph_spacing_ratio = typography.get("minParagraphSpacingRatio")
    small_body_text = (
        min_body_font_size is not None
        and min_body_font_size < DEFAULT_MIN_BODY_FONT_SIZE_PX
    )
    tight_line_height = (
        min_line_height_ratio is not None
        and min_line_height_ratio < DEFAULT_MIN_BODY_LINE_HEIGHT_RATIO
    )
    tight_paragraph_spacing = (
        min_paragraph_spacing_ratio is not None
        and min_paragraph_spacing_ratio < DEFAULT_MIN_PARAGRAPH_SPACING_RATIO
    )
    return small_body_text or (tight_line_height and tight_paragraph_spacing)

def sheet_has_meta_leakage_candidates(sheet: dict[str, Any]) -> bool:
    meta = sheet.get("meta") or {}
    return meta.get("candidateCount", 0) > 0

def sheet_has_inner_container_text_overflow(sheet: dict[str, Any]) -> bool:
    container_text_overflow = sheet.get("containerTextOverflow") or {}
    return container_text_overflow.get("count", 0) > 0

def sheet_has_svg_visual_enclosure_failures(sheet: dict[str, Any]) -> bool:
    svg_visual_enclosure = sheet.get("svgVisualEnclosure") or {}
    return svg_visual_enclosure.get("count", 0) > 0

def analyze_document(page: Any, html_path: Path) -> dict[str, Any]:
    sheet_count = page.locator(".sheet").count()
    if sheet_count == 0:
        raise RuntimeError("No `.sheet` pages found. This validator expects print pages to use the `.sheet` convention.")

    analysis = {
        "title": page.title(),
        "sheetCount": sheet_count,
        "images": page.locator("img").evaluate_all(IMAGE_EVAL_JS),
        "sheets": page.locator(".sheet").evaluate_all(SHEET_EVAL_JS),
        "rules": page.evaluate(STYLE_RULES_EVAL_JS),
    }
    attach_svg_visual_enclosure_issues(html_path=html_path, analysis=analysis)
    return analysis

def build_checks(summary: dict[str, Any]) -> tuple[dict[str, bool | None], dict[str, bool]]:
    analysis = summary["analysis"]
    sheets = analysis["sheets"]
    pdf_screenshots = summary["pdf"]["screenshots"]["pages"]
    parity_pages = summary["parity"]["pages"]
    required_checks = {
        "noConsoleProblems": len(summary["consoleMessages"]) == 0,
        "allImagesLoaded": all(
            image["complete"]
            and image["naturalWidth"] > 0
            and image["naturalHeight"] > 0
            for image in analysis["images"]
        ),
        "noSheetOverflow": all(
            sheet["overflow"]["x"] <= 1 and sheet["overflow"]["y"] <= 1
            for sheet in sheets
        ),
        "noDetectedClipping": all(
            sheet["issueCount"] == 0 for sheet in sheets
        ),
        "hasA4PageRule": analysis["rules"]["a4Page"],
        "hasPrintMediaRule": analysis["rules"]["printMedia"],
        "hasBreakAvoidRule": analysis["rules"]["breakAvoid"],
        "hasPrintColorAdjust": analysis["rules"]["printColorAdjust"],
        "sheetsUseA4Aspect": all(
            sheet.get("usesA4Aspect") for sheet in sheets
        ),
        "pdfOptimizedForFastView": summary["pdf"].get("optimization", {}).get("linearized") is True,
        "pdfPageCountMatches": summary["pdf"]["pageCount"] == analysis["sheetCount"],
        "pdfScreenshotCountMatchesHtml": len(pdf_screenshots) == len(summary["screenshots"]["pages"]),
        "pageScreenshotsUseA4Aspect": all(
            artifact["usesA4Aspect"] for artifact in summary["screenshots"]["pages"]
        ),
        "pdfScreenshotsUseA4Aspect": all(
            artifact["usesA4Aspect"] for artifact in pdf_screenshots
        ),
        "fastViewPdfPageCountMatchesHtml": summary["fastViewPdf"]["pageCount"] == analysis["sheetCount"],
        "fastViewPdfOptimizedForFastView": summary["fastViewPdf"].get("optimization", {}).get("linearized") is True,
        "avoidsCardGridAntipattern": all(
            not sheet_has_card_grid_antipattern(sheet) for sheet in sheets
        ),
        "maintainsComfortableTypographicRhythm": all(
            not sheet_has_compressed_typography(sheet) for sheet in sheets
        ),
        "avoidsMetaLeakageCandidates": all(
            not sheet_has_meta_leakage_candidates(sheet) for sheet in sheets
        ),
        "avoidsInnerContainerTextOverflow": all(
            not sheet_has_inner_container_text_overflow(sheet) for sheet in sheets
        ),
        "avoidsSvgVisualEnclosureFailures": all(
            not sheet_has_svg_visual_enclosure_failures(sheet) for sheet in sheets
        ),
    }
    optional_checks = {
        "pageQueryIsolatesSheets": all(
            artifact["visibleSheetCount"] == 1 for artifact in summary["screenshots"]["pages"]
        ),
        "pagesAvoidLargeBottomGaps": all(
            (sheet.get("density") or {}).get("bottomGapRatio", 0) <= 0.22
            for sheet in sheets
        ),
        "pdfVisualParityLooksClose": all(
            page.get("matchSuggested") is True for page in parity_pages
        ) if parity_pages else True,
    }
    return required_checks, optional_checks
