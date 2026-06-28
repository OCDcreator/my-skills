#!/usr/bin/env node
/**
 * 翻译记忆库管理（obsidian-plugin-i18n 技能）
 *
 * 用法:
 *   node memory.js load <pluginId> <version>
 *     读记忆库，输出 { entries:[{key,translation,status}], stats } 到 stdout
 *
 *   node memory.js diff <pluginId> <version> <currentKeysJsonFile>
 *     输入"当前提取到的 key 列表"（JSON 文件，见下），与记忆库比对，
 *     输出 { reuse:[{key,translation}], stale:[{key,translation}], need:[{key}], stats }
 *       reuse = 记忆库里有且当前还在用 → 复用译文，不用重译
 *       stale = 记忆库里有但当前已消失 → 失效 key，标记留存（不删，下次可能回来）
 *       need  = 当前有但记忆库没有     → 需新翻译
 *
 *   node memory.js save <pluginId> <version> <translationsJsonFile>
 *     输入"当前 key→译文"（JSON 文件，见下），合并进记忆库：
 *       当前条目 → status=active（新增或更新译文+时间戳）
 *       记忆库有但当前没有 → status=stale（保留译文，标记失效）
 *
 * currentKeysJsonFile 格式：     { "pluginId":"...", "keys":["key1","key2",...] }
 *                                （key 来自 zh-cn.json 的 dict key 或 extract.js 的 original）
 * translationsJsonFile 格式：    { "pluginId":"...", "targetLanguage":"zh-cn",
 *                                  "entries":[ {"key":"...","translation":"..."}, ... ] }
 *
 * 记忆库存储：本脚本同级的 ../memory/<pluginId>@<version>.json
 * （集中存技能目录，插件更新不会丢；version 固定用主版本如 2.0.10）
 *
 * 设计：纯文件操作，无外部依赖；记忆库按 key 原样索引（不区分 Notice()/name: 形态）。
 */
"use strict";

const fs = require("fs");
const path = require("path");

const MEMORY_DIR = path.resolve(__dirname, "..", "memory");

function memoryPath(pluginId, version) {
  // version 形如 "2.0.10"；文件名里的 @ 分隔，避免和路径冲突
  const safe = String(pluginId).replace(/[\\/:*?"<>|]/g, "_");
  return path.join(MEMORY_DIR, `${safe}@${version}.json`);
}

function readMemory(pluginId, version) {
  const p = memoryPath(pluginId, version);
  if (!fs.existsSync(p)) return null;
  try {
    const data = JSON.parse(fs.readFileSync(p, "utf-8"));
    if (!Array.isArray(data.entries)) data.entries = [];
    return data;
  } catch (e) {
    console.error(`[memory] 读取失败 ${p}: ${e.message}`);
    return null;
  }
}

function writeMemory(pluginId, version, data) {
  if (!fs.existsSync(MEMORY_DIR)) fs.mkdirSync(MEMORY_DIR, { recursive: true });
  const p = memoryPath(pluginId, version);
  fs.writeFileSync(p, JSON.stringify(data, null, 2), "utf-8");
  return p;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

// ---- 子命令：load ----
function cmdLoad(pluginId, version) {
  const mem = readMemory(pluginId, version);
  if (!mem) {
    console.log(JSON.stringify({ entries: [], stats: { total: 0, active: 0, stale: 0, exists: false } }));
    return;
  }
  const active = mem.entries.filter((e) => e.status === "active").length;
  const stale = mem.entries.filter((e) => e.status === "stale").length;
  console.log(JSON.stringify({
    entries: mem.entries,
    stats: { total: mem.entries.length, active, stale, exists: true,
             lastPluginVersion: mem.lastPluginVersion, updatedAt: mem.updatedAt }
  }));
}

// ---- 子命令：diff ----
function cmdDiff(pluginId, version, currentKeysFile) {
  const cur = JSON.parse(fs.readFileSync(currentKeysFile, "utf-8"));
  const currentKeys = Array.isArray(cur.keys) ? cur.keys : [];
  const mem = readMemory(pluginId, version);
  const memEntries = mem ? mem.entries : [];
  const memByKey = new Map();
  for (const e of memEntries) memByKey.set(e.key, e);

  const reuse = [];   // 记忆库有 + 当前在用
  const need = [];    // 当前有 + 记忆库没有
  const curSet = new Set(currentKeys);
  for (const k of currentKeys) {
    const m = memByKey.get(k);
    if (m && m.translation && m.status === "active") {
      reuse.push({ key: k, translation: m.translation });
    } else {
      need.push({ key: k });
    }
  }
  // stale = 记忆库里 active 但当前没出现
  const stale = [];
  for (const e of memEntries) {
    if (e.status === "active" && !curSet.has(e.key)) {
      stale.push({ key: e.key, translation: e.translation });
    }
  }

  console.log(JSON.stringify({
    reuse, stale, need,
    stats: {
      current: currentKeys.length, reuse: reuse.length,
      need: need.length, stale: stale.length
    }
  }));
  console.error(`[memory] diff: 当前 ${currentKeys.length} 条 → 复用 ${reuse.length} / 需翻 ${need.length} / 失效 ${stale.length}`);
}

// ---- 子命令：save ----
function cmdSave(pluginId, version, translationsFile) {
  const input = JSON.parse(fs.readFileSync(translationsFile, "utf-8"));
  const targetLang = input.targetLanguage || "zh-cn";
  const newEntries = Array.isArray(input.entries) ? input.entries : [];
  const curKeys = new Set(newEntries.map((e) => e.key));

  const mem = readMemory(pluginId, version) || {
    pluginId, lastPluginVersion: version, targetLanguage: targetLang,
    updatedAt: today(), entries: []
  };
  const byKey = new Map();
  for (const e of mem.entries) byKey.set(e.key, e);

  const ts = today();
  // 当前条目 → active（新增或更新）
  for (const e of newEntries) {
    const existing = byKey.get(e.key);
    byKey.set(e.key, {
      key: e.key,
      translation: e.translation,
      status: "active",
      updatedAt: ts,
      // 保留首次翻译时间
      createdAt: existing ? existing.createdAt : ts
    });
  }
  // 记忆库有但当前没有 → stale（保留译文，标记失效）
  for (const [k, e] of byKey) {
    if (!curKeys.has(k) && e.status === "active") {
      e.status = "stale";
      e.updatedAt = ts;
    }
  }

  const entries = Array.from(byKey.values());
  const data = {
    pluginId,
    lastPluginVersion: version,
    targetLanguage: targetLang,
    updatedAt: ts,
    entries
  };
  const p = writeMemory(pluginId, version, data);
  const active = entries.filter((e) => e.status === "active").length;
  const stale = entries.filter((e) => e.status === "stale").length;
  console.log(JSON.stringify({
    saved: p,
    stats: { total: entries.length, active, stale, updatedAt: ts }
  }));
  console.error(`[memory] saved ${p}: active ${active} / stale ${stale}`);
}

// ---- 入口 ----
const [cmd, pluginId, version, fileArg] = process.argv.slice(2);
if (!cmd || !pluginId || !version) {
  console.error("用法: node memory.js <load|diff|save> <pluginId> <version> [keysFile|translationsFile]");
  process.exit(1);
}
try {
  if (cmd === "load") cmdLoad(pluginId, version);
  else if (cmd === "diff") {
    if (!fileArg) { console.error("diff 需要 <currentKeysJsonFile>"); process.exit(1); }
    cmdDiff(pluginId, version, fileArg);
  } else if (cmd === "save") {
    if (!fileArg) { console.error("save 需要 <translationsJsonFile>"); process.exit(1); }
    cmdSave(pluginId, version, fileArg);
  } else {
    console.error(`未知命令: ${cmd}（应为 load/diff/save）`);
    process.exit(1);
  }
} catch (e) {
  console.error(`[memory] 错误: ${e.message}`);
  process.exit(1);
}
