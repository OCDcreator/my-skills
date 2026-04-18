import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const scenarioName = getStringOption(options, 'scenario-name', '').trim();
const explicitScenarioPath = getStringOption(options, 'scenario-path', '').trim();
const pluginId = getStringOption(options, 'plugin-id', '').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const obsidianCommand = getStringOption(options, 'obsidian-command', '').trim();
const scenarioCommandId = getStringOption(options, 'scenario-command-id', '').trim();
const scenarioSleepMs = getNumberOption(options, 'scenario-sleep-ms', 2000);
const outputPath = getStringOption(
  options,
  'output',
  path.resolve('.obsidian-debug/scenario-report.json'),
);

if (!obsidianCommand) {
  throw new Error('--obsidian-command is required');
}

function resolveScenarioPath() {
  if (explicitScenarioPath) {
    return path.resolve(explicitScenarioPath);
  }
  if (!scenarioName) {
    throw new Error('Either --scenario-name or --scenario-path is required');
  }

  return path.resolve(scriptDirectory, '..', 'scenarios', `${scenarioName}.json`);
}

function substituteTemplate(value, context) {
  if (typeof value !== 'string') {
    return value;
  }

  return value.replace(/\$\{([^}]+)\}/g, (_, key) => {
    const resolved = context[key];
    return resolved === undefined || resolved === null ? '' : String(resolved);
  });
}

function normalizeArgs(args, context) {
  if (!Array.isArray(args)) {
    return [];
  }

  return args.map((entry) => substituteTemplate(entry, context)).filter((entry) => entry.length > 0);
}

function runObsidianCli(command, args) {
  const cliArgs = [];
  if (vaultName) {
    cliArgs.push(`vault=${vaultName}`);
  }
  cliArgs.push(command, ...args);

  const startedAt = nowIso();
  const result = spawnSync(obsidianCommand, cliArgs, {
    encoding: 'utf8',
    windowsHide: true,
  });
  const finishedAt = nowIso();

  return {
    type: 'obsidian-cli',
    command,
    args,
    startedAt,
    finishedAt,
    exitCode: result.status ?? 0,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    ok: (result.status ?? 0) === 0,
  };
}

const scenarioPath = resolveScenarioPath();
const scenario = JSON.parse(await fs.readFile(scenarioPath, 'utf8'));
const variableContext = {
  pluginId,
  vaultName,
  commandId: scenarioCommandId || `${pluginId}:open-view`,
  sleepAfterMs: scenarioSleepMs,
};

const executedSteps = [];
let success = true;

for (const step of scenario.steps ?? []) {
  if (step.type === 'sleep') {
    const ms = Number(substituteTemplate(String(step.ms ?? 0), variableContext)) || 0;
    const startedAt = nowIso();
    await new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));
    executedSteps.push({
      type: 'sleep',
      ms,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    });
    continue;
  }

  if (step.type === 'obsidian-cli') {
    const command = substituteTemplate(step.command ?? '', variableContext);
    const args = normalizeArgs(step.args, variableContext);
    const result = runObsidianCli(command, args);
    executedSteps.push(result);
    if (!result.ok) {
      success = false;
      break;
    }
    continue;
  }

  executedSteps.push({
    type: step.type ?? 'unknown',
    ok: false,
    error: `Unsupported scenario step type: ${step.type ?? 'unknown'}`,
    startedAt: nowIso(),
    finishedAt: nowIso(),
  });
  success = false;
  break;
}

const report = {
  generatedAt: nowIso(),
  success,
  scenarioName: scenario.name ?? scenarioName ?? path.basename(scenarioPath, '.json'),
  description: scenario.description ?? '',
  scenarioPath,
  obsidianCommand,
  vaultName: vaultName || null,
  pluginId: pluginId || null,
  variables: variableContext,
  steps: executedSteps,
};

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(report, null, 2));

if (!success) {
  throw new Error(`Scenario failed: ${report.scenarioName}`);
}
