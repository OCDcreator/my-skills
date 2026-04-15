---
name: syncthing
description: >-
  Use when diagnosing Syncthing sync failures: stuck syncing, out of sync,
  0% completion between Windows and macOS, folder errors, `.stignore` ignore
  rule surprises, Windows reserved names such as aux/con/prn/nul/com/lpt,
  delete-dir not-empty loops, permission denied, or device connection problems.
---

# Syncthing 排障

通过 REST API 先取证再修复。Syncthing 问题常见于多端状态不一致，尤其是 Windows/macOS 文件名规则、`.stignore` 匹配顺序、版本目录残留和远端未连接。

## 官方依据

优先引用官方文档，避免靠记忆猜规则：

| 主题 | 文档 |
|------|------|
| REST API 与 `X-API-Key` | https://docs.syncthing.net/dev/rest.html |
| 忽略规则、首个匹配生效、`.stignore` 不同步 | https://docs.syncthing.net/users/ignoring.html |
| 设备连接 | https://docs.syncthing.net/rest/system-connections-get.html |
| 文件夹状态 | https://docs.syncthing.net/rest/db-status-get.html |
| 完成度与 `remoteState` | https://docs.syncthing.net/rest/db-completion-get.html |
| 待同步列表 | https://docs.syncthing.net/rest/db-need-get.html |
| 文件夹错误 | https://docs.syncthing.net/rest/folder-errors-get.html |
| 当前加载的忽略规则 | https://docs.syncthing.net/rest/db-ignores-get.html |
| 触发重扫 | https://docs.syncthing.net/rest/db-scan-post.html |

## 快速诊断

先定位配置文件和 API Key，再按设备、文件夹、具体错误逐层缩小范围。

**macOS：**

```bash
API_KEY=$(grep -o '<apikey>[^<]*</apikey>' ~/Library/Application\ Support/Syncthing/config.xml | sed 's/<apikey>//;s/<\/apikey>//')
```

**Windows PowerShell：**

```powershell
[xml]$cfg = Get-Content "$env:LOCALAPPDATA\Syncthing\config.xml"
$api = $cfg.configuration.gui.apikey
$headers = @{ 'X-API-Key' = $api }
```

**检查顺序：**

1. `GET /rest/system/connections`：目标设备是否 `connected=true`，是否 paused。
2. `GET /rest/config/folders` 或配置文件：确认 folder ID、label、path、共享设备。
3. `GET /rest/db/status?folder=<id>`：看 `state`、`needFiles`、`needDeletes`、`needBytes`、`pullErrors`。
4. `GET /rest/folder/errors?folder=<id>`：直接看扫描/拉取失败路径和错误文本。
5. `GET /rest/db/need?folder=<id>&page=1&perpage=50`：看是哪台设备修改的哪些条目还没落地。
6. `GET /rest/db/completion?folder=<id>&device=<device-id>`：判断对端是否 `remoteState=valid`，完成度是否 100%。
7. 如果怀疑 `.stignore`：`GET /rest/db/ignores?folder=<id>`，对照 `ignore` 和 `expanded` 看当前加载规则。

## 常见问题模式

### Windows 保留名阻塞同步

**症状：** Windows 端 `folder/errors` 出现 `name is invalid, contains Windows reserved name: "aux"`，或者 Windows 与 macOS 间完成度 0%/非 100%。

**保留名：** `CON`、`PRN`、`AUX`、`NUL`、`COM1`-`COM9`、`LPT1`-`LPT9`。按基本名判断，`aux`、`aux.txt`、`AUX` 都需要当成风险。

**关键规则：** Syncthing 忽略规则是首个匹配生效。`.stignore` 自身不会同步到其他设备，所以 Windows 和 Mac 需要各自检查/写入同等规则。

**高发坑：** 如果 `!some/path/**` 例外规则排在 `some/path/aux` 排除规则前面，例外会先命中，后面的 `aux` 排除永远不会生效。

**修复原则：** 把具体保留名排除放在会包含它的 `!` 例外规则之前，并同时写目录本身和递归内容。

```text
# 先排除 Windows 保留文件名，避免被后续例外提前命中
custom-project/opencodian/reference-projects/claudian/src/providers/claude/aux
custom-project/opencodian/reference-projects/claudian/src/providers/claude/aux/**

# 再放例外
!custom-project/opencodian/reference-projects/
!custom-project/opencodian/reference-projects/**
```

**验证：**

1. `GET /rest/db/ignores?folder=<id>`：确认 `aux` 排除出现在 `!` 例外前。
2. `POST /rest/db/scan?folder=<id>`：触发重扫；大库可能需要等待。
3. `GET /rest/folder/errors?folder=<id>`：应为 `errors=null` 或空列表。
4. `GET /rest/db/status?folder=<id>`：应为 `needFiles=0`、`needDeletes=0`、`pullErrors=0`。
5. `GET /rest/db/completion?folder=<id>&device=<device-id>`：目标设备应为 `completion=100` 且 `remoteState=valid`。

**扫描 macOS 活跃目录中的保留名：**

```bash
python3 - <<'PY'
import os
root = '/Volumes/SDD2T/obsidian-vault-write'
reserved = {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d != '.stversions']
    for name in dirnames:
        if os.path.splitext(name)[0].upper() in reserved:
            print(os.path.join(dirpath, name))
PY
```

`.stversions` 里的保留名通常只是本机历史版本残留，不参与当前活跃同步树。先区分活跃目录和 `.stversions`，不要把历史残留误判成当前同步失败根因。

### 删除死循环

**症状：** 状态一直显示同步中，completion 不是 100%，日志出现 `Failed to sync: delete dir: directory has been deleted on a remote device but is not empty`。

**根因：** A 端删除目录，B 端残留空目录或 macOS 扩展属性，如 `com.apple.provenance`，Syncthing 反复尝试删除但失败。

**修复：**

```bash
xattr -cr <残留目录路径>
rm -rf <残留目录路径>
curl -s -X POST -H "X-API-Key: $API_KEY" "http://localhost:8384/rest/db/scan?folder=<id>"
```

### 设备不在线

**症状：** `GET /rest/system/connections` 中目标设备 `connected=false`，completion 的 `remoteState=unknown`。

**排查：** 确认两台设备在线、未暂停、同一局域网可达，防火墙放行 `22000` TCP/QUIC 和 `22067` relay。

### 文件系统权限

**症状：** `folder/errors` 或日志中有 `permission denied`。

**修复：** 检查路径权限、Syncthing 运行用户、folder 的 `ignorePerms` 设置。只在确认权限同步没有意义时启用 `ignorePerms=true`。

## 输出格式

排障完成时简要报告：

- 根因：引用具体错误、路径、设备或规则。
- 改动：列出修改的 `.stignore` 或清理的残留目录。
- 验证：给出 `state`、`needFiles`、`needDeletes`、`pullErrors/errors`、`completion`、`remoteState`。
- 风险：说明 `.stignore` 是否已同步到每台设备、`.stversions` 是否只是历史残留。
