# Evolution Log Format

Each target skill gets (or has appended) `references/evolution-log.md` — an append-only log of every skill-evolution run against it. This is what makes "avoid repeating mistakes" durable: a `discard` verdict that recurs across sessions is detectable and promotable. This is an append-only reference file, NOT a cross-session batch engine.

## Format

One block per run, newest at the bottom:

```
## YYYY-MM-DD — run against <skill>
- candidate: <one-line summary>
  verdict: add_new | strengthen | discard | human_review | surface
  reason: <one line>
  gate: { g1, g2, g3 }
  recurrence: first | second | third+ (promoted)
```

## Pre-read step (Step 2 of the pipeline)

Before gating, read the target's `references/evolution-log.md`; if absent, treat as empty (do **not** create it yet — the file is created only when appending in Step 9). For each current candidate, scan prior entries for the **same substance** that was previously `discard`ed or `surface`d. Tag the recurrence count:

- **first** — no prior match.
- **second** — one prior discard/surface of the same substance. Gate normally, but flag "recurrence #2" in the retro.
- **third+** — two or more prior discards/surfaces of the same substance. **Promote**: even if Gate 3 would say `preference-clear`, route to `surface` with the recurrence history shown — the user decides whether this is finally becoming a rule. This is the third-strike promotion that defeats a self-serving-biased gate.

"Same substance" is a semantic match on the trigger/mistake pair, not a string match — note the matched prior entry dates in the retro.

## Lifecycle

- **Bulletproof append.** Append an entry on EVERY run, regardless of verdict — `add_new`, `strengthen`, `discard`, `human_review`, `surface`, and even error or abort. The log records what happened, including failures. Create `references/evolution-log.md` on the first run (during the Step 9 write phase) if it does not exist. Step 2's pre-read treats an absent log as empty; it never creates the file mid-read.
- **Never infer unrecorded history.** If the log is absent or incomplete (runs before skill-evolution existed, or runs that failed to log), you cannot reconstruct what was never recorded. Do not fabricate recurrence data — mark provenance honestly.
- **Cold-start limitation (known).** A young skill gets no recurrence protection for its first runs — every candidate is `first` until the log accrues. The third-strike promotion only fires from run 3 onward (once two prior same-substance entries exist). This is a documented limitation, not a bug to paper over.
- The log is append-only. Never edit prior entries.
- Stale `add_new`/`strengthen` rules that were later removed from the skill keep their log entry (it's history).
- Date stamps on rules (landing-zone-rules.md) cross-reference the log dates.
