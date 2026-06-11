/**
 * OpenCode Plugin Template — copy-paste starting point.
 *
 * Usage:
 *   1. Copy this file to your project: .opencode/plugins/my-plugin.ts
 *   2. Uncomment the hooks you need
 *   3. Restart opencode
 *
 * The plugin auto-loads from .opencode/plugins/ — no opencode.json changes needed.
 */
import { type Plugin, tool } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ client, project, directory, worktree, serverUrl, $ }) => {
  // ── Setup (runs once on load) ──────────────────────────────────────────
  // Check external tool availability, initialize state, etc.
  let externalAvailable = false
  try {
    await $`which my-external-tool`.quiet()
    externalAvailable = true
  } catch {
    console.warn("[my-plugin] my-external-tool not found — some features disabled")
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  // CRITICAL: Use Bun.spawn for external CLI tools, NOT $ template strings
  async function runExternal(args: string[]): Promise<string | null> {
    if (!externalAvailable) return null
    try {
      const proc = Bun.spawn(["my-external-tool", ...args], {
        stdout: "pipe",
        stderr: "pipe",
      })
      await proc.exited
      const stdout = await new Response(proc.stdout).text()
      return stdout.trim() || null
    } catch {
      return null
    }
  }

  return {
    // ── Custom Tools ───────────────────────────────────────────────────
    // tool: {
    //   my_tool: tool({
    //     description: "Description of what this tool does",
    //     args: {
    //       input: tool.schema.string().describe("Input parameter"),
    //       count: tool.schema.number().optional().describe("Optional count"),
    //     },
    //     async execute(args, ctx) {
    //       // ctx.sessionID, ctx.directory, ctx.worktree, ctx.abort
    //       // ctx.metadata({ title: "Processing..." })
    //       return `Result: ${args.input}`
    //     },
    //   }),
    // },

    // ── Override Built-in Tools ────────────────────────────────────────
    // Use the SAME key as a built-in tool (read, grep, glob, bash) to override
    // tool: {
    //   read: tool({
    //     description: "Read file (enhanced)",
    //     args: {
    //       filePath: tool.schema.string().describe("Absolute file path"),
    //       offset: tool.schema.number().optional(),
    //       limit: tool.schema.number().optional(),
    //     },
    //     async execute(args) {
    //       // Try custom logic first, fallback to native
    //       const result = await runExternal(["read", args.filePath])
    //       if (result) return result
    //       return await Bun.file(args.filePath).text()
    //     },
    //   }),
    // },

    // ── Hooks ──────────────────────────────────────────────────────────

    // Modify tool arguments before execution
    // "tool.execute.before": async (input, output) => {
    //   // input: { tool: string, sessionID: string, callID: string }
    //   // output: { args: any } — mutate in place
    // },

    // Transform tool results after execution
    // "tool.execute.after": async (input, output) => {
    //   // input: { tool, sessionID, callID, args }
    //   // output: { title, output, metadata } — mutate in place
    // },

    // Inject environment variables into shell commands
    // "shell.env": async (input, output) => {
    //   // input: { cwd, sessionID?, callID? }
    //   // output: { env: Record<string, string> }
    //   output.env["MY_VAR"] = "value"
    // },

    // Modify the merged config at startup
    // config: async (cfg) => {
    //   // Mutate cfg fields as needed
    // },

    // Listen to all bus events
    // event: async ({ event }) => {
    //   console.log(`[my-plugin] ${event.type}`)
    // },

    // Modify incoming user messages
    // "chat.message": async (input, output) => {
    //   // output: { message, parts }
    // },

    // Adjust LLM parameters per request
    // "chat.params": async (input, output) => {
    //   // output: { temperature, topP, topK, maxOutputTokens, options }
    // },

    // Add custom HTTP headers to LLM API requests
    // "chat.headers": async (input, output) => {
    //   output.headers["X-Custom"] = "value"
    // },

    // Override permission decisions
    // "permission.ask": async (input, output) => {
    //   // output: { status: "ask" | "deny" | "allow" }
    // },

    // Modify tool descriptions/parameters shown to LLM
    // "tool.definition": async (input, output) => {
    //   // output: { description, parameters }
    // },

    // Pre-process slash commands
    // "command.execute.before": async (input, output) => {
    //   // output: { parts: Part[] }
    // },

    // Experimental hooks
    // "experimental.chat.system.transform": async (input, output) => {
    //   // output: { system: string[] }
    // },
    // "experimental.session.compacting": async (input, output) => {
    //   // output: { context: string[], prompt?: string }
    // },
    // "experimental.compaction.autocontinue": async (input, output) => {
    //   // output: { enabled: boolean }
    // },

  } // end return
}
