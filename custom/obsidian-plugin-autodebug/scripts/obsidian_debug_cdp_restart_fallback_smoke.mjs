#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getNumberOption,
  getStringOption,
  hasHelpOption,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_cdp_restart_fallback_smoke.mjs [options]

Options:
  --csc-path <path>                  Optional path to csc.exe.
  --cdp-port <n>                     Fixed port to test. Defaults to an ephemeral port.
  --wait-ms <n>                      Launch-helper wait window. Defaults to 4000.
  --poll-interval-ms <n>             Launch-helper poll interval. Defaults to 250.
  --output <path>                    Optional JSON summary output.
  --keep-temp                        Preserve the temporary fake-app directory.
`);
}

if (process.platform !== 'win32') {
  const skipped = {
    status: 'skipped',
    platform: process.platform,
    reason: 'Synthetic CDP restart fallback smoke currently validates the Windows restart helper only.',
  };
  console.log(JSON.stringify(skipped, null, 2));
  process.exit(0);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const toolRoot = path.resolve(scriptDir, '..');
const outputPath = getStringOption(options, 'output', '').trim();
const waitMs = Math.max(1000, getNumberOption(options, 'wait-ms', 4000));
const pollIntervalMs = Math.max(100, getNumberOption(options, 'poll-interval-ms', 250));
const keepTemp = Object.prototype.hasOwnProperty.call(options, 'keep-temp');

function normalizePath(filePath) {
  return path.normalize(path.resolve(filePath));
}

function describeError(error) {
  return error?.message ? String(error.message) : String(error);
}

function runCommand(command, args, { cwd = '', timeoutMs = 20000 } = {}) {
  return new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    let settled = false;
    let child;

    try {
      child = spawn(command, args, {
        cwd: cwd || undefined,
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

async function getAvailablePort() {
  return await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        reject(new Error('Unable to reserve an ephemeral port for CDP smoke.'));
        server.close();
        return;
      }
      const { port } = address;
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
  });
}

function resolveCscCandidates() {
  const requested = getStringOption(options, 'csc-path', '').trim();
  if (requested) {
    return [requested];
  }
  return [
    'C:\\Windows\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe',
    'C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe',
  ];
}

const FAKE_APP_SOURCE = `using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public static class Program
{
    public static void Main(string[] args)
    {
        int port = 9222;
        foreach (var arg in args)
        {
            const string prefix = "--remote-debugging-port=";
            if (arg.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
            {
                int parsed;
                if (int.TryParse(arg.Substring(prefix.Length), out parsed))
                {
                    port = parsed;
                }
            }
        }

        string markerPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "restart.marker");
        if (!File.Exists(markerPath))
        {
            File.WriteAllText(markerPath, "first-run");
            while (true)
            {
                Thread.Sleep(1000);
            }
        }

        var listener = new TcpListener(IPAddress.Loopback, port);
        listener.Start();
        var payload = "[{\\"title\\":\\"Obsidian Smoke\\",\\"url\\":\\"app://obsidian.md/index.html\\"}]";
        var bodyBytes = Encoding.UTF8.GetBytes(payload);
        while (true)
        {
            using (var client = listener.AcceptTcpClient())
            using (var stream = client.GetStream())
            {
                var requestBuffer = new byte[4096];
                stream.Read(requestBuffer, 0, requestBuffer.Length);
                var header = string.Format("HTTP/1.1 200 OK\\r\\nContent-Type: application/json\\r\\nContent-Length: {0}\\r\\nConnection: close\\r\\n\\r\\n", bodyBytes.Length);
                var headerBytes = Encoding.ASCII.GetBytes(header);
                stream.Write(headerBytes, 0, headerBytes.Length);
                stream.Write(bodyBytes, 0, bodyBytes.Length);
            }
        }
    }
}
`;

async function compileFakeApp(tempRoot, cscPath) {
  const sourcePath = path.join(tempRoot, 'FakeObsidianSmoke.cs');
  const exePath = path.join(tempRoot, 'FakeObsidianSmoke.exe');
  await fs.writeFile(sourcePath, FAKE_APP_SOURCE, 'utf8');

  const compileResult = await runCommand(
    cscPath,
    ['/nologo', '/t:exe', `/out:${exePath}`, sourcePath],
    { timeoutMs: 20000 },
  );
  if (!compileResult.ok) {
    throw new Error(`Failed to compile fake Obsidian app: ${compileResult.stderr || compileResult.stdout || 'no output'}`);
  }

  return exePath;
}

async function cleanupFakeProcess(exePath) {
  const processName = path.basename(exePath, path.extname(exePath));
  const cleanupResult = await runCommand(
    'powershell',
    [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-Command',
      `Get-Process -Name '${processName}' -ErrorAction SilentlyContinue | Stop-Process -Force`,
    ],
    { timeoutMs: 8000 },
  );
  return cleanupResult;
}

async function main() {
  const cscCandidates = resolveCscCandidates();
  const cscPath = (await Promise.all(
    cscCandidates.map(async (candidate) => ({
      candidate,
      stat: await fs.stat(candidate).catch(() => null),
    })),
  )).find((entry) => entry.stat?.isFile())?.candidate ?? '';
  assert(cscPath, `csc.exe was not found. Checked: ${cscCandidates.join(', ')}`);

  const cdpPort = getNumberOption(options, 'cdp-port', 0) || await getAvailablePort();
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-cdp-restart-smoke-'));
  const launchReportPath = path.join(tempRoot, 'app-launch.json');
  let fakeExePath = '';
  let cleanupResult = null;

  try {
    fakeExePath = await compileFakeApp(tempRoot, cscPath);
    const launchResult = await runCommand(
      'node',
      [
        path.join(scriptDir, 'obsidian_debug_launch_app.mjs'),
        '--mode',
        'cdp',
        '--app-path',
        fakeExePath,
        '--cdp-port',
        String(cdpPort),
        '--wait-ms',
        String(waitMs),
        '--poll-interval-ms',
        String(pollIntervalMs),
        '--output',
        launchReportPath,
      ],
      {
        cwd: toolRoot,
        timeoutMs: Math.max(25000, waitMs * 3),
      },
    );

    assert.equal(launchResult.ok, true, `Launch helper should succeed:\n${launchResult.stderr || launchResult.stdout}`);

    const report = JSON.parse(await fs.readFile(launchReportPath, 'utf8'));
    assert.equal(report.mode, 'cdp', 'Smoke must exercise CDP mode.');
    assert.equal(report.ready, true, 'Launch helper should report readiness after restart fallback.');
    assert.equal(report.initialReadiness?.ok, false, 'Initial readiness should fail before restart fallback.');
    assert.equal(report.cdpRestartFallback?.attempted, true, 'Restart fallback should be attempted.');
    assert.equal(report.cdpRestartFallback?.ok, true, 'Restart fallback should succeed.');
    assert.equal(report.cdpRestartFallback?.readyAfterRestart, true, 'CDP should become reachable after restart.');
    assert.equal(
      normalizePath(report.cdpRestartFallback?.appPath ?? ''),
      normalizePath(fakeExePath),
      'Restart fallback should target the synthetic fake app.',
    );
    assert.equal(
      normalizePath(report.launchSteps?.[0]?.command ?? ''),
      normalizePath(fakeExePath),
      'Initial launch should target the synthetic fake app.',
    );
    assert.equal(report.finalReadiness?.ok, true, 'Final readiness should succeed.');
    assert.match(
      report.finalReadiness?.probes?.[0]?.detail ?? '',
      /CDP target is reachable/i,
      'Final CDP probe should confirm the synthetic target is reachable.',
    );

    cleanupResult = await cleanupFakeProcess(fakeExePath);
    const summary = {
      status: 'pass',
      platform: process.platform,
      cscPath,
      cdpPort,
      tempArtifactsRetained: keepTemp,
      fakeExePath: keepTemp ? fakeExePath : null,
      launchReportPath: keepTemp ? launchReportPath : null,
      cleanupOk: cleanupResult.ok,
      launchReportSnapshot: {
        ready: report.ready,
        initialReadiness: report.initialReadiness,
        launchSteps: report.launchSteps,
        cdpRestartFallback: report.cdpRestartFallback,
        finalReadiness: report.finalReadiness,
      },
      assertedFields: [
        'launchSteps[0].command',
        'cdpRestartFallback.attempted',
        'cdpRestartFallback.ok',
        'cdpRestartFallback.readyAfterRestart',
        'finalReadiness.ok',
      ],
    };

    if (outputPath) {
      const resolvedOutputPath = path.resolve(outputPath);
      await ensureParentDirectory(resolvedOutputPath);
      await fs.writeFile(resolvedOutputPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
    }

    console.log(JSON.stringify(summary, null, 2));
  } finally {
    if (!cleanupResult && fakeExePath) {
      await cleanupFakeProcess(fakeExePath).catch(() => null);
    }
    if (!keepTemp) {
      await fs.rm(tempRoot, { recursive: true, force: true });
    }
  }
}

await main();
