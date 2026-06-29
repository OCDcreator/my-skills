# Step 1-GATE — Auto-Fix Stop-Gate (MANDATORY)

Run these **mandatory verification checks** after Step 1 (Auto-Fix) and before Step 2 (Proofread). If ANY check fails, go back and fix before continuing. Do NOT skip this gate.

This gate runs again after Step 2.7 assembly — formula integrity (`$` count, `\begin{array}` count, callout count) must survive every rewrite pass.

```bash
# Check 1: No fused formulas remain (Rule 4)
# Look for commas between independent relations inside $...$
rg -n '\$[^$]*[，,][^$]*[=<>≥≤][^$]*\$' source-transcript.md
# If any results appear that contain TWO independent relations split by a comma, they must be split.
# Exception: a single relation with a comma in a function argument like $f(x,y)$ is NOT fused.

# Check 2: No boundary spaces in inline math (Rule 2)
rg -n '\$ +[^\$]' source-transcript.md   # opening $ followed by space
rg -n '[^\$] +\$' source-transcript.md   # closing $ preceded by space
# Both should return 0 results (excluding $$ display blocks).

# Check 3: No \$ corruption (Forbidden Pattern F2)
rg -n '\\\$' source-transcript.md
# Must return 0 results.

# Check 4: \begin{array} count unchanged (Forbidden Pattern F3)
# Count in source-transcript.md should match raw transcript
rg -c '\\begin\{array\}' source-transcript.md
rg -c '\\begin\{array\}' doc2x/page-transcript.raw.md
# Counts must be equal.

# Check 5: No \begin{cases} introduced
rg -c '\\begin\{cases\}' source-transcript.md
# Must be 0 unless raw transcript already had cases.

# Check 6: Every 例/例题 has a callout (structural rule)
rg -c '> \[!question\]' source-transcript.md
# Should match the number of examples in the document.

# Check 7: No example/exercise label sits OUTSIDE a callout (the downstream
# "examples have no quote block" defect). Run the validator's dedicated lint
# rather than a manual rg, because it correctly scopes to question callouts.
py -3 scripts/validate_canonical_markdown.py --md source-transcript.md
# A non-zero exit with "example/exercise stem must be wrapped in a `> [!question]`
# callout" means a 例题N/练习N paragraph is a bare paragraph. Fix by wrapping
# it (and its stem/options) in a `> [!question]` callout. Note: analysis
# (解析) paragraphs must stay OUT of callouts — only the question side is wrapped.
```

If any check fails, fix the issue and re-run the check before proceeding.
