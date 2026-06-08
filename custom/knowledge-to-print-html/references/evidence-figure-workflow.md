# Evidence Figure Workflow

Use this file when the artifact needs charts, tables, model diagrams, or paper-ready figures that are supposed to represent real evidence.

## First Decide The Figure Type

Every figure should be classified before it is built.

### Explanatory Figure

Use when the figure teaches:

- a process
- a mechanism
- a structure
- a comparison

These can often be built as SVG diagrams.

### Evidence Figure

Use when the figure is meant to show:

- measured data
- extracted values from sources
- literature-backed comparisons
- model structure tied to a cited framework

These should not start from freeform image generation.

## Source-Backed Pipeline

For evidence figures, use this order:

1. identify the source-backed numbers, categories, or relationships
2. record the source in `research.md`
3. draft the chart/table from those values
4. refine the visual styling
5. attach a caption and source note

If the source values are not available yet, stop and research them before polishing the figure.

## What Not To Do

Do not:

- ask an image model to invent empirical chart contents
- leave unrelated labels, slogans, decorative badges, or poster text inside a paper figure
- make the chart look like a marketing infographic when the artifact claims to be a formal paper
- create a figure first and try to backfill the evidence later

## If You Use An Image Model Anyway

Use it only as a finishing pass on a tightly specified figure concept.

Provide:

- the real data or categorical structure
- exact axis labels
- series names
- caption intent
- paper-safe styling constraints

Do not prompt vaguely.

Bad:

- “make a cool chart about ideology”

Better:

- “render a clean two-series academic line chart with the following year-by-year values...”

Even then, prefer direct chart construction when possible.

## Placement Rules

Evidence figures should usually appear:

- near the first paragraph that interprets them
- with nearby caption/source information
- in a size that remains readable at print scale

Do not dump them at the end by habit.

## Minimum Caption Standard

For evidence figures, captions should usually answer:

- what the figure shows
- what unit/group/time range is represented
- where the data came from

Short is fine. Decorative is not.
