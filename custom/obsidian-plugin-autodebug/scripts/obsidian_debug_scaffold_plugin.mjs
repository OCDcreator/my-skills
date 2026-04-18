import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getBooleanOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import { generateQualityGateTemplates } from './obsidian_debug_ci_templates.mjs';

const SUPPORTED_PACKAGE_MANAGERS = new Set(['npm', 'pnpm', 'yarn', 'bun']);
const PACKAGE_MANAGER_FIELDS = {
  npm: 'npm@10',
  pnpm: 'pnpm@9',
  yarn: 'yarn@1.22.22',
  bun: 'bun@1',
};

const options = parseArgs(process.argv.slice(2));
const outputDirRaw = getStringOption(options, 'output-dir', '').trim();
if (!outputDirRaw) {
  throw new Error('--output-dir is required');
}

const pluginId = sanitizePluginId(getStringOption(options, 'plugin-id', '').trim());
if (!pluginId) {
  throw new Error('--plugin-id is required');
}

const workspaceDir = path.resolve(outputDirRaw);
const defaultPluginName = toTitleCase(pluginId);
const pluginName = getStringOption(options, 'plugin-name', defaultPluginName).trim() || defaultPluginName;
const description = getStringOption(
  options,
  'description',
  `${pluginName} scaffolded by obsidian-plugin-autodebug for bootstrap-friendly smoke validation.`,
).trim();
const author = getStringOption(options, 'author', 'my-skills').trim() || 'my-skills';
const authorUrl = getStringOption(options, 'author-url', '').trim();
const minAppVersion = getStringOption(options, 'min-app-version', '1.4.5').trim() || '1.4.5';
const obsidianCommand = normalizeCommandReference(
  getStringOption(options, 'obsidian-command', 'obsidian').trim() || 'obsidian',
);
const testVaultRoot = path.resolve(
  getStringOption(options, 'test-vault-root', '').trim() || path.join(workspaceDir, 'test-vault'),
);
const vaultName = getStringOption(options, 'vault-name', path.basename(testVaultRoot)).trim() || path.basename(testVaultRoot);
const packageManager = normalizePackageManager(getStringOption(options, 'package-manager', 'npm'));
const overwrite = getBooleanOption(options, 'overwrite', false);
const outputPath = getStringOption(options, 'output', '').trim();

const testVaultPluginDir = path.join(testVaultRoot, '.obsidian', 'plugins', pluginId);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const skillRoot = path.resolve(scriptDir, '..');

await ensureWritableWorkspace(workspaceDir, { overwrite });

const classBase = toPascalCase(pluginId);
const viewType = `${pluginId}-view`;
const rootClass = `${pluginId}-root`;
const settingsRootClass = `${pluginId}-settings-root`;
const openViewCommandId = `${pluginId}:open-view`;
const openSettingsCommandId = `${pluginId}:open-settings`;
const readyText = `${pluginName} sample view ready`;
const settingsText = `${pluginName} settings ready`;
const viewHeader = `${pluginName} Sample View`;
const packageManagerField = PACKAGE_MANAGER_FIELDS[packageManager];

const report = {
  generatedAt: nowIso(),
  status: 'pending',
  pluginId,
  pluginName,
  workspaceDir,
  testVaultRoot,
  testVaultPluginDir,
  packageManager,
  obsidianCommand,
  jobPath: path.join(workspaceDir, 'autodebug', `${pluginId}-debug-job.json`),
  files: [],
  notes: [
    'Open the generated test-vault in Obsidian for a self-contained fresh-vault bootstrap path.',
    'Use the generated autodebug job for scaffold smoke runs; keep the generic template flow for existing plugin repositories.',
    'Use autodebug/ci/ for headless quality gates; desktop reload/bootstrap capture remains local-only.',
  ],
};

const packageJson = {
  name: pluginId,
  version: '0.0.1',
  description,
  main: 'dist/main.js',
  packageManager: packageManagerField,
  scripts: {
    build: 'node scripts/build.mjs',
    dev: 'node scripts/build.mjs --watch',
    test: 'node scripts/build.mjs --check',
  },
  author,
  license: 'MIT',
};

const manifest = {
  id: pluginId,
  name: pluginName,
  version: '0.0.1',
  minAppVersion,
  description,
  author,
  isDesktopOnly: false,
  ...(authorUrl ? { authorUrl } : {}),
};

const versions = {
  [minAppVersion]: '0.0.1',
};

const stylesCss = `.${rootClass},\n.${settingsRootClass} {\n  display: block;\n  padding: 16px;\n}\n\n.${rootClass} {\n  border: 1px solid var(--background-modifier-border);\n  border-radius: 12px;\n  background: var(--background-secondary);\n}\n`;

const mainJs = buildPluginSource({
  classBase,
  openSettingsCommandId,
  openViewCommandId,
  pluginId,
  pluginName,
  readyText,
  rootClass,
  settingsRootClass,
  settingsText,
  viewHeader,
  viewType,
});

const buildScript = buildWorkspaceBuildScript();
const readme = buildWorkspaceReadme({
  jobPath: `autodebug/${pluginId}-debug-job.json`,
  pluginId,
  pluginName,
  testVaultRoot: path.relative(workspaceDir, testVaultRoot) || '.',
});
const gitignore = ['.obsidian-debug/', 'node_modules/', 'test-vault/.obsidian/workspace*', 'test-vault/.trash/'].join('\n');

const scenarioTemplate = await readJsonTemplate(path.join(skillRoot, 'scenarios', 'open-plugin-view.json'));
const surfaceTemplate = await readJsonTemplate(path.join(skillRoot, 'surface-profiles', 'plugin-surface.template.json'));
const assertionTemplate = await readJsonTemplate(path.join(skillRoot, 'assertions', 'plugin-view-health.template.json'));
const jobTemplate = await readJsonTemplate(path.join(skillRoot, 'job-specs', 'generic-debug-job.template.json'));
const jobSchemaText = await fs.readFile(path.join(skillRoot, 'job-specs', 'obsidian-debug-job.schema.json'), 'utf8');

const surfaceProfile = {
  ...surfaceTemplate,
  plugin: {
    id: pluginId,
    name: pluginName,
  },
  metadata: {
    ...(surfaceTemplate.metadata ?? {}),
    preferredOpenCommandIds: [openViewCommandId],
    viewTypes: [viewType],
    settingsTabNames: [pluginName],
    selectorHints: [`.${rootClass}`, `.${settingsRootClass}`],
  },
  commands: [
    {
      id: openViewCommandId,
      label: `Open ${pluginName} view`,
      surface: 'view',
    },
    {
      id: openSettingsCommandId,
      label: `Open ${pluginName} settings`,
      surface: 'settings',
    },
  ],
  dom: {
    elements: [
      {
        tag: 'section',
        classes: ['workspace-leaf', 'mod-active', rootClass],
        text: readyText,
        attributes: {
          'data-type': viewType,
          'data-ready-state': 'ready',
        },
      },
      {
        tag: 'h2',
        classes: ['view-header-title'],
        text: viewHeader,
      },
      {
        tag: 'div',
        classes: ['vertical-tab-nav-item', 'is-active'],
        text: pluginName,
        attributes: {
          'data-tab': pluginId,
        },
      },
    ],
  },
};

const assertions = {
  ...assertionTemplate,
  name: `${pluginId}-view-health`,
  description: `Scaffold-ready assertion set for ${pluginName} generated by obsidian-plugin-autodebug.`,
  assertions: (assertionTemplate.assertions ?? []).map((assertion) => customizeAssertion(assertion, {
    pluginId,
    pluginName,
    readyText,
    rootSelector: `.${rootClass}`,
  })),
};

const jobSpec = {
  ...jobTemplate,
  $schema: './obsidian-debug-job.schema.json',
  job: {
    ...(jobTemplate.job ?? {}),
    id: `${pluginId}-sample-health`,
    label: `${pluginName} scaffold health cycle`,
    description: `Build, deploy, bootstrap, reload, and validate the scaffolded ${pluginName} sample workspace.`,
  },
  runtime: {
    ...(jobTemplate.runtime ?? {}),
    cwd: workspaceDir,
    pluginId,
    testVaultPluginDir,
    vaultName,
    obsidianCommand,
    outputDir: '.obsidian-debug/{{jobId}}-{{platform}}',
  },
  build: {
    ...(jobTemplate.build ?? {}),
    enabled: true,
    command: ['node', 'scripts/build.mjs'],
  },
  deploy: {
    ...(jobTemplate.deploy ?? {}),
    enabled: true,
    from: 'dist',
  },
  bootstrap: {
    ...(jobTemplate.bootstrap ?? {}),
    enabled: true,
    allowRestart: true,
  },
  scenario: {
    ...(jobTemplate.scenario ?? {}),
    enabled: true,
    name: 'open-plugin-view',
    path: 'autodebug/scenarios/open-plugin-view.json',
    commandId: openViewCommandId,
    surfaceProfile: `autodebug/surface-profiles/${pluginId}-surface.json`,
    sleepMs: 500,
  },
  assertions: {
    ...(jobTemplate.assertions ?? {}),
    path: 'autodebug/assertions/plugin-view-health.json',
    domSelector: `.${rootClass}`,
    domText: true,
  },
  report: {
    ...(jobTemplate.report ?? {}),
    enabled: true,
    diagnosis: '',
    profile: '',
    comparison: '',
    output: '.obsidian-debug/report.html',
  },
  state: {
    ...(jobTemplate.state ?? {}),
    restoreAfterRun: false,
    vaultSnapshot: {
      ...(jobTemplate.state?.vaultSnapshot ?? {}),
      enabled: false,
      snapshotDir: '.obsidian-debug/vault-state',
      allowMissing: true,
      targets: [path.join(testVaultPluginDir, 'data.json')],
    },
    pluginReset: {
      ...(jobTemplate.state?.pluginReset ?? {}),
      enabled: false,
      mode: 'preview',
      statePlan: 'state-plans/plugin-data-reset.json',
      vaultRoot: testVaultRoot,
      snapshotDir: '.obsidian-debug/plugin-state-reset',
      targets: [path.join(testVaultPluginDir, 'data.json')],
      recreateFiles: [],
      recreateDirs: [],
    },
  },
};

await writeTextFile('package.json', `${JSON.stringify(packageJson, null, 2)}\n`);
await writeTextFile('manifest.json', `${JSON.stringify(manifest, null, 2)}\n`);
await writeTextFile('versions.json', `${JSON.stringify(versions, null, 2)}\n`);
await writeTextFile('styles.css', `${stylesCss}\n`);
await writeTextFile('src/main.js', mainJs);
await writeTextFile('scripts/build.mjs', buildScript);
await writeTextFile('README.md', readme);
await writeTextFile('.gitignore', `${gitignore}\n`);
await writeTextFile('autodebug/README.md', buildAutodebugReadme({ pluginId, pluginName }));
await writeTextFile('autodebug/scenarios/open-plugin-view.json', `${JSON.stringify(scenarioTemplate, null, 2)}\n`);
await writeTextFile(
  `autodebug/surface-profiles/${pluginId}-surface.json`,
  `${JSON.stringify(surfaceProfile, null, 2)}\n`,
);
await writeTextFile('autodebug/assertions/plugin-view-health.json', `${JSON.stringify(assertions, null, 2)}\n`);
await writeTextFile('autodebug/obsidian-debug-job.schema.json', ensureTrailingNewline(jobSchemaText));
await writeTextFile(`autodebug/${pluginId}-debug-job.json`, `${JSON.stringify(jobSpec, null, 2)}\n`);
await writeTextFile('test-vault/Welcome.md', `# ${pluginName} Test Vault\n\nOpen this folder as a fresh Obsidian vault to exercise bootstrap mode against the scaffolded plugin.\n`);

const ciTemplateReport = await generateQualityGateTemplates({
  repoDir: workspaceDir,
  jobPath: path.join('autodebug', `${pluginId}-debug-job.json`),
  outputDir: path.join('autodebug', 'ci'),
  toolRootRef: '.agents/skills/obsidian-plugin-autodebug',
});
for (const filePath of ciTemplateReport.files) {
  if (!report.files.includes(filePath)) {
    report.files.push(filePath);
  }
}
report.ciTemplates = {
  outputDir: path.relative(workspaceDir, ciTemplateReport.outputDir),
  files: ciTemplateReport.files,
  ciSuitable: ciTemplateReport.ciSuitable,
  localOnly: ciTemplateReport.localOnly,
};

const distFiles = await buildDistArtifacts({
  workspaceDir,
  manifestText: `${JSON.stringify(manifest, null, 2)}\n`,
  mainJs,
  stylesCss: `${stylesCss}\n`,
});
await deployDistToVault({ distFiles, testVaultPluginDir });

report.status = 'pass';
report.distFiles = distFiles.map((filePath) => path.relative(workspaceDir, filePath));
report.sampleCommands = {
  bashDryRun: `node /path/to/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job ${path.join('autodebug', `${pluginId}-debug-job.json`)} --platform bash --dry-run`,
  windowsDryRun: `node C:\\path\\to\\obsidian-plugin-autodebug\\scripts\\obsidian_debug_job.mjs --job autodebug\\${pluginId}-debug-job.json --platform windows --dry-run`,
  ciQualityGateBash: `AUTODEBUG_TOOL_ROOT=/path/to/obsidian-plugin-autodebug bash autodebug/ci/quality-gate.sh`,
  ciQualityGateWindows: `$env:AUTODEBUG_TOOL_ROOT='C:\\path\\to\\obsidian-plugin-autodebug'; powershell -NoProfile -ExecutionPolicy Bypass -File autodebug\\ci\\quality-gate.ps1`,
};

if (outputPath) {
  const resolvedOutput = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutput);
  await fs.writeFile(resolvedOutput, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(report, null, 2));

async function writeTextFile(relativePath, content) {
  const targetPath = path.join(workspaceDir, relativePath);
  await ensureParentDirectory(targetPath);
  await fs.writeFile(targetPath, content, 'utf8');
  report.files.push(relativePath);
}

async function readJsonTemplate(filePath) {
  return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
}

function ensureTrailingNewline(text) {
  return text.endsWith('\n') ? text : `${text}\n`;
}

async function ensureWritableWorkspace(targetDir, { overwrite }) {
  const exists = await pathExists(targetDir);
  if (!exists) {
    await fs.mkdir(targetDir, { recursive: true });
    return;
  }

  const entries = await fs.readdir(targetDir);
  if (entries.length > 0 && !overwrite) {
    throw new Error(`Refusing to scaffold into non-empty directory: ${targetDir}. Pass --overwrite true to reuse it.`);
  }

  await fs.mkdir(targetDir, { recursive: true });
}

async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function sanitizePluginId(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '');
}

function normalizePackageManager(value) {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (!SUPPORTED_PACKAGE_MANAGERS.has(normalized)) {
    throw new Error(`--package-manager must be one of: ${[...SUPPORTED_PACKAGE_MANAGERS].join(', ')}`);
  }
  return normalized;
}

function normalizeCommandReference(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return 'obsidian';
  }
  if (normalized.startsWith('.') || normalized.startsWith('/') || normalized.includes('/') || normalized.includes('\\')) {
    return path.resolve(normalized);
  }
  return normalized;
}

function toTitleCase(value) {
  return String(value ?? '')
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Sample Plugin';
}

function toPascalCase(value) {
  const base = String(value ?? '')
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('') || 'SamplePlugin';
  return /^[A-Za-z_$]/.test(base) ? base : `Sample${base}`;
}

function escapeRegex(value) {
  return String(value ?? '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function customizeAssertion(assertion, { pluginId, pluginName, readyText, rootSelector }) {
  const clone = JSON.parse(JSON.stringify(assertion));
  const textPattern = `${escapeRegex(pluginName)}|${escapeRegex(readyText)}`;

  function replaceValue(value) {
    if (typeof value !== 'string') {
      return value;
    }
    return value
      .replaceAll('<plugin-root-selector>', rootSelector)
      .replaceAll('<plugin-empty-state-selector>', rootSelector)
      .replaceAll('<expected-heading-or-status-regex>', textPattern)
      .replaceAll('<known-empty-state-regex>', `${escapeRegex(readyText)}|loading`)
      .replaceAll('<known-fatal-error-substring>', `[${pluginId}] fatal`);
  }

  return deepReplace(clone, replaceValue);
}

function deepReplace(value, replacer) {
  if (Array.isArray(value)) {
    return value.map((entry) => deepReplace(entry, replacer));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, deepReplace(entry, replacer)]));
  }
  return replacer(value);
}

function buildPluginSource({
  classBase,
  openSettingsCommandId,
  openViewCommandId,
  pluginId,
  pluginName,
  readyText,
  rootClass,
  settingsRootClass,
  settingsText,
  viewHeader,
  viewType,
}) {
  return `const obsidian = require('obsidian');

const VIEW_TYPE = '${viewType}';
const ROOT_CLASS = '${rootClass}';
const SETTINGS_ROOT_CLASS = '${settingsRootClass}';

class ${classBase}View extends obsidian.ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType() {
    return VIEW_TYPE;
  }

  getDisplayText() {
    return '${pluginName}';
  }

  getIcon() {
    return 'bug';
  }

  async onOpen() {
    const { contentEl } = this;
    contentEl.empty();

    const root = contentEl.createDiv({ cls: ROOT_CLASS });
    root.setAttr('data-ready-state', 'ready');
    root.createEl('h2', { text: '${viewHeader}' });
    root.createEl('p', { text: '${readyText}' });
  }

  async onClose() {
    this.contentEl.empty();
  }
}

class ${classBase}SettingTab extends obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();

    const root = containerEl.createDiv({ cls: SETTINGS_ROOT_CLASS });
    root.setAttr('data-ready-state', 'ready');
    root.createEl('h2', { text: '${pluginName} Settings' });
    root.createEl('p', { text: '${settingsText}' });
    new obsidian.Setting(containerEl)
      .setName('Status')
      .setDesc('${settingsText}');
  }
}

class ${classBase}Plugin extends obsidian.Plugin {
  async onload() {
    console.log('[${pluginId}] onload');

    this.registerView(VIEW_TYPE, (leaf) => new ${classBase}View(leaf, this));
    this.addRibbonIcon('bug', 'Open ${pluginName} view', () => {
      void this.activateView();
    });
    this.addCommand({
      id: '${openViewCommandId.split(':')[1]}',
      name: 'Open ${pluginName} view',
      callback: () => this.activateView(),
    });
    this.addCommand({
      id: '${openSettingsCommandId.split(':')[1]}',
      name: 'Open ${pluginName} settings',
      callback: () => {
        this.app.setting.open();
        this.app.setting.openTabById(this.manifest.id);
      },
    });
    this.addSettingTab(new ${classBase}SettingTab(this.app, this));
  }

  onunload() {
    console.log('[${pluginId}] onunload');
    this.app.workspace.detachLeavesOfType(VIEW_TYPE);
  }

  async activateView() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];

    if (!leaf) {
      leaf = this.app.workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }

    this.app.workspace.revealLeaf(leaf);
  }
}

module.exports = {
  default: ${classBase}Plugin,
};
`;
}

function buildWorkspaceBuildScript() {
  return `import fs from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, '..');
const watchMode = process.argv.includes('--watch');
const checkMode = process.argv.includes('--check');

const files = [
  ['src/main.js', 'dist/main.js'],
  ['manifest.json', 'dist/manifest.json'],
  ['styles.css', 'dist/styles.css'],
];

async function readFile(filePath) {
  return fsp.readFile(filePath, 'utf8');
}

async function ensureDir(filePath) {
  await fsp.mkdir(path.dirname(filePath), { recursive: true });
}

async function buildOnce() {
  const written = [];
  for (const [sourceRelative, targetRelative] of files) {
    const sourcePath = path.join(rootDir, sourceRelative);
    const targetPath = path.join(rootDir, targetRelative);
    const content = await readFile(sourcePath);
    await ensureDir(targetPath);
    await fsp.writeFile(targetPath, content, 'utf8');
    written.push(targetRelative);
  }
  return written;
}

async function checkOnce() {
  const mismatches = [];
  for (const [sourceRelative, targetRelative] of files) {
    const sourcePath = path.join(rootDir, sourceRelative);
    const targetPath = path.join(rootDir, targetRelative);
    const sourceContent = await readFile(sourcePath);
    let targetContent = '';
    try {
      targetContent = await readFile(targetPath);
    } catch {
      mismatches.push(\`\${targetRelative} is missing\`);
      continue;
    }
    if (sourceContent !== targetContent) {
      mismatches.push(\`\${targetRelative} is stale\`);
    }
  }

  if (mismatches.length > 0) {
    throw new Error(mismatches.join('; '));
  }
}

function watchAndRebuild() {
  let timer = null;
  const queueBuild = () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const written = await buildOnce();
        console.log(JSON.stringify({ status: 'pass', mode: 'watch', written }, null, 2));
      } catch (error) {
        console.error(error.message);
      }
    }, 100);
  };

  for (const [sourceRelative] of files) {
    fs.watch(path.join(rootDir, sourceRelative), queueBuild);
  }

  process.on('SIGINT', () => process.exit(0));
  process.on('SIGTERM', () => process.exit(0));
}

if (checkMode) {
  await checkOnce();
  console.log(JSON.stringify({ status: 'pass', mode: 'check' }, null, 2));
} else {
  const written = await buildOnce();
  console.log(JSON.stringify({ status: 'pass', mode: watchMode ? 'watch' : 'build', written }, null, 2));
  if (watchMode) {
    watchAndRebuild();
    await new Promise(() => {});
  }
}
`;
}

function buildWorkspaceReadme({ jobPath, pluginId, pluginName, testVaultRoot }) {
  return `# ${pluginName}

This workspace was scaffolded by \`obsidian-plugin-autodebug\`.

## What it includes

- A minimal Obsidian community plugin with a sample view and settings tab
- A zero-dependency local build script at \`scripts/build.mjs\`
- A local fresh-vault target at \`${testVaultRoot}\`
- Bootstrap-ready autodebug configs under \`autodebug/\`
- Headless quality-gate templates under \`autodebug/ci/\`

## Scaffold flow

1. Open \`${testVaultRoot}\` as an Obsidian vault once.
2. Run \`npm run build\` (or the matching package-manager command if you change it).
3. Use the generated autodebug job at \`${jobPath}\`.
4. Run \`AUTODEBUG_TOOL_ROOT=/path/to/obsidian-plugin-autodebug bash autodebug/ci/quality-gate.sh\` for a headless build/test/dry-run gate.

## Existing-plugin retrofit flow

If you already have a plugin repository, keep using the generic job template from \`custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json\` instead of re-scaffolding the repo.

## Plugin id

\`${pluginId}\`
`;
}

function buildAutodebugReadme({ pluginId, pluginName }) {
  return `# ${pluginName} Autodebug Config

- Job: \`${pluginId}-debug-job.json\`
- Scenario: \`scenarios/open-plugin-view.json\`
- Surface profile: \`surface-profiles/${pluginId}-surface.json\`
- Assertions: \`assertions/plugin-view-health.json\`
- CI templates: \`ci/quality-gate.sh\`, \`ci/quality-gate.ps1\`, and \`ci/github-actions-quality-gate.yml\`

This directory is generated for scaffold smoke runs. Existing plugin repositories can instead copy and tailor the shared templates from the skill source tree.
The CI templates are headless by default; run the desktop bootstrap/reload/screenshot/CDP phases locally after the headless gate passes.
`;
}

async function buildDistArtifacts({ workspaceDir, manifestText, mainJs, stylesCss }) {
  const files = [
    ['dist/main.js', mainJs],
    ['dist/manifest.json', manifestText],
    ['dist/styles.css', stylesCss],
  ];

  const written = [];
  for (const [relativePath, content] of files) {
    const targetPath = path.join(workspaceDir, relativePath);
    await ensureParentDirectory(targetPath);
    await fs.writeFile(targetPath, content, 'utf8');
    written.push(targetPath);
    report.files.push(relativePath);
  }
  return written;
}

async function deployDistToVault({ distFiles, testVaultPluginDir }) {
  await fs.mkdir(testVaultPluginDir, { recursive: true });
  for (const distFile of distFiles) {
    const targetPath = path.join(testVaultPluginDir, path.basename(distFile));
    await fs.copyFile(distFile, targetPath);
  }
}
