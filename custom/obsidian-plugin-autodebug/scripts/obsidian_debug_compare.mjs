import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const baselinePath = getStringOption(options, 'baseline').trim();
const candidatePath = getStringOption(options, 'candidate').trim();
if (!baselinePath || !candidatePath) {
  throw new Error('--baseline and --candidate are required');
}

const outputPath = getStringOption(
  options,
  'output',
  path.join(path.dirname(path.resolve(candidatePath)), 'comparison.json'),
);

function statusRank(status) {
  switch (status) {
    case 'fail':
      return 3;
    case 'warning':
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

const baseline = JSON.parse((await fs.readFile(baselinePath, 'utf8')).replace(/^\uFEFF/, ''));
const candidate = JSON.parse((await fs.readFile(candidatePath, 'utf8')).replace(/^\uFEFF/, ''));

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

const comparison = {
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

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(comparison, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(comparison, null, 2));
