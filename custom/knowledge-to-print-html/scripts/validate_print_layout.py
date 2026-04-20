from __future__ import annotations

import argparse
import base64
import glob
import importlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_ASPECT_RATIO = A4_WIDTH_MM / A4_HEIGHT_MM
DEFAULT_PARITY_DIFF_THRESHOLD = 0.035
DEFAULT_MAX_CARD_GRID_COUNT = 2
DEFAULT_MAX_CARD_AREA_RATIO = 0.35
DEFAULT_MIN_CARD_TEXT_SIZE_PX = 11.0
DEFAULT_MIN_BODY_FONT_SIZE_PX = 11.5
DEFAULT_MIN_BODY_LINE_HEIGHT_RATIO = 1.35
DEFAULT_MIN_PARAGRAPH_SPACING_RATIO = 0.45
SVG_FRAME_MIN_WIDTH = 140.0
SVG_FRAME_MIN_HEIGHT = 80.0
SVG_FRAME_BACKGROUND_AREA_RATIO = 0.75
SVG_FRAME_OVERFLOW_TOLERANCE = 4.0
SVG_FRAME_VERTICAL_SLACK = 120.0
SVG_TEXT_BOX_MAX_WIDTH = 420.0
SVG_TEXT_BOX_MAX_HEIGHT = 220.0
SVG_STRUCTURED_FRAME_MAX_WIDTH = 600.0
SVG_STRUCTURED_FRAME_MAX_HEIGHT = 400.0
SVG_TEXT_BOX_MIN_SIDE_PADDING = 12.0
SVG_TEXT_BOX_MIN_TOP_PADDING = 12.0
SVG_TEXT_BOX_MIN_BOTTOM_PADDING = 10.0
SVG_TEXT_BOX_MAX_HORIZONTAL_IMBALANCE = 14.0
SVG_TEXT_BOX_MAX_VERTICAL_IMBALANCE = 16.0


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

RECT_EVAL_JS = r"""
sheet => {
  const rect = sheet.getBoundingClientRect();
  return {
    width: Math.round(rect.width * 100) / 100,
    height: Math.round(rect.height * 100) / 100,
    hidden: sheet.hidden,
  };
}
"""

VISIBLE_SHEET_COUNT_EVAL_JS = r"""
elements => elements.filter((sheet) => !sheet.hidden).length
"""

IMAGE_DIFF_EVAL_JS = r"""
async payload => {
  const { leftDataUrl, rightDataUrl, sampleSize } = payload;
  const loadImage = src => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to decode comparison image."));
    image.src = src;
  });

  const [leftImage, rightImage] = await Promise.all([
    loadImage(leftDataUrl),
    loadImage(rightDataUrl),
  ]);

  const canvas = document.createElement("canvas");
  canvas.width = sampleSize;
  canvas.height = sampleSize;
  const context = canvas.getContext("2d", { willReadFrequently: true });

  const sampleImage = image => {
    context.clearRect(0, 0, sampleSize, sampleSize);
    context.drawImage(image, 0, 0, sampleSize, sampleSize);
    return context.getImageData(0, 0, sampleSize, sampleSize).data;
  };

  const leftPixels = sampleImage(leftImage);
  const rightPixels = sampleImage(rightImage);
  let totalDifference = 0;

  for (let index = 0; index < leftPixels.length; index += 4) {
    const leftGray = (
      leftPixels[index] * 0.299 +
      leftPixels[index + 1] * 0.587 +
      leftPixels[index + 2] * 0.114
    ) / 255;
    const rightGray = (
      rightPixels[index] * 0.299 +
      rightPixels[index + 1] * 0.587 +
      rightPixels[index + 2] * 0.114
    ) / 255;
    totalDifference += Math.abs(leftGray - rightGray);
  }

  return Math.round((totalDifference / (sampleSize * sampleSize)) * 10000) / 10000;
}
"""


def run_bootstrap_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def ensure_python_package(
    import_name: str,
    *,
    pip_name: str,
    auto_install: bool,
) -> Any:
    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        if not auto_install:
            raise RuntimeError(
                f"Missing Python dependency `{pip_name}`. "
                f"Install it with: {' '.join([sys.executable, '-m', 'pip', 'install', pip_name])}"
            ) from exc

    run_bootstrap_command([sys.executable, "-m", "pip", "install", pip_name])

    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Automatic installation finished, but `{pip_name}` still could not be imported."
        ) from exc


def try_install_system_browser() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.extend(
            [
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Microsoft.Edge",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Google.Chrome",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.extend(
            [
                ["brew", "install", "--cask", "microsoft-edge"],
                ["brew", "install", "--cask", "google-chrome"],
            ]
        )
    elif shutil.which("apt-get"):
        commands.extend(
            [
                ["apt-get", "install", "-y", "chromium-browser"],
                ["apt-get", "install", "-y", "chromium"],
            ]
        )

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        browser_path = resolve_browser_path(None)
        if browser_path:
            return browser_path

    return None


def resolve_qpdf_path() -> str | None:
    candidates = [
        shutil.which("qpdf"),
        r"C:\Program Files\qpdf\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf\bin\qpdf.exe",
        "/opt/homebrew/bin/qpdf",
        "/usr/local/bin/qpdf",
        "/usr/bin/qpdf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    glob_patterns = [
        r"C:\Program Files\qpdf*\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf*\bin\qpdf.exe",
        str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/QPDF.QPDF_*" / "*" / "qpdf.exe"),
    ]
    for pattern in glob_patterns:
        matches = sorted(glob.glob(pattern))
        for match in matches:
            if Path(match).exists():
                return str(Path(match))
    return None


def try_install_qpdf() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.append(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "QPDF.QPDF",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.append(["brew", "install", "qpdf"])
    elif shutil.which("apt-get"):
        commands.append(["apt-get", "install", "-y", "qpdf"])

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        qpdf_path = resolve_qpdf_path()
        if qpdf_path:
            return qpdf_path

    return None


def inspect_pdf_fast_view_features(path: Path) -> dict[str, bool]:
    data = path.read_bytes()
    head = data[:2048]
    return {
        "linearized": b"/Linearized" in head,
        "objectStreams": b"/ObjStm" in data,
        "xrefStream": b"/XRef" in data,
    }


def optimize_pdf_for_fast_view(
    raw_pdf_path: Path,
    final_pdf_path: Path,
    *,
    auto_install: bool,
) -> dict[str, Any]:
    qpdf_path = resolve_qpdf_path()
    if not qpdf_path and auto_install:
        qpdf_path = try_install_qpdf()

    raw_bytes = raw_pdf_path.stat().st_size
    if not qpdf_path:
        if raw_pdf_path != final_pdf_path:
            shutil.copyfile(raw_pdf_path, final_pdf_path)
        features = inspect_pdf_fast_view_features(final_pdf_path)
        return {
            "tool": None,
            "linearized": features["linearized"],
            "objectStreams": features["objectStreams"],
            "xrefStream": features["xrefStream"],
            "rawBytes": raw_bytes,
            "optimizedBytes": final_pdf_path.stat().st_size,
            "optimized": False,
            "reason": "qpdf was not available and could not be installed automatically.",
        }

    command = [
        qpdf_path,
        "--linearize",
        "--object-streams=generate",
        str(raw_pdf_path),
        str(final_pdf_path),
    ]
    run_bootstrap_command(command)
    features = inspect_pdf_fast_view_features(final_pdf_path)
    return {
        "tool": "qpdf",
        "toolPath": qpdf_path,
        "linearized": features["linearized"],
        "objectStreams": features["objectStreams"],
        "xrefStream": features["xrefStream"],
        "rawBytes": raw_bytes,
        "optimizedBytes": final_pdf_path.stat().st_size,
        "optimized": features["linearized"],
        "reason": None if features["linearized"] else "qpdf ran but the output is not linearized.",
    }


def build_fast_view_pdf(
    html_page_artifacts: list[dict[str, Any]],
    output_dir: Path,
    prefix: str,
    *,
    auto_install: bool,
) -> dict[str, Any]:
    fitz = load_pymupdf(auto_install)
    raw_pdf_path = output_dir / f"{prefix}-fastview-raw.pdf"
    final_pdf_path = output_dir / f"{prefix}-fastview.pdf"
    document = fitz.open()

    try:
        for artifact in html_page_artifacts:
            image_path = Path(artifact["path"])
            page = document.new_page(width=594.96, height=841.92)
            page.insert_image(page.rect, filename=str(image_path), keep_proportion=False)
        document.save(raw_pdf_path, garbage=4, deflate=True, clean=True)
    finally:
        document.close()

    optimization = optimize_pdf_for_fast_view(
        raw_pdf_path,
        final_pdf_path,
        auto_install=auto_install,
    )
    try:
        raw_pdf_path.unlink()
    except OSError:
        pass

    page_count, media_boxes = inspect_pdf_document(
        final_pdf_path,
        auto_install=auto_install,
    )
    return {
        "path": str(final_pdf_path),
        "bytes": final_pdf_path.stat().st_size,
        "pageCount": page_count,
        "mediaBoxes": media_boxes,
        "source": "html-page-screenshots",
        "optimization": optimization,
    }


def ensure_playwright_runtime(auto_install: bool) -> None:
    if not auto_install:
        return
    run_bootstrap_command([sys.executable, "-m", "playwright", "install", "chromium"])


def load_playwright(auto_install: bool) -> Any:
    module = ensure_python_package(
        "playwright.sync_api",
        pip_name="playwright",
        auto_install=auto_install,
    )
    return module.sync_playwright


def load_pymupdf(auto_install: bool) -> Any:
    return ensure_python_package(
        "fitz",
        pip_name="pymupdf",
        auto_install=auto_install,
    )

ISOLATE_PAGE_EVAL_JS = r"""
pageNumber => {
  const sheets = Array.from(document.querySelectorAll(".sheet"));
  if (sheets.length === 0) return { visibleSheetCount: 0, targetFound: false };

  const pageKey = String(pageNumber);
  const sheetByDataPage = sheets.find((sheet) => sheet.dataset.page === pageKey);
  const targetSheet = sheetByDataPage || sheets[pageNumber - 1] || sheets[0];

  for (const sheet of sheets) {
    const shouldShow = sheet === targetSheet;
    sheet.hidden = !shouldShow;
    sheet.toggleAttribute("aria-hidden", !shouldShow);
    sheet.dataset.printReviewVisible = shouldShow ? "true" : "false";
  }

  return {
    visibleSheetCount: sheets.filter((sheet) => !sheet.hidden).length,
    targetFound: Boolean(targetSheet),
    targetPage: targetSheet.dataset.page || String(sheets.indexOf(targetSheet) + 1),
  };
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local print-first handout.html and export screenshots, PDF, and a JSON report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_print_layout.py --html artifacts/knowledge-handout/topic/handout.html\n"
            "  python scripts/validate_print_layout.py --html artifacts/knowledge-handout/topic/handout.html --device-scale-factor 3.125 --out-dir artifacts/knowledge-handout/topic/screens/high-dpi\n"
            "\n"
            "Use the high-DPI example when you need a raster/image-only PDF at roughly 300 DPI."
        ),
    )
    parser.add_argument("--html", required=True, help="Path to the local handout.html file.")
    parser.add_argument(
        "--out-dir",
        help="Directory for screenshots, PDF, and report. Defaults to <html-dir>/screens/py-latest.",
    )
    parser.add_argument(
        "--browser-path",
        help="Optional Chrome/Chromium executable path. Falls back to common system paths or Playwright's bundled browser.",
    )
    parser.add_argument(
        "--prefix",
        help="Artifact filename prefix. Defaults to the HTML filename stem.",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=300,
        help="Extra wait after page load before capture. Default: 300.",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1400,
        help="Viewport width for screen captures. Default: 1400.",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1800,
        help="Viewport height for screen captures. Default: 1800.",
    )
    parser.add_argument(
        "--device-scale-factor",
        type=float,
        default=1.5,
        help="Device scale factor for captures. Default: 1.5. Use 3.125 for roughly 300 DPI A4 image-only PDF output.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Disable automatic dependency installation and browser provisioning.",
    )
    parser.add_argument(
        "--parity-sample-size",
        type=int,
        default=64,
        help="Downsample size for lightweight HTML-vs-PDF visual diff scoring. Default: 64.",
    )
    return parser.parse_args()


def resolve_browser_path(explicit_path: str | None) -> str | None:
    candidates = [
        explicit_path,
        os.environ.get("PLAYWRIGHT_CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    return None


def with_query_params(url: str, **params: Any) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def default_output_dir(html_path: Path) -> Path:
    return html_path.parent / "screens" / "py-latest"


def parse_svg_number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else default


def parse_svg_numbers(value: str | None) -> list[float]:
    if not value:
        return []
    return [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", value)]


def parse_translate_transform(transform: str | None) -> tuple[float, float]:
    if not transform:
        return (0.0, 0.0)

    translate_x = 0.0
    translate_y = 0.0
    for func_name, args in re.findall(r"([A-Za-z]+)\(([^)]*)\)", transform):
        if func_name != "translate":
            continue
        numbers = parse_svg_numbers(args)
        if numbers:
            translate_x += numbers[0]
            translate_y += numbers[1] if len(numbers) > 1 else 0.0
    return (translate_x, translate_y)


def parse_svg_viewbox(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox")
    numbers = parse_svg_numbers(view_box)
    if len(numbers) == 4 and numbers[2] > 0 and numbers[3] > 0:
        return (numbers[2], numbers[3])

    width = parse_svg_number(root.attrib.get("width"), default=0.0)
    height = parse_svg_number(root.attrib.get("height"), default=0.0)
    return (width, height)


def parse_svg_class_font_sizes(root: ET.Element) -> dict[str, float]:
    class_font_sizes: dict[str, float] = {}

    for style_node in root.iter():
        if style_node.tag.split("}")[-1] != "style":
            continue
        style_text = style_node.text or ""
        for selector_block, body in re.findall(r"([^{}]+)\{([^}]*)\}", style_text):
            font_match = re.search(r"font-size\s*:\s*([0-9.]+)px", body)
            if not font_match:
                font_match = re.search(r"font\s*:[^;]*?([0-9.]+)px", body)
            if not font_match:
                continue
            font_size = float(font_match.group(1))
            for class_name in re.findall(r"\.([A-Za-z0-9_-]+)", selector_block):
                class_font_sizes[class_name] = font_size

    return class_font_sizes


def resolve_svg_font_size(
    element: ET.Element,
    class_font_sizes: dict[str, float],
    *,
    fallback: float = 16.0,
) -> float:
    if "font-size" in element.attrib:
        return parse_svg_number(element.attrib.get("font-size"), default=fallback)

    style_attr = element.attrib.get("style", "")
    style_match = re.search(r"font-size\s*:\s*([0-9.]+)px", style_attr)
    if style_match:
        return float(style_match.group(1))

    font_match = re.search(r"font\s*:\s*[^;]*?([0-9.]+)px", style_attr)
    if font_match:
        return float(font_match.group(1))

    class_names = element.attrib.get("class", "").split()
    for class_name in class_names:
        if class_name in class_font_sizes:
            return class_font_sizes[class_name]

    return fallback


def estimate_svg_text_width(text: str, font_size: float) -> float:
    units = 0.0
    for character in text:
        if character.isspace():
            units += 0.35
        elif ord(character) > 127:
            units += 1.0
        elif character.isupper():
            units += 0.68
        else:
            units += 0.56
    return max(font_size * 0.8, units * font_size)


def compute_svg_element_bounds(
    element: ET.Element,
    *,
    offset: tuple[float, float],
    class_font_sizes: dict[str, float],
) -> dict[str, Any] | None:
    tag = element.tag.split("}")[-1]
    offset_x, offset_y = offset

    if tag == "rect":
        width = parse_svg_number(element.attrib.get("width"), default=0.0)
        height = parse_svg_number(element.attrib.get("height"), default=0.0)
        if width <= 0 or height <= 0:
            return None
        left = parse_svg_number(element.attrib.get("x"), default=0.0) + offset_x
        top = parse_svg_number(element.attrib.get("y"), default=0.0) + offset_y
        return {
            "tag": "rect",
            "left": left,
            "top": top,
            "right": left + width,
            "bottom": top + height,
            "width": width,
            "height": height,
            "text": None,
            "fontSize": None,
        }

    if tag != "text":
        return None

    text_content = re.sub(r"\s+", " ", "".join(element.itertext())).strip()
    if not text_content:
        return None

    font_size = resolve_svg_font_size(element, class_font_sizes)
    x_values = parse_svg_numbers(element.attrib.get("x"))
    y_values = parse_svg_numbers(element.attrib.get("y"))
    x_position = (x_values[0] if x_values else 0.0) + offset_x
    y_position = (y_values[0] if y_values else 0.0) + offset_y
    width = estimate_svg_text_width(text_content, font_size)
    height = font_size * 1.2
    anchor = element.attrib.get("text-anchor", "start")

    if anchor == "middle":
        left = x_position - (width / 2)
    elif anchor == "end":
        left = x_position - width
    else:
        left = x_position

    top = y_position - (font_size * 0.85)
    return {
        "tag": "text",
        "left": left,
        "top": top,
        "right": left + width,
        "bottom": top + height,
        "width": width,
        "height": height,
        "text": text_content,
        "fontSize": font_size,
    }


def collect_svg_drawables(
    node: ET.Element,
    *,
    parent_key: tuple[int, ...],
    offset: tuple[float, float],
    class_font_sizes: dict[str, float],
    elements: list[dict[str, Any]],
    order_counter: list[int],
) -> None:
    translate_x, translate_y = parse_translate_transform(node.attrib.get("transform"))
    current_offset = (offset[0] + translate_x, offset[1] + translate_y)

    for child_index, child in enumerate(list(node)):
        bounds = compute_svg_element_bounds(
            child,
            offset=current_offset,
            class_font_sizes=class_font_sizes,
        )
        order = order_counter[0]
        order_counter[0] += 1
        if bounds:
            class_names = child.attrib.get("class", "").split()
            elements.append(
                {
                    "tag": bounds["tag"],
                    "left": bounds["left"],
                    "top": bounds["top"],
                    "right": bounds["right"],
                    "bottom": bounds["bottom"],
                    "width": bounds["width"],
                    "height": bounds["height"],
                    "text": bounds["text"],
                    "fontSize": bounds["fontSize"],
                    "parentKey": parent_key,
                    "order": order,
                    "classes": class_names,
                }
            )

        collect_svg_drawables(
            child,
            parent_key=parent_key + (child_index,),
            offset=current_offset,
            class_font_sizes=class_font_sizes,
            elements=elements,
            order_counter=order_counter,
        )


def horizontal_overlap_ratio(
    left_a: float,
    right_a: float,
    left_b: float,
    right_b: float,
) -> float:
    overlap = max(0.0, min(right_a, right_b) - max(left_a, left_b))
    smallest_width = max(1.0, min(right_a - left_a, right_b - left_b))
    return overlap / smallest_width


def inspect_svg_visual_enclosure(svg_path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError, UnicodeDecodeError):
        return []

    svg_width, svg_height = parse_svg_viewbox(root)
    svg_area = max(svg_width * svg_height, 1.0)
    class_font_sizes = parse_svg_class_font_sizes(root)
    elements: list[dict[str, Any]] = []
    collect_svg_drawables(
        root,
        parent_key=(),
        offset=(0.0, 0.0),
        class_font_sizes=class_font_sizes,
        elements=elements,
        order_counter=[0],
    )

    issues: list[dict[str, Any]] = []
    candidate_frames = [
        element
        for element in elements
        if element["tag"] == "rect"
        and element["width"] >= SVG_FRAME_MIN_WIDTH
        and element["height"] >= SVG_FRAME_MIN_HEIGHT
        and (element["width"] * element["height"]) < (svg_area * SVG_FRAME_BACKGROUND_AREA_RATIO)
    ]

    for frame in candidate_frames:
        overflowing_items: list[dict[str, Any]] = []
        padding_issue: dict[str, Any] | None = None
        is_small_text_box = (
            frame["width"] <= SVG_TEXT_BOX_MAX_WIDTH
            and frame["height"] <= SVG_TEXT_BOX_MAX_HEIGHT
        )
        is_structured_content_frame = (
            frame["width"] <= SVG_STRUCTURED_FRAME_MAX_WIDTH
            and frame["height"] <= SVG_STRUCTURED_FRAME_MAX_HEIGHT
        )
        vertical_limit = frame["bottom"] + min(
            SVG_FRAME_VERTICAL_SLACK,
            max(36.0, frame["height"] * 0.45),
        )
        for element in elements:
            if element["parentKey"] != frame["parentKey"]:
                continue
            if element["order"] <= frame["order"]:
                continue
            if element["tag"] not in {"rect", "text"}:
                continue

            center_x = (element["left"] + element["right"]) / 2
            center_y = (element["top"] + element["bottom"]) / 2
            if element["tag"] == "text":
                overlaps_horizontally = (
                    (frame["left"] - 12.0) <= element["left"] <= (frame["right"] - 12.0)
                    or (frame["left"] + 8.0) <= center_x <= (frame["right"] - 8.0)
                )
            else:
                overlaps_horizontally = (
                    horizontal_overlap_ratio(
                        frame["left"],
                        frame["right"],
                        element["left"],
                        element["right"],
                    ) >= 0.6
                    or (frame["left"] - 6.0) <= center_x <= (frame["right"] + 6.0)
                )
            if not overlaps_horizontally:
                continue
            if center_y < (frame["top"] - 12.0) or center_y > vertical_limit:
                continue

            overflow_left = max(0.0, frame["left"] - element["left"])
            overflow_right = max(0.0, element["right"] - frame["right"])
            overflow_top = max(0.0, frame["top"] - element["top"])
            overflow_bottom = max(0.0, element["bottom"] - frame["bottom"])
            max_overflow = max(
                overflow_left,
                overflow_right,
                overflow_top,
                overflow_bottom,
            )
            if max_overflow <= SVG_FRAME_OVERFLOW_TOLERANCE:
                continue
            if element["tag"] == "text":
                font_size = element.get("fontSize") or 16.0
                if max_overflow <= font_size * 0.35:
                    continue

            overflowing_items.append(
                {
                    "tag": element["tag"],
                    "text": element.get("text"),
                    "left": round(element["left"], 2),
                    "top": round(element["top"], 2),
                    "right": round(element["right"], 2),
                    "bottom": round(element["bottom"], 2),
                    "overflowLeft": round(overflow_left, 2),
                    "overflowRight": round(overflow_right, 2),
                    "overflowTop": round(overflow_top, 2),
                    "overflowBottom": round(overflow_bottom, 2),
                }
            )

        if is_small_text_box or is_structured_content_frame:
            content_text_items = []
            content_rect_items = []
            for element in elements:
                if element["parentKey"] != frame["parentKey"]:
                    continue
                if element["order"] <= frame["order"] or element["tag"] not in {"rect", "text"}:
                    continue
                center_x = (element["left"] + element["right"]) / 2
                center_y = (element["top"] + element["bottom"]) / 2
                if (
                    (frame["left"] + 4.0) <= center_x <= (frame["right"] - 4.0)
                    and (frame["top"] + 2.0) <= center_y <= (frame["bottom"] + 8.0)
                ):
                    if element["tag"] == "text":
                        content_text_items.append(element)
                    elif (
                        0.0 < element["width"] < frame["width"]
                        and 0.0 < element["height"] < frame["height"]
                    ):
                        content_rect_items.append(element)

            content_items = content_text_items
            if is_structured_content_frame and content_rect_items:
                content_items = [*content_text_items, *content_rect_items]

            if content_text_items and content_items:
                content_left = min(item["left"] for item in content_items)
                content_right = max(item["right"] for item in content_items)
                content_top = min(item["top"] for item in content_items)
                content_bottom = max(item["bottom"] for item in content_items)
                padding = {
                    "left": round(frame["left"] - content_left if content_left < frame["left"] else content_left - frame["left"], 2),
                    "right": round(frame["right"] - content_right, 2),
                    "top": round(content_top - frame["top"], 2),
                    "bottom": round(frame["bottom"] - content_bottom, 2),
                }
                compact_multiline_box = is_small_text_box and frame["width"] <= 260.0 and len(content_text_items) >= 4
                structured_content_frame = is_structured_content_frame and bool(content_rect_items)
                horizontal_imbalance = abs(padding["left"] - padding["right"])
                vertical_imbalance = abs(padding["top"] - padding["bottom"])
                fails_padding = (
                    padding["left"] < SVG_TEXT_BOX_MIN_SIDE_PADDING
                    or padding["right"] < SVG_TEXT_BOX_MIN_SIDE_PADDING
                    or padding["top"] < SVG_TEXT_BOX_MIN_TOP_PADDING
                    or padding["bottom"] < SVG_TEXT_BOX_MIN_BOTTOM_PADDING
                    or (
                        compact_multiline_box
                        and horizontal_imbalance > SVG_TEXT_BOX_MAX_HORIZONTAL_IMBALANCE
                    )
                    or (
                        (compact_multiline_box or structured_content_frame)
                        and vertical_imbalance > SVG_TEXT_BOX_MAX_VERTICAL_IMBALANCE
                    )
                )
                if fails_padding:
                    padding_issue = {
                        "contentBounds": {
                            "left": round(content_left, 2),
                            "right": round(content_right, 2),
                            "top": round(content_top, 2),
                            "bottom": round(content_bottom, 2),
                        },
                        "padding": padding,
                        "horizontalImbalance": round(horizontal_imbalance, 2),
                        "verticalImbalance": round(vertical_imbalance, 2),
                        "compactMultilineBox": compact_multiline_box,
                        "structuredContentFrame": structured_content_frame,
                    }

        rect_overflows = [item for item in overflowing_items if item["tag"] == "rect"]
        text_overflows = [item for item in overflowing_items if item["tag"] == "text"]
        if not rect_overflows and not text_overflows:
            if padding_issue is None:
                continue
        if not is_small_text_box and padding_issue is None and not rect_overflows and len(text_overflows) < 2:
            continue

        issues.append(
            {
                "svgPath": str(svg_path),
                "kind": (
                    "small_text_box_overflow"
                    if is_small_text_box and text_overflows
                    else "small_text_box_padding_failure"
                    if is_small_text_box and padding_issue is not None
                    else "svg_inner_padding_failure"
                    if padding_issue is not None
                    else "group_enclosure_failure"
                ),
                "frame": {
                    "left": round(frame["left"], 2),
                    "top": round(frame["top"], 2),
                    "right": round(frame["right"], 2),
                    "bottom": round(frame["bottom"], 2),
                    "width": round(frame["width"], 2),
                    "height": round(frame["height"], 2),
                },
                "overflowItems": overflowing_items,
                "paddingIssue": padding_issue,
            }
        )

    return issues


def resolve_local_image_path(html_path: Path, image_src: str | None) -> Path | None:
    if not image_src:
        return None
    if image_src.startswith(("http://", "https://", "data:")):
        return None

    normalized_src = image_src.split("?", 1)[0].split("#", 1)[0]
    return (html_path.parent / normalized_src).resolve()


def attach_svg_visual_enclosure_issues(
    *,
    html_path: Path,
    analysis: dict[str, Any],
) -> None:
    sheet_index = {
        str(sheet.get("page")): sheet
        for sheet in analysis["sheets"]
    }
    for sheet in analysis["sheets"]:
        sheet["svgVisualEnclosure"] = {"count": 0, "items": []}

    all_issues: list[dict[str, Any]] = []
    for image in analysis["images"]:
        image_path = resolve_local_image_path(html_path, image.get("src"))
        if not image_path or image_path.suffix.lower() != ".svg" or not image_path.exists():
            continue

        svg_issues = inspect_svg_visual_enclosure(image_path)
        for issue in svg_issues:
            item = {
                "src": image.get("src"),
                "alt": image.get("alt"),
                "page": image.get("page"),
                "svgPath": issue["svgPath"],
                "frame": issue["frame"],
                "overflowItems": issue["overflowItems"],
            }
            all_issues.append(item)
            page_key = str(image.get("page"))
            if page_key in sheet_index:
                sheet_index[page_key]["svgVisualEnclosure"]["items"].append(item)

    for sheet in analysis["sheets"]:
        sheet["svgVisualEnclosure"]["count"] = len(sheet["svgVisualEnclosure"]["items"])

    analysis["svgVisualEnclosureIssues"] = {
        "count": len(all_issues),
        "items": all_issues,
    }


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


def isolate_page_for_capture(page: Any, page_number: int) -> dict[str, Any]:
    isolation = page.evaluate(ISOLATE_PAGE_EVAL_JS, page_number)
    if isolation["visibleSheetCount"] != 1:
        raise RuntimeError(
            f"Unable to isolate page {page_number}; "
            f"visible sheets: {isolation['visibleSheetCount']}."
        )
    return isolation


def page_sheet_locator(page: Any, page_number: int) -> Any:
    data_page_locator = page.locator(f'.sheet[data-page="{page_number}"]')
    if data_page_locator.count() > 0:
        return data_page_locator.first
    return page.locator(".sheet").nth(page_number - 1)


def read_png_dimensions(path: Path) -> tuple[int, int]:
    png_bytes = path.read_bytes()
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Expected PNG screenshot artifact: {path}")
    return struct.unpack(">II", png_bytes[16:24])


def path_to_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_a4_clip(box: dict[str, float]) -> dict[str, float]:
    width = float(box["width"])
    return {
        "x": float(box["x"]),
        "y": float(box["y"]),
        "width": width,
        "height": width / A4_ASPECT_RATIO,
    }


def capture_page_artifacts(
    context: Any,
    base_url: str,
    sheet_count: int,
    output_dir: Path,
    prefix: str,
    settle_ms: int,
) -> list[dict[str, Any]]:
    page_artifacts: list[dict[str, Any]] = []

    for page_number in range(1, sheet_count + 1):
        page = context.new_page()
        try:
            page.goto(
                with_query_params(base_url, print=1, page=page_number),
                wait_until="load",
            )
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(settle_ms)

            isolation = isolate_page_for_capture(page, page_number)
            screenshot_path = output_dir / f"{prefix}-print-page-{page_number}.png"

            target_locator = page_sheet_locator(page, page_number)
            target_locator.scroll_into_view_if_needed()
            bounding_box = target_locator.bounding_box()
            if not bounding_box:
                raise RuntimeError(f"Unable to measure page {page_number} for A4 clipping.")
            page.screenshot(
                path=str(screenshot_path),
                clip=build_a4_clip(bounding_box),
            )

            rect = target_locator.evaluate(RECT_EVAL_JS)
            visible_sheet_count = page.locator(".sheet").evaluate_all(
                VISIBLE_SHEET_COUNT_EVAL_JS
            )
            screenshot_width_px, screenshot_height_px = read_png_dimensions(
                screenshot_path
            )
            screenshot_aspect_ratio = screenshot_width_px / screenshot_height_px
            screenshot_uses_a4_aspect = abs(screenshot_aspect_ratio - A4_ASPECT_RATIO) <= 0.02

            page_artifacts.append(
                {
                    "page": page_number,
                    "path": str(screenshot_path),
                    "width": rect["width"],
                    "height": rect["height"],
                    "hidden": rect["hidden"],
                    "visibleSheetCount": visible_sheet_count,
                    "isolatedTargetPage": isolation["targetPage"],
                    "screenshotWidthPx": screenshot_width_px,
                    "screenshotHeightPx": screenshot_height_px,
                    "screenshotAspectRatio": round(screenshot_aspect_ratio, 4),
                    "usesA4Aspect": screenshot_uses_a4_aspect,
                }
            )
        finally:
            page.close()

    return page_artifacts


def render_pdf_page_artifacts(
    pdf_path: Path,
    output_dir: Path,
    prefix: str,
    html_page_artifacts: list[dict[str, Any]],
    *,
    auto_install: bool,
) -> list[dict[str, Any]]:
    fitz = load_pymupdf(auto_install)
    document = fitz.open(str(pdf_path))
    artifacts: list[dict[str, Any]] = []

    try:
        for page_number, pdf_page in enumerate(document, start=1):
            html_artifact = next(
                (artifact for artifact in html_page_artifacts if artifact["page"] == page_number),
                None,
            )
            target_width = (
                int(html_artifact["screenshotWidthPx"])
                if html_artifact
                else int(round(pdf_page.rect.width * 2))
            )
            zoom = target_width / float(pdf_page.rect.width)
            pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            screenshot_path = output_dir / f"{prefix}-pdf-page-{page_number}.png"
            pixmap.save(str(screenshot_path))
            screenshot_width_px, screenshot_height_px = read_png_dimensions(screenshot_path)
            screenshot_aspect_ratio = screenshot_width_px / screenshot_height_px

            artifacts.append(
                {
                    "page": page_number,
                    "path": str(screenshot_path),
                    "widthPt": round(float(pdf_page.rect.width), 2),
                    "heightPt": round(float(pdf_page.rect.height), 2),
                    "screenshotWidthPx": screenshot_width_px,
                    "screenshotHeightPx": screenshot_height_px,
                    "screenshotAspectRatio": round(screenshot_aspect_ratio, 4),
                    "usesA4Aspect": abs(screenshot_aspect_ratio - A4_ASPECT_RATIO) <= 0.02,
                }
            )
    finally:
        document.close()

    return artifacts


def inspect_pdf_document(
    pdf_path: Path,
    *,
    auto_install: bool,
) -> tuple[int, list[dict[str, float]]]:
    fitz = load_pymupdf(auto_install)
    document = fitz.open(str(pdf_path))
    try:
        media_boxes = [
            {
                "widthPt": round(float(page.rect.width), 2),
                "heightPt": round(float(page.rect.height), 2),
            }
            for page in document
        ]
        return document.page_count, media_boxes
    finally:
        document.close()


def build_pdf_html_parity(
    context: Any,
    html_page_artifacts: list[dict[str, Any]],
    pdf_page_artifacts: list[dict[str, Any]],
    *,
    sample_size: int,
) -> list[dict[str, Any]]:
    comparison_page = context.new_page()
    comparison_page.set_content("<!doctype html><html><body></body></html>")
    parity_pages: list[dict[str, Any]] = []

    try:
        pdf_index = {artifact["page"]: artifact for artifact in pdf_page_artifacts}
        for html_artifact in html_page_artifacts:
            page_number = html_artifact["page"]
            pdf_artifact = pdf_index.get(page_number)
            if not pdf_artifact:
                parity_pages.append(
                    {
                        "page": page_number,
                        "htmlScreenshot": html_artifact["path"],
                        "pdfScreenshot": None,
                        "visualDiffScore": None,
                        "matchSuggested": False,
                    }
                )
                continue

            visual_diff_score = comparison_page.evaluate(
                IMAGE_DIFF_EVAL_JS,
                {
                    "leftDataUrl": path_to_data_url(Path(html_artifact["path"])),
                    "rightDataUrl": path_to_data_url(Path(pdf_artifact["path"])),
                    "sampleSize": sample_size,
                },
            )
            same_dimensions = (
                abs(html_artifact["screenshotWidthPx"] - pdf_artifact["screenshotWidthPx"]) <= 4
                and abs(html_artifact["screenshotHeightPx"] - pdf_artifact["screenshotHeightPx"]) <= 4
            )
            match_suggested = (
                visual_diff_score <= DEFAULT_PARITY_DIFF_THRESHOLD
                and same_dimensions
                and pdf_artifact["usesA4Aspect"]
            )

            parity_pages.append(
                {
                    "page": page_number,
                    "htmlScreenshot": html_artifact["path"],
                    "pdfScreenshot": pdf_artifact["path"],
                    "htmlScreenshotWidthPx": html_artifact["screenshotWidthPx"],
                    "htmlScreenshotHeightPx": html_artifact["screenshotHeightPx"],
                    "pdfScreenshotWidthPx": pdf_artifact["screenshotWidthPx"],
                    "pdfScreenshotHeightPx": pdf_artifact["screenshotHeightPx"],
                    "sameDimensions": same_dimensions,
                    "visualDiffScore": visual_diff_score,
                    "matchSuggested": match_suggested,
                }
            )
    finally:
        comparison_page.close()

    return parity_pages


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


def launch_browser(playwright: Any, *, browser_path: str | None, auto_install: bool) -> tuple[Any, str | None]:
    launch_kwargs: dict[str, Any] = {"headless": True}
    if browser_path:
        launch_kwargs["executable_path"] = browser_path

    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as first_error:
        if not auto_install:
            raise

    ensure_playwright_runtime(auto_install=True)
    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as second_error:
        fallback_browser_path = resolve_browser_path(None) or try_install_system_browser()
        if fallback_browser_path:
            return (
                playwright.chromium.launch(
                    headless=True,
                    executable_path=fallback_browser_path,
                ),
                fallback_browser_path,
            )
        raise RuntimeError(
            "Unable to launch Chromium even after automatic Playwright/browser provisioning."
        ) from second_error


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file does not exist: {html_path}")

    output_dir = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else default_output_dir(html_path)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or html_path.stem
    base_url = html_path.as_uri()
    browser_path = resolve_browser_path(args.browser_path)
    auto_install = not args.no_auto_install
    console_messages: list[dict[str, str]] = []
    sync_playwright = load_playwright(auto_install)

    with sync_playwright() as playwright:
        browser, browser_path = launch_browser(
            playwright,
            browser_path=browser_path,
            auto_install=auto_install,
        )
        context = browser.new_context(
            viewport={
                "width": args.viewport_width,
                "height": args.viewport_height,
            },
            device_scale_factor=args.device_scale_factor,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_messages.append(
                {"type": message.type, "text": message.text}
            )
            if message.type in {"warning", "error"}
            else None,
        )
        page.on(
            "pageerror",
            lambda error: console_messages.append(
                {"type": "pageerror", "text": str(error)}
            ),
        )

        page.goto(with_query_params(base_url, print=1), wait_until="load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(args.settle_ms)

        analysis = analyze_document(page, html_path)

        stacked_path = output_dir / f"{prefix}-screen-stacked.png"
        page.screenshot(path=str(stacked_path), full_page=True)

        page_artifacts = capture_page_artifacts(
            context=context,
            base_url=base_url,
            sheet_count=analysis["sheetCount"],
            output_dir=output_dir,
            prefix=prefix,
            settle_ms=args.settle_ms,
        )
        fast_view_pdf = build_fast_view_pdf(
            page_artifacts,
            output_dir,
            prefix,
            auto_install=auto_install,
        )

        page.emulate_media(media="print")
        pdf_path = output_dir / f"{prefix}.pdf"
        raw_pdf_path = output_dir / f"{prefix}-raw.pdf"
        page.pdf(
            path=str(raw_pdf_path),
            print_background=True,
            prefer_css_page_size=True,
        )
        pdf_optimization = optimize_pdf_for_fast_view(
            raw_pdf_path,
            pdf_path,
            auto_install=auto_install,
        )
        try:
            raw_pdf_path.unlink()
        except OSError:
            pass
        pdf_page_artifacts = render_pdf_page_artifacts(
            pdf_path,
            output_dir,
            prefix,
            page_artifacts,
            auto_install=auto_install,
        )
        parity_pages = build_pdf_html_parity(
            context,
            page_artifacts,
            pdf_page_artifacts,
            sample_size=args.parity_sample_size,
        )
        pdf_page_count, media_boxes = inspect_pdf_document(
            pdf_path,
            auto_install=auto_install,
        )

        browser.close()

    summary: dict[str, Any] = {
        "htmlPath": str(html_path),
        "outputDir": str(output_dir),
        "browser": {
            "resolvedPath": browser_path,
            "usesBundledBrowser": browser_path is None,
            "autoInstallEnabled": auto_install,
        },
        "analysis": analysis,
        "consoleMessages": console_messages,
        "screenshots": {
            "stacked": str(stacked_path),
            "pages": page_artifacts,
        },
        "pdf": {
            "path": str(pdf_path),
            "bytes": pdf_path.stat().st_size,
            "pageCount": pdf_page_count,
            "mediaBoxes": media_boxes,
            "optimization": pdf_optimization,
            "screenshots": {
                "pages": pdf_page_artifacts,
            },
        },
        "fastViewPdf": fast_view_pdf,
        "parity": {
            "sampleSize": args.parity_sample_size,
            "diffThreshold": DEFAULT_PARITY_DIFF_THRESHOLD,
            "pages": parity_pages,
        },
    }

    checks, optional_checks = build_checks(summary)
    summary["checks"] = checks
    summary["optionalChecks"] = optional_checks
    summary["pass"] = all(value is True or value is None for value in checks.values())

    report_path = output_dir / f"{prefix}-validation-report.json"
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    print(f"Report: {report_path}")
    print(f"Pass: {summary['pass']}")
    print(f"Pages: {analysis['sheetCount']}")
    print(f"PDF: {pdf_path}")
    print(f"Fast-view PDF: {fast_view_pdf['path']}")
    if optional_checks:
        print(f"Optional checks: {json.dumps(optional_checks, ensure_ascii=False)}")
    if failed_checks:
        print(f"Failed checks: {', '.join(failed_checks)}")

    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
