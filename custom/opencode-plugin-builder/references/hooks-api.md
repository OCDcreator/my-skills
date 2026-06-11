# OpenCode Plugin Hooks API Reference

Complete hook signatures, input/output types, and code samples for every hook.

---

## Custom Tools — `tool: { [name]: ToolDefinition }`

Register tools that appear in the agent's tool palette. Uses Zod schemas via `tool.schema` (which is `z` from Zod).

```typescript
import { tool } from "@opencode-ai/plugin"

tool({
  description: "Description of what the tool does",
  args: {
    param1: tool.schema.string().describe("Param description"),
    param2: tool.schema.number().optional().describe("Optional param"),
    param3: tool.schema.array(tool.schema.string()).describe("Array param"),
    param4: tool.schema.enum(["a", "b", "c"]).describe("Enum param"),
  },
  async execute(args, ctx) {
    // args: typed from Zod schema
    // ctx: ToolContext
    //   - ctx.sessionID: string
    //   - ctx.messageID: string
    //   - ctx.agent: string
    //   - ctx.directory: string (project dir, prefer over process.cwd())
    //   - ctx.worktree: string (git worktree root)
    //   - ctx.abort: AbortSignal
    //   - ctx.metadata({ title?, metadata? }): void — UI feedback
    //   - ctx.ask({ permission, patterns, always, metadata }): Effect

    return "string result"
    // or: return { output: "string", metadata: { key: "value" } }
  },
})
```

**Override built-in tools:** Use the same key name as a built-in tool (`read`, `grep`, `glob`, `bash`). Plugin tools take precedence.

---

## tool.execute.before — Intercept Tool Calls

Modify tool arguments before the tool runs.

**Input:** `{ tool: string, sessionID: string, callID: string }`
**Output:** `{ args: any }` — mutate in place

```typescript
"tool.execute.before": async (input, output) => {
  if (input.tool === "bash") {
    const cmd = output.args?.command
    if (typeof cmd === "string" && cmd.startsWith("dangerous-cmd")) {
      output.args.command = `echo "Blocked: ${cmd}"`
    }
  }
},
```

---

## tool.execute.after — Post-Process Tool Output

Transform tool results after execution.

**Input:** `{ tool: string, sessionID: string, callID: string, args: any }`
**Output:** `{ title: string, output: string, metadata: any }` — mutate in place

```typescript
"tool.execute.after": async (input, output) => {
  if (input.tool === "bash" && output.output.length > 5000) {
    output.output = output.output.slice(0, 5000) + "\n... [truncated]"
    output.title = "bash (truncated)"
  }
},
```

---

## shell.env — Inject Environment Variables

Add environment variables to all shell executions (both AI tools and user terminals).

**Input:** `{ cwd: string, sessionID?: string, callID?: string }`
**Output:** `{ env: Record<string, string> }` — mutate in place

```typescript
"shell.env": async (input, output) => {
  output.env["MY_API_KEY"] = "secret"
  output.env["PROJECT_ROOT"] = input.cwd
},
```

---

## config — Modify Merged Config

Mutate the live config object after all config files are merged. Runs once at startup.

**Input:** `Config` (the full merged config object)
**Output:** none — mutate the input object directly

```typescript
config: async (cfg) => {
  if (!cfg.instructions) cfg.instructions = []
  cfg.instructions.push("docs/style.md")
},
```

---

## event — Listen to All Bus Events

Receive every event on the OpenCode event bus.

**Input:** `{ event: Event }`

Key event types: `session.idle`, `session.created`, `session.compacted`, `session.error`, `message.updated`, `file.edited`, `permission.asked`, `tool.execute.before`, `tool.execute.after`

```typescript
event: async ({ event }) => {
  if (event.type === "session.idle") {
    await $`osascript -e 'display notification "Done!" with title "opencode"'`.nothrow()
  }
},
```

---

## chat.message — Modify User Messages

Transform incoming messages before they reach the LLM.

**Input:** `{ sessionID: string, agent?: string, model?: object, messageID?: string, variant?: string }`
**Output:** `{ message: UserMessage, parts: Part[] }` — mutate in place

```typescript
"chat.message": async (input, output) => {
  // Modify output.message or output.parts before LLM sees them
},
```

---

## chat.params — Adjust LLM Parameters

Per-request adjustments to temperature, topP, topK, maxTokens.

**Input:** `{ sessionID: string, agent: string, model: Model, provider: ProviderContext, message: UserMessage }`
**Output:** `{ temperature: number, topP: number, topK: number, maxOutputTokens: number|undefined, options: Record<string,any> }` — mutate in place

```typescript
"chat.params": async (input, output) => {
  if (input.agent === "plan") {
    output.temperature = 0.2
  }
},
```

---

## chat.headers — Add Custom HTTP Headers

Inject headers into LLM API requests.

**Input:** `{ sessionID: string, agent: string, model: Model, provider: ProviderContext, message: UserMessage }`
**Output:** `{ headers: Record<string, string> }` — mutate in place

```typescript
"chat.headers": async (input, output) => {
  output.headers["X-Custom-Header"] = "value"
},
```

---

## permission.ask — Override Permission Decisions

Customize whether OpenCode asks, allows, or denies a permission.

**Input:** `Permission` object
**Output:** `{ status: "ask" | "deny" | "allow" }` — mutate in place

```typescript
"permission.ask": async (input, output) => {
  if (input.tool === "my_custom_tool") {
    output.status = "allow"
  }
},
```

---

## tool.definition — Modify Tool Descriptions

Change how tools appear to the LLM (description, parameters).

**Input:** `{ toolID: string }`
**Output:** `{ description: string, parameters: any }` — mutate in place

```typescript
"tool.definition": async (input, output) => {
  if (input.toolID === "bash") {
    output.description += "\nIMPORTANT: Always use --dry-run first."
  }
},
```

---

## command.execute.before — Pre-process Slash Commands

**Input:** `{ command: string, sessionID: string, arguments: string }`
**Output:** `{ parts: Part[] }` — mutate in place

```typescript
"command.execute.before": async (input, output) => {
  // Modify output.parts before command executes
},
```

---

## Experimental Hooks

### experimental.chat.messages.transform

Transform message history before sending to LLM.

**Output:** `{ messages: Array<{ info: Message, parts: Part[] }> }`

### experimental.chat.system.transform

Modify system prompt per session/model.

**Input:** `{ sessionID?: string, model: Model }`
**Output:** `{ system: string[] }` — mutate in place

```typescript
"experimental.chat.system.transform": async (input, output) => {
  output.system.push("Additional system instruction here")
},
```

### experimental.session.compacting

Customize compaction prompt/context. Fires before LLM generates continuation summary.

**Input:** `{ sessionID: string }`
**Output:** `{ context: string[], prompt?: string }` — mutate in place

- `output.context.push(...)`: appends to default prompt
- `output.prompt = "..."`: replaces default prompt entirely (ignores `context`)

```typescript
"experimental.session.compacting": async (input, output) => {
  output.context.push("## Custom Context\n- Current task status")
},
```

### experimental.compaction.autocontinue

Control auto-continue after compaction.

**Input:** `{ sessionID, agent, model, provider, message, overflow: boolean }`
**Output:** `{ enabled: boolean }` — set `false` to skip auto-continue

### experimental.text.complete

Intercept text completion.

**Input:** `{ sessionID: string, messageID: string, partID: string }`
**Output:** `{ text: string }`
