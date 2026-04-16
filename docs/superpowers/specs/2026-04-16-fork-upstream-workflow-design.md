# Fork Upstream Workflow Design

**Goal**

Create a custom skill that teaches a personal-maintainer workflow for Git fork repositories: keep `origin` as the user's fork, track `upstream` from the original author, isolate personal changes on feature branches, and sync upstream updates without losing local work.

**Audience**

- Developers maintaining a personal fork long-term
- Users who understand basic Git but are unsure how to manage `origin`, `upstream`, `main`, and feature branches together
- Chinese-first users are the primary audience, but the skill must still trigger reliably from English frontmatter

**Skill Shape**

- Path: `custom/fork-upstream-workflow/`
- Style: English frontmatter for triggering, Chinese body for practical guidance
- Format: workflow-first, command-second
- Scope: Git fork maintenance only; not generic Git tutorials and not PR/release policy automation

**Key Guidance The Skill Must Teach**

1. `origin` is the user's fork; `upstream` is the canonical original repository
2. `main` should stay as the user's stable integration branch instead of becoming a long-lived scratchpad
3. New work should normally start from `main` into `feat/*`, `fix/*`, or similar short-lived branches
4. Syncing original author changes should default to `git fetch upstream` + `git merge upstream/main` while on local `main`
5. Personal feature branches should usually update from `main`, and `rebase main` is appropriate there when the user wants a cleaner feature history
6. Force-pushing `main` is dangerous and should not be recommended as the default maintenance pattern
7. The skill should explicitly tell the user to clean or stash a dirty worktree before syncing upstream

**Out Of Scope**

- GitHub PR automation
- Multi-maintainer team branching strategy
- Release workflows and tagging
- Rewriting a complicated Git history after it is already broken beyond normal conflict resolution

**Repository Changes**

- Add the new skill under `custom/fork-upstream-workflow/`
- Add `evals/evals.json` for skill tests
- Add a sibling workspace directory for run outputs
- Update `README.md` directory tree and custom skill table

**Test Strategy**

- Run baseline prompts without the skill first
- Then write the skill to address the weak spots from the baseline
- Run the same prompts with the skill
- Grade outputs against concrete expectations:
  - explains `origin` vs `upstream`
  - recommends `main` + feature branch separation
  - uses `merge upstream/main` on `main` as the stable default
  - reserves `rebase` mainly for feature branches
  - warns about dirty worktrees or force-pushing `main`

**Success Criteria**

- The new skill is added in the correct custom-skill location
- `README.md` reflects the new skill
- The with-skill runs cover the required fork-maintenance guidance more completely than baseline runs
- A review artifact is generated so the human can inspect outputs if needed
