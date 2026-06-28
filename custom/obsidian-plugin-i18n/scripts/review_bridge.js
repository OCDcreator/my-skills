#!/usr/bin/env node
/**
 * review_bridge.js — agent 与 review_gui.exe 之间的桥
 *
 * 用法（被 skill/agent 调用）：
 *   node review_bridge.js <review_in.json> [review_out.json]
 *
 * 流程：
 *   1. 校验输入 JSON 存在
 *   2. spawn review_gui.exe（带 REVIEW_IN/REVIEW_OUT 环境变量）
 *   3. 阻塞等待 exe 退出（人在窗口里操作）
 *   4. 读取 out.json，校验 status，打印结果摘要
 *   5. 退出码：0=已导出(applied)，1=用户取消(cancelled)，2=出错
 *
 * agent 拿到 stdout 的摘要后，据 enabled/translation 字段执行写回 main.js。
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const args = process.argv.slice(2);
if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    console.error("用法: node review_bridge.js <review_in.json> [review_out.json]");
    console.error("  review_in.json  — 待审核数据（由 extract.js 产出后转换）");
    console.error("  review_out.json — 人工审核结果（默认写到 in 同目录的 review_out.json）");
    process.exit(args.length === 0 ? 2 : 0);
}

const inPath = path.resolve(args[0]);
const outPath = path.resolve(args[1] || path.join(path.dirname(inPath), "review_out.json"));

// 定位 review_gui 二进制：按平台选对的
//   Windows → review_gui.exe
//   macOS (arm64) → review_gui-macos-arm64
//   macOS (x64)   → review_gui-macos-x64  (需另行编译)
//   Linux        → review_gui-linux      (需另行编译)
const BIN_DIR = path.join(__dirname, "..", "bin");
let binName;
if (process.platform === "win32") {
    binName = "review_gui.exe";
} else if (process.platform === "darwin") {
    binName = process.arch === "arm64"
        ? "review_gui-macos-arm64"
        : "review_gui-macos-x64";
} else {
    binName = "review_gui-linux";
}
const candidates = [
    path.join(BIN_DIR, binName),
    path.join(__dirname, binName),
    path.join(process.cwd(), binName),
];
const exePath = candidates.find(p => fs.existsSync(p));

if (!fs.existsSync(inPath)) {
    console.error(`[review_bridge] 输入文件不存在: ${inPath}`);
    process.exit(2);
}
if (!exePath) {
    console.error(`[review_bridge] 找不到 ${binName} (平台: ${process.platform}/${process.arch})`);
    console.error(`  尝试过: ${candidates.join(", ")}`);
    console.error("  请先编译对应平台的二进制（见 review_gui/build_review_gui.bat / .sh）");
    process.exit(2);
}

// 读输入，统计待审核条数（给日志用）
let inData;
try {
    inData = JSON.parse(fs.readFileSync(inPath, "utf8"));
} catch (e) {
    console.error(`[review_bridge] 输入 JSON 解析失败: ${e.message}`);
    process.exit(2);
}
const totalCount = Array.isArray(inData.entries) ? inData.entries.length : 0;
process.stderr.write(`[review_bridge] 启动审核台：${inData.plugin || "?"}@${inData.version || "?"}，${totalCount} 条待审\n`);
process.stderr.write(`[review_bridge] exe: ${exePath}\n`);
process.stderr.write(`[review_bridge] 请在弹出的窗口里操作，完成后关闭窗口\n`);

// Unix 平台确保二进制有执行权限（跨机器拷贝可能丢失 +x）
if (process.platform !== "win32") {
    try { fs.chmodSync(exePath, 0o755); } catch (e) { /* 忽略 */ }
}

// spawn：GUI 程序，detached=false 让我们等它
const child = spawn(exePath, [], {
    env: {
        ...process.env,
        REVIEW_IN: inPath,
        REVIEW_OUT: outPath,
    },
    windowsHide: false,
    stdio: ["ignore", "inherit", "inherit"],
});

child.on("error", (err) => {
    console.error(`[review_bridge] 启动 exe 失败: ${err.message}`);
    process.exit(2);
});

child.on("exit", (code, signal) => {
    // exe 退出后，读取 out.json
    if (!fs.existsSync(outPath)) {
        console.error(`[review_bridge] exe 退出但未生成输出: ${outPath}`);
        process.exit(2);
    }

    let out;
    try {
        out = JSON.parse(fs.readFileSync(outPath, "utf8"));
    } catch (e) {
        console.error(`[review_bridge] 输出 JSON 解析失败: ${e.message}`);
        process.exit(2);
    }

    const enabledEntries = (out.entries || []).filter(e => e.enabled);
    const skippedCount = (out.entries || []).length - enabledEntries.length;

    // stdout 输出结构化摘要（agent 读这个）
    const summary = {
        status: out.status,           // applied | cancelled
        plugin: out.plugin,
        version: out.version,
        targetLanguage: out.targetLanguage,
        total: (out.entries || []).length,
        enabled: enabledEntries.length,
        skipped: skippedCount,
        // 只返回 enabled 的（agent 实际写回用的就是这些）
        entries: enabledEntries.map(e => ({
            id: e.id,
            original: e.original,
            translation: e.translation,
        })),
        outPath: outPath,
    };
    process.stdout.write(JSON.stringify(summary, null, 2));

    process.stderr.write(`\n[review_bridge] 完成：status=${out.status}，启用 ${enabledEntries.length}/${(out.entries||[]).length}，跳过 ${skippedCount}\n`);

    process.exit(out.status === "applied" ? 0 : 1);
});
