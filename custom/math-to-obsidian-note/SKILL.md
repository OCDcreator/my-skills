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
3. Decide the output directory:
   - If the user explicitly gives an output directory, use that directory.
   - If no output directory is specified and the source is a math problem, answer, solution, exam screenshot, or exercise, save the note under `C:\Users\lt\Desktop\Obsidian Vault\数学\高中数学\答疑`.
   - If no output directory is specified and the source is a high-school math knowledge point rather than a specific problem, save the note under `C:\Users\lt\Desktop\Obsidian Vault\数学\高中数学\<大方向>`, such as `导数`, `函数`, `数列`, `概率统计`, `立体几何`, or `解析几何`.
   - If the required high-school math `<大方向>` folder does not exist, create it before writing the note.
4. Create the Markdown file using this filename pattern:
   `大方向-细分方向-年-月日-小时分钟.md`
   Example: `几何-圆与切线-2026-0517-2130.md`.
5. Convert the content into an Obsidian-friendly math note:
   - Use Chinese as the default writing language unless the source is clearly in another language.
   - Use LaTeX for formulas: inline `$...$`, block `$$...$$`.
   - Use `\dfrac` for ordinary displayed or inline fractions so fractions remain readable. When a fraction's numerator or denominator contains another fraction, use `\dfrac` for the outer fraction and `\frac` for the nested inner fraction.
   - Keep the original problem statements, answer choices, given answers, and solution logic distinct.
   - Do not invent missing givens, diagrams, numbers, or conclusions. Mark unclear OCR as `（待核对：...）`.
   - Keep the note body knowledge-only. Do not include workflow metadata, source image paths, OCR/process notes, tool availability notes, or generation comments in the Markdown body.
6. Redraw images when needed:
   - If an uploaded image is mainly text or formulas, transcribe it instead of redrawing.
   - If it contains a geometry figure, graph, table-like visual, coordinate system, handwritten diagram, or image needed for understanding, call `scripts/generate_math_image.py` to generate or edit a clean redraw with model `gpt-image-2`.
   - Ask for a clean educational redraw faithful to the source: same labels, relative positions, axes, angles, tick marks, and key annotations; use a white or transparent background unless the user asks otherwise.
   - Configure image generation through environment variables:
     - `OPENAI_API_KEY` is required.
     - `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`.
     - `OPENAI_IMAGE_MODEL` defaults to `gpt-image-2`.
     - `OPENAI_IMAGE_API_DIALECT` defaults to `openai-native`.
     - `OPENAI_IMAGE_SIZE` defaults to `auto`; keep it `auto` unless the user explicitly asks for a fixed square, landscape, or portrait output.
     - `OPENAI_IMAGE_BACKGROUND` defaults to `auto`; use `transparent` only with `png` or `webp`.
   - The script also reads simple `.env` files from the current working directory, the skill directory, or a path specified by `OPENAI_IMAGE_ENV`; do not commit secrets.
   - Put layout intent in the prompt instead of hard-coding size: say whether the image is for an Obsidian Markdown note, whether it should be a compact inline figure, a landscape table/coordinate graph, a portrait multi-step diagram, or a square geometry sketch. Let the image model choose the actual size with `OPENAI_IMAGE_SIZE=auto`.
   - Use `png` by default for math note images because formulas, labels, axes, and thin lines should stay crisp. Use `webp` only when the user prioritizes small file size; avoid `jpeg` for math diagrams unless the source is photo-like.
   - Example generation command:
     `python C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\math-to-obsidian-note\scripts\generate_math_image.py --prompt "Clean high-school geometry diagram..." --output <asset-path>\figure-01.png`
   - Example redraw/edit command with a reference screenshot:
     `python C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\math-to-obsidian-note\scripts\generate_math_image.py --prompt "Redraw this math table as a clean white-background educational figure..." --input-image <source-image> --output <asset-path>\figure-01.png`
   - Save generated images beside the note in an attachment folder named `_assets/<note-stem>/`.
   - Embed images with Obsidian syntax, for example `![[ _assets/<note-stem>/figure-01.png ]]` without the spaces: `![[_assets/<note-stem>/figure-01.png]]`.
   - If the image script fails because credentials or API access are unavailable, do not add a note-body explanation. Mention this only in the final reply, and use a clear textual description, Markdown table, or `（待补图：...）` marker only when the missing diagram is necessary.
7. Review the final `.md` with the local `obsidian-markdown` skill at:
   `C:\Users\lt\Desktop\Write\custom-project\my-skills\external\kepano-obsidian-skills\obsidian-markdown\SKILL.md`
   Apply its rules for properties, embeds, callouts, LaTeX, and Obsidian syntax before finishing. This review must include readability checks, not just syntax checks.
8. Run the deterministic validator before final delivery:
   - For problem notes, run:
     `python C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\math-to-obsidian-note\scripts\validate_math_note.py <path-to-md> --content-type problem`
   - For high-school knowledge notes, run with the chosen big-direction folder:
     `python C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\math-to-obsidian-note\scripts\validate_math_note.py <path-to-md> --content-type knowledge --topic-dir <大方向>`
   - If the user explicitly requested a non-default output directory, add `--explicit-destination` to skip the default path check while keeping all other checks.
   If validation fails, fix the Markdown and rerun until it passes. Report the validation result in the final reply.

## Hard Constraints

The following constraints are not only style guidance. They must be checked manually and with `scripts/validate_math_note.py` when possible.

- Do not create sections named `原始内容整理`, `来源图片`, `图表处理`, `处理说明`, or similar process/log sections.
- Without an explicit user destination, put problem/exercise notes in `C:\Users\lt\Desktop\Obsidian Vault\数学\高中数学\答疑`.
- Without an explicit user destination, put high-school math knowledge-point notes in `C:\Users\lt\Desktop\Obsidian Vault\数学\高中数学\<大方向>` and create `<大方向>` if missing.
- Do not include source file paths in the Markdown body unless the user explicitly asks.
- Do not add `## 相关链接` or wikilinks unless the user explicitly asks for related links.
- Do not add frontmatter fields that are merely process metadata, such as `image_redraw`, OCR status, tool status, `created`, or `modified`, unless the user explicitly requests them.
- Put every original problem statement inside an Obsidian question callout: `> [!question] 题目（第 N 题）`.
- Use `> [!question]` for problem statements. Do not use `> [!example]` for the original problem.
- Preserve visible group labels inside the question callout, such as `C 组（能力挑战）`, directly under the callout title.
- Use Chinese parenthesized subproblem labels from the source, such as `(1)`, `(2)`, `(i)`, `(ii)`. Do not convert them to Markdown numbered lists unless the source itself is a simple numbered list and readability improves.
- Use block LaTeX only for formulas that deserve display treatment: definitions, important final formulas, multi-step derivations, aligned transformations, or long expressions.
- Use `\dfrac` instead of `\frac` for normal fractions. Use `\frac` only for nested fractions inside a numerator or denominator. Example: `$\dfrac{\frac{1}{2}+x}{3}$`, not `$\dfrac{\dfrac{1}{2}+x}{3}$`.
- Keep short numbers, short counts, and short equations inline. Examples: write `共有 $12$ 种情况`, `总数为 $C_8^2=28$`, and `无序对数为 $\dfrac{C_k^m \cdot 2^k}{2}$`; do not place `12` or `C_8^2=28` alone in `$$...$$`.
- Do not split a normal sentence around a block formula unless the formula is genuinely central and display-worthy.
- Tables from screenshots should usually be transcribed as Markdown tables. Redraw only when visual structure is needed for understanding beyond a simple table.
- Use `scripts/generate_math_image.py` for needed raster redraws instead of relying on an implicit model/tool call.

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

> [!question] 题目（第 N 题）
> 可选分组标签，例如：C 组（能力挑战）
>
> 题目正文。
>
> (1) 小问。
>
> (2) 小问。

## 解答

## 知识点

## 易错点
```

For multiple problems, use one `> [!question] 题目（第 N 题）` callout per problem, followed by that problem's answer sections. Keep shared knowledge points in a final summary section if useful.

## Formatting Rules

- Prefer clear headings over dense paragraphs.
- Use numbered steps for solution processes.
- Use tables only when they improve comparison, such as formulas, conditions, or theorem variants.
- Use callouts sparingly:
  - `> [!question]` for original problem statements. This is mandatory.
  - `> [!tip]` for key methods.
  - `> [!warning]` for common traps.
  - `> [!example]` only for additional examples created as learning aids, never for the original problem.
- Keep answers and derivations checkable; include intermediate transformations for nontrivial algebra.
- Preserve original labels from diagrams and answer options exactly when legible.
- Keep the Markdown visually natural in Obsidian reading view: avoid isolated one-token formula blocks, oversized spacing caused by unnecessary block math, and headings that describe the conversion process rather than the math.

## Final Checklist

- The file path follows the default destination rule: problems under `高中数学\答疑`, high-school knowledge points under `高中数学\<大方向>`, unless the user explicitly gave another destination.
- The filename matches `大方向-细分方向-年-月日-小时分钟.md`.
- The note body contains only math learning content, not processing notes or source path logs.
- Every problem statement is wrapped in `> [!question]`.
- No `## 相关链接` section or wikilinks are present unless explicitly requested.
- All formulas render as valid Markdown LaTeX.
- Fractions use `\dfrac` by default, with `\frac` reserved for nested fractions inside a numerator or denominator.
- Short counts and short equations are inline, not standalone block formulas.
- All generated/redrawn images are saved and embedded with valid Obsidian embeds.
- Needed raster redraws were generated through `scripts/generate_math_image.py` with `OPENAI_IMAGE_MODEL=gpt-image-2` unless the final reply explicitly reports a credential/API failure.
- Ambiguous OCR or uncertain content is clearly marked for later checking.
- If `gpt-image-2` was unavailable, that fact is reported in the final reply, not inserted into the note body.
- The final Markdown has been reviewed against `obsidian-markdown` for Obsidian syntax and against the hard constraints above for readability and noise.
- `scripts/validate_math_note.py` passes for the generated Markdown file.

## Validator

Use `scripts/validate_math_note.py` as the enforceable gate for mechanical rules. It checks filename shape, vault location, default destination for problem and high-school knowledge notes, forbidden process sections, source-path noise, required question callouts for problem notes, disallowed wikilinks, process frontmatter fields, and the `\dfrac` / nested `\frac` convention. It is intentionally conservative: when it reports a failure, revise the note instead of explaining the failure away.

## Image Script

Use `scripts/generate_math_image.py` as the enforceable path for `gpt-image-2` redraws. It calls the OpenAI-compatible Image API directly, reads `OPENAI_*` configuration from the environment or `.env`, writes the image file to the requested path, and prints only the output path on success.
