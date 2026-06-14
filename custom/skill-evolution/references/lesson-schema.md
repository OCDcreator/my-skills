# Lesson Schema

Every `rework | missing | wrong` user message becomes one candidate lesson with these fields. The trace-enrichment fields (assistant action, file states, validator outputs, resolved?, uncertainty) are mandatory — elliptical corrections ("还是不对", "看第17页") are meaningless without the failure context. Each enrichment field carries a **provenance tag** — `(extracted)` if it is exact content from the in-context transcript/files, `(user-pasted)` if exact content supplied by the user. **Memory-only reconstruction is NOT evidence**: put it in `uncertainty` and tag the field `unverified`; never present reconstructed-from-memory content as a real trace field. Every evidence field must paste **real content** (the actual assistant turn, the real file bytes/excerpt), never a paraphrase. See SKILL.md Hard Contract (CAPTURE runs in the main context; evidence-backed claims).

## Fields

```
LESSON #N
  user_message     : <verbatim user message>
  classify         : rework | missing | wrong | style-pref | off-topic
  --- trace enrichment (rework/missing/wrong only) ---
  preceding_action : <PASTE the real assistant turn right before this correction — do not paraphrase>
  affected_paths   : <file paths touched, with their state at that moment>
  final_state      : <accepted / latest state of those paths>
  validator_output : <relevant validator/self-check output at that point, or "none">
  resolved         : yes | no | partial | unknown
  uncertainty      : <anything that cannot be reconstructed — surface to user, do not guess>
  provenance       : extracted | user-pasted | unverified   (extracted = exact content from in-context transcript/files; user-pasted = exact content supplied by user; memory-only reconstruction is NOT evidence → put in `uncertainty`, tag `unverified`)
  --- candidate rule ---
  trigger          : <generalized situation: "when X class of input...">
  mistake          : <what the skill/model did wrong>
  desired          : <what the user wanted>
  candidate_rule   : <proposed generalized rule, written as an executable instruction>
  --- gate (filled in Step 4) ---
  gate             : { g1: pass|fail, g2: new|strengthen|duplicate|conflict, g3: principle|preference-clear|preference-borderline }
  decision         : add_new | strengthen | discard | human_review | surface
  target_location  : <landing zone per landing-zone-rules.md>
  date_stamp       : YYYY-MM-DD  (applied to the rule when written)
```

## Worked example (rewrite-doc2x-markdown) — illustrative; fields abbreviated for readability. Real runs paste exact excerpts.

```
LESSON #1
  user_message     : "法一和法二是两个独立方法，不能合在一段"
  classify         : rework
  preceding_action : model emitted analysis section with 法一 + 法二 merged into one paragraph
  affected_paths   : source-transcript.md (the merged paragraph at L210-224)
  final_state      : two separate paragraphs, one per method
  validator_output : validate_canonical_markdown.py PASS on final_state
  resolved         : yes
  uncertainty      : none
  trigger          : analysis sections containing multiple distinct solution methods (法一/法二/法三)
  mistake          : merged distinct methods into a single paragraph
  desired          : one paragraph per method
  candidate_rule   : "Distinct solution methods (法一/法二/法三) must each occupy their own paragraph; never merge."
  gate             : { g1: pass, g2: strengthen, g3: principle }
  decision         : strengthen   (Step 2 already says "Split at method boundaries"; wording hardened)
  target_location  : rewrite-doc2x-markdown/SKILL.md → Step 2 paragraph-splitting rule
  date_stamp       : 2026-06-14
```
