# Autopilot Round Roadmap

## Queue

### [DONE] P4 - Review and repair page 4

- **Lane**: Bugfix / backlog
- **Goal**: Make page 4 pass the sequential print-review gate for the salts handout.
- **Target artifact**:
  - `custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/handout.html`
- **Required validation**:
  - `python3 custom/knowledge-to-print-html/review_print_pages.py --html custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/handout.html`
- **Acceptance**:
  - Page 4 is regenerated and reviewed in the latest packet
  - Page 4 has no remaining blocking issue for this lane
  - The phase doc records exact edited artifact paths and the review result

### [NEXT] P5 - Review and repair page 5

- **Lane**: Bugfix / backlog
- **Goal**: Make page 5 pass after page 4 is complete.
- **Constraints**:
  - Do not start until page 4 is `[DONE]`

### [QUEUED] P6 - Review and repair page 6

- **Lane**: Bugfix / backlog
- **Goal**: Make page 6 pass after page 5 is complete.
- **Constraints**:
  - Do not start until page 5 is `[DONE]`

## Current state

- The target handout copy lives in the isolated worktree only.
- This lane exists to avoid exploding one long interactive session.
- Use one page as one queue slice; repeat the same page across multiple rounds if needed.
