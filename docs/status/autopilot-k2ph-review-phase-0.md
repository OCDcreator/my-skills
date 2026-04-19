# Autopilot Phase 0

- Created a dedicated isolated worktree from `origin/main` for salts handout page review.
- Copied `custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/` into the worktree because the artifact path is gitignored and did not exist in the fresh checkout.
- Provisioned a local venv at `automation/runtime/.venv-autopilot` so `review_print_pages.py` can use `playwright` on macOS without changing system Python.
- The next queued slice is `P4 - Review and repair page 4`.
