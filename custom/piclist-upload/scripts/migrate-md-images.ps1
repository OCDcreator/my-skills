<#
.SYNOPSIS
  把 Markdown/HTML 里的远程图片迁移到 pic.ltreen.tech（通过本地 PicList）

.DESCRIPTION
  解析文档里所有远程图片 URL，下载到临时目录，通过 PicList server 批量上传，
  用返回的新 URL 替换原文，生成 .uploaded.md（不动原文件）。
  PicList 默认图床已切到兰空，开箱即用。

.PARAMETER InputPath
  源 md/html 文件路径。

.PARAMETER OutputPath
  输出路径。默认在源文件同目录加 .uploaded 后缀。

.PARAMETER PicBed
  可选。指定 picbed（如 lskyplist）。留空=用 PicList 默认图床。

.PARAMETER ConfigName
  可选。配合 PicBed 用（如 picltreen）。

.EXAMPLE
  pwsh -File migrate-md-images.ps1 -InputPath "note.md"
  pwsh -File migrate-md-images.ps1 -InputPath "a.html" -OutputPath "a-migrated.html"
#>
param(
  [Parameter(Mandatory = $true)][string]$InputPath,
  [string]$OutputPath = "",
  [string]$PicBed = "",
  [string]$ConfigName = "",
  [int]$DownloadTimeout = 30,
  [int]$UploadTimeout = 180
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InputPath)) { throw "input not found: $InputPath" }
if (-not $OutputPath) {
  $OutputPath = [System.IO.Path]::ChangeExtension($InputPath, ".uploaded" + [System.IO.Path]::GetExtension($InputPath))
}

$tmpDir = Join-Path $env:TEMP "piclist-migrate-$(Get-Random -Maximum 100000)"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

try {
  $content = [System.IO.File]::ReadAllText($InputPath)

  # 匹配远程图片 URL：http(s)://...图片扩展名 + 可选查询参数
  $pattern = 'https?://[^\s"''<>]+\.(?:png|jpe?g|gif|webp|bmp|svg|tiff?|avif|heic)(?:\?[^\s"''<>]*)?'
  $all = [regex]::Matches($content, $pattern) | ForEach-Object { $_.Value }

  # 去重保序
  $unique = [System.Collections.Generic.List[string]]::new()
  $seen = @{}
  foreach ($u in $all) { if (-not $seen.ContainsKey($u)) { $seen[$u] = 1; $unique.Add($u) } }

  Write-Host "found $($all.Count) occurrences, $($unique.Count) unique remote images"
  if ($unique.Count -eq 0) { Write-Host "no remote images to migrate; nothing to do."; exit 0 }

  # 1. 下载
  Write-Host "`ndownloading..."
  $files = @()
  for ($i = 0; $i -lt $unique.Count; $i++) {
    $url = $unique[$i]
    $ext = if ($url -match '\.(png|jpe?g|gif|webp|bmp|svg|tiff?|avif|heic)') { $matches[1] } else { 'jpg' }
    if ($ext -eq 'jpeg') { $ext = 'jpg' }
    $f = Join-Path $tmpDir "img_$i.$ext"
    try {
      Invoke-WebRequest -Uri $url -OutFile $f -TimeoutSec $DownloadTimeout -UseBasicParsing
      $files += $f
      Write-Host "  [$($i+1)/$($unique.Count)] OK  $url"
    } catch {
      Write-Host "  [$($i+1)/$($unique.Count)] FAIL $url -- $($_.Exception.Message)" -ForegroundColor Yellow
      $files += $null
    }
  }
  $valid = $files.Where({ $_ -ne $null })
  Write-Host "downloaded $($valid.Count)/$($unique.Count)"
  if ($valid.Count -eq 0) { throw "no images downloaded (check network / CDN 防盗链)" }

  # 2. PicList 批量上传
  $uri = "http://127.0.0.1:36677/upload"
  if ($PicBed) {
    $uri += "?picbed=$PicBed"
    if ($ConfigName) { $uri += "&configName=$ConfigName" }
  }
  $body = @{ list = $valid } | ConvertTo-Json
  Write-Host "`nuploading $($valid.Count) via PicList ($uri)..."
  try {
    $resp = Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" -TimeoutSec $UploadTimeout
  } catch {
    throw "PicList server 调用失败：$($_.Exception.Message)。确认 PicList 在运行（系统托盘）。"
  }
  if (-not $resp.success) { throw "PicList upload failed: $($resp | ConvertTo-Json -Compress)" }
  Write-Host "uploaded $($resp.result.Count) urls"

  # 3. 映射（原 URL → 新 URL，按 list 顺序对齐 result）
  $map = @{}
  $ri = 0
  for ($i = 0; $i -lt $unique.Count; $i++) {
    if ($files[$i] -ne $null) { $map[$unique[$i]] = $resp.result[$ri]; $ri++ }
  }

  # 4. 替换 + 写出
  $newContent = $content
  foreach ($k in $map.Keys) { $newContent = $newContent.Replace($k, $map[$k]) }
  [System.IO.File]::WriteAllText($OutputPath, $newContent, [System.Text.UTF8Encoding]::new($false))

  # 5. 校验：统计原 CDN 域名是否还残留
  $origDomains = ($unique | ForEach-Object { ([System.Uri]$_).Host } | Sort-Object -Unique)
  $remain = 0
  foreach ($d in $origDomains) {
    $remain += ([regex]::Matches($newContent, [regex]::Escape($d))).Count
  }

  Write-Host "`n========== DONE ==========" -ForegroundColor Green
  Write-Host "output:    $OutputPath"
  Write-Host "replaced:  $($map.Count) images"
  Write-Host "remaining refs to original CDN hosts: $remain"
  Write-Host "sample new urls:"
  $map.Values | Select-Object -First 3 | ForEach-Object { Write-Host "  $_" }
  if ($remain -gt 0) { Write-Host "(注：可能含未下载成功的图，检查上面 FAIL 列表)" -ForegroundColor Yellow }
}
finally {
  Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}
