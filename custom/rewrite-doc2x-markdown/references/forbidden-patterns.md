# Forbidden Patterns (LESSONS LEARNED)

These patterns caused critical failures in past sessions. Violating them is a critical error. The SKILL.md Hard Contract summarizes them; this file holds the full reasoning and code examples.

## F1 — No regex for semantic rewrites

**NEVER** use Python `re.sub()`, `str.replace()`, or any script to perform:
- Fused formula splitting (Rule 4) — requires understanding which commas separate independent formulas
- Paragraph splitting — requires understanding logical break points
- Structural formatting (callouts, bold markers) — requires understanding document structure
- Analysis block re-typesetting — requires understanding reasoning flow

These transformations need **semantic understanding**. Use subagents to read and edit manually, chunk by chunk.

**Scripts are ONLY allowed for**: pure mechanical substitution (`\(` → `$`), noise tag deletion, `\frac` → `\dfrac`, and other single-pattern replacements that cannot misfire.

> **F6 (no regex for fraction nesting) has been removed** — the `lint_fraction_nesting` validator now automates this check with a brace-depth parser. See SKILL.md Step 4.

## F2 — No `\$` in regex replacement strings

**NEVER** write `re.sub(pattern, r'\$', text)` or `re.sub(pattern, '\\$', text)`. In Python, the replacement string `r'\$'` inserts a literal backslash + dollar sign (`\$`), corrupting every `$` in the document.

**Correct way** to strip boundary spaces from `$ a $`:
```python
text = re.sub(r'\$ +', '$', text)   # plain string, NOT raw string with backslash
text = re.sub(r' +\$', '$', text)
```

## F3 — No unauthorized format conversions

**NEVER** convert `\begin{array}` to `\begin{cases}`, `\left\{` to other brace constructs, or change any LaTeX structural macro from Doc2X output. The Doc2X formulas are authoritative — only split fused formulas and move punctuation; never alter the internal LaTeX structure.

## F4 — No dismissing user complaints without byte-level verification

When a user reports a problem (e.g., "the formulas look wrong"):
1. **Immediately check the actual file bytes** — use `Read` tool or `grep` on the file, not reasoning
2. If the problem exists, fix it
3. If you believe it doesn't exist, **show the evidence** (actual byte content) and let the user judge
4. **NEVER** claim "it's just a rendering issue" without checking the raw file content first

## F5 — No silent chunk-boundary duplication

When dispatching subagents for parallel chunking, **each chunk must process its assigned pages and STOP** — never continue into the next chunk's content. If a section heading (e.g., `## 题型-3`) appears at the boundary between chunk N and chunk N+1, it belongs to **chunk N+1 only**, not both.

After assembly, if duplicate section headers or duplicate bullet points appear at chunk boundaries, remove the duplication immediately. The assembler is responsible for clean boundaries — subagents must not "helpfully" include the next section's opening. (See `references/parallel-chunking.md`.)
