# Evolution Log — pdf-toc-bookmarker

Append-only record of every skill-evolution run against this skill. Newest at the bottom.

## 2026-06-29 — run against pdf-toc-bookmarker
- candidate: confirm subagent image ingestion (URL-only vision tools); discard OCR JSON produced after a vision-tool error as fabricated
  verdict: add_new
  reason: URL-only-vision environments not covered; fabricated-OCR-after-error is silent corruption the skill never guarded against (caught in-session by orchestrator during 26张宇基础30讲高数.pdf job)
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
  landed: Step 5 (ingestion mechanics) + Safety Rules (fabrication hardening); date-stamped 2026-06-29
  provenance: extracted (full trace in-context; subagent's analyze_image MCP returned HTTP 400 on local path, then emitted fabricated JSON)
  snapshot: SKILL.md.bak-2026-06-29
