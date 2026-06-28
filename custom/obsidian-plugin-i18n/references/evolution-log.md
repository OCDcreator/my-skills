# Evolution Log — obsidian-plugin-i18n

Append-only log of every skill-evolution run against this skill. Newest at the bottom. Never edit prior entries.

## 2026-06-29 — run against obsidian-plugin-i18n

Session context: 路线 A（i18n 插件协作）翻译 claudian 插件，过程中翻译破坏 main.js 导致插件崩溃，经多轮修复后收敛。CAPTURE 在主上下文执行，trace 字段 provenance = extracted（来自 in-context 对话与文件）。

- candidate: i18n 应用译文导致 main.js 崩溃 + node --check 预检 + autodebug 抓控制台
  verdict: discard
  reason: Gate 2 duplicate —— SKILL.md 244-278 行已在本次修复中完整写入（"⚠️ 路线 A 的关键安全规则" + "翻译后必须验证"节）
  gate: { g1: pass, g2: duplicate, g3: principle }
  recurrence: first

- candidate: 应让用户先还原（不要擅自找备份/覆盖 main.js）
  verdict: discard
  reason: 通用 agent 行为（破坏性操作需用户授权），非技能专属；SKILL.md "不覆盖原始 main.js" 规则已隐含覆盖
  gate: { g1: pass, g2: duplicate, g3: principle }
  recurrence: first

- candidate: memory.js save 的输入必须是【当前全部已翻译条目】，不是"本次新增"
  verdict: add_new
  reason: Gate 2 new（grep "save|stale|完整" 无此规则）；Gate 3 principle（数据一致性/正确性）。本次踩坑：save 189 条导致之前 47 条被误判 stale
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
  landed: SKILL.md "翻译记忆库"节第4步旁，标注 `<!-- 2026-06-29 add_new: LESSON#4 -->`

- candidate: 只翻用户可见的英文 UI 文案，跳过非英文/代码标识符/内部 i18n key
  verdict: strengthen
  reason: Gate 2 strengthen（第2步"清洗与过滤"已有"剔除非英文/代码表达式"但缺范围原则 + 两个真实陷阱：作者内置多语言样本、内部 i18n key settings.xxx）；Gate 3 principle（翻译正确性/避免破坏）
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first
  landed: SKILL.md 第2步"清洗与过滤"首条，标注 `<!-- 2026-06-29 strengthen: LESSON#5 -->`

Snapshot: SKILL.md.bak-2026-06-29 (18178 bytes pre-edit)
Files touched: SKILL.md (2 edits), references/evolution-log.md (created)
Dev Eval: N/A — 无 validator 脚本（技能是 markdown 指令，无 runtime）
Frontmatter: 未改动（无需重跑 catalog 生成器）
