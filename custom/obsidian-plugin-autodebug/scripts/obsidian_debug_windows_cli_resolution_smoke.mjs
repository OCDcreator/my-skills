#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const toolRoot = path.resolve(scriptDir, '..');

function describeError(error) {
  return error?.message ? String(error.message) : String(error);
}

function runProcess(command, args, { cwd = '', env, timeoutMs = 30000 } = {}) {
  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    let settled = false;
    let child;

    try {
      child = spawn(command, args, {
        cwd: cwd || undefined,
        env,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (error) {
      resolve({
        ok: false,
        exitCode: null,
        stdout,
        stderr: describeError(error),
        timedOut: false,
      });
      return;
    }

    const timeout = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      child.kill();
      resolve({ ok: false, exitCode: null, stdout, stderr, timedOut: true });
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        ok: false,
        exitCode: null,
        stdout,
        stderr: `${stderr}${describeError(error)}`,
        timedOut: false,
      });
    });
    child.on('close', (code) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        ok: code === 0,
        exitCode: code,
        stdout,
        stderr,
        timedOut: false,
      });
    });
  });
}

async function readWindowsPathScopes() {
  const result = await runProcess(
    'powershell',
    [
      '-NoProfile',
      '-Command',
      "[Environment]::GetEnvironmentVariable('Path','User'); '---'; [Environment]::GetEnvironmentVariable('Path','Machine')",
    ],
    { timeoutMs: 10000 },
  );
  if (!result.ok) {
    throw new Error(`Unable to read Windows PATH scopes: ${result.stderr || result.stdout || 'unknown error'}`);
  }

  const [userPath = '', machinePath = ''] = result.stdout.split(/\r?\n---\r?\n/, 2);
  return { userPath: userPath.trim(), machinePath: machinePath.trim() };
}

function splitPathEntries(value) {
  return String(value || '')
    .split(path.delimiter)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

async function existingObsidianDirs(...pathValues) {
  const seen = new Set();
  const found = [];

  for (const entry of pathValues.flatMap((value) => splitPathEntries(value))) {
    const normalized = path.normalize(entry);
    if (seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);

    try {
      const entries = await fs.readdir(normalized);
      if (entries.some((name) => /^obsidian\.(com|exe)$/i.test(name))) {
        found.push(normalized);
      }
    } catch {
      // Ignore unreadable path entries.
    }
  }

  return found;
}

function withStrippedObsidianPath(baseEnv, obsidianDirs) {
  const stripSet = new Set(obsidianDirs.map((entry) => path.normalize(entry).toLowerCase()));
  const env = { ...baseEnv };
  const keys = Object.keys(env).filter((key) => key.toLowerCase() === 'path');
  const currentPath = keys.length > 0 ? env[keys[0]] : process.env.PATH ?? '';
  const filtered = splitPathEntries(currentPath)
    .filter((entry) => !stripSet.has(path.normalize(entry).toLowerCase()))
    .join(path.delimiter);

  for (const key of keys) {
    env[key] = filtered;
  }
  if (!keys.some((key) => key === 'PATH')) {
    env.PATH = filtered;
  }
  return env;
}

async function main() {
  if (process.platform !== 'win32') {
    console.log(JSON.stringify({
      status: 'skipped',
      platform: process.platform,
      reason: 'Windows-only smoke for stale PATH Obsidian CLI recovery.',
    }, null, 2));
    return;
  }

  const nodeExecutable = process.execPath;
  const { userPath, machinePath } = await readWindowsPathScopes();
  const obsidianDirs = await existingObsidianDirs(process.env.PATH ?? '', userPath, machinePath);

  if (obsidianDirs.length === 0) {
    console.log(JSON.stringify({
      status: 'skipped',
      reason: 'No Obsidian directory was found in current/user/machine PATH scopes.',
    }, null, 2));
    return;
  }

  const childEnv = withStrippedObsidianPath(process.env, obsidianDirs);
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-cli-resolution-smoke-'));
  const fixtureRepo = path.join(toolRoot, 'fixtures', 'native-smoke-sample-plugin');
  const launchOutput = path.join(tempDir, 'launch.json');
  const doctorOutput = path.join(tempDir, 'doctor.json');

  const launchResult = await runProcess(
    nodeExecutable,
    [
      path.join(scriptDir, 'obsidian_debug_launch_app.mjs'),
      '--mode',
      'cli',
      '--wait-ms',
      '1000',
      '--poll-interval-ms',
      '200',
      '--output',
      launchOutput,
    ],
    {
      cwd: toolRoot,
      env: childEnv,
      timeoutMs: 30000,
    },
  );
  assert.equal(launchResult.exitCode, 0, `launch helper exited unexpectedly: ${launchResult.stderr || launchResult.stdout}`);

  const launchReport = JSON.parse(await fs.readFile(launchOutput, 'utf8'));
  const cliProbe = launchReport.finalReadiness?.probes?.find((probe) => probe.channel === 'cli');
  assert.equal(cliProbe?.ok, true, `launch helper did not recover CLI readiness from stale PATH: ${JSON.stringify(launchReport, null, 2)}`);

  const doctorResult = await runProcess(
    nodeExecutable,
    [
      path.join(scriptDir, 'obsidian_debug_doctor.mjs'),
      '--repo-dir',
      fixtureRepo,
      '--plugin-id',
      'native-smoke-sample-plugin',
      '--output',
      doctorOutput,
    ],
    {
      cwd: toolRoot,
      env: childEnv,
      timeoutMs: 60000,
    },
  );
  assert.equal(doctorResult.exitCode, 0, `doctor exited unexpectedly: ${doctorResult.stderr || doctorResult.stdout}`);

  const doctorReport = JSON.parse(await fs.readFile(doctorOutput, 'utf8'));
  const obsidianCliCheck = Array.isArray(doctorReport.checks)
    ? doctorReport.checks.find((check) => check.id === 'obsidian-cli')
    : null;
  assert.equal(
    obsidianCliCheck?.status,
    'pass',
    `doctor did not mark Obsidian CLI as available after stale PATH recovery: ${JSON.stringify(obsidianCliCheck, null, 2)}`,
  );

  console.log(JSON.stringify({
    status: 'ok',
    obsidianDirs,
    launchCliProbe: cliProbe,
    doctorCliCheck: obsidianCliCheck,
    tempDir,
  }, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exit(1);
});
