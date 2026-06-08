# Preflight Density Check

Run this before full drafting when the artifact is likely to be long, reference-heavy, or visually dense.

Trigger this check when any of these are true:

- likely more than 8 A4 pages
- 3 or more figures/tables
- 20 or more references
- both annotated guidance and clean submission content are requested
- the topic needs heavy quotations, tables, or endnotes

## Goal

Catch page-density collapse before `handout.html` exists.

This check is not about micro-spacing. It is about whether the document structure is realistic.

## Preflight Questions

Answer these before drafting the full article:

1. What is the artifact mode?
2. Is this really one artifact, or should it split into two variants?
3. How many pages are reserved for the main body?
4. How many pages are reserved for figures/tables?
5. How many pages are reserved for bibliography/endnotes?
6. Which sections are likely to become visually dense?

## Warning Signs

You are on a bad path if:

- the outline already needs tiny reference text to fit
- the bibliography count is rising but citation coverage is unclear
- several figures are being postponed to the back just to make the body fit
- annotated callouts are being layered on top of a clean essay draft
- a “cover page” is consuming space in a document that is already tight

## Recovery Moves

Prefer these fixes early:

1. split coaching copy from submission copy
2. reduce the number of page-level teaching motifs
3. combine related short sections
4. reserve bibliography/endnote pages explicitly
5. move some explanation from figure text into body prose
6. reduce unnecessary decorative blocks before touching type size

## What Not To Use As The Primary Fix

Do not rely on:

- smaller body text
- tighter line height
- crushed paragraph spacing
- more card-like boxes

Those choices often make the validator fail later under `maintainsComfortableTypographicRhythm`, and even when they pass technically, the result feels stressed.
