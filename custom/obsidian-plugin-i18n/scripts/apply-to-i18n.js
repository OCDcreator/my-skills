#!/usr/bin/env node
/**
 * 把翻译结果回填到 i18n 插件的 lang/zh-cn.json（obsidian-plugin-i18n 技能）
 *
 * 用法:
 *   node apply-to-i18n.js <translationsJson> <zh-cn.json路径>
 *
 * translationsJson 格式（来自 agent 翻译 + 审核）:
 *   { "plugin":"...", "targetLanguage":"zh-cn",
 *     "entries":[ {"key":"setName(\"...\")", "translation":"...", "enabled":true}, ... ] }
 *   key    = zh-cn.json 里 dict 的 key（i18n 插件 AST 提取的调用片段，如 Notice("...") / name: "..."）
 *   translation = 纯目标语言译文（字符串字面量的新内容，不含外壳）
 *   enabled=false 的条目跳过（保持 value==key 原样）
 *
 * ⚠️ 关键（崩溃教训）：i18n 应用译文时是【整段替换】——拿 dict 的 key 去 main.js 里
 * 匹配整段，替换成 value。所以 value 必须保留 key 的"外壳"（方法名、括号、引号、
 * 模板变量 ${...}），只把里面的字符串内容换成译文。
 *   ✗ 错误：key=Notice("Failed to save") value="保存失败"  → 替换后 new X.保存失败; 崩
 *   ✓ 正确：key=Notice("Failed to save") value=Notice("保存失败") → 替换后 new X.Notice("保存失败")
 *
 * 行为:
 *   - 把 key 里的【第一个字符串字面量】替换成 translation，其余原样保留，作为 value
 *   - manifest / description 段保持不动
 *   - translation 为空 / == 原文字面量 / enabled=false → 跳过（保持 value==key）
 *   - 写回前备份原文件为 <zh-cn.json>.bak-<timestamp>
 *   - 输出 {applied, skipped, total, backupPath} 到 stdout
 *
 * 之后用户在 Obsidian 里点 i18n 插件的"应用译文"即可回写 main.js（插件原生支持 + 可还原）。
 */
"use strict";

const fs = require("fs");

const [translationsFile, zhcnPath] = process.argv.slice(2);
if (!translationsFile || !zhcnPath) {
  console.error("用法: node apply-to-i18n.js <translationsJson> <zh-cn.json路径>");
  process.exit(1);
}
if (!fs.existsSync(zhcnPath)) {
  console.error(`错误: zh-cn.json 不存在: ${zhcnPath}`);
  process.exit(1);
}

const input = JSON.parse(fs.readFileSync(translationsFile, "utf-8"));
const entries = Array.isArray(input.entries) ? input.entries : [];

const data = JSON.parse(fs.readFileSync(zhcnPath, "utf-8"));
if (!data || typeof data !== "object" || !data.dict) {
  console.error(`错误: ${zhcnPath} 不是合法的 i18n zh-cn.json（缺少 dict 段）`);
  process.exit(1);
}

/**
 * 把 key（调用片段）里的【第一个字符串字面量】替换成译文，返回带外壳的 value。
 * 支持 "..." '...' `...` 三种引号。找不到字面量则返回 null。
 * 例如:
 *   rewrap('Notice("Failed to save")', '保存失败') → 'Notice("保存失败")'
 *   rewrap('name: "Auto backup"', '自动备份')      → 'name: "自动备份"'
 *   rewrap('Notice(`skill ${n}`)', '技能 ${n}')    → 'Notice(`技能 ${n}`)'
 */
function rewrap(key, translation) {
  // 匹配第一个字符串字面量：双引号/单引号/反引号，处理反斜杠转义
  const m = key.match(/^([\s\S]*?)(["'`])((?:\\.|(?!\2).)*?)\2([\s\S]*)$/);
  if (!m) return null;
  const [, prefix, quote, /*content*/, suffix] = m;
  // 转义译文里的引号/反斜杠，避免破坏字面量（按所用引号类型转义）
  let safe = translation;
  if (quote === '"') safe = safe.replace(/[\\"]/g, (c) => "\\" + c);
  else if (quote === "'") safe = safe.replace(/[\\']/g, (c) => "\\" + c);
  else safe = safe.replace(/[\\`]/g, (c) => "\\" + c);  // 模板串不转义 ${}
  return `${prefix}${quote}${safe}${quote}${suffix}`;
}

// 取出 key 里第一个字符串字面量的【原始内容】（用于判等，避免重复翻译）
function literalContent(key) {
  const m = key.match(/["'`]((?:\\.|(?!(["'`])).)*?)["'`]/);
  return m ? m[1] : null;
}

let applied = 0, skipped = 0, notFound = 0, noLiteral = 0;
const transByKey = new Map();
for (const e of entries) {
  if (e.enabled === false) continue;            // 审核台取消勾选 → 跳过
  if (!e.translation) { skipped++; continue; }  // 空译文 → 跳过
  // 译文 == 原文字面量 → 视为未翻，跳过
  const orig = literalContent(e.key);
  if (orig !== null && e.translation === orig) { skipped++; continue; }
  transByKey.set(e.key, e.translation);
}

for (const key of Object.keys(data.dict)) {
  if (!transByKey.has(key)) continue;
  const value = rewrap(key, transByKey.get(key));
  if (value === null) { noLiteral++; continue; }  // key 里找不到字符串字面量 → 跳过（安全）
  data.dict[key] = value;
  applied++;
}
// 翻译结果里有但 zh-cn.json dict 里没有的 key（提取源不一致）
for (const key of transByKey.keys()) {
  if (!(key in data.dict)) notFound++;
}

const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const backupPath = `${zhcnPath}.bak-${ts}`;
fs.writeFileSync(backupPath, JSON.stringify(data, null, 2), "utf-8");
fs.writeFileSync(zhcnPath, JSON.stringify(data, null, 4) + "\n", "utf-8");

console.log(JSON.stringify({ applied, skipped, noLiteral, notFound, total: Object.keys(data.dict).length, backupPath }));
console.error(`[apply-to-i18n] 已回填 ${applied} 条，跳过 ${skipped}，无字面量 ${noLiteral}，未匹配 ${notFound}；备份 ${backupPath}`);
