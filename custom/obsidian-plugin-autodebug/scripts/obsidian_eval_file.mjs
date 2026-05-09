#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

function parseArgs(argv) {
  const options = {
    obsidianCommand: 'obsidian',
    vaultName: '',
    file: '',
    output: '',
    timeoutMs: 30000,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--obsidian-command':
        options.obsidianCommand = argv[++index] ?? '';
        break;
      case '--vault-name':
        options.vaultName = argv[++index] ?? '';
        break;
      case '--file':
        options.file = argv[++index] ?? '';
        break;
      case '--output':
        options.output = argv[++index] ?? '';
        break;
      case '--timeout-ms':
        options.timeoutMs = Number(argv[++index] ?? '30000');
        break;
      case '--help':
        printHelp();
        process.exit(0);
        break;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  if (!options.file) {
    throw new Error('--file is required');
  }

  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) {
    throw new Error('--timeout-ms must be a positive number');
  }

  return options;
}

function printHelp() {
  console.log(`Usage: node scripts/obsidian_eval_file.mjs --file assertion.js [options]

Options:
  --obsidian-command <cmd>   Obsidian CLI command. Defaults to obsidian.
  --vault-name <name>        Optional vault name passed as vault=<name>.
  --output <path>            Optional JSON result path.
  --timeout-ms <number>      Timeout in milliseconds. Defaults to 30000.
  --help                     Show this help.
`);
}

function runCommand(command, args, timeoutMs) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGTERM');
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      clearTimeout(timer);
      resolve({
        exitCode: 1,
        timedOut,
        stdout,
        stderr: stderr + error.message,
      });
    });
    child.on('close', (exitCode) => {
      clearTimeout(timer);
      resolve({
        exitCode: timedOut ? 124 : exitCode ?? 0,
        timedOut,
        stdout,
        stderr,
      });
    });
  });
}

function parseEvalStdout(stdout) {
  const lines = stdout.trim().split(/\r?\n/).filter(Boolean);
  const resultLine = [...lines].reverse().find((line) => line.trim().startsWith('=>'));
  if (!resultLine) {
    return { text: '', json: null };
  }

  const text = resultLine.replace(/^\s*=>\s*/, '').trim();
  if (!text) {
    return { text, json: null };
  }

  try {
    return { text, json: JSON.parse(text) };
  } catch {
    return { text, json: null };
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const source = await readFile(options.file, 'utf8');
  const args = [];
  if (options.vaultName) {
    args.push(`vault=${options.vaultName}`);
  }
  args.push('eval', `code=${source}`);

  const result = await runCommand(options.obsidianCommand, args, options.timeoutMs);
  const evalResult = parseEvalStdout(result.stdout);
  const assertionFailed = evalResult.json && evalResult.json.ok === false;
  const payload = {
    generatedAt: new Date().toISOString(),
    file: path.resolve(options.file),
    obsidianCommand: options.obsidianCommand,
    vaultName: options.vaultName || null,
    ok: result.exitCode === 0 && !result.timedOut && !assertionFailed,
    evalResultText: evalResult.text || null,
    evalJson: evalResult.json,
    ...result,
  };

  if (options.output) {
    await mkdir(path.dirname(options.output), { recursive: true });
    await writeFile(options.output, `${JSON.stringify(payload, null, 2)}\n`);
  }

  if (result.stdout) {
    process.stdout.write(result.stdout);
  }
  if (result.stderr) {
    process.stderr.write(result.stderr);
  }
  process.exit(payload.ok ? 0 : payload.exitCode || 1);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
