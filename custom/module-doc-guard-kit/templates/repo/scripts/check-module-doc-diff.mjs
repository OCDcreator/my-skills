#!/usr/bin/env node
import {
  autoDetectRange,
  loadConfig,
  parseArgs,
  printList,
  readGitDiffNameStatus,
  repoRoot,
  requiredDocsFromDiff,
} from './module-doc-guard-lib.mjs';

const args = parseArgs();
const root = repoRoot();
const range = args.range ?? autoDetectRange(root);
const config = loadConfig(root, args.config ?? 'module-docs.config.json');
const diffRecords = readGitDiffNameStatus(root, range);
const { changedPaths, requiredDocs } = requiredDocsFromDiff(config, diffRecords);

const missingDocTouches = requiredDocs.filter((requirement) => !changedPaths.has(requirement.docPath));

if (missingDocTouches.length > 0) {
  console.error(`[module-docs:diff] FAILED (${range})`);
  printList(
    'Changed source modules without mapped doc changes:',
    missingDocTouches,
    (requirement) => `- ${requirement.sourcePaths.join(', ')} -> ${requirement.docPath}`,
  );
  console.error('');
  console.error('Update the mapped docs in this branch, or run list-module-doc-targets-from-diff.mjs for the full target list.');
  process.exit(1);
}

console.log(`[module-docs:diff] OK (${requiredDocs.length} required doc targets, range ${range})`);
