import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const mode = getStringOption(options, 'mode', '').trim().toLowerCase();
if (!['save', 'compare', 'list'].includes(mode)) {
  throw new Error('--mode must be save, compare, or list');
}

const baselineRoot = path.resolve(getStringOption(options, 'baseline-root', '.obsidian-debug/baselines'));
const name = getStringOption(options, 'name', '').trim();
const diagnosisPath = getStringOption(options, 'diagnosis', '').trim();
const profilePath = getStringOption(options, 'profile', '').trim();
const reportPath = getStringOption(options, 'report', '').trim();
const comparisonPath = getStringOption(options, 'comparison', '').trim();
const candidateDiagnosisPath = getStringOption(options, 'candidate-diagnosis', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();

function statusRank(status) {
  switch (status) {
    case 'fail':
      return 5;
    case 'warning':
    case 'warn':
      return 4;
    case 'flaky':
      return 3;
    case 'expected':
      return 2;
    case 'pass':
      return 1;
    default:
      return 0;
  }
}

function toMapById(entries) {
  const map = new Map();
  for (const entry of entries ?? []) {
    if (entry?.id) {
      map.set(entry.id, entry);
    }
  }
  return map;
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

async function copyIfExists(sourcePath, destinationPath) {
  if (!sourcePath || !(await exists(sourcePath))) {
    return null;
  }
  await ensureParentDirectory(destinationPath);
  await fs.copyFile(sourcePath, destinationPath);
  return destinationPath;
}

function buildComparison(baselinePath, baseline, candidatePath, candidate) {
  const timingKeys = [...new Set([
    ...Object.keys(baseline.timings ?? {}),
    ...Object.keys(candidate.timings ?? {}),
  ])];

  const timingDiffs = timingKeys.map((metric) => {
    const baselineValue = baseline.timings?.[metric] ?? null;
    const candidateValue = candidate.timings?.[metric] ?? null;
    return {
      metric,
      baseline: baselineValue,
      candidate: candidateValue,
      delta:
        Number.isFinite(baselineValue) && Number.isFinite(candidateValue)
          ? candidateValue - baselineValue
          : null,
    };
  });

  const baselineSignatures = new Set((baseline.signatures ?? []).map((entry) => entry.id));
  const candidateSignatures = new Set((candidate.signatures ?? []).map((entry) => entry.id));

  const addedSignatures = [...candidateSignatures].filter((id) => !baselineSignatures.has(id));
  const removedSignatures = [...baselineSignatures].filter((id) => !candidateSignatures.has(id));

  const baselineAssertions = toMapById([
    ...(baseline.assertions ?? []),
    ...(baseline.customAssertions ?? []),
  ]);
  const candidateAssertions = toMapById([
    ...(candidate.assertions ?? []),
    ...(candidate.customAssertions ?? []),
  ]);

  const allAssertionIds = [...new Set([
    ...baselineAssertions.keys(),
    ...candidateAssertions.keys(),
  ])];

  const assertionChanges = allAssertionIds.map((id) => ({
    id,
    baseline: baselineAssertions.get(id)?.status ?? null,
    candidate: candidateAssertions.get(id)?.status ?? null,
  })).filter((entry) => entry.baseline !== entry.candidate);

  const regressions = assertionChanges.filter((entry) => {
    const baselineRank = statusRank(entry.baseline ?? 'pass');
    const candidateRank = statusRank(entry.candidate ?? 'pass');
    return candidateRank > baselineRank;
  });

  const fixes = assertionChanges.filter((entry) => {
    const baselineRank = statusRank(entry.baseline ?? 'pass');
    const candidateRank = statusRank(entry.candidate ?? 'pass');
    return candidateRank < baselineRank;
  });

  const comparisonStatus = (() => {
    const baselineRank = statusRank(baseline.status);
    const candidateRank = statusRank(candidate.status);
    if (candidateRank > baselineRank || regressions.length > 0 || addedSignatures.length > 0) {
      return 'regressed';
    }
    if (candidateRank < baselineRank || fixes.length > 0 || removedSignatures.length > 0) {
      return 'improved';
    }
    return 'unchanged';
  })();

  return {
    generatedAt: nowIso(),
    status: comparisonStatus,
    baseline: {
      path: path.resolve(baselinePath),
      status: baseline.status,
      headline: baseline.headline,
    },
    candidate: {
      path: path.resolve(candidatePath),
      status: candidate.status,
      headline: candidate.headline,
    },
    timingDiffs,
    signatures: {
      added: addedSignatures,
      removed: removedSignatures,
    },
    assertions: {
      changed: assertionChanges,
      regressions,
      fixes,
    },
  };
}

if (mode === 'list') {
  await fs.mkdir(baselineRoot, { recursive: true });
  const entries = await fs.readdir(baselineRoot, { withFileTypes: true });
  const baselines = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    const metadataPath = path.join(baselineRoot, entry.name, 'baseline.json');
    if (!(await exists(metadataPath))) {
      continue;
    }
    baselines.push(await readJson(metadataPath));
  }
  console.log(JSON.stringify({
    generatedAt: nowIso(),
    baselineRoot,
    baselines,
  }, null, 2));
} else if (mode === 'save') {
  if (!name || !diagnosisPath) {
    throw new Error('--name and --diagnosis are required for save mode');
  }

  const resolvedDiagnosisPath = path.resolve(diagnosisPath);
  const diagnosis = await readJson(resolvedDiagnosisPath);
  const baselineDir = path.join(baselineRoot, name);
  await fs.rm(baselineDir, { recursive: true, force: true });
  await fs.mkdir(baselineDir, { recursive: true });

  const savedDiagnosisPath = await copyIfExists(resolvedDiagnosisPath, path.join(baselineDir, 'diagnosis.json'));
  const savedProfilePath = await copyIfExists(profilePath ? path.resolve(profilePath) : '', path.join(baselineDir, 'profile-summary.json'));
  const savedReportPath = await copyIfExists(reportPath ? path.resolve(reportPath) : '', path.join(baselineDir, 'report.html'));
  const savedComparisonPath = await copyIfExists(comparisonPath ? path.resolve(comparisonPath) : '', path.join(baselineDir, 'comparison.json'));

  const metadata = {
    generatedAt: nowIso(),
    mode,
    name,
    baselineRoot,
    baselineDir,
    diagnosis: {
      path: savedDiagnosisPath,
      status: diagnosis.status ?? null,
      headline: diagnosis.headline ?? null,
      pluginId: diagnosis.pluginId ?? null,
      timings: diagnosis.timings ?? {},
      signatures: (diagnosis.signatures ?? []).map((entry) => entry.id),
    },
    profilePath: savedProfilePath,
    reportPath: savedReportPath,
    comparisonPath: savedComparisonPath,
    sourcePaths: {
      diagnosis: resolvedDiagnosisPath,
      profile: profilePath ? path.resolve(profilePath) : null,
      report: reportPath ? path.resolve(reportPath) : null,
      comparison: comparisonPath ? path.resolve(comparisonPath) : null,
    },
  };

  await fs.writeFile(path.join(baselineDir, 'baseline.json'), `${JSON.stringify(metadata, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(metadata, null, 2));
} else {
  if (!name || !candidateDiagnosisPath) {
    throw new Error('--name and --candidate-diagnosis are required for compare mode');
  }

  const baselineDiagnosisPath = path.join(baselineRoot, name, 'diagnosis.json');
  if (!(await exists(baselineDiagnosisPath))) {
    throw new Error(`Baseline diagnosis does not exist: ${baselineDiagnosisPath}`);
  }

  const baseline = await readJson(baselineDiagnosisPath);
  const candidate = await readJson(path.resolve(candidateDiagnosisPath));
  const comparison = buildComparison(baselineDiagnosisPath, baseline, path.resolve(candidateDiagnosisPath), candidate);
  const resolvedOutputPath = path.resolve(
    outputPath || path.join(path.dirname(path.resolve(candidateDiagnosisPath)), 'baseline-comparison.json'),
  );
  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(comparison, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify({
    ...comparison,
    baselineName: name,
    outputPath: resolvedOutputPath,
  }, null, 2));
}
