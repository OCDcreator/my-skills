---
name: piclist-upload
description: >-
  Use when uploading images to the user's personal image host (pic.ltreen.tech,
  a Lsky Pro+ bed on fnOS reached via frp), migrating images embedded in
  Markdown/HTML files (remote CDN links like noedgeai/unsplash/imgur, or local
  paths) to that bed, getting image URLs/外链, or anything involving PicList
  upload, 图床, 图片上传, 图片外链, 批量传图, markdown 图片替换, markdown
  里图片迁移, 兰空/Lsky 直连 API, or uploading from a non-Windows machine
  (Mac/Linux). Always use this skill when the user mentions uploading pictures,
  image hosting, PicList, pic.ltreen.tech, Lsky/兰空图床, or wants to
  replace/migrate image links in documents — even if they don't name PicList
  explicitly.
---

# 上传图片到个人图床（pic.ltreen.tech）

把图片（本地文件、剪贴板、文档里引用的远程 URL）上传到个人图床 `https://pic.ltreen.tech`（兰空 Pro+ 2.4.1，部署在飞牛 NAS，frp 穿透阿里云 VPS）。日常走本地 PicList 客户端，没有 PicList 时走兰空直连 API。

## 先决定走哪条路径

| 场景 | 路径 | 为什么 |
|------|------|--------|
| 本机装了 PicList，批量/程序化上传，想要自动 webp | **PicList server API** | 客户端会转 webp + 清 EXIF，最省事 |
| 本机装了 PicList，单张截图快传 | **剪贴板快捷键** `Ctrl+Alt+P` | 不用开终端 |
| 没有 PicList（服务器 / 新机器 / 不想装），不在乎格式 | **兰空直连 API** | 公网 HTTPS，任何机器能跑 |
| 没有 PicList，但想要 webp | 兰空直连 API **+ 上传前自己转** | PicList 不在就不自动转 |
| Markdown/HTML 里远程 CDN 图批量迁移到图床 | **`migrate-md-images.ps1`** | 现成脚本，下载→上传→替换一气呵成 |

**关键差异**（实测 2026-06-22）：PicList 会把 png/jpg 在上传前转成 webp + 清 EXIF；兰空直连 API 只按 md5 重命名 + 按日期分目录，**不转格式、不清 EXIF**。两条路径都会自动 md5 重命名。

## 路径 1：PicList server API（推荐）

PicList 必须在运行（系统托盘有图标）。

```
POST http://127.0.0.1:36677/upload
Content-Type: application/json

{"list": ["C:\\absolute\\path\\img1.png", "C:\\path\\img2.jpg"]}
```

- `list` = **本机绝对路径**数组（不是 URL；远程图必须先下载到本机）
- 默认图床直接 POST；指定图床加 `?picbed=lskyplist&configName=picltreen`
- 返回 `result[i]` 与 `list[i]` **顺序对齐**——靠这个做链接替换
- 批量建议 ≤50 张/次，更多分批；`TimeoutSec` 每张给 3-5s

PowerShell：
```powershell
$body = @{ list = @("C:\path\a.png","C:\path\b.jpg") } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:36677/upload" -Method Post `
  -Body $body -ContentType "application/json" -TimeoutSec 180
$resp.result   # URL 数组，顺序与 list 一致
```

返回样例：
```json
{"success": true,
 "result": ["https://pic.ltreen.tech/uploads/20260615/abc.webp"],
 "fullResult": [{"imgUrl": "...", "fileName": "...", "type": "lskyplist"}]}
```

## 路径 2：剪贴板快捷键（单张交互）

`Ctrl+Alt+P` —— 上传剪贴板里的图（截图、复制的图）。返回格式按 PicList `pasteStyle`（当前 HTML）。

## 路径 3：兰空直连 API（不用 PicList）

公网 HTTPS 链路，Mac/Linux/服务器都能用。**必须带 `strategy_id=1`**，否则返回"服务异常"。

```bash
curl -X POST https://pic.ltreen.tech/api/v1/upload \
  -H "Authorization: Bearer 1|<40字符token>" \
  -F "file=@/path/img.png" -F "strategy_id=1"
```

返回的 URL 在 `data.links.url`，markdown 格式在 `data.links.markdown`。token 从已配好 PicList 的机器读：`<用户配置目录>/piclist/data.json` → `picBed.lskyplist.token`；token 格式 `Bearer 1|<40字符>`（Laravel Sanctum）。完整返回字段、Mac/Linux 上传函数、webp 转换对比见 `references/upload-paths.md`。

## 路径 4：迁移 Markdown/HTML 里的远程图片

OCR 产物（Doc2X 等）常引用远程 CDN 图（`cdn.noedgeai.com` 等），不稳定且会失效。现成脚本：

```powershell
pwsh -File custom/piclist-upload/scripts/migrate-md-images.ps1 -InputPath "文档.md"
# 默认输出 "文档.uploaded.md"；可用 -OutputPath 自定义
```

脚本流程：解析文档 → 提取所有远程图片 URL（**保留完整 URL 含查询参数**，`?x=&y=&w=&h=` 裁剪参数丢了会拿错图）→ 去重 → 下载到临时目录 → PicList 批量上传 → 建立「原 URL → 新 URL」映射 → 替换生成 `.uploaded.md`（**不改原文件**）→ 校验输出里原 CDN 域名引用应为 0。

会打印：找到 N 处引用 / M 张唯一 / 下载成功数 / 上传成功数 / 替换数 / 剩余原域名引用数。

## 多机使用（Windows + Mac 等）

PicList 已在 Windows 和 Mac 两端配好同一图床（lskyplist + webp 转换）。日常用法两机一致，都走 `http://127.0.0.1:36677/upload`。

**唯一长期负担**：token 在 `/admin` 轮换后，要**同时**更新所有装了 PicList 的机器的 `data.json`。配置同步方法（字段映射、备份、SHA 校验、不包含真实 token）见 `references/piclist-multi-machine.md`。

## 注意事项

- **strategyId**：兰空 Pro+ 上传**必须带** `strategy_id=1`。PicList 配置已含 `strategyId:"1"`，server 上传自动带；绕过 PicList 直连兰空 API 要手动加，否则返回"服务异常"。
- **自动转 webp**：仅 PicList 路径生效（png/jpg → .webp）。要保持原格式 → PicList 设置→图片处理 关掉「转 webp」。兰空直连 API 不转格式。
- **token**：`Bearer 1|<40字符>`（Laravel Sanctum）。失效 → 后台 `/admin` 重生成 + 更新 PicList 配置（多机都更）。
- **下载失败**：某些 CDN 防盗链。失败时**跳过该图不阻塞其他**，最终报告失败列表让用户决定。
- **原文件不动**：迁移永远生成新文件（`.uploaded.md`），保留原始。
- **PicList `list` 只吃本机路径**：Mac 上的图不能直接传给 Windows 的 PicList，因为 Windows 读不到 Mac 文件系统。跨机上传要么各自跑本地 PicList，要么走兰空直连 API。

## 排错

按链路层次从下往上诊断，详见 `references/troubleshooting.md`。快速对照：

| 现象 | 最可能的原因 |
|------|-------------|
| server connection refused | PicList 没运行 → 启动（系统托盘） |
| `{"success":false,"message":"服务异常..."}` | 飞牛 NAS 关机 / lsky-pro 容器挂 / 网络断 |
| 上传 401/未授权 | token 过期 → 后台重生成 + 更新所有机器配置 |
| 上传成功但图片 502/打不开 | frp 链路断：飞牛 frpc 或 VPS frps/nginx |
| md 里是本地图片路径 | 直接放 `list`，跳过下载步骤 |
| PicList 转成了 webp 但不想要 | `buildIn.compress` 设置，不是 bug，关掉即可 |

## 图床架构（理解链路，便于排错）

```
PicList(本机) → POST → pic.ltreen.tech:443 (VPS nginx 终止 SSL)
   → 127.0.0.1:18320 (frps tcp) → 飞牛 frpc → 飞牛 lsky-pro:8188 → 落盘 → 返回公网 URL
```

- **飞牛 NAS** `192.168.31.147`：docker 跑 `lsky-pro` + `lsky-mysql` + `frpc`，数据在 `/vol1/1000/lsky-pro/`
- **阿里云 VPS** `47.94.235.59`：nginx 反代（`pic.ltreen.tech.conf`）+ `frps`
- **域名**：`pic.ltreen.tech`（主域名 `ltreen.tech` 已绑 Pro+ license）
