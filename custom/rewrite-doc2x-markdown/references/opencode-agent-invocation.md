# OpenCode Agent Invocation (optional high-performance dispatch path)

This skill's Steps 2.5 / 2.7 and the Parallel Chunking Workflow say "dispatch a subagent" without naming a mechanism. There are **two** valid dispatch runtimes:

1. **Host-native subagent** (default, always available) — the host agent (ZCode/Claude/etc.) spawns its own subagent via its native Agent/Task tool, feeding it the prompt templates in `analysis-retypesetting.md` / `question-block-rewrite-guide.md`.
2. **Pre-registered OpenCode agent** (optional optimization) — if the host can detect the `opencode` CLI **and** the project's `.opencode/agents/` defines the agents below, prefer them: they come pre-configured with model, scoped edit permissions, and a self-contained distilled system prompt, so the caller skips CLI exploration, model selection, and permission-flag fiddling.

**This is an OPTIONAL optimization.** The skill runs correctly under path 1 alone. Path 2 exists because OpenCode agents eliminate real per-session overhead (the orchestrator otherwise re-explores `opencode run` syntax, smoke-tests the model, and fiddles with `--dangerously-skip-permissions`). Use path 2 when available; fall back to path 1 silently otherwise.

## Detection (run before choosing the path)

```bash
command -v opencode >/dev/null 2>&1 \
  && test -f .opencode/agents/md-cleaner.md \
  && test -f .opencode/agents/question-block-rewriter.md \
  && test -f .opencode/agents/analysis-retypesetter.md \
  && echo "OPENCODE_AGENTS_AVAILABLE" || echo "FALLBACK_TO_HOST_SUBAGENT"
```

Run this from the project root (`scan-PDF-print-HTML/`). If it prints `FALLBACK_TO_HOST_SUBAGENT`, use the host-native path and do not mention OpenCode to the user.

## The three agents

| Agent | Skill step | Domain | System prompt embeds |
|---|---|---|---|
| `md-cleaner` | Step 1 (Auto-Fix) + Step 1-GATE | Mechanical cleanup: noise removal, delimiter normalization, `\frac`→`\dfrac`, callout `>` prefix, fused-formula splitting judgment | distilled `auto-fix-rules.md` + content-preservation iron law |
| `question-block-rewriter` | Step 2.7 | Rewrite 例题/练习/Q&A structure: stem→callout, options→table, sub-questions→own lines, analysis≤300 chars | `question-block-rewrite-guide.md` Subagent Template **with the Step 0 heading-preservation guard** (weak models drop headings — recorded 2026-06-28 failure) |
| `analysis-retypesetter` | Step 2.5 | Re-typeset 解析/解/证明: split one-massive-paragraph dumps into ≤300-char logical paragraphs, fix OCR typos, verify formula integrity | `analysis-retypesetting.md` Subagent Template |

Each agent's frontmatter sets `model: opencode-go/deepseek-v4-flash` and `permission: {edit: allow, write: allow, read: allow}`. The scoped permission map auto-approves file edits **for that agent only** — this is why the invocation below does **NOT** need `--dangerously-skip-permissions` (the global dangerous flag). Prefer the scoped permission; reserve the global flag for nothing.

## Standard invocation (background + JSON completion detection)

OpenCode has no `--timeout` flag, and a foreground `opencode run` can exceed a 10-minute bash timeout (the timeout kills the terminal but NOT the opencode process — learned the hard way). So run it **backgrounded** and detect completion via the JSON event stream:

```bash
# From the project root. <agent> = md-cleaner | question-block-rewriter | analysis-retypesetter
opencode run --agent <agent> --format json "<task message: absolute file path + range + what to do>" \
  > .opencode/<agent>-run.jsonl 2>&1 &
OC_PID=$!

# Poll until opencode exits (md5-stability is the pragmatic fallback if JSON parsing is unsure).
prev=""; stable=0
for i in $(seq 1 40); do
  if ! kill -0 $OC_PID 2>/dev/null; then echo "opencode exited"; break; fi
  cur=$(md5sum "<target-file>" | cut -d' ' -f1)
  [ "$cur" = "$prev" ] && stable=$((stable+1)) || stable=0
  prev=$cur
  [ "$stable" -ge 4 ] && { echo "file stable (md5)"; break; }
  sleep 15
done
```

- `--format json` streams JSONL (one event per line, each with a `type` field) to stdout — the terminal event signals completion. **The exact terminal `type` string is not in the official docs** (sourced from a community cheatsheet); treat md5-stability as the reliable fallback, as shown.
- The `<task message>` is passed **positionally**. Do NOT use `-f` (`--file`) for the message body — that attaches files, it does not substitute the prompt. Long prompts: build a shell variable / here-string and pass it positionally.
- `model` is set in the agent frontmatter, so **do not** also pass `-m` (precedence between frontmatter-`model` and CLI-`-m` is undocumented — set it in exactly one place).

## Caller contract — the orchestrator MUST verify, never trust the agent's self-report

This is a hard lesson from the session that produced this doc: **the orchestrating host agent is responsible for content integrity, not the OpenCode agent.** After every agent run:

1. **Diff the target file against its pre-run backup** (the orchestrator MUST create a timestamped `.bak` before invoking any agent). Confirm no semantic content was deleted.
2. **Re-run the metric guards**: example count (例N), callout count, `$` count, `\frac` total, `<img>` count — none may decrease (except `$`/`\frac` may *increase* from legitimate formula-list splitting / fraction standardization).
3. **Run the skill validator**: `py -3 scripts/validate_canonical_markdown.py --md <file> --fix` then `--check-proofreading`.
4. **Do not accept the agent's own "all checks passed" report as evidence** — re-run the checks independently and paste their output. (The agent's self-check is a guardrail, not proof.)

The OpenCode agents are scoped to their step (cleaner never rewrites question structure; rewriter never touches auto-fix noise). The orchestrator assembles results across agents and runs the cross-cutting gates (Step 1-GATE, Step 4 validator, Step 6 self-check).

## Known pitfalls (carry these forward)

- **Weak models drop headings.** The `question-block-rewriter` agent embeds Step 0 literal-echo specifically to prevent this. If you build a new rewrite-flavored agent, include the same guard. (Recorded failure: deepseek-v4-flash dropped ALL `#`/`##` headings under prompts v1 and v2; only an explicit "scan every `#` line, copy verbatim" step fixed it.)
- **No `--timeout`.** Bound the run in the wrapper (the polling loop above caps at ~10 min; raise for big docs).
- **Foreground bash timeout ≠ opencode exit.** A 10-minute foreground `timeout` kills your shell visibility but the opencode process keeps editing. Always background + poll.
- **`-f` is attachments, not message.** Pass the prompt positionally.
- **`permission: {edit/write/read: allow}` is agent-scoped, not file-scoped.** It still lets the agent edit any file in the project. The compensating control is the caller-contract diff/backup discipline above — never invoke an agent without a pre-run backup and a post-run independent verification.
- **Validator false positives** (ignore, don't "fix"): `已/己`, `入/人`, unbalanced-brace warnings from `\begin{array}`, HTML/MathML warnings for formula-heavy content, and the `lint_markdown_analysis_paragraphs` prose-count glitch where `\mathrm{}` tokens confuse the math-stripper (verify actual prose length by hand; a blank line between adjacent sub-answer lines satisfies the counter).

## When NOT to use the OpenCode path

- Host has no `opencode` CLI, or the agents aren't on disk → use host-native subagent (path 1). Do not fail.
- The task is a single small edit the host can do directly → don't spawn an agent at all.
- The user explicitly wants a specific different model → pass `-m <provider>/<model>` and accept the frontmatter/CLI precedence ambiguity (or edit the agent's frontmatter `model` for the session).
