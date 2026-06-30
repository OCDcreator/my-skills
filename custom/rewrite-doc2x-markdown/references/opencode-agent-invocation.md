# OpenCode Agent Invocation (optional dispatch path)

<!-- evolved 2026-06-30 — the refinement chain now has 8 fine-grained roles (plus md-cleaner) and a default-main-agent policy. The "three agents" model is replaced by "nine agents" + the main-agent-default rule. -->

## The default executor is the MAIN AGENT, not a subagent

**Read this first — it overrides any older "dispatch a subagent" wording elsewhere.** Every refinement role (the chain in `refinement-agent-chain.md`) is executed by the **main agent itself by default**: the main agent reads each role's logic, runs it inline, and runs that role's `--only` self-check right after. Dispatch to a subagent (OpenCode agent OR host-native subagent) happens **only when the user explicitly asks** ("用子代理 / dispatch agents / parallelize"). Do NOT auto-dispatch by document size.

The OpenCode agents below are the **opt-in** runtime for when the user does ask for subagents. Each embeds the *same* role logic and the *same* `--only` self-check as the main-agent path — verification is path-independent.

## The two dispatch runtimes (used only on opt-in)

1. **Host-native subagent** — the host agent (ZCode/Claude/etc.) spawns its own subagent via its native Agent/Task tool, feeding it the role logic from `refinement-agent-chain.md`.
2. **Pre-registered OpenCode agent** — if the host can detect the `opencode` CLI **and** the project's `.opencode/agents/` defines the agents below, prefer them: pre-configured with model, scoped edit permissions, and a self-contained distilled system prompt, so the caller skips CLI exploration, model selection, and permission-flag fiddling.

**Path 2 is an optimization.** The skill runs correctly under the main-agent path alone, or path 1 alone. Path 2 exists because OpenCode agents eliminate real per-session overhead when subagents are requested.

## Detection (run only when the user asked for subagents)

```bash
command -v opencode >/dev/null 2>&1 \
  && test -f .opencode/agents/md-cleaner.md \
  && test -f .opencode/agents/source-skeleton-builder.md \
  && test -f .opencode/agents/question-source-merger.md \
  && test -f .opencode/agents/question-subparts-splitter.md \
  && test -f .opencode/agents/question-options-to-table.md \
  && test -f .opencode/agents/analysis-retypesetter.md \
  && test -f .opencode/agents/math-comma-splitter.md \
  && test -f .opencode/agents/ocr-typo-fixer.md \
  && test -f .opencode/agents/sentence-displacement-fixer.md \
  && test -f .opencode/agents/key-point-marker.md \
  && echo "OPENCODE_AGENTS_AVAILABLE" || echo "FALLBACK_TO_HOST_SUBAGENT"
```

Run this from the project root (`scan-PDF-print-HTML/`). If it prints `FALLBACK_TO_HOST_SUBAGENT`, use the host-native path (path 1) or the main-agent path, and do not mention OpenCode to the user.

## The nine agents (+1 legacy fallback)

| Agent | Chain role | Domain | Self-check `--only` |
|---|---|---|---|
| `md-cleaner` | Step 1 (Auto-Fix) + Step 1-GATE | Mechanical cleanup: noise removal, delimiter normalization, `\frac`→`\dfrac`, callout `>` prefix, fused-formula splitting judgment | (runs full validator + its own GATE) |
| `source-skeleton-builder` | ★ skeleton | Establish `#`/`##`/`###` hierarchy (from `outline.md` or semantic judgment) + block boundaries | `lint_headings_and_print_noise,lint_numeric_outline_labels` |
| `question-source-merger` | ① | Title line = label + source only; normalize bare-number titles; strip OCR noise | `lint_question_callout_title_attached` |
| `question-subparts-splitter` | ④ | `(1)(2)(3)` sub-questions onto own `>` lines with spacers | `lint_bare_question_starts,lint_qa_ordering` |
| `question-options-to-table` | ② | A/B/C/D options → 1×4 / 2×2 / 4×1 table, center-aligned | `lint_choice_options,lint_tables` |
| `analysis-retypesetter` | ⑤ | Re-typeset 解析/解/证明 into ≤300-char paragraphs (SOLE owner of analysis) | `lint_markdown_analysis_paragraphs,lint_analysis` |
| `math-comma-splitter` | ③ | Split enumerated/fused commas out of `$...$`; preserve structural commas | `lint_formula_dangling_tail,lint_list_inside_math,lint_long_inline_formula,lint_inline_math_spacing` |
| `ocr-typo-fixer` | ⑥ | Fix confusable chars (己/已/巳, 人/入, 末/未, i↔1) against raw | `--check-proofreading` (NOT `--only`; lint_proofreading lives on its own branch) |
| `sentence-displacement-fixer` | ⑦ | Return OCR-displaced stem-tail/analysis-opener sentences to place | `lint_qa_ordering` (coarse) |
| `key-point-marker` | ⑧ | ≤2 color marks/block from fixed palette, pure-text spans | (no lint; IRON LAW checklist) |
| ~~`question-block-rewriter`~~ | **legacy fallback** | The old monolithic agent (title+options+subparts+analysis bundled). Retained for when OpenCode is requested but the fine-grained agents are unavailable, or for a tiny-doc fast path. NOT the default. | `question-block-rewrite-guide.md` rules |

Each agent's frontmatter sets `model: opencode-go/deepseek-v4-flash` and `permission: {edit: allow, write: allow, read: allow}`. The scoped permission map auto-approves file edits **for that agent only** — this is why the invocation below does **NOT** need `--dangerously-skip-permissions` (the global dangerous flag). Prefer the scoped permission; reserve the global flag for nothing.

## Per-role self-check (path-independent)

Every refinement agent runs its `--only` self-check **before reporting done**, fix FAILs in place, retry ≤3, mark `[TO VERIFY]` if still failing. This is the same contract the main-agent path follows — that is why a subagent return and a main-agent pass are equally trustworthy.

```bash
py -3 scripts/validate_canonical_markdown.py --md "<file>" --only "<this agent's lints from the table above>"
```

The `--only` flag was added 2026-06-30 precisely so each role sees only its own FAILs (the validator's `LintMessage` has no category field; `--only` filters by lint-function name). See `tests/test_only_flag.py`.

## Standard invocation (background + JSON completion detection)

OpenCode has no `--timeout` flag, and a foreground `opencode run` can exceed a 10-minute bash timeout (the timeout kills the terminal but NOT the opencode process — learned the hard way). So run it **backgrounded** and detect completion via the JSON event stream:

```bash
# From the project root. <agent> = any of the 9 chain agents in the table above
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

- **Weak models drop headings.** The `source-skeleton-builder` and `question-source-merger` agents embed heading-preservation discipline (the skeleton role establishes levels; later roles must not remove them). The legacy `question-block-rewriter` keeps its Step 0 literal-echo guard. If you build a new rewrite-flavored agent, include the same guard. (Recorded failure: deepseek-v4-flash dropped ALL `#`/`##` headings under prompts v1 and v2; only an explicit "scan every `#` line, copy verbatim" step fixed it.)
- **No `--timeout`.** Bound the run in the wrapper (the polling loop above caps at ~10 min; raise for big docs).
- **Foreground bash timeout ≠ opencode exit.** A 10-minute foreground `timeout` kills your shell visibility but the opencode process keeps editing. Always background + poll.
- **`-f` is attachments, not message.** Pass the prompt positionally.
- **`permission` is agent-scoped, not file-scoped.** An `allow` still lets the agent edit any file in the project. The compensating control is the caller-contract diff/backup discipline above — never invoke an agent without a pre-run backup and a post-run independent verification.
- **Validator false positives** (ignore, don't "fix"): `已/己`, `入/人`, unbalanced-brace warnings from `\begin{array}`, HTML/MathML warnings for formula-heavy content, and the `lint_markdown_analysis_paragraphs` prose-count glitch where `\mathrm{}` tokens confuse the math-stripper (verify actual prose length by hand; a blank line between adjacent sub-answer lines satisfies the counter).

## Agent permission lockdown (MANDATORY — evolved 2026-06-30)

<!-- evolved 2026-06-30 — rework: role ⑤ analysis-retypesetter, given only {edit/write/read: allow}, used the `task` tool to spawn a grandchild analysis-retypesetter subagent. The grandchild had no boundary discipline and destroyed 6 option tables built by role ② + reverted role ①'s 例6 label. Root cause: leaf agents must NEVER re-dispatch. Fix: deny every tool except the 4 they actually need. -->

**Every refinement-chain agent is a LEAF EXECUTOR.** It must edit the file itself with `edit`/`write` — it must never re-dispatch via `task`, never load a `skill`, never touch MCP tools, never manage todos. The canonical frontmatter `permission` block (applied to all 11 agents in `.opencode/agents/`):

```yaml
permission:
  edit: allow
  write: allow
  read: allow
  bash: allow
  task: deny          # ← forbids grandchild dispatch (the ⑤ root cause)
  skill: deny
  todowrite: deny     # leaf agents shouldn't burn tokens on self-todos
  grep: deny          # use bash rg instead
  glob: deny
  webfetch: deny
  websearch: deny
  lsp: deny           # md files have no LSP
  patch: deny
  question: deny      # batch mode, no interactive prompts
  memory: deny
  "lean-ctx_*": deny  # MCP wildcard — covers ctx_read/_edit/_shell/_call/... (ctx_edit + ctx_shell are second write/exec channels that bypass the native tools)
  "doc2x_*": deny
  "web-reader_*": deny
  "web-search-prime_*": deny
  "zread_*": deny
  "zai-mcp-server_*": deny
```

**Verified empirically on opencode 1.17.11** (probe agent `_perm-test` + real `analysis-retypesetter`): after this block, the agent's visible toolset is reduced to exactly `{bash, edit, read, write}` — all four. `task`, every MCP tool, `todowrite`, etc. are absent from the tool list, and a `task` call attempt returns `"Model tried to call unavailable tool 'task'"`.

**Three things this lockdown depends on (verified, not assumed):**

1. **Agent-level `deny` DOES override project-level `"*":"allow"`.** The project `opencode.json` ships with `"permission": {"*":"allow"}`. GitHub issue #15664 warned this could silently override `deny` rules — that bug did **not** recur on 1.17.11; the agent-scoped `deny` wins for that agent. (If a future opencode upgrade breaks this, the probe in `.opencode/run-logs/perm-verify-real.jsonl` is the regression detector — re-run it after upgrades.)
2. **Wildcard `"<server>_*": deny` is the reliable MCP form**, NOT bare `doc2x: deny` (which matches nothing because real tool names are `doc2x_doc2x_parse_pdf_submit` — double-prefixed). Quoting the key (`"doc2x_*":`) is required because `*` is not a bare YAML token.
3. **Enumerating `lean-ctx_ctx_read/_tree/_search/_shell` individually is NOT enough** — that server also exposes `lean-ctx_ctx_edit` (a second write channel) and `lean-ctx_ctx_call`/`_session`. Only the `lean-ctx_*` wildcard catches all of them. Always use the wildcard for MCP servers.

**Regression check (run if permissions seem to misbehave):** re-dispatch any agent with the prompt "list every tool currently visible to you" and confirm the answer is exactly `{bash, edit, read, write}`. If any MCP or `task` tool leaks back, the opencode version's permission resolution changed — re-verify before trusting agent isolation.

## When NOT to use the OpenCode path

- Host has no `opencode` CLI, or the agents aren't on disk → use host-native subagent (path 1). Do not fail.
- The task is a single small edit the host can do directly → don't spawn an agent at all.
- The user explicitly wants a specific different model → pass `-m <provider>/<model>` and accept the frontmatter/CLI precedence ambiguity (or edit the agent's frontmatter `model` for the session).
