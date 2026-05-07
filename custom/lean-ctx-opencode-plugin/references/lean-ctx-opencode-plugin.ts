/**
 * lean-ctx OpenCode plugin — cross-platform reference implementation (Windows + macOS).
 *
 * This file is a standalone reference. To use it, copy to:
 *   your-project/.opencode/plugins/lean-ctx.ts
 *
 * Tested on: Windows 11, macOS (Mac Mini), OpenCode 1.14.x
 *
 * Two mechanisms:
 * 1. Custom tool override — registers read/grep/glob as plugin tools
 *    with the same name as built-ins. OpenCode prioritizes plugin tools,
 *    so these replace the native implementations with lean-ctx compressed versions.
 * 2. tool.execute.before hook — rewrites bash commands through lean-ctx for
 *    output compression (rewrites command text, native bash still runs).
 *
 * Edit / write / patch are NEVER intercepted.
 */
import { type Plugin, tool } from "@opencode-ai/plugin"

export const LeanCtxOpenCodePlugin: Plugin = async ({ $ }) => {
  // --- availability check ---------------------------------------------------
  let available = false
  try {
    await $`which lean-ctx`.quiet()
    available = true
  } catch {
    console.warn("[lean-ctx] binary not found in PATH — plugin disabled")
  }

  // --- helper ---------------------------------------------------------------
  // CRITICAL: Use Bun.spawn directly, NOT Bun shell template strings.
  // Bun shell ($`cmd ${args}`) breaks multi-word args on Windows.
  async function leanCtx(args: string[]): Promise<string | null> {
    if (!available) return null
    try {
      const proc = Bun.spawn(["lean-ctx", ...args], {
        stdout: "pipe",
        stderr: "pipe",
      })
      const exitCode = await proc.exited
      const stdout = await new Response(proc.stdout).text()
      const out = stdout.trim()
      return out || null
    } catch {
      return null
    }
  }

  // ---- bash rewrite (tool.execute.before) ----------------------------------
  const beforeHook = async (_input: unknown, output: { args: Record<string, unknown> }) => {
    const command = output?.args?.command
    if (typeof command !== "string" || !command) return
    // Don't intercept our own calls or already-rewritten commands
    if (command.includes("lean-ctx") || command.includes("lean_ctx")) return

    const rewritten = await leanCtx(["hook", "rewrite-inline", command])
    if (rewritten && rewritten !== command) {
      // On Windows, hook rewrite-inline returns Unix-style paths (/c/...)
      // which PowerShell can't execute — skip rewrite in that case
      const isUnixPath = /^\/[a-zA-Z]\//.test(rewritten)
      if (isUnixPath) {
        return
      }
      output.args.command = rewritten
    }
  }

  // ---- tool overrides (read / grep / glob) ---------------------------------
  const tools = {
    read: tool({
      description: "Read file contents (compressed through lean-ctx for token savings). Falls back to raw read if lean-ctx is unavailable.",
      args: {
        filePath: tool.schema.string().describe("Absolute path to the file"),
        offset: tool.schema.number().optional().describe("0-based line offset"),
        limit: tool.schema.number().optional().describe("Max number of lines to read"),
      },
      async execute(args: { filePath: string; offset?: number; limit?: number }) {
        const path = args.filePath.replace(/\\/g, "/")

        // Build lean-ctx read args
        const lcArgs = ["read", path]
        if (args.offset != null || args.limit != null) {
          const start = (args.offset ?? 0) + 1
          const end = args.limit != null ? start + args.limit - 1 : undefined
          lcArgs.push("-m", end ? `lines:${start}-${end}` : `lines:${start}-`)
        }

        const compressed = await leanCtx(lcArgs)
        if (compressed) return compressed

        // Fallback: read file directly via Bun
        const file = Bun.file(path)
        if (args.offset != null || args.limit != null) {
          const text = await file.text()
          const lines = text.split("\n")
          const start = args.offset ?? 0
          const end = args.limit != null ? start + args.limit : lines.length
          return lines.slice(start, end).join("\n")
        }
        return await file.text()
      },
    }),

    // ---- grep override -------------------------------------------------------
    grep: tool({
      description: "Search file contents with regex (compressed through lean-ctx). Falls back to native grep if lean-ctx is unavailable.",
      args: {
        pattern: tool.schema.string().describe("Regex pattern to search for"),
        path: tool.schema.string().optional().describe("Directory or file to search in"),
        includePattern: tool.schema.string().optional().describe("Glob pattern to filter files"),
      },
      async execute(args: { pattern: string; path?: string; includePattern?: string }) {
        const searchPath = (args.path ?? ".").replace(/\\/g, "/")
        const lcArgs = ["grep", args.pattern, searchPath]
        if (args.includePattern) lcArgs.push("--ext", args.includePattern)

        const compressed = await leanCtx(lcArgs)
        if (compressed) return compressed

        // Fallback: use ripgrep via shell
        const rgArgs = [args.pattern, searchPath]
        if (args.includePattern) rgArgs.push("-g", args.includePattern)
        const result = await $`rg ${rgArgs}`.quiet().nothrow()
        return String(result.stdout) || "No matches found."
      },
    }),

    // ---- glob override -------------------------------------------------------
    glob: tool({
      description: "Find files by glob pattern (compressed through lean-ctx). Falls back to native glob if lean-ctx is unavailable.",
      args: {
        pattern: tool.schema.string().describe("Glob pattern, e.g. 'src/**/*.ts'"),
        path: tool.schema.string().optional().describe("Base directory to search in"),
      },
      async execute(args: { pattern: string; path?: string }) {
        let basePath = (args.path ?? ".").replace(/\\/g, "/")
        const rawPattern = args.pattern

        // Extract leaf glob (e.g. "*.rs") and search path from the pattern.
        // "src-tauri/src/commands/**/*.rs" -> searchPath="src-tauri/src/commands", leafPattern="*.rs"
        // lean-ctx find does NOT support recursive glob patterns like **/*.rs
        const parts = rawPattern.split("/")
        let leafPattern = parts[parts.length - 1] || "*"
        // If pattern contains path segments, merge into basePath
        if (parts.length > 1) {
          const patternDir = parts.slice(0, -1).join("/").replace(/\*\*\/?/g, "")
          basePath = basePath === "." ? patternDir : `${basePath}/${patternDir}`
        }

        // Try lean-ctx find first
        const compressed = await leanCtx(["find", leafPattern, basePath])
        if (compressed) return compressed

        // Fallback: ripgrep --files with glob filter
        const result = await $`rg --files ${basePath} -g ${rawPattern}`.quiet().nothrow()
        return String(result.stdout) || "No files matched."
      },
    }),
  }

  return {
    "tool.execute.before": beforeHook,
    tool: tools,
  }
}
