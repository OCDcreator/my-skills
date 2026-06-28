#!/usr/bin/env node
/**
 * Obsidian 插件字符串提取器
 * 用法: node extract.js <main.js路径> [--lang <目标语言代码,默认zh-cn>]
 *
 * 输出 JSON 到 stdout，结构：
 * { plugin, count, entries: [{ match, method, original, quote, offset }] }
 *
 * 设计：覆盖 Obsidian 核心 API 的字符串暴露点，正确处理
 * 引号转义、模板字符串占位符、变量表达式过滤。
 */
"use strict";

const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
  console.error("用法: node extract.js <main.js路径> [--lang zh-cn]");
  process.exit(args.length === 0 ? 1 : 0);
}

const mainPath = args[0];
const langIdx = args.indexOf("--lang");
const targetLang = langIdx > -1 ? args[langIdx + 1] : "zh-cn";

if (!fs.existsSync(mainPath)) {
  console.error(`错误: 文件不存在: ${mainPath}`);
  process.exit(1);
}

const src = fs.readFileSync(mainPath, "utf-8");
const pluginDir = path.dirname(mainPath);
const manifestPath = path.join(pluginDir, "manifest.json");
let pluginId = "unknown", pluginVersion = "unknown";
try {
  const m = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  pluginId = m.id;
  pluginVersion = m.version;
} catch { /* 忽略 */ }

/**
 * 提取规则。每条 = { method, pattern }
 * pattern 必须捕获"字符串字面量的内容"，且匹配完整的方法调用。
 * 用函数调用前缀锁定，避免误匹配对象字段。
 *
 * 三种字符串字面量：双引号 "..."、单引号 '...'、模板 `...`
 */
const STRING = `(?:"((?:[^"\\\\]|\\\\.)*)"|'((?:[^'\\\\]|\\\\.)*)'|\`((?:[^\`\\\\]|\\\\.)*)\`)`;

const RULES = [
  // 函数调用类（锁定方法名前缀，避免误伤）
  { method: "setText",        pattern: new RegExp(`setText\\(\\s*${STRING}`, "g") },
  { method: "setDesc",        pattern: new RegExp(`setDesc\\(\\s*${STRING}`, "g") },
  { method: "setName",        pattern: new RegExp(`setName\\(\\s*${STRING}`, "g") },
  { method: "setPlaceholder", pattern: new RegExp(`setPlaceholder\\(\\s*${STRING}`, "g") },
  { method: "setTooltip",     pattern: new RegExp(`setTooltip\\(\\s*${STRING}`, "g") },
  { method: "setButtonText",  pattern: new RegExp(`setButtonText\\(\\s*${STRING}`, "g") },
  { method: "setHint",        pattern: new RegExp(`setHint\\(\\s*${STRING}`, "g") },
  { method: "setTitle",       pattern: new RegExp(`setTitle\\(\\s*${STRING}`, "g") },
  { method: "appendText",     pattern: new RegExp(`appendText\\(\\s*${STRING}`, "g") },
  { method: "addHeading",     pattern: new RegExp(`addHeading\\(\\s*${STRING}`, "g") },
  { method: "renderMarkdown", pattern: new RegExp(`renderMarkdown\\(\\s*${STRING}`, "g") },
  // Notice / Error 消息
  { method: "Notice",         pattern: new RegExp(`new\\s+Notice\\(\\s*${STRING}`, "g") },
  { method: "Error",          pattern: new RegExp(`new\\s+Error\\(\\s*${STRING}`, "g") },
];

// 对象字面量字段（name/description 等）—— 风险较高，单独宽松匹配
const FIELD_RULES = [
  { method: "field:name",        pattern: new RegExp(`\\bname\\s*:\\s*${STRING}`, "g") },
  { method: "field:description", pattern: new RegExp(`\\bdescription\\s*:\\s*${STRING}`, "g") },
  { method: "field:placeholder", pattern: new RegExp(`\\bplaceholder\\s*:\\s*${STRING}`, "g") },
  { method: "field:tooltip",     pattern: new RegExp(`\\btooltip\\s*:\\s*${STRING}`, "g") },
];

function decodeCapture(matchArr) {
  // STRING 里三组捕获分别对应 " ' `，取非 undefined 的那个
  const raw = matchArr[1] !== undefined ? matchArr[1]
            : matchArr[2] !== undefined ? matchArr[2]
            : matchArr[3];
  const quote = matchArr[1] !== undefined ? '"'
              : matchArr[2] !== undefined ? "'"
              : "`";
  // 反转义常见转义（\n \t \" \\ 等），便于翻译阅读；写回时由调用方重新转义
  const decoded = raw
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    .replace(/\\\\/g, "\\");
  return { original: decoded, quote };
}

/**
 * 过滤：剔除不该翻译的字符串。
 * 返回 true 表示"应跳过"。
 */
function shouldSkip(original) {
  const s = original.trim();
  if (s === "") return true;
  // 纯数字
  if (/^\d+(\.\d+)?$/.test(s)) return true;
  // 单字符 / 纯标点
  if (s.length <= 2 && /[\s\W]/.test(s)) return true;
  // 纯代码标识符（变量名、camelCase 标识，无空格且含下划线/驼峰）
  // 如 "autoSaveInterval" —— 这通常是 setText(this.config.autoSaveInterval) 之类漏抓的
  if (/^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(s) && !/[A-Z]/.test(s.slice(1)) === false && !s.includes(" ")) {
    // 但允许 "Auto Backup" 这种多词，所以只剔除无空格的纯标识符
    if (!/\s/.test(s) && /^[a-z][a-zA-Z0-9_$]*$/.test(s)) return true;
  }
  // 已包含中文 —— 可能已部分翻译，保留但标记
  // 完全是目标语言的也跳过（避免重复翻译）
  // 这里宽松处理：含 CJK 的字符串保留，交给人工/agent 判断
  return false;
}

const entries = [];
const seen = new Set(); // 去重：(method, original)

function collect(ruleSet) {
  for (const rule of ruleSet) {
    rule.pattern.lastIndex = 0;
    let m;
    while ((m = rule.pattern.exec(src)) !== null) {
      const { original, quote } = decodeCapture(m);
      if (shouldSkip(original)) continue;
      const key = `${rule.method}\u0000${original}`;
      if (seen.has(key)) continue;
      seen.add(key);
      entries.push({
        method: rule.method,
        original,
        quote,
        offset: m.index,
        // 还原"完整匹配片段"便于回写定位
        match: m[0].trim(),
      });
    }
  }
}

collect(RULES);
collect(FIELD_RULES);

const result = {
  plugin: pluginId,
  version: pluginVersion,
  sourceFile: path.basename(mainPath),
  sourceLanguage: "en",
  targetLanguage: targetLang,
  extractedAt: new Date().toISOString().slice(0, 10),
  count: entries.length,
  entries,
};

const out = JSON.stringify(result, null, 2);
process.stdout.write(out);
process.stderr.write(`\n[extract] ${pluginId}@${pluginVersion}: 提取到 ${entries.length} 条候选字符串\n`);
