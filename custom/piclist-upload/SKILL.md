---
name: piclist-upload
description: >-
  Use when uploading images to the user's personal image host (pic.ltreen.tech,
  a Lsky Pro+ bed on fnOS reached via frp), migrating images embedded in
  Markdown/HTML files (remote CDN links like noedgeai/unsplash/imgur, or local
  paths) to that bed through the local PicList client, getting image URLs/外链,
  or anything involving PicList upload, 图床, 图片上传, 图片外链, 批量传图,
  markdown 图片替换, markdown 里图片迁移. Always use this skill when the user
  mentions uploading pictures, image hosting, PicList, pic.ltreen.tech, Lsky/
  兰空图床, or wants to replace/migrate image links in documents — even if they
  don't name PicList explicitly.
---

# 通过 PicList 上传图片到个人图床

把图片（本地文件、剪贴板、或文档里引用的远程 URL）通过本地 PicList 客户端上传到用户的个人图床 `https://pic.ltreen.tech`（兰空 Pro+ 2.4.1，部署在飞牛 NAS，frp 穿透阿里云 VPS）。PicList 已配置为默认图床，开箱即用。

## 环境现状（已配好，无需重配）

| 项 | 值 |
|---|---|
| PicList server | `http://127.0.0.1:36677`（本机，已启用） |
| 图床 | 兰空 Pro+ 2.4.1，`https://pic.ltreen.tech` |
| PicList 默认图床 | `lskyplist`（已切为默认） |
| configName | `picltreen` |
| 上传接口（PicList 侧） | `POST /upload` |
| strategyId | `1`（本地储存） |
| PicList 图片处理 | 自动转 webp（`buildIn.compress.isConvert=true`）+ 去 EXIF |
| 后台管理 | `https://pic.ltreen.tech/admin` |

**前置**：PicList 必须在运行（系统托盘有图标）。server 无响应就提示用户启动 PicList。

## 三种上传方式

### 1. PicList server API（程序化/批量，推荐脚本与迁移用）

```
POST http://127.0.0.1:36677/upload
Content-Type: application/json

{"list": ["C:\\absolute\\path\\img1.png", "C:\\path\\img2.jpg"]}
```

- `list` = **本地文件绝对路径**数组（不是 URL；远程图必须先下载到本地）。
- 默认图床：直接 POST。指定图床：`?picbed=lskyplist&configName=picltreen`。
- 返回 `result[i]` 与 `list[i]` **顺序对齐**——靠这个做链接替换。
- PicList 按其 `buildIn` 处理（默认转 webp + 清 EXIF + 压缩）。

返回样例：
```json
{"success": true,
 "result": ["https://pic.ltreen.tech/uploads/20260615/abc.webp"],
 "fullResult": [{"imgUrl": "...", "fileName": "...", "type": "lskyplist"}]}
```

PowerShell：
```powershell
$body = @{ list = @("C:\path\a.png","C:\path\b.jpg") } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:36677/upload" -Method Post `
  -Body $body -ContentType "application/json" -TimeoutSec 180
$resp.result   # URL 数组，顺序与 list 一致
```

### 2. 剪贴板快捷键（单张/交互）

`Ctrl+Alt+P` —— 上传剪贴板里的图（截图、复制的图）。返回格式按 PicList `pasteStyle`（当前 HTML）。

### 3. PicList GUI 拖拽

主界面拖图到上传区。

## 核心用例：迁移 Markdown/HTML 里的远程图片

OCR 产物（Doc2X 等）常引用远程 CDN 图（`cdn.noedgeai.com` 等），不稳定且会失效。迁到自己的图床：

**流程**：
1. 解析文档，提取所有远程图片 URL —— **保留完整 URL 含查询参数**（`?x=&y=&w=&h=` 这类裁剪参数决定了实际图片内容，丢了就拿到错图）
2. 去重（同一 URL 多次引用只下载上传一次）
3. 下载到本地临时目录
4. PicList server 批量上传（`list`=本地路径）
5. 建立「原 URL → 新 URL」映射（按 list 顺序对齐 `result`）
6. 替换文档内容，生成 `.uploaded.md` —— **不改原文件**
7. 校验：输出里原 CDN 域名引用应为 0

**直接用现成脚本**（避免每次重写）：
```powershell
pwsh -File .codex/skills/piclist-upload/scripts/migrate-md-images.ps1 -InputPath "文档.md"
# 默认输出 "文档.uploaded.md"；可用 -OutputPath 自定义
```

脚本会打印：找到 N 处引用 / M 张唯一 / 下载成功数 / 上传成功数 / 替换数 / 剩余原域名引用数。

## 注意事项

- **strategyId**：兰空 Pro+ 上传**必须带** `strategy_id=1`。PicList lskyplist 配置已含 `strategyId:"1"`，server 上传自动带上。若绕过 PicList 直接调兰空 `POST /api/v1/upload`，要手动加 `strategy_id=1`，否则返回"服务异常"。
- **自动转 webp**：png/jpg 会变 .webp（体积小、浏览器都支持）。要保持原格式 → PicList 设置→图片处理 关掉「转 webp」。
- **token**：lskyplist token 是 `Bearer 1|xxxxx`（Laravel Sanctum）。PicList 已配好，无需手动处理。token 失效 → 后台重新生成 + 更新 PicList lskyplist 配置。
- **下载失败**：某些 CDN 防盗链。失败时**跳过该图不阻塞其他**，最终报告失败列表让用户决定。
- **批量上限**：`list` 一次建议 ≤50 张；更多分批。`TimeoutSec` 每张给 3-5s。
- **原文件不动**：迁移永远生成新文件（`.uploaded.md`），保留原始。

## 排错

| 现象 | 原因/处理 |
|---|---|
| server connection refused | PicList 没运行 → 让用户启动（系统托盘） |
| `{"success":false,"message":"服务异常..."}` | 图床侧异常：飞牛 NAS 关机 / lsky-pro 容器挂 / 网络断。SSH 飞牛查 `docker ps` |
| 上传 401/未授权 | token 过期 → 后台 `/admin` 重生成 token，更新 PicList 配置 |
| 上传成功但图片 502/打不开 | frp 链路断：飞牛 frpc 容器或 VPS frps/nginx。查飞牛 `docker logs frpc` + VPS `nginx -t` |
| md 里是本地图片路径 | 直接把路径放 `list`，跳过下载步骤 |
| PicList 把图转成了 webp 但不想要 | 这是 `buildIn.compress` 设置，不是 bug。关掉转换即可 |

## 图床架构（理解链路，便于排错）

```
PicList(Windows) → POST → pic.ltreen.tech:443 (VPS nginx 终止 SSL)
   → 127.0.0.1:18320 (frps tcp) → 飞牛 frpc → 飞牛 lsky-pro:8188 → 落盘 → 返回公网 URL
```

- **飞牛 NAS** `192.168.31.147`：docker 跑 `lsky-pro` + `lsky-mysql` + `frpc`。数据在 `/vol1/1000/lsky-pro/`
- **阿里云 VPS** `47.94.235.59`：nginx 反代（`pic.ltreen.tech.conf`，已禁 proxy_cache 因为会缓存动态 cookie）+ `frps`
- **域名**：`pic.ltreen.tech`（主域名 `ltreen.tech` 已绑定 Pro+ license，pic 作为子域名覆盖）

## 直接调兰空 API（不用 PicList 时）

只在 PicList 不可用、或需要在非 Windows 机器上传时才用：

```bash
# 上传（必须带 strategy_id=1）
curl -X POST https://pic.ltreen.tech/api/v1/upload \
  -H "Authorization: Bearer 1|xxxxx" \
  -F "file=@/path/img.png" -F "strategy_id=1"
```

token 获取：`POST /api/v1/images/tokens`（需先登录）或后台 tinker `createToken`。日常用 PicList 更省事。
