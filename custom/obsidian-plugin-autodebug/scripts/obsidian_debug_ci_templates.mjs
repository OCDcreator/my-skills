import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import { detectRepoRuntime } from './obsidian_debug_repo_runtime.mjs';
import { detectTestingFrameworkSupport } from './obsidian_debug_testing_framework_support.mjs';

const DEFAULT_TOOL_ROOT_REF = '.agents/skills/obsidian-plugin-autodebug';
const DEFAULT_OUTPUT_DIR = 'autodebug/ci';
const DEFAULT_CI_OUTPUT_DIR = '.obsidian-debug/ci';

function toPosixPath(value) {
  return String(value ?? '').replaceAll(path.sep, '/');
}

function relativeFromRepo(repoDir, targetPath) {
  if (!targetPath) {
    return '';
  }

  const resolvedRepoDir = path.resolve(repoDir);
  const resolvedTargetPath = path.resolve(resolvedRepoDir, targetPath);
  return toPosixPath(path.relative(resolvedRepoDir, resolvedTargetPath) || '.');
}

function normalizeToolRootRef(value) {
  const normalized = String(value ?? '').trim();
  return normalized.length > 0 ? toPosixPath(normalized) : DEFAULT_TOOL_ROOT_REF;
}

function recommendedPackageRunner(manager) {
  const normalized = String(manager ?? '').trim().toLowerCase();
  if (normalized === 'pnpm') {
    return 'corepack pnpm run';
  }
  if (normalized === 'yarn') {
    return 'corepack yarn run';
  }
  if (normalized === 'bun') {
    return 'bun run';
  }
  return 'npm run';
}

function envDefault(value) {
  return String(value ?? '').replaceAll('"', '\\"');
}

function yamlQuote(value) {
  return JSON.stringify(String(value ?? ''));
}

function firstTestingFrameworkScript(testingFramework) {
  return testingFramework.scripts?.[0]?.name ?? '';
}

function renderBashQualityGate(defaults) {
  return `#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "\${SCRIPT_DIR}/../.." && pwd)"
cd "\${REPO_ROOT}"

AUTODEBUG_TOOL_ROOT="\${AUTODEBUG_TOOL_ROOT:-${envDefault(defaults.toolRootRef)}}"
AUTODEBUG_JOB_PATH="\${AUTODEBUG_JOB_PATH:-${envDefault(defaults.jobPath)}}"
AUTODEBUG_INSTALL_COMMAND="\${AUTODEBUG_INSTALL_COMMAND:-${envDefault(defaults.installCommand)}}"
AUTODEBUG_PACKAGE_RUNNER="\${AUTODEBUG_PACKAGE_RUNNER:-${envDefault(defaults.packageRunner)}}"
AUTODEBUG_BUILD_SCRIPT="\${AUTODEBUG_BUILD_SCRIPT:-${envDefault(defaults.buildScript)}}"
AUTODEBUG_TEST_SCRIPT="\${AUTODEBUG_TEST_SCRIPT:-${envDefault(defaults.testScript)}}"
AUTODEBUG_TESTING_FRAMEWORK_SCRIPT="\${AUTODEBUG_TESTING_FRAMEWORK_SCRIPT:-${envDefault(defaults.testingFrameworkScript)}}"
AUTODEBUG_OUTPUT_DIR="\${AUTODEBUG_OUTPUT_DIR:-${envDefault(defaults.outputDir)}}"

run_optional_command() {
  local label="$1"
  local command="$2"

  if [[ -z "\${command// }" ]]; then
    echo "[skip] \${label}"
    return 0
  fi

  echo "[run] \${label}: \${command}"
  bash -lc "\${command}"
}

run_optional_script() {
  local label="$1"
  local script_name="$2"

  if [[ -z "\${script_name// }" ]]; then
    echo "[skip] \${label}"
    return 0
  fi

  run_optional_command "\${label}" "\${AUTODEBUG_PACKAGE_RUNNER} \${script_name}"
}

mkdir -p "\${AUTODEBUG_OUTPUT_DIR}"

run_optional_command "install" "\${AUTODEBUG_INSTALL_COMMAND}"
run_optional_script "build" "\${AUTODEBUG_BUILD_SCRIPT}"
run_optional_script "repo test" "\${AUTODEBUG_TEST_SCRIPT}"
run_optional_script "obsidian-testing-framework" "\${AUTODEBUG_TESTING_FRAMEWORK_SCRIPT}"

node "\${AUTODEBUG_TOOL_ROOT}/scripts/obsidian_debug_job.mjs" \\
  --job "\${AUTODEBUG_JOB_PATH}" \\
  --platform bash \\
  --dry-run \\
  --output "\${AUTODEBUG_OUTPUT_DIR}/job-plan-bash.json"
`;
}

function renderPowerShellQualityGate(defaults) {
  return `$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\\..')).Path
Set-Location $RepoRoot

$ToolRoot = if ($env:AUTODEBUG_TOOL_ROOT) { $env:AUTODEBUG_TOOL_ROOT } else { '${defaults.toolRootRef.replaceAll("'", "''")}' }
$JobPath = if ($env:AUTODEBUG_JOB_PATH) { $env:AUTODEBUG_JOB_PATH } else { '${defaults.jobPath.replaceAll("'", "''")}' }
$InstallCommand = if ($env:AUTODEBUG_INSTALL_COMMAND) { $env:AUTODEBUG_INSTALL_COMMAND } else { '${defaults.installCommand.replaceAll("'", "''")}' }
$PackageRunner = if ($env:AUTODEBUG_PACKAGE_RUNNER) { $env:AUTODEBUG_PACKAGE_RUNNER } else { '${defaults.packageRunner.replaceAll("'", "''")}' }
$BuildScript = if ($env:AUTODEBUG_BUILD_SCRIPT) { $env:AUTODEBUG_BUILD_SCRIPT } else { '${defaults.buildScript.replaceAll("'", "''")}' }
$TestScript = if ($env:AUTODEBUG_TEST_SCRIPT) { $env:AUTODEBUG_TEST_SCRIPT } else { '${defaults.testScript.replaceAll("'", "''")}' }
$TestingFrameworkScript = if ($env:AUTODEBUG_TESTING_FRAMEWORK_SCRIPT) { $env:AUTODEBUG_TESTING_FRAMEWORK_SCRIPT } else { '${defaults.testingFrameworkScript.replaceAll("'", "''")}' }
$OutputDir = if ($env:AUTODEBUG_OUTPUT_DIR) { $env:AUTODEBUG_OUTPUT_DIR } else { '${defaults.outputDir.replaceAll("'", "''")}' }

function Invoke-OptionalCommand {
  param(
    [string]$Label,
    [string]$Command
  )

  if ([string]::IsNullOrWhiteSpace($Command)) {
    Write-Host "[skip] $Label"
    return
  }

  Write-Host "[run] \${Label}: $Command"
  Invoke-Expression $Command
}

function Invoke-OptionalScript {
  param(
    [string]$Label,
    [string]$ScriptName
  )

  if ([string]::IsNullOrWhiteSpace($ScriptName)) {
    Write-Host "[skip] $Label"
    return
  }

  Invoke-OptionalCommand -Label $Label -Command "$PackageRunner $ScriptName"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Invoke-OptionalCommand -Label 'install' -Command $InstallCommand
Invoke-OptionalScript -Label 'build' -ScriptName $BuildScript
Invoke-OptionalScript -Label 'repo test' -ScriptName $TestScript
Invoke-OptionalScript -Label 'obsidian-testing-framework' -ScriptName $TestingFrameworkScript

$JobRunner = Join-Path $ToolRoot 'scripts/obsidian_debug_job.mjs'
$JobPlan = Join-Path $OutputDir 'job-plan-windows.json'
& node $JobRunner --job $JobPath --platform windows --dry-run --output $JobPlan
`;
}

function renderGithubActionsQualityGate(defaults) {
  const corepackCondition = "${{ startsWith(env.AUTODEBUG_PACKAGE_RUNNER, 'corepack ') }}";
  return `name: Obsidian Plugin Headless Quality Gate

on:
  workflow_dispatch:
  pull_request:
  push:
    branches:
      - main

jobs:
  headless-quality-gate:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    env:
      AUTODEBUG_TOOL_ROOT: ${yamlQuote(defaults.toolRootRef)}
      AUTODEBUG_JOB_PATH: ${yamlQuote(defaults.jobPath)}
      AUTODEBUG_INSTALL_COMMAND: ${yamlQuote(defaults.installCommand)}
      AUTODEBUG_PACKAGE_RUNNER: ${yamlQuote(defaults.packageRunner)}
      AUTODEBUG_BUILD_SCRIPT: ${yamlQuote(defaults.buildScript)}
      AUTODEBUG_TEST_SCRIPT: ${yamlQuote(defaults.testScript)}
      AUTODEBUG_TESTING_FRAMEWORK_SCRIPT: ${yamlQuote(defaults.testingFrameworkScript)}
      AUTODEBUG_OUTPUT_DIR: ${yamlQuote(defaults.outputDir)}

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Enable Corepack for pnpm/yarn
        if: ${corepackCondition}
        run: corepack enable

      - name: Run headless quality gate
        shell: bash
        run: bash ${defaults.templateDir}/quality-gate.sh
`;
}

function renderReadme(defaults, testingFramework) {
  const testingScript = defaults.testingFrameworkScript
    ? `\`${defaults.packageRunner} ${defaults.testingFrameworkScript}\``
    : 'not configured by package.json scripts';
  const testingStatus = testingFramework.available
    ? `installed as \`${testingFramework.moduleName}\`${testingFramework.version ? ` (${testingFramework.version})` : ''}`
    : testingFramework.declared
      ? `declared as \`${testingFramework.moduleName}\` but not installed in this checkout`
      : 'not declared in this checkout';

  return `# Obsidian Autodebug Quality Gates

These generated templates keep CI/headless checks separate from local desktop smoke runs.

## CI-Suitable Steps

- Optional install command from \`AUTODEBUG_INSTALL_COMMAND\` (blank by default so repo-owned install policy stays explicit).
- Repo-owned build script: \`${defaults.buildScript || '(none detected)'}\`.
- Repo-owned test script: \`${defaults.testScript || '(none detected)'}\`.
- Optional \`obsidian-testing-framework\` script: ${testingScript}.
- Cross-platform dry-run plan generation through \`${defaults.toolRootRef}/scripts/obsidian_debug_job.mjs\`.

## Local-Only Steps

- Fresh-vault bootstrap, real Obsidian reloads, CLI/CDP log capture, screenshots, DOM snapshots, and Playwright traces still require a desktop Obsidian session.
- Keep those local-only phases in the generated autodebug job and run them after the headless gate has passed.

## Template Files

- \`quality-gate.sh\` for Bash/macOS/Linux runners.
- \`quality-gate.ps1\` for Windows PowerShell runners.
- \`github-actions-quality-gate.yml\` as a copy-ready GitHub Actions workflow template.

## Defaults

- \`AUTODEBUG_TOOL_ROOT=${defaults.toolRootRef}\`
- \`AUTODEBUG_JOB_PATH=${defaults.jobPath}\`
- \`AUTODEBUG_PACKAGE_RUNNER=${defaults.packageRunner}\`
- \`AUTODEBUG_OUTPUT_DIR=${defaults.outputDir}\`

\`obsidian-testing-framework\` is ${testingStatus}. Re-run the doctor after installing dependencies if this should become an active E2E gate.
`;
}

export async function generateQualityGateTemplates({
  repoDir = process.cwd(),
  jobPath,
  outputDir = DEFAULT_OUTPUT_DIR,
  toolRootRef = DEFAULT_TOOL_ROOT_REF,
  installCommand = '',
  ciOutputDir = DEFAULT_CI_OUTPUT_DIR,
  testingFrameworkModule = '',
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  if (!jobPath || String(jobPath).trim().length === 0) {
    throw new Error('--job is required to generate quality-gate templates');
  }

  const resolvedOutputDir = path.resolve(resolvedRepoDir, outputDir);
  const repoRuntime = await detectRepoRuntime({ repoDir: resolvedRepoDir, probeTools: false });
  const testingFramework = await detectTestingFrameworkSupport({
    repoDir: resolvedRepoDir,
    moduleName: testingFrameworkModule,
  });
  const inferredManager = repoRuntime.inference?.manager ?? 'npm';
  const testScript = repoRuntime.scripts?.important?.test?.exists ? 'test' : '';
  const detectedTestingFrameworkScript = firstTestingFrameworkScript(testingFramework);
  const defaults = {
    toolRootRef: normalizeToolRootRef(toolRootRef),
    jobPath: relativeFromRepo(resolvedRepoDir, jobPath),
    installCommand: String(installCommand ?? '').trim(),
    packageRunner: recommendedPackageRunner(inferredManager),
    buildScript: repoRuntime.scripts?.important?.build?.exists ? 'build' : '',
    testScript,
    testingFrameworkScript: detectedTestingFrameworkScript && detectedTestingFrameworkScript !== testScript
      ? detectedTestingFrameworkScript
      : '',
    outputDir: ciOutputDir,
    templateDir: toPosixPath(path.relative(resolvedRepoDir, resolvedOutputDir) || '.'),
    githubActionsPath: path.join(resolvedOutputDir, 'github-actions-quality-gate.yml'),
  };
  const files = [
    {
      path: path.join(resolvedOutputDir, 'README.md'),
      content: renderReadme(defaults, testingFramework),
    },
    {
      path: path.join(resolvedOutputDir, 'quality-gate.sh'),
      content: renderBashQualityGate(defaults),
    },
    {
      path: path.join(resolvedOutputDir, 'quality-gate.ps1'),
      content: renderPowerShellQualityGate(defaults),
    },
    {
      path: path.join(resolvedOutputDir, 'github-actions-quality-gate.yml'),
      content: renderGithubActionsQualityGate(defaults),
    },
  ];

  for (const file of files) {
    await ensureParentDirectory(file.path);
    await fs.writeFile(file.path, file.content.endsWith('\n') ? file.content : `${file.content}\n`, 'utf8');
  }

  return {
    generatedAt: nowIso(),
    status: 'pass',
    repoDir: resolvedRepoDir,
    outputDir: resolvedOutputDir,
    jobPath: defaults.jobPath,
    packageManager: inferredManager,
    defaults,
    templateDir: defaults.templateDir,
    testingFramework: {
      available: testingFramework.available,
      declared: testingFramework.declared,
      moduleName: testingFramework.moduleName,
      version: testingFramework.version,
      scripts: testingFramework.scripts,
      detail: testingFramework.detail,
    },
    ciSuitable: [
      'repo-owned install/build/test commands',
      'optional obsidian-testing-framework package script',
      'autodebug job dry-run plan generation',
    ],
    localOnly: [
      'fresh-vault bootstrap',
      'desktop Obsidian reload',
      'CLI/CDP console capture',
      'screenshots, DOM snapshots, and Playwright traces',
    ],
    files: files.map((file) => toPosixPath(path.relative(resolvedRepoDir, file.path))),
  };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
  const jobPath = getStringOption(options, 'job', '').trim();
  const outputDir = getStringOption(options, 'output-dir', DEFAULT_OUTPUT_DIR).trim() || DEFAULT_OUTPUT_DIR;
  const outputPath = getStringOption(options, 'output', '').trim();
  const toolRootRef = getStringOption(options, 'tool-root-ref', DEFAULT_TOOL_ROOT_REF);
  const installCommand = getStringOption(options, 'install-command', '');
  const ciOutputDir = getStringOption(options, 'ci-output-dir', DEFAULT_CI_OUTPUT_DIR);
  const testingFrameworkModule = getStringOption(options, 'testing-framework-module', '');

  const report = await generateQualityGateTemplates({
    repoDir,
    jobPath,
    outputDir,
    toolRootRef,
    installCommand,
    ciOutputDir,
    testingFrameworkModule,
  });

  if (outputPath) {
    const resolvedOutputPath = path.resolve(outputPath);
    await ensureParentDirectory(resolvedOutputPath);
    await fs.writeFile(resolvedOutputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(report, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
