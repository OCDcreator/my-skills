# skill-evolution v0 — Scenario Verification

For each scenario, trace the input through the authored SKILL.md + references and confirm the decision matches `expected`. These are the behavioral tests for a content skill.

## S1 — strengthen (rewrite, multi-method merge)
- input: rewrite session, model merged 法一/法二, user corrected "法一和法二是两个独立方法"
- expected: CAPTURE classifies rework; Gate2 grep hits Step 2 "method boundaries" → strengthen; lands in Step 2 wording with date stamp
- pass criterion: decision == strengthen AND target_location references Step 2

## S2 — discard preference-clear
- input: only feedback is "make paragraphs shorter" (rewrite already has 300-char rule)
- expected: Gate3 preference-clear → discard (row 5, beaten by row 3 duplicate)
- pass criterion: decision == discard, reason cites preference + existing rule

## S3 — surface preference-borderline
- input: "I'd like paragraphs a bit shorter" (borderline — could be config)
- expected: Gate3 preference-borderline → surface (ask user), NOT silent discard
- pass criterion: decision == surface, user is prompted

## S4 — conflict → human_review
- input: candidate rule "段落到 400 字也行" contradicts rewrite's 300-char rule
- expected: Gate2 conflict → human_review, no auto-overwrite
- pass criterion: decision == human_review, no write happens

## S5 — fail generality → discard
- input: "第 274 页那个图标位置不对"
- expected: Gate1 fail → discard (single-doc instance)
- pass criterion: decision == discard, reason cites overfit/single-doc

## S6 — external target refused
- input: target = external/anthropics-skills/skill-creator
- expected: Step 0 refuses, fork-first guidance shown
- pass criterion: no read/write, fork-first message shown

## S7 — landing zone generalization (no Lessons section)
- input: target = a custom skill WITHOUT a Lessons section (e.g. custom/ssh)
- expected: cascade tier 2 (insert ## Lessons Learned) or tier 4 (references/lessons-learned.md if near cap)
- pass criterion: rule lands somewhere sensible, not assumed into a nonexistent section

## S8 — third-strike promotion (recurrence)
- input: same substance as two prior discard entries in evolution-log.md
- expected: Step 2 pre-read tags recurrence third+ → promoted to surface even if Gate3 would discard
- pass criterion: decision == surface, recurrence history shown

## S9 — pre-edit snapshot + log append regardless of verdict
- input: any approved run
- expected: SKILL.md.bak-YYYY-MM-DD created BEFORE write; evolution-log.md appended AFTER (even on discard)
- pass criterion: snapshot exists pre-write; log entry exists post-run

## S10 — v0 structural-change routing
- input: candidate touches target's Hard Contract
- expected: Step 6 routes to human_review + defer; NOT auto-applied
- pass criterion: no structural auto-write; presented + deferred
