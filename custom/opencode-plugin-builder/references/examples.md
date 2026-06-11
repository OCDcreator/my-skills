# OpenCode Plugin Examples

Real-world plugin patterns you can adapt.

---

## Example 1: Simple Custom Tool

Register a new tool that counts files matching a glob pattern:

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ $ }) => {
  return {
    tool: {
      count_files: tool({
        description: "Count files matching a glob pattern in the project",
        args: {
          pattern: tool.schema.string().describe("Glob pattern, e.g. 'src/**/*.ts'"),
          directory: tool.schema.string().optional().describe("Base directory"),
        },
        async execute(args) {
          const base = args.directory ?? "."
          const result = await $`rg --files ${base} -g ${args.pattern}`.quiet().nothrow()
          const count = result.stdout.toString().split("\n").filter(Boolean).length
          return `Found ${count} files matching '${args.pattern}' in ${base}`
        },
      }),
    },
  }
}
```

---

## Example 2: Tool Override with Fallback

Override a built-in tool (`read`) while keeping native fallback:

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const ReadOverridePlugin: Plugin = async ({ $ }) => {
  const COMPRESSOR = "my-compressor" // hypothetical CLI tool

  async function compress(content: string): Promise<string | null> {
    try {
      const proc = Bun.spawn([COMPRESSOR, "--stdin"], {
        stdin: "pipe", stdout: "pipe", stderr: "pipe",
      })
      proc.stdin.write(content)
      proc.stdin.end()
      const exitCode = await proc.exited
      if (exitCode !== 0) return null
      return await new Response(proc.stdout).text()
    } catch { return null }
  }

  return {
    tool: {
      read: tool({
        description: "Read file (compressed for token savings)",
        args: {
          filePath: tool.schema.string().describe("Absolute file path"),
          offset: tool.schema.number().optional().describe("0-based line offset"),
          limit: tool.schema.number().optional().describe("Max lines"),
        },
        async execute(args) {
          const file = Bun.file(args.filePath)
          let text = await file.text()
          if (args.offset != null || args.limit != null) {
            const lines = text.split("\n")
            const start = args.offset ?? 0
            const end = args.limit != null ? start + args.limit : lines.length
            text = lines.slice(start, end).join("\n")
          }
          const compressed = await compress(text)
          return compressed ?? text  // Fallback to raw content
        },
      }),
    },
  }
}
```

---

## Example 3: .env File Protection

Block reading of sensitive files by intercepting the `read` tool:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const EnvProtection: Plugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

---

## Example 4: Session Notification

Send a system notification when opencode finishes a task:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const NotificationPlugin: Plugin = async ({ $ }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        // macOS notification via osascript
        await $`osascript -e 'display notification "Session completed!" with title "opencode"'`.nothrow()
      }
    },
  }
}
```

---

## Example 5: Inject Environment Variables

Add environment variables to all shell executions:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const InjectEnvPlugin: Plugin = async () => {
  return {
    "shell.env": async (input, output) => {
      output.env.MY_API_KEY = "secret"
      output.env.PROJECT_ROOT = input.cwd
    },
  }
}
```

---

## Example 6: Compaction Context Hook

Inject domain-specific context during session compaction:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const CompactionPlugin: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      output.context.push(`## Custom Context

Include any state that should persist across compaction:
- Current task status
- Important decisions made
- Files being actively worked on`)
    },
  }
}
```
