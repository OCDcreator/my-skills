#!/usr/bin/env python3
"""把 Markdown 里引用的【本地图片】批量迁移到 pic.ltreen.tech（本机 PicList server）。

与 migrate-md-images.ps1 互补：那个脚本只迁移【远程 CDN URL】图片；
本脚本处理 md 里 src 为本地路径（如 doc2x/export/images/*.jpg）的情况。

流程：
  1. 解析 InputPath 里所有 `![](...)` / `src="..."` 本地图片引用
  2. 解析为绝对路径（相对 InputPath 所在目录），去重保序
  3. 按 ≤50 张/批通过 http://127.0.0.1:36677/upload 上传（PicList 自动转 webp + md5 重命名）
  4. 用返回 URL 替换原本地路径，写 OutputPath（默认 .uploaded.md，不动原文件）
  5. 落盘 _piclist_url_map.json（basename -> new URL）便于复核/复用

用法：
  python3 migrate-md-local-images.py --input note.md
  python3 migrate-md-local-images.py --input note.md --output note.uploaded.md
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

SERVER = "http://127.0.0.1:36677/upload"
BATCH = 50

# markdown image + html img src. Capture the path token (non-whitespace, non-quote).
MD_IMG = re.compile(r'!\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
HTML_SRC = re.compile(r'src="([^"]+)"')


def extract_local_refs(content):
    """Return ordered-unique list of local image paths found in the markdown."""
    found = []
    for m in MD_IMG.finditer(content):
        found.append(m.group(1))
    for m in HTML_SRC.finditer(content):
        found.append(m.group(1))
    # keep only local refs (not http/data/file URIs)
    local = []
    seen = set()
    for p in found:
        if p.startswith(("http://", "https://", "data:", "file:")):
            continue
        if p in seen:
            continue
        seen.add(p)
        local.append(p)
    return local


def upload_batch(paths, picbed, config, timeout):
    uri = SERVER
    if picbed:
        uri += f"?picbed={picbed}"
        if config:
            uri += f"&configName={config}"
    body = json.dumps({"list": paths}).encode()
    req = urllib.request.Request(
        uri, data=body, headers={"Content-Type": "application/json"}
    )
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if not r.get("success"):
        raise RuntimeError(f"PicList upload failed: {json.dumps(r, ensure_ascii=False)}")
    return r["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="")
    ap.add_argument("--picbed", default="")
    ap.add_argument("--config", default="")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"input not found: {args.input}")
    base_dir = os.path.dirname(os.path.abspath(args.input))
    if not args.output:
        root, ext = os.path.splitext(args.input)
        args.output = root + ".uploaded" + ext

    with open(args.input, encoding="utf-8") as f:
        content = f.read()

    refs = extract_local_refs(content)
    print(f"found {len(refs)} unique local image refs")
    if not refs:
        print("nothing to upload; copying input to output unchanged")
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
        return

    # resolve to absolute paths; only keep those that exist on disk
    abs_map = {}  # ref-as-in-md -> abs path
    missing = []
    for r in refs:
        ap2 = r if os.path.isabs(r) else os.path.join(base_dir, r)
        if os.path.isfile(ap2):
            abs_map[r] = ap2
        else:
            missing.append(r)
    if missing:
        print(f"WARN: {len(missing)} refs not found on disk (skipped):")
        for m in missing[:10]:
            print(f"  {m}")
    if not abs_map:
        sys.exit("no resolvable local images; aborting")

    ordered = list(abs_map.keys())
    abs_paths = [abs_map[r] for r in ordered]
    print(f"uploading {len(abs_paths)} images in batches of {BATCH} via PicList ({SERVER})...")

    new_urls = []
    for i in range(0, len(abs_paths), BATCH):
        chunk = abs_paths[i:i + BATCH]
        print(f"  batch {i // BATCH + 1}: {len(chunk)} images...")
        result = upload_batch(chunk, args.picbed, args.config, args.timeout)
        if len(result) != len(chunk):
            sys.exit(f"batch {i // BATCH + 1} returned {len(result)} urls, expected {len(chunk)}")
        new_urls.extend(result)
        print(f"    -> {len(result)} urls")

    # map ref -> new url (order-aligned)
    ref2url = {ordered[i]: new_urls[i] for i in range(len(ordered))}

    # replace in content (longest first to avoid prefix collisions)
    new_content = content
    for ref in sorted(ref2url, key=len, reverse=True):
        new_content = new_content.replace(ref, ref2url[ref])

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(new_content)

    # save url map (basename -> url) for audit
    urlmap_path = os.path.join(base_dir, "_piclist_url_map.json")
    basemap = {os.path.basename(abs_map[r]): ref2url[r] for r in ordered}
    with open(urlmap_path, "w", encoding="utf-8") as f:
        json.dump(basemap, f, ensure_ascii=False, indent=2)

    # sanity: count remaining local refs
    remain = len(extract_local_refs(new_content))
    print("\n========== DONE ==========")
    print(f"output:    {args.output}")
    print(f"replaced:  {len(ref2url)} images")
    print(f"url map:   {urlmap_path}")
    print(f"remaining local image refs in output: {remain}")
    print("sample new urls:")
    for u in list(ref2url.values())[:3]:
        print(f"  {u}")
    if remain:
        print("WARN: some local refs remain (check missing-file warnings above)")


if __name__ == "__main__":
    main()
