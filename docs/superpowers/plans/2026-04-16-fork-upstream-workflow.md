# Fork Upstream Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate a custom skill that teaches how to manage a personal Git fork while following upstream updates safely.

**Architecture:** The work follows a skill-TDD loop. First create realistic eval prompts and collect baseline behavior without the skill. Then add the skill and README entries, rerun the same prompts with the skill, grade both sets of outputs, and generate a viewer artifact for human review.

**Tech Stack:** Markdown skill authoring, JSON eval metadata, Git repository docs, subagent-based prompt runs, Python review tooling.

---

### Task 1: Create Eval Skeleton And Baseline Inputs

**Files:**
- Create: `custom/fork-upstream-workflow/evals/evals.json`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-0/eval_metadata.json`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-1/eval_metadata.json`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-2/eval_metadata.json`

- [ ] Write three realistic prompts for fork maintenance
- [ ] Save prompt set to `custom/fork-upstream-workflow/evals/evals.json`
- [ ] Save one `eval_metadata.json` per eval directory with empty assertions
- [ ] Run baseline executions without the skill and save outputs under `without_skill/run-1/outputs/`

### Task 2: Write The Skill

**Files:**
- Create: `custom/fork-upstream-workflow/SKILL.md`

- [ ] Review baseline outputs for missing or weak guidance
- [ ] Write frontmatter with an aggressive trigger description for fork/upstream maintenance requests
- [ ] Write the skill body around workflow decisions first, commands second
- [ ] Include a short decision table for `merge` on `main` vs `rebase` on feature branches

### Task 3: Update Skill Catalog Surface

**Files:**
- Modify: `README.md`

- [ ] Add the new skill to the custom directory tree
- [ ] Add the new skill to the custom skill table with a concise description

### Task 4: Run With-Skill Evals And Grade Results

**Files:**
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-0/with_skill/run-1/outputs/*`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-1/with_skill/run-1/outputs/*`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-2/with_skill/run-1/outputs/*`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-*/with_skill/run-1/grading.json`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/eval-*/without_skill/run-1/grading.json`
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/benchmark.json`

- [ ] Run the same prompts with the skill and save outputs under `with_skill/run-1/outputs/`
- [ ] Grade baseline and with-skill runs against the eval expectations
- [ ] Aggregate results into `benchmark.json`
- [ ] Generate a static review HTML with `generate_review.py`

### Task 5: Summarize First Iteration

**Files:**
- Create: `custom/fork-upstream-workflow-workspace/iteration-1/benchmark.md`

- [ ] Compare with-skill vs baseline coverage
- [ ] Report which expectations improved
- [ ] Tell the human where to inspect the viewer artifact and outputs
