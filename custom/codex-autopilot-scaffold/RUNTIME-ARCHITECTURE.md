# Codex Autopilot Runtime Architecture

## What this shows

This document explains the generated target-repo runtime after the scaffold has already been installed. It focuses on how the repo-local Python controller drives unattended rounds, where the runtime artifacts live, and how `status`, `watch`, and `health` observe the run.

The key mental model is:

- the scaffold installs a durable Python control loop into the repo,
- each round is delegated to a child `codex exec`,
- the controller validates the round and updates machine-readable state,
- observer commands read that state from different angles.

## Main runtime architecture

```mermaid
flowchart TD
    Operator["Operator<br/>CLI commands and wrappers<br/>start / bootstrap-and-daemonize / status / watch / health"]

    subgraph Control["Control Plane"]
        CLI["automation/autopilot.py<br/>thin CLI entrypoint"]
        Parser["automation/_autopilot/cli_parser.py<br/>subcommand routing"]
        StateLock["state + lock coordination<br/>state_runtime / locking / process_control"]
    end

    subgraph Execution["Execution Plane"]
        Config["automation/autopilot-config.json<br/>profiles + lane docs + prompt template"]
        Start["start_runtime<br/>load config, resume state, choose lane"]
        Round["round_flow<br/>prepare round context + prompt"]
        Runner["runner<br/>invoke codex exec"]
        Validation["validation<br/>check structured result + git/runtime rules"]
        Update["controller runtime updates<br/>state + phase docs + commit metadata"]
    end

    subgraph Runtime["Runtime Artifacts"]
        StateFile["automation/runtime/autopilot-state.json"]
        Progress["automation/runtime/round-XXX/progress.log"]
        RunnerStatus["automation/runtime/round-XXX/runner-status.json"]
        Output["automation/runtime/round-XXX/assistant-output.json"]
        LaneDocs["docs/status/lanes/...<br/>phase docs + roadmap"]
    end

    subgraph Observability["Observability Plane"]
        Status["status<br/>summary view"]
        Watch["watch<br/>prefixed live stream"]
        Health["health<br/>pid + fresh progress + runner-status truth check"]
    end

    Operator --> CLI
    CLI --> Parser
    Parser --> StateLock
    Parser --> Start
    Config --> Start
    Start --> Round
    Round --> Runner
    Runner --> Validation
    Validation --> Update
    Update --> StateFile
    Update --> Progress
    Update --> RunnerStatus
    Update --> Output
    Update --> LaneDocs
    StateFile --> Status
    StateFile --> Watch
    Progress --> Watch
    StateFile --> Health
    Progress --> Health
    RunnerStatus --> Health
```

- The controller is the durable loop owner; `codex exec` is only the worker for one round.
- `automation/autopilot-config.json`, profile JSON, and lane docs together define what the next round should attempt.
- Runtime state is split on purpose: one summary state file, one live progress stream, one runner liveness artifact, one structured assistant result, plus lane-local docs.

## Single-round sequence

```mermaid
sequenceDiagram
    participant Operator
    participant Controller as autopilot.py + start_runtime
    participant RoundFlow as round_flow
    participant Runner as runner / codex exec
    participant Runtime as automation/runtime + lane docs

    Operator->>Controller: start --profile ...<br/>or bootstrap-and-daemonize
    Controller->>Controller: load profile, config, state, lock
    Controller->>Controller: select active lane + next phase
    Controller->>RoundFlow: prepare round context
    RoundFlow->>Runtime: write round-XXX/prompt.md
    RoundFlow->>Runner: launch codex exec for one round
    Runner->>Runtime: append progress.log
    Runner->>Runtime: update runner-status.json
    Runner->>Runtime: write assistant-output.json
    Runner-->>Controller: exit code + structured result
    Controller->>Controller: validate result and git/runtime constraints
    Controller->>Runtime: update autopilot-state.json
    Controller->>Runtime: update phase doc / roadmap progress
    Controller->>Runtime: record commit + summary metadata
```

- `round_flow` is where the controller turns repo intent into a concrete per-round prompt and runtime directory.
- The runner writes artifacts during execution so observers can inspect the live state before the round fully ends.
- Validation is where the scaffold enforces its contract: schema, build/deploy reporting, commit prefix rules, dirty-worktree expectations, and similar safety checks.

## Key runtime artifacts

- `automation/runtime/autopilot-state.json`
  - The controller's summary view of the current run: current round, lane progress, status, last successful metadata.
- `automation/runtime/round-XXX/progress.log`
  - Human-readable live stream for the active round; `watch` tails this with autopilot metadata prefixes.
- `automation/runtime/round-XXX/runner-status.json`
  - Child-runner liveness evidence, including the `codex exec` child pid and `exec_confirmed_at`.
- `automation/runtime/round-XXX/assistant-output.json`
  - Structured final result returned by the round worker and consumed by validation.
- `docs/status/lanes/<lane-id>/autopilot-phase-N.md`
  - Lane-local record of what just happened in the latest phase.
- `docs/status/lanes/<lane-id>/autopilot-round-roadmap.md`
  - Lane-local queue source for what should happen next.

## Reading the runtime in practice

- Use `status` when you want the current high-level summary from `autopilot-state.json`.
- Use `watch` when you want the live operator stream with lane, phase, round, and status prefixes while `progress.log` is updating.
- Use `health` when `status=active` looks suspicious. It is the stronger truth source because it checks three things together:
  - the autopilot parent pid is still alive,
  - the watched `progress.log` is fresh,
  - the watched `runner-status.json` still proves a live child `codex exec`.

That distinction matters because a stale state file alone does not prove the unattended runner is still healthy.

## What is intentionally out of scope

This explainer intentionally leaves out advanced operator flows such as `review-gated` review wrappers, remote Mac rollout, `restart-after-next-commit`, and platform-specific wrapper internals. Those features sit on top of the same runtime skeleton shown here.
