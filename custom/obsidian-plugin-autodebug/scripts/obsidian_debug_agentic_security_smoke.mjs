import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  hasHelpOption,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const scriptRoot = path.join(toolRoot, 'scripts');
const fixtureDir = path.join(toolRoot, 'fixtures', 'agentic-ai-smoke-plugin');
const options = parseArgs(process.argv.slice(2));

if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_agentic_security_smoke.mjs

Runs a synthetic smoke test for optional AI-plugin safety checks and local REST/MCP probing.
It starts a temporary localhost tools server, runs agentic support detection, runs doctor,
and verifies SecretStorage/redaction/network-boundary plus mcp-rest-security checks.
`);
}

function runJson(command, args, { cwd } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Command failed (${code}): ${command} ${args.join(' ')}\n${stderr || stdout}`));
        return;
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        reject(new Error(`Expected JSON output from ${command} ${args.join(' ')}\n${stdout}\n${stderr}\n${error}`));
      }
    });
  });
}

function startFakeRestServer() {
  const server = http.createServer((request, response) => {
    const url = new URL(request.url ?? '/', 'http://127.0.0.1');
    const auth = request.headers.authorization ?? '';
    const commonHeaders = { 'content-type': 'application/json' };

    if (url.pathname === '/health') {
      response.writeHead(200, commonHeaders);
      response.end(JSON.stringify({ ok: true, service: 'obsidian-cli-rest-smoke' }));
      return;
    }

    if (url.pathname === '/tools') {
      response.writeHead(auth ? 200 : 401, commonHeaders);
      response.end(JSON.stringify({
        ok: Boolean(auth),
        tools: [
          { name: 'plugin.reload', description: 'Reload an Obsidian community plugin.' },
          { name: 'dev.console', description: 'Read developer console output.' },
        ],
        toolWhitelist: ['plugin.reload', 'dev.console'],
        authRequired: true,
      }));
      return;
    }

    response.writeHead(404, commonHeaders);
    response.end(JSON.stringify({ ok: false, error: 'not-found' }));
  });

  return new Promise((resolve, reject) => {
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        reject(new Error('Fake REST server did not expose a TCP port.'));
        return;
      }
      resolve({
        baseUrl: `http://127.0.0.1:${address.port}`,
        close: () => new Promise((closeResolve, closeReject) => {
          server.close((error) => (error ? closeReject(error) : closeResolve()));
        }),
      });
    });
  });
}

async function main() {
  const restServer = await startFakeRestServer();
  const tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-agentic-security-smoke-'));
  const supportOutputPath = path.join(tempRoot, 'agentic-support.json');
  const doctorOutputPath = path.join(tempRoot, 'doctor.json');

  try {
    const support = await runJson(
      'node',
      [
        path.join(scriptRoot, 'obsidian_debug_agentic_support.mjs'),
        '--repo-dir',
        fixtureDir,
        '--rest-base-url',
        restServer.baseUrl,
        '--rest-api-key',
        'fixture-key',
        '--output',
        supportOutputPath,
      ],
      { cwd: toolRoot },
    );

    assert.equal(support.aiSafety?.secretStorage?.present, true, 'fixture should expose positive SecretStorage evidence');
    assert.equal(support.aiSafety?.redaction?.present, true, 'fixture should expose redaction evidence');
    assert.equal(support.aiSafety?.externalRequests?.present, true, 'fixture should expose external request evidence');
    assert.equal(support.runtimeProbes?.rest?.ok, true, 'REST probe should succeed against the fake local server');
    assert.equal(support.runtimeProbes?.rest?.localhost, true, 'REST probe should record localhost binding');
    assert.equal(support.runtimeProbes?.rest?.authProvided, true, 'REST probe should record that auth was provided');
    assert(
      support.runtimeProbes?.rest?.tools?.some((tool) => tool.name === 'plugin.reload'),
      'REST probe should collect available tool names',
    );
    assert(
      support.recommendations?.some((entry) => /SecretStorage|redaction|MCP\/REST|REST/i.test(entry)),
      'agentic support should emit actionable recommendations',
    );

    const doctor = await runJson(
      'node',
      [
        path.join(scriptRoot, 'obsidian_debug_doctor.mjs'),
        '--repo-dir',
        fixtureDir,
        '--plugin-id',
        'agentic-ai-smoke-plugin',
        '--agentic-rest-base-url',
        restServer.baseUrl,
        '--agentic-rest-api-key',
        'fixture-key',
        '--output',
        doctorOutputPath,
      ],
      { cwd: toolRoot },
    );
    const checksById = new Map(doctor.checks.map((entry) => [entry.id, entry]));

    for (const id of [
      'agentic-control-surfaces',
      'ai-plugin-secret-storage',
      'ai-plugin-network-boundary',
      'mcp-rest-security',
    ]) {
      assert(checksById.has(id), `Doctor should include ${id}`);
    }

    assert.equal(checksById.get('ai-plugin-secret-storage').status, 'pass');
    assert.equal(checksById.get('mcp-rest-security').status, 'pass');
    assert.equal(doctor.agenticSupport?.runtimeProbes?.rest?.ok, true);

    console.log(JSON.stringify({
      status: 'pass',
      fixture: path.relative(toolRoot, fixtureDir).replaceAll('\\', '/'),
      checkedDoctorIds: [...checksById.keys()].filter((id) => id.includes('agentic') || id.includes('ai-plugin') || id.includes('mcp-rest')),
      restBaseUrl: restServer.baseUrl,
    }, null, 2));
  } finally {
    await restServer.close();
    await fs.rm(tempRoot, { recursive: true, force: true });
  }
}

await main();
