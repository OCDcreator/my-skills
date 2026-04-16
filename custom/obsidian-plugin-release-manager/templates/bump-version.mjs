import fs from 'fs';
import path from 'path';

const root = process.cwd();
const files = [
	'package.json',
	'package-lock.json',
	'manifest.json'
].map(file => path.join(root, file));

const mode = process.argv[2] ?? 'check';

function readJson(filePath) {
	return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function writeJson(filePath, data) {
	fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf-8');
}

function bumpVersion(version, bumpMode) {
	const [major, minor, patch] = version.split('.').map(Number);

	switch (bumpMode) {
		case 'major':
			return `${major + 1}.0.0`;
		case 'minor':
			return `${major}.${minor + 1}.0`;
		case 'patch':
			return `${major}.${minor}.${patch + 1}`;
		default:
			return bumpMode;
	}
}

const packageJson = readJson(files[0]);
const packageLockJson = readJson(files[1]);
const manifestJson = readJson(files[2]);
const versions = [
	packageJson.version,
	packageLockJson.version,
	packageLockJson.packages?.['']?.version,
	manifestJson.version
].filter(Boolean);
const uniqueVersions = [...new Set(versions)];

if (mode === 'check') {
	if (uniqueVersions.length !== 1) {
		console.error(`Version mismatch detected: ${uniqueVersions.join(', ')}`);
		process.exit(1);
	}

	console.log(`Version check passed: ${uniqueVersions[0]}`);
	process.exit(0);
}

const currentVersion = packageJson.version;
const nextVersion = bumpVersion(currentVersion, mode);

packageJson.version = nextVersion;
packageLockJson.version = nextVersion;
if (packageLockJson.packages?.['']) {
	packageLockJson.packages[''].version = nextVersion;
}
manifestJson.version = nextVersion;

writeJson(files[0], packageJson);
writeJson(files[1], packageLockJson);
writeJson(files[2], manifestJson);

console.log(`Version bumped: ${currentVersion} -> ${nextVersion}`);
