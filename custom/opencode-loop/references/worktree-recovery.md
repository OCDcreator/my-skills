# Worktree Isolation Lifecycle

When `profile.isolation` is `worktree`, each queue task runs in an isolated Git worktree. The Python isolation manager handles creation, cleanup, and integration automatically — but when an agent needs to manually manage worktrees (for recovery, continuation, or inspection), follow this lifecycle.

## Recovery From Interrupted Worktree Creation

If `git worktree add -b <branch>` was killed mid-operation (SIGKILL, timeout, `index.lock` blockage), the branch may exist but the worktree directory may be missing or unregistered. Recovery:

```bash
TASK_ID="tm-8"
BRANCH="task/${TASK_ID}"
WORKTREE_PATH="/path/to/target/.opencode-loop/worktrees/${TASK_ID}"

# Step 1: Clear stale index.lock (use git rev-parse for worktree-safe path)
LOCK=$(git -C /path/to/target rev-parse --git-path index.lock 2>/dev/null || true)
if [[ -f "$LOCK" ]]; then
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "[g]it.*target" >/dev/null 2>&1 && echo "active lock" || rm -f "$LOCK"
  else
    PS_OUT=$(ps aux 2>/dev/null || true)
    if [[ -z "$PS_OUT" ]] || echo "$PS_OUT" | grep -q "[g]it.*target"; then
      echo "cannot confirm liveness — not removing lock"
    else
      rm -f "$LOCK"
    fi
  fi
fi

# Step 2: Inspect current state
git -C /path/to/target worktree list
git -C /path/to/target branch --list "$BRANCH"

# Step 3: Re-bind existing branch OR create fresh (conditional)
if git -C /path/to/target show-ref --verify "refs/heads/$BRANCH" 2>/dev/null &&
   ! git -C /path/to/target worktree list | grep -qF "$WORKTREE_PATH"; then
  git -C /path/to/target worktree add "$WORKTREE_PATH" "$BRANCH"
else
  git -C /path/to/target worktree add "$WORKTREE_PATH" -b "$BRANCH" HEAD
fi
```

If the loop's isolation manager refuses to delete a branch with unique commits, you must manually decide: (a) integrate the commits into base with `git checkout main && git merge --ff-only task/<id>`, or (b) re-bind the branch to a worktree path with `git worktree add <path> task/<id>`. Do not force-delete branches with unmerged work.

## State Migration To New Worktree

New worktrees carry only Git-tracked files — not the `.opencode-loop/` runtime state from the original tree. To continue a paused queue in a new worktree:

```bash
OLD="/path/to/original-target"
NEW="/path/to/new-worktree"

opencode-loop init --dir "$NEW" --mode execute

cp "$OLD/.opencode-loop/queue.json"   "$NEW/.opencode-loop/"
cp "$OLD/.opencode-loop/program.md"   "$NEW/.opencode-loop/"
cp "$OLD/.opencode-loop/hooks.json"   "$NEW/.opencode-loop/"

# Reset stuck tasks to retryable
opencode-loop queue set-status --dir "$NEW" --task tm-8 --status todo --reason "continuing in new worktree"
```

## Dependency Installation Before Execute

New worktrees start with no runtime dependencies. Install them before starting the loop:

```bash
cd /path/to/new-worktree
npm install          # Node.js
# pip install -r requirements.txt   # Python
# bundle install                     # Ruby
opencode-loop doctor --dir . --json
# Run project baseline tests
```

## Full Continuation Checklist

After creating a worktree for execution continuation:

1. Create/add worktree with recovery checks (index.lock, branch state)
2. Install project dependencies
3. `opencode-loop doctor --dir <worktree> --json` to validate
4. Run project baseline tests to verify environment health
5. Migrate `.opencode-loop/` runtime state (`queue.json`, `program.md`, `hooks.json`)
6. Reset tasks to appropriate statuses
7. `opencode-loop start --dir <worktree> --profile execute`

## Post-Commit / Post-Task Repo Cleanliness

After a task commits changes but before the loop finalizes the iteration, repo-visible runtime files (`opencode.json`) may show as uncommitted. (`.opencode-loop/` is already gitignored by `setup.sh` — it's `opencode.json` in the project root that causes the problem.) When this is detected with no active task, the loop immediately exits with `environment_blocked` status (exit code 6) — it does NOT spin or retry.

Resolution:

```bash
git status --porcelain
# If the only dirty file is opencode.json (everything else is clean or under .gitignore):

# Option A: Ensure opencode.json is in .gitignore (preferred, one-time fix)
grep -q "^opencode.json$" .gitignore 2>/dev/null || echo "opencode.json" >> .gitignore

# Option B: Absorb the runtime config change into the task's cleanup commit
git add opencode.json && git commit --amend --no-edit

# Option C: Discard the runtime noise
git checkout -- opencode.json
```

This is not a task-execution failure — the task's code changed successfully, but `opencode.json` was rewritten by runtime and left dirty. The loop correctly detects this and exits cleanly rather than spinning. Option A is preferred; verify `.gitignore` has `opencode.json` before starting long unattended runs.
