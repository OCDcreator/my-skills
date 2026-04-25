# Codex Autopilot Runtime Architecture Design

## Goal

Add a focused architecture explainer for `custom/codex-autopilot-scaffold` so a reader can quickly understand how a scaffolded target repository actually runs unattended autopilot rounds after installation.

The explainer should answer two questions:

- what major runtime layers exist in a generated repo,
- how one unattended round flows from operator command to `codex exec` to runtime artifacts and observability commands.

## Current State

- `custom/codex-autopilot-scaffold/SKILL.md` explains when to use the skill, scaffold boundaries, presets, and operator commands.
- `custom/codex-autopilot-scaffold/templates/common/automation/README.md` explains generated files and operating procedures in detail.
- The generated runtime is already modular:
  - `automation/autopilot.py` is the thin CLI entrypoint,
  - `automation/_autopilot/cli_parser.py` defines the operator subcommands,
  - `automation/_autopilot/start_runtime.py`, `round_flow.py`, `runner.py`, and `validation.py` drive execution,
  - `automation/_autopilot/health_runtime.py`, `watch_runtime.py`, and `status_views.py` expose observability.
- What is missing is a single visual explanation that connects those pieces into one mental model.

## Requirements

### 1. Deliverables

- Add one standalone architecture explainer document under `custom/codex-autopilot-scaffold/`.
- Add a discoverable link to that document from `custom/codex-autopilot-scaffold/SKILL.md`.
- The standalone document must be self-sufficient: a reader should understand the runtime without opening source files first.

### 2. Diagram set

The explainer should contain exactly two diagrams:

- a main runtime architecture diagram,
- a smaller single-round sequence diagram.

This keeps the document compact while still covering both static structure and dynamic flow.

### 3. Main diagram scope

The main diagram should use a layered view centered on generated target-repo runtime behavior:

- **Control plane**: operator commands, wrappers, `autopilot.py`, CLI routing, lock and state coordination
- **Execution plane**: config loading, lane selection, round preparation, prompt rendering, `codex exec`, result validation, git/state updates
- **Observability plane**: `status`, `health`, `watch`, and the runtime artifacts they inspect

The diagram should explicitly show that the Python controller is the durable loop owner and that `codex exec` is invoked as a child execution step inside each round, not as the long-lived loop.

### 4. Single-round diagram scope

The single-round diagram should show the lifecycle of one unattended round:

1. operator launches `start` or `bootstrap-and-daemonize`,
2. controller loads profile/config/state and selects the active lane,
3. round context is prepared and `round-XXX/prompt.md` is written,
4. runner invokes `codex exec`,
5. runtime artifacts are written,
6. validation decides success or failure,
7. state, phase docs, and commit history are updated for the next round and for observer commands.

### 5. Artifact coverage

The document should call out the runtime artifacts that matter most to operators:

- `automation/runtime/autopilot-state.json`
- `automation/runtime/round-XXX/progress.log`
- `automation/runtime/round-XXX/runner-status.json`
- `automation/runtime/round-XXX/assistant-output.json`
- lane phase docs and roadmap docs under `docs/status/lanes/`

It should also explain which observability command primarily consumes which artifact family.

### 6. Format and maintenance

- Prefer Mermaid diagrams embedded in Markdown.
- Keep naming aligned with the real generated file/module names already used by the scaffold.
- Avoid drifting into preset-specific detail except where a short note adds clarity.
- Keep the explanation concise enough to remain maintainable when scaffold internals evolve.

## Recommended Approach

Use a standalone Markdown file with:

1. a short “how to read this” intro,
2. one Mermaid flowchart for the layered runtime architecture,
3. one Mermaid sequence diagram for a single round,
4. a short bullet explanation of the key artifacts and observability commands,
5. a short “what this diagram intentionally leaves out” note for advanced features such as `review-gated`, cutover, or remote Mac rollout.

This keeps the first-pass mental model clean while leaving room for future advanced companion docs.

## Content Structure

### Standalone explainer

The new explainer should follow this structure:

1. `# Codex Autopilot Runtime Architecture`
2. `## What this shows`
3. `## Main runtime architecture`
4. `## Single-round sequence`
5. `## Key runtime artifacts`
6. `## Reading the runtime in practice`
7. `## What is intentionally out of scope`

### `SKILL.md` link placement

Add the link near the top of `SKILL.md`, close to the primary entrypoint and generated-repo explanation, so readers can discover it before diving into preset rules and operator procedures.

## Design Notes

### Main mental model

The document should teach this primary model:

- the scaffold installs a repo-local Python controller,
- the controller reads repo config and lane docs to decide the next slice,
- each round renders an explicit prompt into runtime storage,
- `codex exec` performs the round work,
- the controller validates the result and updates machine-readable state,
- operator commands such as `health`, `watch`, and `status` observe that state from different angles.

### Observability emphasis

The main diagram should make `health` different from `status` and `watch`:

- `status` reads summarized state,
- `watch` tails the active round stream with metadata prefixes,
- `health` is the liveness truth source because it checks pid, fresh progress, and `runner-status.json` together.

This distinction is important because it is one of the scaffold’s key runtime guarantees.

### Scope control

Do not overload the first architecture doc with:

- every preset variant,
- remote Mac launch flow,
- `restart-after-next-commit`,
- OpenCode review wrapper internals,
- launchd or PowerShell wrapper implementation details.

Those belong to advanced operator docs, not to the first architecture picture.

## Risks and Mitigations

- **Diagram becomes too dense**: keep the main diagram layered instead of fully enumerating every helper module.
- **Docs drift from code**: name only stable runtime surfaces and group helper modules by responsibility.
- **Readers confuse scaffold generation with runtime execution**: explicitly state that this document describes the generated target repo after scaffold installation.

## Success Criteria

- A reader new to the scaffold can explain the roles of control plane, execution plane, and observability plane after reading the document once.
- A reader can point to where one round’s prompt, progress, runner state, output JSON, and state file live.
- A reader can explain why `health` is a stronger “is it really running?” signal than `status`.
- `SKILL.md` contains a clear link to the standalone explainer.
