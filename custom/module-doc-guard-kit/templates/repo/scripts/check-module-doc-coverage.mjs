#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

import {
  collectDocFiles,
  collectSourceMappings,
  loadConfig,
  parseArgs,
  printList,
  repoRoot,
  toPosix,
} from './module-doc-guard-lib.mjs';

const args = parseArgs();
const root = repoRoot();
const config = loadConfig(root, args.config ?? 'module-docs.config.json');
const sourceMappings = collectSourceMappings(root, config);
const expectedDocs = new Set(sourceMappings.map((mapping) => mapping.docPath));
const docFiles = collectDocFiles(root, config);

const missingDocs = sourceMappings
  .filter((mapping) => !fs.existsSync(path.join(root, mapping.docPath)))
  .map((mapping) => `${mapping.sourcePath} -> ${mapping.docPath}`);

const orphanDocs = docFiles.filter((docPath) => !expectedDocs.has(docPath));

if (missingDocs.length > 0 || orphanDocs.length > 0) {
  console.error('[module-docs:coverage] FAILED');
  console.error('');
  printList('Missing module docs:', missingDocs);
  printList('Orphan module docs:', orphanDocs);
  console.error('');
  console.error('Fix by adding missing docs, deleting orphan docs, or encoding real exceptions in module-docs.config.json.');
  process.exit(1);
}

console.log(
  `[module-docs:coverage] OK (${sourceMappings.length} source modules, ${docFiles.length} mapped docs, config ${toPosix(args.config ?? 'module-docs.config.json')})`,
);
