# Landing Zone Rules

Only a minority of `custom/` skills have a dedicated Lessons / Forbidden Patterns section (strict match: `rewrite-doc2x-markdown`). So the landing zone is chosen by this cascade, not assumed.

## 4-tier cascade

1. **Prefer** the target skill's existing Lessons / Forbidden Patterns section if one exists.
2. **Else insert** a `## Lessons Learned` section if the skill has none and is well below the size cap.
3. **Else append** the rule to the most relevant existing Step / section.
4. **Near the size cap** (SKILL.md within ~15% of 500 lines): route the rule to `references/lessons-learned.md` with a one-line pointer from SKILL.md.

## Failure diagnosis (informs the landing)

Classify *why* the failure happened — it determines where the fix lands:

| diagnosis | meaning | typical landing |
|---|---|---|
| did-not-exist | no rule covered this | add_new (cascade tier 1–4) |
| weak | rule existed but too soft/vague | strengthen existing rule in place |
| ignored | rule existed and was clear | do NOT add a rule — flag a compliance/process problem for human review |
| validator-gap | the failure is something a validator could catch | note it; Dev Eval (v0.5) territory |
| preference | personal taste | discard (per Gate 3) |
| conflict | contradicts existing rule | human_review |

The `ignored` case is important: if the rule was already clear and the model still violated it, adding a louder rule rarely helps — surface it as a process issue instead.

## Date stamps

Every new rule carries a date stamp so accumulated rules don't become an undifferentiated blob and stale rules can later be retired. Format: an HTML comment on the line above the rule, or an inline tag.

```
<!-- evolved 2026-06-14 -->
- Distinct solution methods (法一/法二/法三) must each occupy their own paragraph; never merge.
```

## Reference-file vs SKILL.md guidance

- A rule that governs the **main workflow** belongs in SKILL.md.
- A rule that is **detailed rubric / long exception table** belongs in `references/` with a one-line pointer from SKILL.md.
- A rule specific to an **existing reference file's domain** (e.g. rewrite's `auto-fix-rules.md`) lands in that file, not SKILL.md.
