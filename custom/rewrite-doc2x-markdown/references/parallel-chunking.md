# Parallel Chunking Workflow

Use this when the document exceeds a single-context threshold (> 6 pages, > 300 lines, or > 10,000 characters). For smaller documents, process single-threaded through Steps 1–7 in SKILL.md.

## Chunk Planning

1. Scan the raw transcript and find all `## Page N` markers.
2. Group pages into chunks of 3-5 pages each. Chunk boundaries must fall on `## Page N` markers.
   - If a question callout or table spans a page boundary, assign it to the chunk containing the starting page.
3. Create `markdown-rewrite-plan.md` with checked chunks:

```markdown
# Markdown Rewrite Plan
- [ ] Chunk 1: Page 274-277 (section description)
- [ ] Chunk 2: Page 278-281 (section description)
- [ ] Chunk 3: Page 282-284 (section description)
```

## Parallel Dispatch

| Total pages | Chunks | Parallel batch size | Batches |
|-------------|--------|---------------------|---------|
| 7-10        | 2-3    | 3                   | 1       |
| 11-20       | 4-6    | 4                   | 1       |
| 21-35       | 7-10   | 5                   | 2       |
| 36-50       | 11-15  | 5                   | 2-3     |
| >50         | 16+    | 5                   | 3+      |

For each chunk, dispatch a subagent with:
- The chunk's raw transcript (page range)
- The chunk's page images
- Instructions: execute Steps 1 through 2.7 (auto-fix → stop-gate → proofread → the **refinement chain** from `refinement-agent-chain.md`: skeleton → ①source-merger → ④subparts → ②options-table → ⑤analysis-retypesetter → ③comma-splitter → ⑥typo → ⑦displacement → ⑧key-point) on this chunk only, then apply Step 3 (structural format) formatting rules
- **Executor policy**: by default the main agent runs each chunk's roles itself. **Parallel chunk dispatch to subagents happens ONLY when the user explicitly asks** ("用子代理 / dispatch agents / parallelize") — do NOT auto-dispatch by document size. When dispatching, use the OpenCode chain agents (`md-cleaner`, `source-skeleton-builder`, then the 8 refinement roles) if detected, else host-native subagent. See `references/opencode-agent-invocation.md` for the detection command, invocation template, and the **mandatory caller-side verification contract** (never trust the agent's self-report — diff against a pre-run backup and re-run the validator independently).
- The current `refinement-agent-chain.md`, `canonical-markdown-rules.md`, `auto-fix-rules.md`, and `analysis-retypesetting.md` as reference
- **CRITICAL**: each chunk must run the refinement chain roles in order, each role running its `--only` self-check (split fused formulas ③, re-typeset analysis ⑤, rewrite question-block structure ①②④, fix OCR typos ⑥, etc.). These are the most commonly missed steps
- **BOUNDARY RULE** (Forbidden Pattern F5): the subagent must NOT include content from the next chunk. If the chunk ends mid-page or at a section boundary, the subagent stops at its last assigned line. It must NOT "continue" into the next chunk to "finish the section"
- Output: cleaned Markdown for the chunk + `[TO VERIFY]` markers encountered

After each batch completes, check for failed chunks (subagent error or timeout > 5 min). Mark failed chunks in `markdown-rewrite-plan.md` and re-dispatch them in the next batch.

## Assembly

1. Concatenate chunks in page order.
2. **Critical — Callout Prefix Check**: After assembly, run `rg -c '^\[!question\]' source-transcript.md` and `rg -c '^\[!example\]' source-transcript.md`. If any result is > 0, STOP. The `>` prefix was lost during assembly. Fix immediately by prefixing all bare `[!question]` and `[!example]` lines with `> `.
3. Check chunk boundaries for:
   - **Duplicate content**: if the last section of chunk N is also the first section of chunk N+1, remove the duplicate. This commonly happens when a section heading appears on the boundary page. Keep the version from the chunk where the section's EXAMPLES/CONTENT live, not the chunk that only has the heading.
   - Truncated formulas or tables at page breaks.
   - Heading level consistency across chunks (adjacent chunks must not jump levels). **When `doc2x/outline.md` exists**, re-verify the assembled document's heading depths against the outline after concatenation — chunk-local decisions can drift at boundaries.
   - Duplicate or missing `## Page N` markers.
4. Merge all `[TO VERIFY: ...]` markers from subagent reports into a single list.
5. Run Step 1-GATE checks on the assembled document (fused formulas, `\$` corruption, `\begin{array}` count, callout count).
6. Run Steps 4-5 (validate --fix → validate --check-proofreading) on the assembled document.
7. Run Step 6 (self-check) on the assembled document.
8. Run a final read-through pass to verify callouts, analysis blocks, tables, formulas, and image references did not break during concatenation.
