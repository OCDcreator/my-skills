# 多机 PicList 配置同步

PicList 已在 Windows 和 Mac 两端配好同一图床。本文件记录配置同步方法，**不含真实 token**（token 在 `/admin` 轮换后按此方法同步到所有机器）。新机器装 PicList、token 轮换、配置漂移排查时读这里。

## 配置文件位置

| 平台 | 路径 |
|------|------|
| Windows | `C:\Users\<user>\AppData\Roaming\piclist\data.json` |
| Mac | `~/Library/Application Support/piclist/data.json` |
| Linux | `~/.config/piclist/data.json`（PicList AppImage 解压后） |

App 本体安装位置不影响配置：`/Applications/PicList.app`（Mac）、开始菜单（Windows）。配置目录名一律小写 `piclist`。

## 需要同步的关键字段

从一台已配好的机器 `data.json` 提取，注入到新机器的同名文件：

| 字段 | 路径（data.json 内） | 含义 |
|------|---------------------|------|
| 默认图床 | `picBed.current` | 值应为 `lskyplist` |
| 默认上传器 | `picBed.uploader` | 值应为 `lskyplist` |
| **lskyplist 床配置** | `picBed.lskyplist` | 整段：`_configName=picltreen` / `host=https://pic.ltreen.tech` / `token=Bearer 1|...` / `strategyId="1"` |
| webp 转换 | `buildIn.compress.isConvert` / `convertFormat` / `quality` / `isRemoveExif` | `true` / `webp` / `90` / `true` |

## 刻意不同步的字段

每台机器保持自己的本地设置，**不要**从源机覆盖：

| 字段 | 为什么不同步 |
|------|------------|
| `picBed.lskyplist._id` / `_createdAt` / `_updatedAt` | 源机生成的时间戳和 uuid，新机保留自己的或新生成 |
| `settings.shortKey` | 快捷键键位两机可不同（Mac 上 `CommandOrControl` 解析为 Cmd） |
| `settings.server.host` / `port` | 监听地址两机独立（都是 `0.0.0.0:36677` 但语义上是本机设置） |
| `settings.autoStart` | 开机自启是本机选择 |
| `settings.sync` | PicList 的跨设备同步设置（含 GitHub token 等），**绝对不要**跨机器复制，会引发循环同步 |
| `settings.miniWindowPosition` 等 GUI 状态 | 窗口位置、主题等本机偏好 |
| `picBed.list` | 床列表是 PicList 版本决定的，新机装的新版可能床不一样，别覆盖 |
| `picBed.smms` / 其它床凭据 | 各机自己的其它床凭据 |

## 同步流程（Windows → Mac 为例）

非破坏性、可回滚。核心是「**先备份目标 → 校验新配置 → 停服务 → 替换 → 重启**」。

### 1. 源机导出关键字段

```powershell
# Windows 上读
$cfg = Get-Content "$env:APPDATA\piclist\data.json" -Raw | ConvertFrom-Json
$cfg.picBed.lskyplist | ConvertTo-Json -Depth 6
$cfg.buildIn.compress | ConvertTo-Json -Depth 6
```

### 2. 目标机拉取现有 data.json，字段级合并

把目标机当前 `data.json` 拉到本地，用 PowerShell 做 PSCustomObject 字段级合并（不要整文件覆盖，避免误带 `settings.sync`）。要点：
- `picBed.lskyplist` 整段注入（用深拷贝避免对象引用污染源机活配置）
- `picBed.current` / `picBed.uploader` 设为 `lskyplist`
- `buildIn.compress` 整段注入
- `settings` 里只追加 `pasteStyle=HTML` / `autoRename=true` 等，不动 `server` / `shortKey` / `autoStart`
- **绝不**复制 `settings.sync`
- 顶层 `needReload=true`，让 PicList 重启后重新加载

输出 UTF-8 无 BOM + LF 换行 + 合理缩进。PicList 不挑缩进，但 LF 是 Unix 习惯。

### 3. 端到端 SHA256 校验

合并文件写到本地后，scp 到目标机 `/tmp/`，对比本地 SHA256 与目标机 SHA256 一致，再 `python3 -c "json.load(...)"` 校验 JSON 合法。**只有校验通过才碰活配置文件**。

### 4. 停 PicList → 备份 → 替换 → 重启

顺序很重要：PicList 在跑时直接覆盖 `data.json` 可能被进程内存状态写回覆盖。

```bash
# Mac（base64 模式避免引号地狱）
DATA="$HOME/Library/Application Support/piclist/data.json"
BAK="$DATA.bak-$(date +%Y%m%d-%H%M%S)"

# 路径安全守卫
case "$DATA" in
  "$HOME/Library/Application Support/piclist/"*) : ;;
  *) echo "Refusing unsafe path"; exit 2 ;;
esac

# 优雅退出
osascript -e 'tell application "PicList" to quit'
sleep 3
pkill -f "PicList.app" 2>/dev/null  # 清残留 helper
sleep 2
pgrep -af "[p]iclist" && { echo "still running, abort"; exit 3; }

cp -p "$DATA" "$BAK"          # 备份原配置
cp /tmp/piclist-data-merged.json "$DATA"   # 落盘新配置
open -a PicList               # 重启
sleep 5
pgrep -af "[p]iclist"          # 确认起来了
```

Windows 对应：任务管理器结束 `piclist.exe` → 备份 → 覆盖 `data.json` → 从开始菜单重启 PicList。

### 5. 实测验证（必做）

光配置对了不算数，必须真实上传一张图验证：

```bash
# Mac：造一张测试 PNG，POST 到本机 PicList
curl -sS -X POST http://127.0.0.1:36677/upload \
  -H "Content-Type: application/json" \
  -d '{"list":["/tmp/probe.png"]}'
```

确认三点：
1. `success: true`
2. `fullResult[0].type == "lskyplist"`（走对了床）
3. 返回 URL 扩展名是 `.webp`（说明 webp 转换生效）

任何一点不对，回滚 `$BAK` 并排查。

## token 轮换时的多机更新

token 在 `/admin` 重新生成后，**所有**装了 PicList 的机器都要更新 `picBed.lskyplist.token`。流程：

1. 后台 `/admin` → 个人设置 → 生成新 token
2. 在每台机器上：
   - 停 PicList
   - 编辑 `data.json`，替换 `picBed.lskyplist.token` 值（保留 `Bearer 1|` 前缀）
   - 重启 PicList
   - 实测上传一张图验证 401 消失

**容易忘的点**：轮换后只更了 Windows 忘了 Mac，下次 Mac 上传会 401。建议轮换时立即在两机都测一次。

## 配置漂移排查

两机行为不一致（比如 Windows 转 webp 但 Mac 不转）时，逐项对比两个 `data.json`：

```bash
# 比较关键字段（Mac 上跑，Windows 的拉过来）
diff <(jq '.buildIn.compress | {isConvert, convertFormat, quality, isRemoveExif}' mac-data.json) \
     <(jq '.buildIn.compress | {isConvert, convertFormat, quality, isRemoveExif}' win-data.json)
diff <(jq '.picBed | {current, uploader, lskyplist: {host, strategyId, _configName}}' mac-data.json) \
     <(jq '.picBed | {current, uploader, lskyplist: {host, strategyId, _configName}}' win-data.json)
```

差异点通常就是行为不一致的根因。

## 备份保留

每次改 `data.json` 前都备份成 `data.json.bak-<时间戳>`，不要覆盖旧备份。回滚时取最近的 bak，不要从 git 拉（data.json 不该入库，含 token）。

**data.json 不入库**：本仓库 `.gitignore` 应排除所有平台的 `piclist/data.json` 路径；如果意外入库了，立即从历史清除并轮换 token。
