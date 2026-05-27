import fs from 'node:fs/promises';
import path from 'node:path';
import {
  connectToCdp,
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_cdp_capture_ui.mjs [options]

Options:
  --host <host> --port <n>            CDP endpoint. Defaults to 127.0.0.1:9222.
  --target-title-contains <text>      Attach to a matching Obsidian window.
  --selector <css>                    DOM selector to capture.
  --html-output <path>                Save matched HTML.
  --text-output <path>                Save matched text.
  --screenshot-output <path>          Save screenshot PNG.
  --summary <path>                    Capture summary JSON output.
  --all <true|false>                  Capture all matches or first match.
  --pre-eval <js-expression>          JS expression to evaluate before capture.
  --ensure-visible <true|false>       Scroll, wait, and verify target is visible before screenshot. Default true.
  --ensure-leaf-active <true|false>   Ensure the workspace leaf containing the target is active before screenshot. Default true.
  --wait-after-eval <ms>              Milliseconds to wait after pre-eval before capture. Default 500.
`);
}

const host = getStringOption(options, 'host', '127.0.0.1');
const port = Number(getStringOption(options, 'port', '9222'));
const targetUrl = getStringOption(options, 'target-url', 'app://obsidian.md/index.html');
const targetTitleContains = getStringOption(options, 'target-title-contains', '').trim();
let selector = getStringOption(options, 'selector', '').trim();
const htmlOutput = getStringOption(options, 'html-output');
const textOutput = getStringOption(options, 'text-output');
const screenshotOutput = getStringOption(options, 'screenshot-output');
const preEval = getStringOption(options, 'pre-eval', '').trim();
const ensureVisible = getBooleanOption(options, 'ensure-visible', true);
const ensureLeafActive = getBooleanOption(options, 'ensure-leaf-active', true);
const waitAfterEval = getNumberOption(options, 'wait-after-eval', 500);
const summaryPath = getStringOption(
  options,
  'summary',
  path.resolve('.obsidian-debug/cdp-capture-ui.summary.json'),
);
const allMatches = getBooleanOption(options, 'all', true);

const session = await connectToCdp({
  host,
  port,
  targetUrl,
  targetTitleContains,
});

if (!selector) {
  const autoDetect = await session.evaluate(`(() => {
    // Check for visible settings modal first (highest priority)
    const settingsModal = document.querySelector('.modal.mod-settings');
    if (settingsModal) {
      const modalContainer = settingsModal.closest('.modal-container');
      if (modalContainer) {
        const style = globalThis.getComputedStyle(modalContainer);
        if (style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0) {
          return { selector: '.modal.mod-settings', type: 'settings-modal' };
        }
      }
    }
    // Check for any visible modal
    const anyModal = document.querySelector('.modal-container');
    if (anyModal) {
      const style = globalThis.getComputedStyle(anyModal);
      if (style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0) {
        const firstModal = anyModal.querySelector('.modal');
        if (firstModal) return { selector: '.modal-container .modal', type: 'modal' };
      }
    }
    // Fallback to active workspace leaf
    return { selector: '.workspace-leaf.mod-active', type: 'active-leaf' };
  })()`);
  selector = autoDetect?.result?.value?.selector || '.workspace-leaf.mod-active';
  console.log(`Auto-detected selector: ${selector} (${autoDetect?.result?.value?.type || 'fallback'})`);
}

if (preEval) {
  await session.evaluate(`(async () => { ${preEval}; })()`);
  await new Promise((resolve) => setTimeout(resolve, waitAfterEval));
}

if (ensureLeafActive) {
  const focusResult = await session.evaluate(`(() => {
    const selector = ${JSON.stringify(selector)};
    const target = document.querySelector(selector);
    if (!target) return { ok: false, reason: 'target-not-found', selector };

    // If target is inside a modal, ensure the modal container is visible and on top
    const modal = target.closest('.modal-container, .modal');
    if (modal) {
      const container = modal.closest('.modal-container') || modal;
      const style = globalThis.getComputedStyle(container);
      if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
        return { ok: false, reason: 'modal-hidden', selector };
      }
      // Ensure modal bg is visible
      const modalBg = document.querySelector('.modal-bg');
      if (modalBg) {
        modalBg.style.opacity = '1';
        modalBg.style.display = 'block';
      }
      return { ok: true, type: 'modal' };
    }

    // Otherwise focus the workspace leaf
    const leaf = target.closest('.workspace-leaf');
    if (!leaf) return { ok: false, reason: 'no-leaf', selector };
    if (!leaf.classList.contains('mod-active')) {
      const parent = leaf.parentElement;
      if (parent) {
        for (const sibling of parent.children) {
          if (sibling !== leaf && sibling.classList.contains('workspace-leaf')) {
            sibling.classList.remove('mod-active');
          }
        }
      }
      leaf.classList.add('mod-active');
    }
    // Scroll the leaf into view if it is off-screen
    const leafRect = leaf.getBoundingClientRect();
    const viewport = { width: globalThis.innerWidth, height: globalThis.innerHeight };
    if (leafRect.bottom < 0 || leafRect.top > viewport.height || leafRect.right < 0 || leafRect.left > viewport.width) {
      leaf.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
    }
    return { ok: true, type: 'leaf', leafActive: leaf.classList.contains('mod-active') };
  })()`);
  if (!focusResult?.result?.value?.ok) {
    console.warn(`Warning: could not focus target for selector "${selector}": ${focusResult?.result?.value?.reason || 'unknown'}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 300));
}

const result = await session.evaluate(`(async () => {
  const selector = ${JSON.stringify(selector)};
  const nodes = Array.from(document.querySelectorAll(selector));
  const picked = ${allMatches ? 'nodes' : 'nodes.slice(0, 1)'};
  const viewport = {
    width: globalThis.innerWidth,
    height: globalThis.innerHeight,
  };
  let firstVisibleNode = picked[0] ?? null;

  if (firstVisibleNode && ${ensureVisible}) {
    firstVisibleNode.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' });

    // Ensure the target's workspace leaf is active so the screenshot captures the right surface
    const leaf = firstVisibleNode.closest('.workspace-leaf');
    if (leaf && !leaf.classList.contains('mod-active')) {
      const parent = leaf.parentElement;
      if (parent) {
        for (const sibling of parent.children) {
          if (sibling !== leaf && sibling.classList.contains('workspace-leaf')) {
            sibling.classList.remove('mod-active');
          }
        }
      }
      leaf.classList.add('mod-active');
    }

    await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 300)));

    const isInViewport = (rect) => (
      rect.width > 0
      && rect.height > 0
      && rect.right > 0
      && rect.bottom > 0
      && rect.left < viewport.width
      && rect.top < viewport.height
    );

    const isActuallyVisible = (node) => {
      if (typeof node.checkVisibility === 'function') {
        return node.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true });
      }
      const style = globalThis.getComputedStyle(node);
      return style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0;
    };

    let rect = firstVisibleNode.getBoundingClientRect();
    let visible = isActuallyVisible(firstVisibleNode) && isInViewport(rect);

    if (!visible) {
      const allNodes = Array.from(document.querySelectorAll(selector));
      for (const node of allNodes) {
        node.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' });
        await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 100)));
        const r = node.getBoundingClientRect();
        if (isActuallyVisible(node) && isInViewport(r)) {
          firstVisibleNode = node;
          rect = r;
          visible = true;
          break;
        }
      }
    }

    if (!visible && firstVisibleNode) {
      let ancestor = firstVisibleNode.parentElement;
      while (ancestor) {
        const aStyle = globalThis.getComputedStyle(ancestor);
        const isModalLike = aStyle.position === 'fixed' || aStyle.position === 'absolute' || ancestor.classList.contains('modal-container');
        if (isModalLike) {
          const focusable = ancestor.querySelector('button, [tabindex]:not([tabindex="-1"]), a, input, select');
          if (focusable) {
            focusable.focus();
            ancestor.scrollTop = 0;
          }
          break;
        }
        ancestor = ancestor.parentElement;
      }
      await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 150)));
      rect = firstVisibleNode.getBoundingClientRect();
      visible = isActuallyVisible(firstVisibleNode) && isInViewport(rect);
    }
  }

  return {
    count: nodes.length,
    viewport,
    ensureVisible: ${ensureVisible},
    preEvalRan: ${JSON.stringify(preEval.length > 0)},
    firstMatchVisible: Boolean(firstVisibleNode),
    matches: picked.map((node) => ({
      outerHTML: node.outerHTML,
      textContent: node.textContent ?? '',
      display: globalThis.getComputedStyle(node).display,
      visibility: globalThis.getComputedStyle(node).visibility,
      opacity: globalThis.getComputedStyle(node).opacity,
      pointerEvents: globalThis.getComputedStyle(node).pointerEvents,
      rect: (() => {
        const { x, y, width, height } = node.getBoundingClientRect();
        return { x, y, width, height };
      })(),
      computedStyle: {
        display: globalThis.getComputedStyle(node).display,
        visibility: globalThis.getComputedStyle(node).visibility,
        opacity: globalThis.getComputedStyle(node).opacity,
        'pointer-events': globalThis.getComputedStyle(node).pointerEvents,
      },
    })),
  };
})()`);

const value = result?.result?.value ?? { count: 0, matches: [] };

if (htmlOutput) {
  await ensureParentDirectory(htmlOutput);
  await fs.writeFile(
    htmlOutput,
    `${value.matches.map((entry) => entry.outerHTML).join('\n')}\n`,
    'utf8',
  );
}

if (textOutput) {
  await ensureParentDirectory(textOutput);
  await fs.writeFile(
    textOutput,
    `${value.matches.map((entry) => entry.textContent).join('\n\n')}\n`,
    'utf8',
  );
}

if (screenshotOutput) {
  await session.send('Page.bringToFront');
  const firstMatch = value.matches[0];
  const rect = firstMatch?.rect;
  const viewport = value.viewport ?? { width: 0, height: 0 };
  const hasRect = rect
    && Number.isFinite(rect.x)
    && Number.isFinite(rect.y)
    && Number.isFinite(rect.width)
    && Number.isFinite(rect.height)
    && rect.width > 0
    && rect.height > 0;
  const clip = hasRect
    ? (() => {
        const padding = 24;
        const x = Math.max(0, rect.x - padding);
        const y = Math.max(0, rect.y - padding);
        const maxWidth = viewport.width > 0 ? Math.max(1, viewport.width - x) : rect.width + padding * 2;
        const maxHeight = viewport.height > 0 ? Math.max(1, viewport.height - y) : rect.height + padding * 2;
        return {
          x,
          y,
          width: Math.min(rect.width + padding * 2, maxWidth),
          height: Math.min(rect.height + padding * 2, maxHeight),
          scale: 1,
        };
      })()
    : null;
  const shot = await session.send('Page.captureScreenshot', clip ? {
    format: 'png',
    clip,
    captureBeyondViewport: false,
  } : {
    format: 'png',
    captureBeyondViewport: true,
  });
  await ensureParentDirectory(screenshotOutput);
  await fs.writeFile(screenshotOutput, Buffer.from(shot.data, 'base64'));
}

await ensureParentDirectory(summaryPath);
await fs.writeFile(
  summaryPath,
  `${JSON.stringify(
    {
      capturedAt: nowIso(),
      host,
      port,
      targetUrl,
      targetTitleContains,
      selector,
      ensureLeafActive,
      waitAfterEval,
      count: value.count,
      matches: value.matches.slice(0, 50).map((entry) => ({
        textContent: String(entry.textContent ?? '').slice(0, 1000),
        display: entry.display,
        visibility: entry.visibility,
        opacity: entry.opacity,
        pointerEvents: entry.pointerEvents,
        rect: entry.rect ?? null,
        computedStyle: entry.computedStyle ?? {},
      })),
      matchesTruncated: value.matches.length > 50,
      htmlOutput: htmlOutput || null,
      textOutput: textOutput || null,
      screenshotOutput: screenshotOutput || null,
    },
    null,
    2,
  )}\n`,
  'utf8',
);

await session.close();
