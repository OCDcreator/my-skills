import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';
import {
  buildDebugComparison,
  resolveArtifactPaths,
  signatureId,
} from './obsidian_debug_compare_core.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_baseline.mjs --mode <save|compare|list|prune> [options]

Modes:
  save      --name <name> --diagnosis <path> [--profile <path>] [--report <path>]
  compare   --candidate-diagnosis <path> (--name <name> | --tags "pluginId=...|platform=...")
  list      [--name <name>] [--tags "pluginId=...|platform=..."]
  prune     [--tags "..."] [--max-age-days <n>] [--keep-recent <n>] [--delete true]

Common options:
  --baseline-root <dir>     Baseline storage root.
  --output <path>           JSON output for compare/list/prune.
  --tags <k=v|k=v>          Taxonomy filters.
`);
}

const mode = getStringOption(options, 'mode', '').trim().toLowerCase();
if (!['save', 'compare', 'list', 'prune'].includes(mode)) {
  throw new Error('--mode must be save, compare, list, or prune');
}

const baselineRoot = path.resolve(getStringOption(options, 'baseline-root', '.obsidian-debug/baselines'));
const name = getStringOption(options, 'name', '').trim();
const diagnosisPath = getStringOption(options, 'diagnosis', '').trim();
const profilePath = getStringOption(options, 'profile', '').trim();
const reportPath = getStringOption(options, 'report', '').trim();
const comparisonPath = getStringOption(options, 'comparison', '').trim();
const candidateDiagnosisPath = getStringOption(options, 'candidate-diagnosis', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();

const taxonomyFields = [
  {
    key: 'pluginId',
    optionAliases: ['plugin-id', 'pluginId'],
    tagAliases: ['plugin-id', 'plugin_id', 'pluginid', 'pluginId'],
    weight: 10,
  },
  {
    key: 'platform',
    optionAliases: ['platform'],
    tagAliases: ['platform', 'os'],
    weight: 8,
  },
  {
    key: 'vaultState',
    optionAliases: ['vault-state', 'vaultState'],
    tagAliases: ['vault-state', 'vault_state', 'vaultstate', 'vaultState'],
    weight: 7,
  },
  {
    key: 'mode',
    optionAliases: ['run-mode', 'startup-mode', 'cold-warm-mode'],
    tagAliases: ['mode', 'run-mode', 'startup-mode', 'cold-warm-mode', 'cold_warm_mode'],
    weight: 6,
  },
  {
    key: 'scenario',
    optionAliases: ['scenario', 'scenario-name', 'scenarioName'],
    tagAliases: ['scenario', 'scenario-name', 'scenario_name', 'scenarioName'],
    weight: 5,
  },
  {
    key: 'runLabel',
    optionAliases: ['run-label', 'runLabel', 'label'],
    tagAliases: ['run-label', 'run_label', 'runlabel', 'runLabel', 'label'],
    weight: 4,
  },
];

const taxonomyKeyAliases = new Map(
  taxonomyFields.flatMap((field) => field.tagAliases.map((alias) => [normalizeKey(alias), field.key])),
);

function normalizeKey(key) {
  return String(key ?? '')
    .trim()
    .replace(/^--/, '')
    .replaceAll('_', '-')
    .replaceAll(' ', '-')
    .toLowerCase();
}

function platformTag() {
  switch (process.platform) {
    case 'win32':
      return 'windows';
    case 'darwin':
      return 'macos';
    case 'linux':
      return 'linux';
    default:
      return process.platform;
  }
}

function setTaxonomyValue(target, key, value) {
  if (!key || value === undefined || value === null) {
    return;
  }
  const normalized = String(value).trim();
  if (normalized) {
    target[key] = normalized;
  }
}

function normalizeTaxonomy(input) {
  const taxonomy = {};
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    return taxonomy;
  }

  for (const [key, value] of Object.entries(input)) {
    const canonicalKey = taxonomyKeyAliases.get(normalizeKey(key));
    setTaxonomyValue(taxonomy, canonicalKey, value);
  }
  return taxonomy;
}

function parseTagString(raw) {
  const trimmed = String(raw ?? '').trim();
  if (!trimmed) {
    return {};
  }

  if (trimmed.startsWith('{')) {
    try {
      return normalizeTaxonomy(JSON.parse(trimmed));
    } catch {
      return {};
    }
  }

  const parsed = {};
  for (const token of trimmed.split(/[|,;]+/)) {
    const match = token.trim().match(/^([^:=]+)\s*[:=]\s*(.+)$/);
    if (!match) {
      continue;
    }
    const canonicalKey = taxonomyKeyAliases.get(normalizeKey(match[1]));
    setTaxonomyValue(parsed, canonicalKey, match[2]);
  }
  return parsed;
}

function readExplicitTaxonomy() {
  const taxonomy = {
    ...parseTagString(getStringOption(options, 'tags', '')),
    ...parseTagString(getStringOption(options, 'tag', '')),
  };

  for (const field of taxonomyFields) {
    for (const alias of field.optionAliases) {
      setTaxonomyValue(taxonomy, field.key, getStringOption(options, alias, ''));
    }
  }

  return normalizeTaxonomy(taxonomy);
}

function mergeTaxonomies(...sources) {
  return sources.reduce((merged, source) => ({
    ...merged,
    ...normalizeTaxonomy(source),
  }), {});
}

function taxonomyFromDiagnosis(diagnosis) {
  return normalizeTaxonomy({
    pluginId: diagnosis?.pluginId,
    vaultState: diagnosis?.vaultState,
    mode: diagnosis?.runMode ?? diagnosis?.mode,
    scenario:
      diagnosis?.scenario?.name
      ?? diagnosis?.scenarioName
      ?? diagnosis?.scenarioReport?.scenarioName,
    runLabel: diagnosis?.runLabel ?? diagnosis?.label,
    platform: diagnosis?.platform,
  });
}

function taxonomyFromProfile(profile) {
  return normalizeTaxonomy({
    pluginId: profile?.pluginId,
    platform: profile?.platform,
    vaultState: profile?.vaultState,
    mode: profile?.mode,
    scenario: profile?.scenario,
    runLabel: profile?.label ?? profile?.runLabel,
  });
}

function buildTaxonomy({ diagnosis = null, profile = null, explicit = {}, includePlatformDefault = false } = {}) {
  return mergeTaxonomies(
    includePlatformDefault ? { platform: platformTag() } : {},
    taxonomyFromDiagnosis(diagnosis),
    taxonomyFromProfile(profile),
    explicit,
  );
}

function tagsMatch(actual, expected) {
  return String(actual ?? '').trim().toLowerCase() === String(expected ?? '').trim().toLowerCase();
}

async function readJson(filePath) {
  return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
}

async function exists(filePath) {
  if (!filePath) {
    return false;
  }
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath) {
  if (!filePath || !(await exists(filePath))) {
    return null;
  }
  return readJson(filePath);
}

async function copyIfExists(sourcePath, destinationPath) {
  if (!sourcePath || !(await exists(sourcePath))) {
    return null;
  }
  await ensureParentDirectory(destinationPath);
  await fs.copyFile(sourcePath, destinationPath);
  return destinationPath;
}

function baselineGeneratedMs(metadata, fallbackStat) {
  const generated = Date.parse(metadata?.generatedAt ?? '');
  if (Number.isFinite(generated)) {
    return generated;
  }
  return fallbackStat?.mtimeMs ?? 0;
}

function normalizeBaselineMetadata(metadata, fallbackName, baselineDir) {
  const legacyTaxonomy = normalizeTaxonomy({
    pluginId: metadata?.diagnosis?.pluginId,
    platform: metadata?.platform,
    vaultState: metadata?.vaultState,
    mode: metadata?.profile?.mode,
    scenario: metadata?.scenario?.name ?? metadata?.scenario,
    runLabel: metadata?.profile?.label ?? metadata?.runLabel,
  });
  const taxonomy = mergeTaxonomies(
    legacyTaxonomy,
    metadata?.classification,
    metadata?.taxonomy,
    metadata?.tags,
  );

  return {
    ...metadata,
    name: metadata?.name ?? fallbackName,
    baselineDir: metadata?.baselineDir ?? baselineDir,
    taxonomy,
    tags: taxonomy,
  };
}

async function readBaselineEntries() {
  await fs.mkdir(baselineRoot, { recursive: true });
  const entries = await fs.readdir(baselineRoot, { withFileTypes: true });
  const baselines = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const baselineDir = path.join(baselineRoot, entry.name);
    const metadataPath = path.join(baselineDir, 'baseline.json');
    if (!(await exists(metadataPath))) {
      continue;
    }

    const stat = await fs.stat(baselineDir);
    const metadata = normalizeBaselineMetadata(await readJson(metadataPath), entry.name, baselineDir);
    baselines.push({
      name: metadata.name,
      dir: baselineDir,
      metadataPath,
      diagnosisPath: path.join(baselineDir, 'diagnosis.json'),
      metadata,
      generatedMs: baselineGeneratedMs(metadata, stat),
    });
  }

  return baselines.sort((left, right) => right.generatedMs - left.generatedMs);
}

async function baselineEntryByName(baselineName) {
  const baselineDir = path.join(baselineRoot, baselineName);
  const baselineDiagnosisPath = path.join(baselineDir, 'diagnosis.json');
  if (!(await exists(baselineDiagnosisPath))) {
    throw new Error(`Baseline diagnosis does not exist: ${baselineDiagnosisPath}`);
  }

  const metadataPath = path.join(baselineDir, 'baseline.json');
  const metadata = (await exists(metadataPath))
    ? normalizeBaselineMetadata(await readJson(metadataPath), baselineName, baselineDir)
    : null;
  const stat = (await exists(baselineDir)) ? await fs.stat(baselineDir) : null;

  return {
    name: metadata?.name ?? baselineName,
    dir: baselineDir,
    metadataPath,
    diagnosisPath: baselineDiagnosisPath,
    metadata,
    generatedMs: baselineGeneratedMs(metadata, stat),
  };
}

function baselineMatchesFilters(entry, filters) {
  return Object.entries(filters).every(
    ([key, expected]) => tagsMatch(entry.metadata?.taxonomy?.[key], expected),
  );
}

function scoreBaseline(entry, desiredTaxonomy) {
  const matched = [];
  const mismatched = [];
  const missing = [];
  let score = 0;
  let possibleScore = 0;

  for (const field of taxonomyFields) {
    const desiredValue = desiredTaxonomy[field.key];
    if (!desiredValue) {
      continue;
    }

    possibleScore += field.weight;
    const baselineValue = entry.metadata?.taxonomy?.[field.key];
    if (tagsMatch(baselineValue, desiredValue)) {
      matched.push({ key: field.key, value: baselineValue });
      score += field.weight;
    } else if (baselineValue) {
      mismatched.push({ key: field.key, baseline: baselineValue, candidate: desiredValue });
    } else {
      missing.push({ key: field.key, candidate: desiredValue });
    }
  }

  return {
    score,
    possibleScore,
    matched,
    mismatched,
    missing,
  };
}

function taxonomyClassKey(taxonomy) {
  return taxonomyFields
    .map((field) => `${field.key}=${taxonomy?.[field.key] ?? 'unspecified'}`)
    .join('|');
}

function ageDays(entry, nowMs) {
  if (!entry.generatedMs) {
    return null;
  }
  return Math.max(0, (nowMs - entry.generatedMs) / 86_400_000);
}

function summarizeEntry(entry, extra = {}) {
  return {
    name: entry.name,
    generatedAt: entry.metadata?.generatedAt ?? null,
    taxonomy: entry.metadata?.taxonomy ?? {},
    baselineDir: entry.dir,
    ...extra,
  };
}

function assertInsideBaselineRoot(targetDir) {
  const relative = path.relative(baselineRoot, targetDir);
  if (!relative || relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error(`Refusing to prune outside baseline root: ${targetDir}`);
  }
}

function cloneJson(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function relativeArtifactPath(baseDir, targetPath) {
  return path.relative(baseDir, targetPath).replaceAll('\\', '/');
}

function copiedArtifactDestination(baselineDir, key, sourcePath) {
  const extension = path.extname(sourcePath);
  return path.join(baselineDir, 'artifacts', `${key}${extension}`);
}

async function copyDiagnosisArtifacts(diagnosis, sourceDiagnosisPath, baselineDir) {
  const resolvedArtifacts = resolveArtifactPaths(diagnosis, sourceDiagnosisPath);
  const copiedArtifacts = {};

  for (const [key, sourcePath] of Object.entries(resolvedArtifacts)) {
    if (!sourcePath || !(await exists(sourcePath))) {
      continue;
    }
    const destinationPath = copiedArtifactDestination(baselineDir, key, sourcePath);
    await copyIfExists(sourcePath, destinationPath);
    copiedArtifacts[key] = relativeArtifactPath(baselineDir, destinationPath);
  }

  return copiedArtifacts;
}

const explicitTaxonomy = readExplicitTaxonomy();

if (mode === 'list') {
  const baselines = (await readBaselineEntries())
    .filter((entry) => baselineMatchesFilters(entry, explicitTaxonomy))
    .map((entry) => entry.metadata);

  console.log(JSON.stringify({
    generatedAt: nowIso(),
    baselineRoot,
    filters: explicitTaxonomy,
    count: baselines.length,
    baselines,
  }, null, 2));
} else if (mode === 'save') {
  if (!name || !diagnosisPath) {
    throw new Error('--name and --diagnosis are required for save mode');
  }

  const resolvedDiagnosisPath = path.resolve(diagnosisPath);
  const diagnosis = await readJson(resolvedDiagnosisPath);
  const profile = await readJsonIfExists(profilePath ? path.resolve(profilePath) : '');
  const taxonomy = buildTaxonomy({
    diagnosis,
    profile,
    explicit: explicitTaxonomy,
    includePlatformDefault: true,
  });
  const baselineDir = path.join(baselineRoot, name);
  await fs.rm(baselineDir, { recursive: true, force: true });
  await fs.mkdir(baselineDir, { recursive: true });

  const savedDiagnosisPath = path.join(baselineDir, 'diagnosis.json');
  const copiedDiagnosisArtifacts = await copyDiagnosisArtifacts(diagnosis, resolvedDiagnosisPath, baselineDir);
  const savedDiagnosis = {
    ...cloneJson(diagnosis),
    artifacts: {
      ...(cloneJson(diagnosis.artifacts) ?? {}),
      ...copiedDiagnosisArtifacts,
    },
  };
  await fs.writeFile(savedDiagnosisPath, `${JSON.stringify(savedDiagnosis, null, 2)}\n`, 'utf8');
  const savedProfilePath = await copyIfExists(profilePath ? path.resolve(profilePath) : '', path.join(baselineDir, 'profile-summary.json'));
  const savedReportPath = await copyIfExists(reportPath ? path.resolve(reportPath) : '', path.join(baselineDir, 'report.html'));
  const savedComparisonPath = await copyIfExists(comparisonPath ? path.resolve(comparisonPath) : '', path.join(baselineDir, 'comparison.json'));

  const metadata = {
    generatedAt: nowIso(),
    mode,
    name,
    baselineRoot,
    baselineDir,
    taxonomy,
    tags: taxonomy,
    diagnosis: {
      path: savedDiagnosisPath,
      status: diagnosis.status ?? null,
      headline: diagnosis.headline ?? null,
      pluginId: diagnosis.pluginId ?? null,
      vaultName: diagnosis.vaultName ?? null,
      scenario: diagnosis.scenario?.name ?? null,
      timings: diagnosis.timings ?? {},
      signatures: (diagnosis.signatures ?? []).map(signatureId).filter(Boolean),
    },
    profile: profile
      ? {
          path: savedProfilePath,
          label: profile.label ?? null,
          mode: profile.mode ?? null,
          runs: profile.runs ?? null,
        }
      : null,
    profilePath: savedProfilePath,
    reportPath: savedReportPath,
    comparisonPath: savedComparisonPath,
    artifacts: {
      diagnosis: savedDiagnosisPath ? path.relative(baselineDir, savedDiagnosisPath) : null,
      profile: savedProfilePath ? path.relative(baselineDir, savedProfilePath) : null,
      report: savedReportPath ? path.relative(baselineDir, savedReportPath) : null,
      comparison: savedComparisonPath ? path.relative(baselineDir, savedComparisonPath) : null,
      captured: copiedDiagnosisArtifacts,
    },
    sourcePaths: {
      diagnosis: resolvedDiagnosisPath,
      profile: profilePath ? path.resolve(profilePath) : null,
      report: reportPath ? path.resolve(reportPath) : null,
      comparison: comparisonPath ? path.resolve(comparisonPath) : null,
    },
  };

  await fs.writeFile(path.join(baselineDir, 'baseline.json'), `${JSON.stringify(metadata, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(metadata, null, 2));
} else if (mode === 'compare') {
  if (!candidateDiagnosisPath) {
    throw new Error('--candidate-diagnosis is required for compare mode');
  }
  if (!name && Object.keys(explicitTaxonomy).length === 0) {
    throw new Error('--name or tag filters such as --tags "pluginId=...|platform=..." are required for compare mode');
  }

  const candidateDiagnosis = await readJson(path.resolve(candidateDiagnosisPath));
  const candidateProfile = await readJsonIfExists(profilePath ? path.resolve(profilePath) : '');
  const desiredTaxonomy = buildTaxonomy({
    diagnosis: candidateDiagnosis,
    profile: candidateProfile,
    explicit: explicitTaxonomy,
    includePlatformDefault: true,
  });

  const selection = name
    ? {
        mode: 'name',
        filters: explicitTaxonomy,
        desiredTaxonomy,
        selected: await baselineEntryByName(name),
      }
    : await (async () => {
        const candidates = (await readBaselineEntries())
          .filter((entry) => baselineMatchesFilters(entry, explicitTaxonomy));
        if (candidates.length === 0) {
          throw new Error(`No baselines match filters: ${JSON.stringify(explicitTaxonomy)}`);
        }

        const scored = candidates
          .map((entry) => ({
            entry,
            score: scoreBaseline(entry, desiredTaxonomy),
          }))
          .sort((left, right) => (
            right.score.score - left.score.score
            || right.score.matched.length - left.score.matched.length
            || right.entry.generatedMs - left.entry.generatedMs
          ));

        return {
          mode: 'tags',
          filters: explicitTaxonomy,
          desiredTaxonomy,
          selected: scored[0].entry,
          score: scored[0].score,
          candidateCount: candidates.length,
        };
      })();

  const selected = selection.selected;
  const baseline = await readJson(selected.diagnosisPath);
  const resolvedOutputPath = path.resolve(
    outputPath || path.join(path.dirname(path.resolve(candidateDiagnosisPath)), 'baseline-comparison.json'),
  );
  const comparison = {
    ...(await buildDebugComparison({
      baselinePath: selected.diagnosisPath,
      baseline,
      candidatePath: path.resolve(candidateDiagnosisPath),
      candidate: candidateDiagnosis,
      outputPath: resolvedOutputPath,
      context: {
      baselineName: selected.name,
      baselineTaxonomy: selected.metadata?.taxonomy ?? {},
      candidateTaxonomy: desiredTaxonomy,
      selection: {
        mode: selection.mode,
        filters: selection.filters,
        desiredTaxonomy: selection.desiredTaxonomy,
        selected: summarizeEntry(selected),
        score: selection.score ?? (
          selected.metadata ? scoreBaseline(selected, desiredTaxonomy) : null
        ),
        candidateCount: selection.candidateCount ?? null,
      },
      },
    })),
    baselineName: selected.name,
  };
  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(comparison, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    ...comparison,
    outputPath: resolvedOutputPath,
  }, null, 2));
} else {
  const maxAgeDays = Math.max(0, getNumberOption(options, 'max-age-days', 30));
  const keepRecent = Math.max(0, getNumberOption(options, 'keep-recent', 5));
  const keepPerClass = Math.max(0, getNumberOption(options, 'keep-per-class', 1));
  const deleteArtifacts = getBooleanOption(options, 'delete', false);
  const dryRun = !deleteArtifacts || getBooleanOption(options, 'dry-run', false);
  const nowMs = Date.now();
  const considered = (await readBaselineEntries())
    .filter((entry) => baselineMatchesFilters(entry, explicitTaxonomy));
  const protectedReasons = new Map();

  function protect(entry, reason) {
    if (!protectedReasons.has(entry.dir)) {
      protectedReasons.set(entry.dir, new Set());
    }
    protectedReasons.get(entry.dir).add(reason);
  }

  for (const entry of considered.slice(0, keepRecent)) {
    protect(entry, 'keep-recent');
  }

  for (const entry of considered) {
    const currentAgeDays = ageDays(entry, nowMs);
    if (currentAgeDays !== null && currentAgeDays <= maxAgeDays) {
      protect(entry, 'within-max-age');
    }
  }

  if (keepPerClass > 0) {
    const byClass = new Map();
    for (const entry of considered) {
      const classKey = taxonomyClassKey(entry.metadata?.taxonomy);
      if (!byClass.has(classKey)) {
        byClass.set(classKey, []);
      }
      byClass.get(classKey).push(entry);
    }

    for (const entries of byClass.values()) {
      for (const entry of entries.slice(0, keepPerClass)) {
        protect(entry, 'latest-for-taxonomy');
      }
    }
  }

  const stale = considered.filter((entry) => !protectedReasons.has(entry.dir));
  const removed = [];
  if (!dryRun) {
    for (const entry of stale) {
      assertInsideBaselineRoot(entry.dir);
      await fs.rm(entry.dir, { recursive: true, force: true });
      removed.push(summarizeEntry(entry, { ageDays: ageDays(entry, nowMs) }));
    }
  }

  console.log(JSON.stringify({
    generatedAt: nowIso(),
    baselineRoot,
    filters: explicitTaxonomy,
    retention: {
      mode: dryRun ? 'dry-run' : 'delete',
      maxAgeDays,
      keepRecent,
      keepPerClass,
      considered: considered.length,
      protected: considered
        .filter((entry) => protectedReasons.has(entry.dir))
        .map((entry) => summarizeEntry(entry, {
          ageDays: ageDays(entry, nowMs),
          reasons: [...protectedReasons.get(entry.dir)],
        })),
      stale: stale.map((entry) => summarizeEntry(entry, { ageDays: ageDays(entry, nowMs) })),
      removed,
    },
  }, null, 2));
}
