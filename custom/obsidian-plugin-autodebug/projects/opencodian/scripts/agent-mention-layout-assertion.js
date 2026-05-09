(async () => {
  const preferredAgentText = '@council';
  const queryText = '@co';
  const fillerLength = 66;
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  await app.commands.executeCommandById('opencodian:open-view');
  await wait(500);

  const leaf = app.workspace.getLeavesOfType('opencodian-view')[0];
  const container = leaf?.view?.containerEl;
  const textarea = container?.querySelector('.opencodian-input');
  const highlightContainer = container?.querySelector('.opencodian-input-highlight-container');
  const backdrop = container?.querySelector('.opencodian-input-highlight-backdrop');
  if (!container || !textarea || !highlightContainer || !backdrop) {
    throw new Error('OpenCodian composer highlight DOM was not found.');
  }

  const dispatchInput = () => {
    textarea.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
  };
  const typeText = async (text) => {
    textarea.focus();
    textarea.value += text;
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    dispatchInput();
    await wait(80);
  };
  const selectMention = async () => {
    await typeText(queryText);
    await wait(600);
    const items = Array.from(container.querySelectorAll('.opencodian-slash-command-menu-item'));
    if (items.length === 0) {
      throw new Error('Agent mention menu did not open.');
    }

    const labels = items.map((item) =>
      (item.querySelector('.opencodian-slash-command-menu-title')?.textContent
        ?? item.textContent
        ?? '').trim());
    const preferredIndex = labels.findIndex((label) => label.startsWith(preferredAgentText));
    const targetIndex = preferredIndex >= 0 ? preferredIndex : 0;
    for (let index = 0; index < targetIndex; index += 1) {
      textarea.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'ArrowDown',
        bubbles: true,
        cancelable: true,
      }));
    }
    textarea.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter',
      bubbles: true,
      cancelable: true,
    }));
    await wait(150);

    const selectedText = (labels[targetIndex] ?? '').match(/^@\S+/)?.[0] ?? preferredAgentText;
    return selectedText;
  };

  textarea.value = '';
  textarea.setSelectionRange(0, 0);
  dispatchInput();
  await wait(100);

  const firstMention = await selectMention();
  await typeText(` ${'n'.repeat(fillerLength)} `);
  await selectMention();
  await typeText('\n');
  await selectMention();
  await typeText(' ');
  await wait(250);

  const pillElements = Array.from(container.querySelectorAll('.opencodian-input-highlight-agent'));
  const agentStyle = getComputedStyle(pillElements[0]);
  const textareaStyle = getComputedStyle(textarea);
  const backdropStyle = getComputedStyle(backdrop);
  const pxValues = Array.from(agentStyle.boxShadow.matchAll(/(-?\d+(?:\.\d+)?)px/g)).map((match) =>
    Number(match[1]));
  const shadowSpread = pxValues.length >= 4 ? Math.max(0, pxValues[3]) : 0;
  const containerRect = highlightContainer.getBoundingClientRect();
  const pills = pillElements.map((pill, index) => {
    const rect = pill.getBoundingClientRect();
    return {
      index,
      text: pill.textContent ?? '',
      leftGapIncludingShadowPx: (rect.left - shadowSpread) - containerRect.left,
      rightGapIncludingShadowPx: containerRect.right - (rect.right + shadowSpread),
      expandedTop: rect.top - shadowSpread,
      expandedBottom: rect.bottom + shadowSpread,
      top: rect.top,
      left: rect.left,
    };
  });

  const rows = [];
  for (const pill of pills.slice().sort((a, b) => a.top - b.top || a.left - b.left)) {
    const row = rows.find((candidate) => Math.abs(candidate.top - pill.top) < 2);
    if (row) {
      row.items.push(pill.index);
      row.expandedTop = Math.min(row.expandedTop, pill.expandedTop);
      row.expandedBottom = Math.max(row.expandedBottom, pill.expandedBottom);
    } else {
      rows.push({
        top: pill.top,
        expandedTop: pill.expandedTop,
        expandedBottom: pill.expandedBottom,
        items: [pill.index],
      });
    }
  }

  const rowGaps = [];
  for (let index = 1; index < rows.length; index += 1) {
    rowGaps.push({
      fromRow: index - 1,
      toRow: index,
      gapIncludingShadowPx: rows[index].expandedTop - rows[index - 1].expandedBottom,
    });
  }

  const assertions = {
    threePills: pills.length === 3,
    noHorizontalClip: pills.every((pill) =>
      pill.leftGapIncludingShadowPx >= 0 && pill.rightGapIncludingShadowPx >= 0),
    noVerticalOverlap: rowGaps.every((gap) => gap.gapIncludingShadowPx >= 0),
    metricsMatch: textareaStyle.padding === backdropStyle.padding
      && textareaStyle.lineHeight === backdropStyle.lineHeight,
    shadowSpreadIsSmall: shadowSpread <= 2,
  };
  const ok = Object.values(assertions).every(Boolean);
  return JSON.stringify({
    ok,
    selectedAgent: firstMention,
    fillerLength,
    assertions,
    computed: {
      textareaPadding: textareaStyle.padding,
      backdropPadding: backdropStyle.padding,
      textareaLineHeight: textareaStyle.lineHeight,
      backdropLineHeight: backdropStyle.lineHeight,
      agentBoxShadow: agentStyle.boxShadow,
      shadowSpreadPx: shadowSpread,
    },
    pills,
    rows,
    rowGaps,
  });
})();
