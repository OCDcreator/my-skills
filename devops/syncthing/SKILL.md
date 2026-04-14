---
name: syncthing
description: >-
  Syncthing 同步排障与诊断。当 Syncthing 显示"同步中"不完成、"未同步"、
  同步卡住、删除失败循环等问题时使用。通过 REST API 诊断设备连接、
  文件夹状态、错误日志，定位删除死循环/权限问题/网络不通等根因并修复。
---

# Syncthing 排障

通过 REST API 诊断 Syncthing 同步问题。

## 快速诊断

获取 API Key 并检查核心状态：

```bash
API_KEY=$(grep -o '<apikey>[^<]*</apikey>' ~/Library/Application\ Support/Syncthing/config.xml | sed 's/<apikey>//;s/<\/apikey>//')
```

按顺序检查以下三项：

1. **设备连接** — `rest/system/connections`，确认目标设备 `connected=true`
2. **文件夹状态** — `rest/db/status?folder=<id>`，查看 state/needFiles/needDeletes/error
3. **错误日志** — `rest/system/log`，过滤 "Failed" 关键词

## 常见问题模式

### 删除死循环（最常见）

**症状**：状态显示"同步中"永不停歇，completion 不是 100%

**诊断**：日志中出现大量 `Failed to sync: delete dir: directory has been deleted on a remote device but is not empty`

**根因**：A 端删除了目录，B 端残留空目录（含 macOS 扩展属性如 `com.apple.provenance`），Syncthing 反复尝试删除但失败，每小时重试一次

**修复**：
```bash
xattr -cr <残留目录路径>
rm -rf <残留目录路径>
```
然后触发重新扫描：`curl -s -X POST -H "X-API-Key: $API_KEY" "http://localhost:8384/rest/db/scan?folder=<id>"`

### 设备不在线

**症状**：目标设备 `connected=false`，lastDialStatus 有 timeout/refused 错误

**排查**：检查两台设备是否在同一局域网、防火墙是否放行 22000(TCP/QUIC) 和 22067(relay)

### 文件系统权限

**症状**：`permission denied` 错误

**修复**：检查 IgnorePerms 设置，或在文件夹配置中启用 `ignorePerms: true`

## API 速查

| 端点 | 用途 |
|------|------|
| `rest/system/status` | 运行时间、发现服务状态 |
| `rest/system/connections` | 所有设备连接详情 |
| `rest/system/log` | 完整日志 |
| `rest/config/devices` | 设备配置 |
| `rest/config/folders` | 文件夹配置 |
| `rest/db/status?folder=X` | 单文件夹同步状态 |
| `rest/db/completion?folder=X&device=Y` | 对某设备的完成度 |
| `rest/db/need?folder=X` | 待同步/待删除文件列表 |
| `rest/db/scan?folder=X` (POST) | 触发重新扫描 |

配置文件位置：`~/Library/Application Support/Syncthing/config.xml`
