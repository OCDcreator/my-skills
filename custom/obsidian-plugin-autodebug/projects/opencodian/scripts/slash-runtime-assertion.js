(async () => {
  const plugin = app.plugins.plugins.opencodian;
  if (!plugin) {
    throw new Error('OpenCodian plugin is not loaded.');
  }

  await app.commands.executeCommandById('opencodian:open-view');
  await new Promise((resolve) => setTimeout(resolve, 500));

  const leaf = app.workspace.getLeavesOfType('opencodian-view')[0];
  const view = leaf?.view;
  const container = view?.containerEl;
  const textarea = container?.querySelector('.opencodian-input');
  if (!container || !textarea) {
    throw new Error('OpenCodian view or composer textarea was not found.');
  }

  const originalSkillMode = plugin.settings.slashCommandSkillMode;
  const dispatchInput = () => {
    textarea.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
  };
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const waitForMenuIdle = async () => {
    const startedAt = Date.now();
    while (Date.now() - startedAt < 5000) {
      const menu = container.querySelector('.opencodian-slash-command-menu');
      const loading = menu?.querySelector('.opencodian-slash-command-menu-state--loading');
      if (menu && !loading) {
        return;
      }
      await wait(100);
    }
    throw new Error('Timed out waiting for slash menu to finish loading.');
  };
  const collectItems = () => Array.from(
    container.querySelectorAll('.opencodian-slash-command-menu-item'),
    (item) => ({
      title: item.querySelector('.opencodian-slash-command-menu-title')?.textContent ?? '',
      badges: Array.from(
        item.querySelectorAll('.opencodian-slash-command-menu-badge'),
        (badge) => ({
          text: badge.textContent ?? '',
          className: badge.className,
        }),
      ),
      text: item.textContent ?? '',
    }),
  );
  const render = async (mode, value) => {
    plugin.settings.slashCommandSkillMode = mode;
    textarea.focus();
    textarea.value = '';
    textarea.setSelectionRange(0, 0);
    dispatchInput();
    await wait(150);
    textarea.value = value;
    textarea.setSelectionRange(value.length, value.length);
    dispatchInput();
    await waitForMenuIdle();
    await wait(200);
    return collectItems();
  };
  const hasCommandBadge = (item) => item.badges.some((badge) =>
    /\bopencodian-slash-command-menu-badge--(?:runtime|override|project)\b/.test(badge.className));
  const hasSkillBadge = (item) => item.badges.some((badge) =>
    /\bopencodian-slash-command-menu-badge--skill\b/.test(badge.className));
  const assert = (condition, message, detail) => {
    if (!condition) {
      throw new Error(`${message}: ${JSON.stringify(detail)}`);
    }
  };

  try {
    const directStart = await render('direct', '/');
    const directMid = await render('direct', 'hello /');
    const prefixedStart = await render('skills-command', '/');
    const prefixedMid = await render('skills-command', 'hello /');
    const explicitPrefixedMid = await render('skills-command', 'hello /skills ');

    assert(directStart.length > 0, 'direct start slash produced no menu items', directStart);
    assert(directMid.length > 0, 'direct mid-text slash produced no skill items', directMid);
    assert(
      directMid.every((item) => hasSkillBadge(item) && !hasCommandBadge(item)),
      'direct mid-text slash included non-skill menu items',
      directMid,
    );
    assert(
      prefixedStart.some((item) => item.title === '/skills'),
      'skills-command start slash did not expose /skills browser entry',
      prefixedStart,
    );
    assert(prefixedMid.length > 0, 'skills-command mid-text slash produced no prefixed skill items', prefixedMid);
    assert(
      prefixedMid.every((item) => hasSkillBadge(item) && !hasCommandBadge(item) && item.title.startsWith('/skills ')),
      'skills-command mid-text slash included commands or unprefixed skills',
      prefixedMid,
    );
    assert(
      explicitPrefixedMid.every((item) => hasSkillBadge(item) && item.title.startsWith('/skills ')),
      'explicit mid-text /skills prefix did not stay in prefixed skill mode',
      explicitPrefixedMid,
    );

    return JSON.stringify({
      ok: true,
      activeType: app.workspace.activeLeaf?.view?.getViewType?.() ?? null,
      counts: {
        directStart: directStart.length,
        directMid: directMid.length,
        prefixedStart: prefixedStart.length,
        prefixedMid: prefixedMid.length,
        explicitPrefixedMid: explicitPrefixedMid.length,
      },
      samples: {
        directMid: directMid.slice(0, 5).map((item) => item.title),
        prefixedMid: prefixedMid.slice(0, 5).map((item) => item.title),
        explicitPrefixedMid: explicitPrefixedMid.slice(0, 5).map((item) => item.title),
      },
    });
  } finally {
    plugin.settings.slashCommandSkillMode = originalSkillMode;
    textarea.value = '';
    textarea.setSelectionRange(0, 0);
    dispatchInput();
  }
})()
