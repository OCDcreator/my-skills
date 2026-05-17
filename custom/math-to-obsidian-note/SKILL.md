---
name: math-to-obsidian-note
description: Convert uploaded math-related images or text into a polished Obsidian Markdown note under the user's math vault. Use when the user provides math problems, answers, solution steps, exam screenshots, handwritten notes, diagrams, formulas, or knowledge points and wants them organized as a Markdown document; also use when the workflow requires redrawing embedded math diagrams/images with gpt-image-2 and then reviewing the final note with the local obsidian-markdown skill.
---

# Math To Obsidian Note

## Overview

Turn math source material into a clean Obsidian note at `C:\Users\lt\Desktop\Obsidian Vault\数学`. Preserve mathematical meaning, convert formulas to LaTeX, redraw necessary diagrams with `gpt-image-2`, embed generated assets, and finish by checking the Markdown with `obsidian-markdown`.

## Workflow

1. Collect all provided source material: uploaded images, pasted text, answers, solution steps, and knowledge points.
2. Determine the note topic:
   - 大方向: broad subject area, such as `代数`, `几何`, `函数`, `概率统计`, `微积分`, `线性代数`, or another clear category from the content.
   - 细分方向: more specific topic, such as `二次函数`, `圆锥曲线`, `导数应用`, `排列组合`, or `矩阵特征值`.
   - If uncertain, infer the best concise Chinese labels from the content and avoid asking unless the source is too ambiguous to classify.
3. Create the Markdown file in `C:\Users\lt\Desktop\Obsidian Vault\数学` using this filename pattern:
   `大方向-细分方向-年-月日-小时分钟.md`
   Example: `几何-圆与切线-2026-0517-2130.md`.
4. Convert the content into an Obsidian-friendly math note:
   - Use Chinese as the default writing language unless the source is clearly in another language.
   - Use LaTeX for formulas: inline `$...$`, block `$$...$$`.
   - Keep the original problem statements, answer choices, given answers, and solution logic distinct.
   - Do not invent missing givens, diagrams, numbers, or conclusions. Mark unclear OCR as `（待核对：...）`.
5. Redraw images when needed:
   - If an uploaded image is mainly text or formulas, transcribe it instead of redrawing.
   - If it contains a geometry figure, graph, table-like visual, coordinate system, handwritten diagram, or image needed for understanding, call image generation/editing with model `gpt-image-2`.
   - Ask for a clean educational redraw faithful to the source: same labels, relative positions, axes, angles, tick marks, and key annotations; use a white or transparent background unless the user asks otherwise.
   - Save generated images beside the note in an attachment folder named `_assets/<note-stem>/`.
   - Embed images with Obsidian syntax, for example `![[ _assets/<note-stem>/figure-01.png ]]` without the spaces: `![[_assets/<note-stem>/figure-01.png]]`.
6. Review the final `.md` with the local `obsidian-markdown` skill at:
   `C:\Users\lt\Desktop\Write\custom-project\my-skills\external\kepano-obsidian-skills\obsidian-markdown\SKILL.md`
   Apply its rules for properties, embeds, callouts, LaTeX, and Obsidian syntax before finishing.

## Note Structure

Use this structure unless the source material strongly suggests a better one:

```markdown
---
title: 大方向-细分方向
date: YYYY-MM-DD
tags:
  - 数学
  - 大方向
  - 细分方向
source_type: 图片/文字/混合
---

# 大方向：细分方向

## 原始内容整理

## 题目

## 解答

## 知识点

## 易错点

## 相关链接
```

For multiple problems, repeat `## 题目 N`, `## 解答 N`, `## 知识点 N`, and keep shared knowledge points in a final summary section.

## Formatting Rules

- Prefer clear headings over dense paragraphs.
- Use numbered steps for solution processes.
- Use tables only when they improve comparison, such as formulas, conditions, or theorem variants.
- Use callouts sparingly:
  - `> [!tip]` for key methods.
  - `> [!warning]` for common traps.
  - `> [!example]` for representative examples.
- Keep answers and derivations checkable; include intermediate transformations for nontrivial algebra.
- Preserve original labels from diagrams and answer options exactly when legible.

## Final Checklist

- The file path is under `C:\Users\lt\Desktop\Obsidian Vault\数学`.
- The filename matches `大方向-细分方向-年-月日-小时分钟.md`.
- All formulas render as valid Markdown LaTeX.
- All generated/redrawn images are saved and embedded with valid Obsidian embeds.
- Ambiguous OCR or uncertain content is clearly marked for later checking.
- The final Markdown has been reviewed against `obsidian-markdown`.
