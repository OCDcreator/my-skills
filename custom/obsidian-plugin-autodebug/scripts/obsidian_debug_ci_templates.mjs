import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';
import { detectEcosystemSupport } from './obsidian_debug_ecosystem_support.mjs';
import {
  detectPreflightSupport,
  getPreflightScriptName,
} from './obsidian_debug_preflight_support.mjs';
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

function firstToolScript(tool) {
  return tool?.scripts?.[0]?.name ?? '';
}

function statusText(tool, missingText) {
  return tool.available
    ? `installed as \`${tool.moduleName}\`${tool.version ? ` (${tool.version})` : ''}`
    : tool.declared
      ? `declared as \`${tool.moduleName}\` but not installed in this checkout`
      : missingText;
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
AUTODEBUG_LINT_SCRIPT="\${AUTODEBUG_LINT_SCRIPT:-${envDefault(defaults.lintScript)}}"
AUTODEBUG_BUILD_SCRIPT="\${AUTODEBUG_BUILD_SCRIPT:-${envDefault(defaults.buildScript)}}"
AUTODEBUG_TEST_SCRIPT="\${AUTODEBUG_TEST_SCRIPT:-${envDefault(defaults.testScript)}}"
AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT="\${AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT:-${envDefault(defaults.pluginEntryValidationScript)}}"
AUTODEBUG_OBSIDIAN_E2E_SCRIPT="\${AUTODEBUG_OBSIDIAN_E2E_SCRIPT:-${envDefault(defaults.obsidianE2EScript)}}"
AUTODEBUG_TESTING_FRAMEWORK_SCRIPT="\${AUTODEBUG_TESTING_FRAMEWORK_SCRIPT:-${envDefault(defaults.testingFrameworkScript)}}"
AUTODEBUG_WDIO_SCRIPT="\${AUTODEBUG_WDIO_SCRIPT:-${envDefault(defaults.wdioScript)}}"
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
run_optional_script "lint" "\${AUTODEBUG_LINT_SCRIPT}"
run_optional_script "plugin entry validation" "\${AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT}"
run_optional_script "build" "\${AUTODEBUG_BUILD_SCRIPT}"
run_optional_script "repo test" "\${AUTODEBUG_TEST_SCRIPT}"
run_optional_script "obsidian-e2e" "\${AUTODEBUG_OBSIDIAN_E2E_SCRIPT}"
run_optional_script "obsidian-testing-framework" "\${AUTODEBUG_TESTING_FRAMEWORK_SCRIPT}"
run_optional_script "wdio-obsidian-service" "\${AUTODEBUG_WDIO_SCRIPT}"

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
$LintScript = if ($env:AUTODEBUG_LINT_SCRIPT) { $env:AUTODEBUG_LINT_SCRIPT } else { '${defaults.lintScript.replaceAll("'", "''")}' }
$BuildScript = if ($env:AUTODEBUG_BUILD_SCRIPT) { $env:AUTODEBUG_BUILD_SCRIPT } else { '${defaults.buildScript.replaceAll("'", "''")}' }
$TestScript = if ($env:AUTODEBUG_TEST_SCRIPT) { $env:AUTODEBUG_TEST_SCRIPT } else { '${defaults.testScript.replaceAll("'", "''")}' }
$PluginEntryValidationScript = if ($env:AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT) { $env:AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT } else { '${defaults.pluginEntryValidationScript.replaceAll("'", "''")}' }
$ObsidianE2EScript = if ($env:AUTODEBUG_OBSIDIAN_E2E_SCRIPT) { $env:AUTODEBUG_OBSIDIAN_E2E_SCRIPT } else { '${defaults.obsidianE2EScript.replaceAll("'", "''")}' }
$TestingFrameworkScript = if ($env:AUTODEBUG_TESTING_FRAMEWORK_SCRIPT) { $env:AUTODEBUG_TESTING_FRAMEWORK_SCRIPT } else { '${defaults.testingFrameworkScript.replaceAll("'", "''")}' }
$WdioScript = if ($env:AUTODEBUG_WDIO_SCRIPT) { $env:AUTODEBUG_WDIO_SCRIPT } else { '${defaults.wdioScript.replaceAll("'", "''")}' }
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
Invoke-OptionalScript -Label 'lint' -ScriptName $LintScript
Invoke-OptionalScript -Label 'plugin entry validation' -ScriptName $PluginEntryValidationScript
Invoke-OptionalScript -Label 'build' -ScriptName $BuildScript
Invoke-OptionalScript -Label 'repo test' -ScriptName $TestScript
Invoke-OptionalScript -Label 'obsidian-e2e' -ScriptName $ObsidianE2EScript
Invoke-OptionalScript -Label 'obsidian-testing-framework' -ScriptName $TestingFrameworkScript
Invoke-OptionalScript -Label 'wdio-obsidian-service' -ScriptName $WdioScript

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
      AUTODEBUG_LINT_SCRIPT: ${yamlQuote(defaults.lintScript)}
      AUTODEBUG_BUILD_SCRIPT: ${yamlQuote(defaults.buildScript)}
      AUTODEBUG_TEST_SCRIPT: ${yamlQuote(defaults.testScript)}
      AUTODEBUG_PLUGIN_ENTRY_VALIDATE_SCRIPT: ${yamlQuote(defaults.pluginEntryValidationScript)}
      AUTODEBUG_OBSIDIAN_E2E_SCRIPT: ${yamlQuote(defaults.obsidianE2EScript)}
      AUTODEBUG_TESTING_FRAMEWORK_SCRIPT: ${yamlQuote(defaults.testingFrameworkScript)}
      AUTODEBUG_WDIO_SCRIPT: ${yamlQuote(defaults.wdioScript)}
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

function renderReadme(defaults, testingFramework, ecosystem) {
  const testingScript = defaults.testingFrameworkScript
    ? `\`${defaults.packageRunner} ${defaults.testingFrameworkScript}\``
    : 'not configured by package.json scripts';
  const testingStatus = testingFramework.available
    ? `installed as \`${testingFramework.moduleName}\`${testingFramework.version ? ` (${testingFramework.version})` : ''}`
    : testingFramework.declared
      ? `declared as \`${testingFramework.moduleName}\` but not installed in this checkout`
      : 'not declared in this checkout';
  const wdioScript = defaults.wdioScript
    ? `\`${defaults.packageRunner} ${defaults.wdioScript}\``
    : 'not configured by package.json scripts';
  const obsidianE2EScript = defaults.obsidianE2EScript
    ? `\`${defaults.packageRunner} ${defaults.obsidianE2EScript}\``
    : 'not configured by package.json scripts';
  const pluginEntryScript = defaults.pluginEntryValidationScript
    ? `\`${defaults.packageRunner} ${defaults.pluginEntryValidationScript}\``
    : 'not configured by package.json scripts';
  const eslintStatus = statusText(
    ecosystem.tools.eslintObsidianmd,
    'not declared in this checkout',
  );
  const obsidianE2EStatus = statusText(
    ecosystem.tools.obsidianE2E,
    'not declared in this checkout',
  );
  const wdioStatus = statusText(
    ecosystem.tools.wdioObsidianService,
    'not declared in this checkout',
  );

  return `# Obsidian Autodebug Quality Gates

These generated templates keep CI/headless checks separate from local desktop smoke runs.

## CI-Suitable Steps

- Optional install command from \`AUTODEBUG_INSTALL_COMMAND\` (blank by default so repo-owned install policy stays explicit).
- Repo-owned lint preflight script: \`${defaults.lintScript || '(none detected)'}\`.
- Optional plugin-entry validation preflight script: ${pluginEntryScript}.
- Repo-owned build script: \`${defaults.buildScript || '(none detected)'}\`.
- Repo-owned test script: \`${defaults.testScript || '(none detected)'}\`.
- Optional \`obsidian-e2e\` script: ${obsidianE2EScript}.
- Optional \`obsidian-testing-framework\` script: ${testingScript}.
- Optional \`wdio-obsidian-service\` script: ${wdioScript}.
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

\`eslint-plugin-obsidianmd\` is ${eslintStatus}.
\`obsidian-e2e\` is ${obsidianE2EStatus}.
\`obsidian-testing-framework\` is ${testingStatus}. Re-run the doctor after installing dependencies if this should become an active E2E gate.
\`wdio-obsidian-service\` is ${wdioStatus}. When the repo owns a WDIO suite, this can move real plugin E2E into CI instead of keeping it desktop-only.
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
  const ecosystem = await detectEcosystemSupport({ repoDir: resolvedRepoDir });
  const preflight = await detectPreflightSupport({
    repoDir: resolvedRepoDir,
    runtimeSupport: repoRuntime,
    ecosystemSupport: ecosystem,
  });
  const testingFramework = await detectTestingFrameworkSupport({
    repoDir: resolvedRepoDir,
    moduleName: testingFrameworkModule,
  });
  const inferredManager = repoRuntime.inference?.manager ?? 'npm';
  const lintScript = getPreflightScriptName(preflight, 'lint');
  const testScript = repoRuntime.scripts?.important?.test?.exists ? 'test' : '';
  const detectedTestingFrameworkScript = firstTestingFrameworkScript(testingFramework);
  const detectedPluginEntryValidationScript = getPreflightScriptName(preflight, 'plugin-entry-validation', {
    exclude: [lintScript],
  });
  const detectedObsidianE2EScript = firstToolScript(ecosystem.tools.obsidianE2E);
  const detectedWdioScript = firstToolScript(ecosystem.tools.wdioObsidianService);
  const defaults = {
    toolRootRef: normalizeToolRootRef(toolRootRef),
    jobPath: relativeFromRepo(resolvedRepoDir, jobPath),
    installCommand: String(installCommand ?? '').trim(),
    packageRunner: recommendedPackageRunner(inferredManager),
    lintScript,
    buildScript: repoRuntime.scripts?.important?.build?.exists ? 'build' : '',
    testScript,
    pluginEntryValidationScript: detectedPluginEntryValidationScript
      && ![testScript].includes(detectedPluginEntryValidationScript)
      ? detectedPluginEntryValidationScript
      : '',
    obsidianE2EScript: detectedObsidianE2EScript
      && ![lintScript, testScript].includes(detectedObsidianE2EScript)
      ? detectedObsidianE2EScript
      : '',
    testingFrameworkScript: detectedTestingFrameworkScript && detectedTestingFrameworkScript !== testScript
      ? detectedTestingFrameworkScript
      : '',
    wdioScript: detectedWdioScript
      && ![lintScript, testScript].includes(detectedWdioScript)
      ? detectedWdioScript
      : '',
    outputDir: ciOutputDir,
    templateDir: toPosixPath(path.relative(resolvedRepoDir, resolvedOutputDir) || '.'),
    githubActionsPath: path.join(resolvedOutputDir, 'github-actions-quality-gate.yml'),
  };
  const files = [
    {
      path: path.join(resolvedOutputDir, 'README.md'),
      content: renderReadme(defaults, testingFramework, ecosystem),
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
    preflight,
    testingFramework: {
      available: testingFramework.available,
      declared: testingFramework.declared,
      moduleName: testingFramework.moduleName,
      version: testingFramework.version,
      scripts: testingFramework.scripts,
      detail: testingFramework.detail,
    },
    ecosystem: {
      tools: ecosystem.tools,
      scripts: ecosystem.scripts,
    },
    ciSuitable: [
      'repo-owned install command',
      'repo-owned lint and optional plugin-entry preflight commands before build',
      'repo-owned build/test commands',
      'optional obsidian-e2e package script',
      'optional obsidian-testing-framework package script',
      'optional wdio-obsidian-service package script',
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
  if (hasHelpOption(options)) {
    printHelpAndExit(`
Usage: node scripts/obsidian_debug_ci_templates.mjs --job <job.json> [options]

Required:
  --job <path>                       Autodebug job spec used for dry-run gates.

Options:
  --repo-dir <path>                  Plugin repo directory. Defaults to cwd.
  --output-dir <dir>                 Template output dir. Defaults to autodebug/ci.
  --output <path>                    JSON report output.
  --tool-root-ref <path>             Portable tool-root reference in generated templates.
  --install-command <command>        Override detected install command.
  --ci-output-dir <dir>              CI artifact output directory.
  --testing-framework-module <name>  Optional testing framework module name.
`);
  }

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
