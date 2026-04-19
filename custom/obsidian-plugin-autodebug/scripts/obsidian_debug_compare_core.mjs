import fs from 'node:fs/promises';
import path from 'node:path';
import { deflateSync, inflateSync } from 'node:zlib';
import { nowIso } from './obsidian_cdp_common.mjs';

const pngSignature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const crcTable = (() => {
  const table = new Uint32Array(256);
  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table[index] = value >>> 0;
  }
  return table;
})();

export function statusRank(status) {
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

function trendRank(status) {
  return status === 'skipped' ? null : statusRank(status);
}

export function signatureId(entry) {
  return typeof entry === 'string' ? entry : entry?.id;
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

function resolveDocumentPath(documentPath, value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    return null;
  }

  const trimmed = value.trim();
  if (path.isAbsolute(trimmed)) {
    return path.resolve(trimmed);
  }

  return path.resolve(path.dirname(path.resolve(documentPath)), trimmed);
}

export function resolveArtifactPaths(diagnosis, diagnosisPath) {
  const artifacts = diagnosis?.artifacts ?? {};
  return {
    summary: resolveDocumentPath(diagnosisPath, artifacts.summary),
    buildLog: resolveDocumentPath(diagnosisPath, artifacts.buildLog),
    deployReport: resolveDocumentPath(diagnosisPath, artifacts.deployReport),
    consoleLog: resolveDocumentPath(diagnosisPath, artifacts.consoleLog),
    errorsLog: resolveDocumentPath(diagnosisPath, artifacts.errorsLog),
    cdpTrace: resolveDocumentPath(diagnosisPath, artifacts.cdpTrace),
    cdpSummary: resolveDocumentPath(diagnosisPath, artifacts.cdpSummary),
    vaultLogCapture: resolveDocumentPath(diagnosisPath, artifacts.vaultLogCapture),
    scenarioReport: resolveDocumentPath(diagnosisPath, artifacts.scenarioReport),
    playwrightTrace: resolveDocumentPath(diagnosisPath, artifacts.playwrightTrace),
    playwrightScreenshot: resolveDocumentPath(diagnosisPath, artifacts.playwrightScreenshot),
    screenshot: resolveDocumentPath(diagnosisPath, artifacts.screenshot),
    dom: resolveDocumentPath(diagnosisPath, artifacts.dom),
  };
}

function normalizeArtifactStates(diagnosis) {
  return diagnosis?.artifactStates && typeof diagnosis.artifactStates === 'object' && !Array.isArray(diagnosis.artifactStates)
    ? diagnosis.artifactStates
    : {};
}

function pngBytesPerPixel(colorType) {
  switch (colorType) {
    case 0:
      return 1;
    case 2:
      return 3;
    case 4:
      return 2;
    case 6:
      return 4;
    default:
      return 0;
  }
}

function crc32(buffer) {
  let value = 0xffffffff;
  for (const byte of buffer) {
    value = crcTable[(value ^ byte) & 0xff] ^ (value >>> 8);
  }
  return (value ^ 0xffffffff) >>> 0;
}

function makeChunk(type, data) {
  const typeBuffer = Buffer.from(type, 'ascii');
  const lengthBuffer = Buffer.alloc(4);
  lengthBuffer.writeUInt32BE(data.length, 0);
  const crcBuffer = Buffer.alloc(4);
  crcBuffer.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), 0);
  return Buffer.concat([lengthBuffer, typeBuffer, data, crcBuffer]);
}

function paethPredictor(left, up, upLeft) {
  const prediction = left + up - upLeft;
  const leftDistance = Math.abs(prediction - left);
  const upDistance = Math.abs(prediction - up);
  const upLeftDistance = Math.abs(prediction - upLeft);

  if (leftDistance <= upDistance && leftDistance <= upLeftDistance) {
    return left;
  }
  if (upDistance <= upLeftDistance) {
    return up;
  }
  return upLeft;
}

function decodePng(buffer) {
  if (!buffer.subarray(0, pngSignature.length).equals(pngSignature)) {
    throw new Error('Unsupported screenshot format: expected PNG');
  }

  let offset = pngSignature.length;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  let interlaceMethod = 0;
  const idat = [];

  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    offset += 4;
    const type = buffer.subarray(offset, offset + 4).toString('ascii');
    offset += 4;
    const data = buffer.subarray(offset, offset + length);
    offset += length;
    offset += 4;

    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      interlaceMethod = data[12];
    } else if (type === 'IDAT') {
      idat.push(data);
    } else if (type === 'IEND') {
      break;
    }
  }

  if (!width || !height || idat.length === 0) {
    throw new Error('Invalid PNG: missing IHDR or IDAT');
  }

  if (bitDepth !== 8) {
    throw new Error(`Unsupported PNG bit depth: ${bitDepth}`);
  }

  if (interlaceMethod !== 0) {
    throw new Error('Unsupported PNG interlace method');
  }

  const bytesPerPixel = pngBytesPerPixel(colorType);
  if (!bytesPerPixel) {
    throw new Error(`Unsupported PNG color type: ${colorType}`);
  }

  const rowLength = width * bytesPerPixel;
  const inflated = inflateSync(Buffer.concat(idat));
  const expectedLength = (rowLength + 1) * height;
  if (inflated.length !== expectedLength) {
    throw new Error('Invalid PNG image data length');
  }

  const rgba = new Uint8Array(width * height * 4);
  let readOffset = 0;
  let writeOffset = 0;
  let previousRow = new Uint8Array(rowLength);

  for (let rowIndex = 0; rowIndex < height; rowIndex += 1) {
    const filterType = inflated[readOffset];
    readOffset += 1;
    const row = Uint8Array.from(inflated.subarray(readOffset, readOffset + rowLength));
    readOffset += rowLength;

    for (let index = 0; index < row.length; index += 1) {
      const left = index >= bytesPerPixel ? row[index - bytesPerPixel] : 0;
      const up = previousRow[index] ?? 0;
      const upLeft = index >= bytesPerPixel ? (previousRow[index - bytesPerPixel] ?? 0) : 0;

      switch (filterType) {
        case 0:
          break;
        case 1:
          row[index] = (row[index] + left) & 0xff;
          break;
        case 2:
          row[index] = (row[index] + up) & 0xff;
          break;
        case 3:
          row[index] = (row[index] + Math.floor((left + up) / 2)) & 0xff;
          break;
        case 4:
          row[index] = (row[index] + paethPredictor(left, up, upLeft)) & 0xff;
          break;
        default:
          throw new Error(`Unsupported PNG filter type: ${filterType}`);
      }
    }

    for (let column = 0; column < width; column += 1) {
      const sourceOffset = column * bytesPerPixel;
      if (colorType === 0) {
        const gray = row[sourceOffset];
        rgba[writeOffset] = gray;
        rgba[writeOffset + 1] = gray;
        rgba[writeOffset + 2] = gray;
        rgba[writeOffset + 3] = 255;
      } else if (colorType === 2) {
        rgba[writeOffset] = row[sourceOffset];
        rgba[writeOffset + 1] = row[sourceOffset + 1];
        rgba[writeOffset + 2] = row[sourceOffset + 2];
        rgba[writeOffset + 3] = 255;
      } else if (colorType === 4) {
        const gray = row[sourceOffset];
        rgba[writeOffset] = gray;
        rgba[writeOffset + 1] = gray;
        rgba[writeOffset + 2] = gray;
        rgba[writeOffset + 3] = row[sourceOffset + 1];
      } else if (colorType === 6) {
        rgba[writeOffset] = row[sourceOffset];
        rgba[writeOffset + 1] = row[sourceOffset + 1];
        rgba[writeOffset + 2] = row[sourceOffset + 2];
        rgba[writeOffset + 3] = row[sourceOffset + 3];
      }
      writeOffset += 4;
    }

    previousRow = row;
  }

  return { width, height, data: rgba };
}

function encodePng({ width, height, data }) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0) {
    throw new Error('PNG encode requires positive integer width/height');
  }
  if (!(data instanceof Uint8Array) || data.length !== width * height * 4) {
    throw new Error('PNG encode requires RGBA byte data');
  }

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  ihdr[10] = 0;
  ihdr[11] = 0;
  ihdr[12] = 0;

  const raw = Buffer.alloc(height * (1 + width * 4));
  let inputOffset = 0;
  let outputOffset = 0;
  for (let row = 0; row < height; row += 1) {
    raw[outputOffset] = 0;
    outputOffset += 1;
    data.subarray(inputOffset, inputOffset + (width * 4)).forEach((value) => {
      raw[outputOffset] = value;
      outputOffset += 1;
    });
    inputOffset += width * 4;
  }

  const idat = deflateSync(raw);
  return Buffer.concat([
    pngSignature,
    makeChunk('IHDR', ihdr),
    makeChunk('IDAT', idat),
    makeChunk('IEND', Buffer.alloc(0)),
  ]);
}

export async function writeRgbaPng(filePath, image) {
  await fs.mkdir(path.dirname(path.resolve(filePath)), { recursive: true });
  await fs.writeFile(filePath, encodePng(image));
  return path.resolve(filePath);
}

function readPixel(image, x, y) {
  if (!image || x < 0 || y < 0 || x >= image.width || y >= image.height) {
    return [0, 0, 0, 0];
  }
  const offset = ((y * image.width) + x) * 4;
  return [
    image.data[offset],
    image.data[offset + 1],
    image.data[offset + 2],
    image.data[offset + 3],
  ];
}

function makeDiffOutputPath(outputPath, candidatePath) {
  if (outputPath) {
    const resolved = path.resolve(outputPath);
    return path.join(
      path.dirname(resolved),
      `${path.basename(resolved, path.extname(resolved))}-screenshot-diff.png`,
    );
  }
  return path.join(path.dirname(path.resolve(candidatePath)), 'comparison-screenshot-diff.png');
}

async function compareScreenshotArtifacts({
  baselinePath,
  candidatePath,
  baselineState = null,
  candidateState = null,
  outputPath = '',
}) {
  const diffPath = makeDiffOutputPath(outputPath, candidatePath ?? baselinePath ?? process.cwd());
  const result = {
    status: 'skipped',
    reason: null,
    baselinePath: baselinePath ? path.resolve(baselinePath) : null,
    candidatePath: candidatePath ? path.resolve(candidatePath) : null,
    diffPath: null,
    baselineDimensions: null,
    candidateDimensions: null,
    dimensionMatch: null,
    comparedPixels: 0,
    changedPixels: 0,
    changedRatio: null,
    diffBounds: null,
  };

  const baselineExists = await exists(baselinePath);
  const candidateExists = await exists(candidatePath);
  if (!baselineExists || !candidateExists) {
    const baselineSkipped = baselineState?.status === 'skipped';
    const candidateSkipped = candidateState?.status === 'skipped';
    result.reason = baselineSkipped && candidateSkipped
      ? 'baseline-and-candidate-screenshots-intentionally-skipped'
      : baselineSkipped
        ? 'baseline-screenshot-intentionally-skipped'
        : candidateSkipped
          ? 'candidate-screenshot-intentionally-skipped'
          : !baselineExists && !candidateExists
            ? 'baseline-and-candidate-screenshots-missing'
            : !baselineExists
              ? 'baseline-screenshot-missing'
              : 'candidate-screenshot-missing';
    await fs.rm(diffPath, { force: true }).catch(() => {});
    return result;
  }

  if (path.extname(baselinePath).toLowerCase() !== '.png' || path.extname(candidatePath).toLowerCase() !== '.png') {
    result.reason = 'unsupported-screenshot-format';
    await fs.rm(diffPath, { force: true }).catch(() => {});
    return result;
  }

  try {
    const baselineImage = decodePng(await fs.readFile(baselinePath));
    const candidateImage = decodePng(await fs.readFile(candidatePath));
    result.baselineDimensions = { width: baselineImage.width, height: baselineImage.height };
    result.candidateDimensions = { width: candidateImage.width, height: candidateImage.height };
    result.dimensionMatch = baselineImage.width === candidateImage.width && baselineImage.height === candidateImage.height;

    const width = Math.max(baselineImage.width, candidateImage.width);
    const height = Math.max(baselineImage.height, candidateImage.height);
    const diffPixels = new Uint8Array(width * height * 4);
    let minX = width;
    let minY = height;
    let maxX = -1;
    let maxY = -1;

    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        const baselinePixel = readPixel(baselineImage, x, y);
        const candidatePixel = readPixel(candidateImage, x, y);
        const changed = baselinePixel.some((value, index) => value !== candidatePixel[index]);
        const offset = ((y * width) + x) * 4;

        if (changed) {
          result.changedPixels += 1;
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);

          const missingPixel = (
            x >= baselineImage.width
            || y >= baselineImage.height
            || x >= candidateImage.width
            || y >= candidateImage.height
          );
          diffPixels[offset] = missingPixel ? 255 : 220;
          diffPixels[offset + 1] = missingPixel ? 140 : 38;
          diffPixels[offset + 2] = missingPixel ? 0 : 38;
          diffPixels[offset + 3] = 255;
          continue;
        }

        const gray = Math.round((candidatePixel[0] + candidatePixel[1] + candidatePixel[2]) / 3);
        const blended = Math.round((gray * 0.65) + (255 * 0.35));
        diffPixels[offset] = blended;
        diffPixels[offset + 1] = blended;
        diffPixels[offset + 2] = blended;
        diffPixels[offset + 3] = 255;
      }
    }

    result.comparedPixels = width * height;
    result.changedRatio = result.comparedPixels > 0
      ? Number((result.changedPixels / result.comparedPixels).toFixed(6))
      : 0;
    result.diffBounds = result.changedPixels > 0
      ? {
          left: minX,
          top: minY,
          right: maxX,
          bottom: maxY,
          width: (maxX - minX) + 1,
          height: (maxY - minY) + 1,
        }
      : null;

    if (result.changedPixels > 0) {
      await writeRgbaPng(diffPath, { width, height, data: diffPixels });
      result.status = 'different';
      result.diffPath = path.resolve(diffPath);
      return result;
    }

    await fs.rm(diffPath, { force: true }).catch(() => {});
    result.status = 'identical';
    return result;
  } catch (error) {
    await fs.rm(diffPath, { force: true }).catch(() => {});
    return {
      ...result,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function buildDebugComparison({
  baselinePath,
  baseline,
  candidatePath,
  candidate,
  context = {},
  outputPath = '',
}) {
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

  const baselineSignatures = new Set((baseline.signatures ?? []).map(signatureId).filter(Boolean));
  const candidateSignatures = new Set((candidate.signatures ?? []).map(signatureId).filter(Boolean));

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
    const baselineRank = trendRank(entry.baseline ?? 'pass');
    const candidateRank = trendRank(entry.candidate ?? 'pass');
    if (baselineRank === null || candidateRank === null) {
      return false;
    }
    return candidateRank > baselineRank;
  });

  const fixes = assertionChanges.filter((entry) => {
    const baselineRank = trendRank(entry.baseline ?? 'pass');
    const candidateRank = trendRank(entry.candidate ?? 'pass');
    if (baselineRank === null || candidateRank === null) {
      return false;
    }
    return candidateRank < baselineRank;
  });

  const baselineArtifacts = resolveArtifactPaths(baseline, baselinePath);
  const candidateArtifacts = resolveArtifactPaths(candidate, candidatePath);
  const baselineArtifactStates = normalizeArtifactStates(baseline);
  const candidateArtifactStates = normalizeArtifactStates(candidate);
  const screenshotDiff = await compareScreenshotArtifacts({
    baselinePath: baselineArtifacts.screenshot,
    candidatePath: candidateArtifacts.screenshot,
    baselineState: baselineArtifactStates.screenshot ?? null,
    candidateState: candidateArtifactStates.screenshot ?? null,
    outputPath,
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
    visualStatus: screenshotDiff.status === 'different'
      ? 'changed'
      : screenshotDiff.status === 'identical'
        ? 'unchanged'
        : 'skipped',
    baseline: {
      path: path.resolve(baselinePath),
      name: context.baselineName ?? null,
      status: baseline.status,
      headline: baseline.headline,
      useCdp: Boolean(baseline.useCdp),
      taxonomy: context.baselineTaxonomy ?? {},
      artifacts: baselineArtifacts,
      artifactStates: baselineArtifactStates,
    },
    candidate: {
      path: path.resolve(candidatePath),
      status: candidate.status,
      headline: candidate.headline,
      useCdp: Boolean(candidate.useCdp),
      taxonomy: context.candidateTaxonomy ?? {},
      artifacts: candidateArtifacts,
      artifactStates: candidateArtifactStates,
    },
    baselineSelection: context.selection ?? null,
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
    screenshotDiff,
  };
}
