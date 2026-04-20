#!/usr/bin/env node
import {
  aggregateDocsFromRequirements,
  autoDetectRange,
  findGroupForSource,
  loadConfig,
  parseArgs,
  readGitDiffNameStatus,
  repoRoot,
  requiredDocsFromDiff,
} from './module-doc-guard-lib.mjs';

const args = parseArgs();
const root = repoRoot();
const range = args.range ?? autoDetectRange(root);
const config = loadConfig(root, args.config ?? 'module-docs.config.json');
const diffRecords = readGitDiffNameStatus(root, range);
const { requiredDocs } = requiredDocsFromDiff(config, diffRecords);

const enrichedRequirements = requiredDocs.map((requirement) => ({
  ...requirement,
  group: findGroupForSource(config, requirement.sourcePaths[0]),
}));

const aggregateDocs = aggregateDocsFromRequirements(enrichedRequirements);

if (args.json) {
  console.log(JSON.stringify({
    range,
    moduleDocs: requiredDocs,
    aggregateDocs,
  }, null, 2));
} else {
  console.log(`[module-docs:list] range ${range}`);
  console.log('');
  console.log('Required module docs:');
  if (requiredDocs.length === 0) {
    console.log('- none');
  } else {
    for (const requirement of requiredDocs) {
      console.log(`- ${requirement.docPath}`);
      console.log(`  source: ${requirement.sourcePaths.join(', ')}`);
      console.log(`  status: ${requirement.statuses.join(', ')}`);
    }
  }

  console.log('');
  console.log('Aggregate docs to inspect:');
  if (aggregateDocs.length === 0) {
    console.log('- none');
  } else {
    for (const docPath of aggregateDocs) {
      console.log(`- ${docPath}`);
    }
  }
}
