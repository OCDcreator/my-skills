---
name: open-source-projects
description: >-
  本地开源项目索引。当用户提到任何开源项目名称（中英文均可）、询问项目在哪里、
  想看某个项目、问项目是做什么的、提到 repo/repository/项目/仓库/open-source-project、
  问"我收藏了什么项目"、或者用户提到任何可能在 open-source-project 目录下的项目时，
  都必须使用这个 skill。永远不要全盘搜索文件系统来猜测项目位置，
  而是先查数据库。
triggers:
  - 开源项目
  - 在哪里
  - 项目索引
  - 项目列表
  - open-source-project
  - repo
  - repository
  - 仓库
  - 克隆的
  - 拉取的
  - 收藏的项目
  - 我有什么项目
---

# 本地开源项目索引

**核心原则：先查数据库，再查文件系统。** 本目录下所有项目信息都在 SQLite 中，不要 `find` 或 `ls` 猜测。

## 第一步：查数据库

**Mac DB 路径**：
```bash
DB="/Volumes/SDD2T/obsidian-vault-write/open-source-project/_index/projects.db"
```

**Windows DB 路径**：
```powershell
$DB = "C:\Users\lt\Desktop\Write\open-source-project\_index-export\projects.json"
```

> Mac 端 `_index/projects.db` 是指向 SQLite 数据库的 symlink。Windows 端没有本地 DB，用 JSON manifest 替代。

### Mac 端查询（SQLite）

```bash
# 列出所有项目
sqlite3 "$DB" "SELECT name, category, substr(description,1,60) FROM projects ORDER BY category, name"

# 搜索项目（按名称/描述/分类模糊匹配）
sqlite3 "$DB" "SELECT name, path_absolute_mac, description, remote_url FROM projects WHERE name LIKE '%KEYWORD%' OR description LIKE '%KEYWORD%' OR category LIKE '%KEYWORD%'"

# 查看单个项目完整信息
sqlite3 "$DB" "SELECT name, path_absolute_mac, category, description, remote_url, default_branch, status FROM projects WHERE name = 'PROJECT_NAME'"
```

### Windows 端查询（JSON manifest）

```powershell
# 列出所有项目
python -c "import json; [print(f'{p[\"name\"]} ({p[\"category\"]}): {p.get(\"description\",\"\")[:60]}') for p in json.load(open(r'C:\Users\lt\Desktop\Write\open-source-project\_index-export\projects.json','r',encoding='utf-8'))]"

# 搜索项目
python -c "import json; [print(p['name'],p.get('description','')[:80]) for p in json.load(open(r'C:\Users\lt\Desktop\Write\open-source-project\_index-export\projects.json','r',encoding='utf-8')) if 'KEYWORD' in p['name'] or 'KEYWORD' in p.get('description','')]"
```

## schema

`projects` 表（Mac SQLite）：name, path_relative, path_absolute_mac, category, description, remote_url, default_branch, status, last_reminded_at

JSON manifest（Windows）字段相同：name, path_relative, category, description, remote_url, default_branch, has_readme

## 使用指引

- 用户问项目在哪 → Mac 查 `path_absolute_mac`，Windows 查 `path_relative`
- 用户问项目是做什么的 → 查 `description`，不够就看 README
- 用户想浏览项目 → 列出 name + description
- 用户提到英文项目名 → 直接 `WHERE name = 'xxx'`
- 拿到路径后，打开项目目录

## 自动化流程

- **Windows**：计划任务 `OpenSourceStudy-AutoScan` 每 30 分钟扫描 → 更新 `_index-export/projects.json`
- **Mac**：launchd `com.opensource-study.auto-sync` 每 30 分钟 → ingest manifest → clone/sync 所有项目 → 更新 SQLite
- **Hermes**：每日 cron → sync_all + 队列重建 → 选当日项目 → Telegram 推送
