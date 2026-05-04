---
name: ssh
description: Use when the user mentions SSH, SCP, remote shell, "SSH 连接", "连 mac", "连 unraid", "连路由器", "连飞牛", "远程执行", "远程命令", "scp 传文件", "连服务器", or any device connection via OpenSSH. Triggers on connecting to any known device (Mac, Windows, Unraid, router, NAS) or general SSH/SCP operations. Includes device inventory, quoting rules, cross-platform pitfalls, and bundled automation scripts.
---

# SSH Remote Operations

Connect to and manage all known devices via SSH/SCP from the current workstation. Covers connection routing, quoting safety, file transfer, background jobs, and device-specific quirks.

## Known Devices

| Alias | IP | User | Port | SSH Command | Notes |
|-------|----|------|------|-------------|-------|
| **macmini** | 192.168.31.215 | dht | 22 | `ssh dht@192.168.31.215` | macOS, key-based auth |
| **windows** | 192.168.31.148 | lt | 22 | `ssh lt@192.168.31.148` | Windows OpenSSH, key-based auth |
| **unraid** | 192.168.31.98 | root | 13322 | `ssh -p 13322 root@192.168.31.98` | Custom SSH port |
| **router** | 192.168.31.204 | root | 22 | `ssh root@192.168.31.204` | QWRT, busybox shell |
| **fnos** | 192.168.31.147 | letian | 22 | `ssh letian@192.168.31.147` | 飞牛 fnOS, Linux |

When the user says "连 Mac", "SSH 到路由器", "Unraid 上执行" etc., resolve to the matching device above. If the target is ambiguous, ask which device.

## Quick decision

| Situation | Use |
|-----------|-----|
| Connect to a known device by name | Look up device table above, run SSH command |
| One simple command, no tricky quotes | `ssh $Target 'remote command'` |
| Multi-line command, pipes, JSON, regex, Chinese, nested quotes, or remote `$VARS` | Base64 pattern (see below) or bundled scripts |
| Copy files Windows ↔ Mac | `scripts/Copy-ToMac.ps1` or tar-over-ssh |
| Copy files to other devices | `scp` with correct port/user |
| Start unattended work on Mac | `scripts/Start-MacBackgroundJob.ps1` |
| Watch a long-running job log on Mac | `scripts/Watch-MacLog.ps1` |
| Verify copied artifacts | `scripts/Compare-WindowsMacHash.ps1` |
| Destructive remote command | Base64 pattern + destructive guard + status check |

## Device-specific notes

### Mac Mini (macmini)

Default profile when the user mentions Mac:

```powershell
$Mac = 'dht@192.168.31.215'
$MacRepo = '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills'
```

Do not "correct" `SDD2T` to `SSD2T` unless you verify the mounted volume name:

```powershell
ssh $Mac 'ls -la /Volumes'
```

Mac uses `/bin/zsh`. For multi-line scripts, always use the base64 pattern to avoid quoting hell.

### Windows (windows)

```powershell
$Win = 'lt@192.168.31.148'
```

Windows OpenSSH uses `cmd.exe` or PowerShell as the default shell depending on configuration. Test first:

```powershell
ssh $Win 'echo %COMSPEC%'
```

### Unraid (unraid)

```powershell
$Unraid = 'root@192.168.31.98'
$UnraidPort = 13322
```

Always specify the port: `ssh -p 13322 $Unraid 'command'`. Unraid runs a Linux-based environment with typical GNU tools.

### QWRT Router (router)

```powershell
$Router = 'root@192.168.31.204'
```

Runs busybox. Not all GNU coreutils are available — use busybox-compatible commands. No package manager for installing extra tools.

### 飞牛 fnOS (fnos)

```powershell
$Fnos = 'letian@192.168.31.147'
```

Standard Linux environment. Uses bash by default.

## Bundled scripts (Mac-specific)

When this skill is available from the `my-skills` repo, prefer these scripts over retyping wrappers:

```powershell
$SkillDir = 'C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\ssh'

& "$SkillDir\scripts\Invoke-MacZsh.ps1" -Script @'
cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills"
git status -sb
'@
```

Scripts included:

| Script | Purpose |
|--------|---------|
| `scripts/Invoke-MacZsh.ps1` | Runs LF-normalized zsh over SSH through base64, checks exit code |
| `scripts/Copy-ToMac.ps1` | Copies Windows files/directories to Mac through tar-over-ssh |
| `scripts/Compare-WindowsMacHash.ps1` | Compares Windows and Mac files/directories by SHA-256 |
| `scripts/Start-MacBackgroundJob.ps1` | Starts a detached Mac zsh job and prints PID/log path |
| `scripts/Watch-MacLog.ps1` | Tails a Mac log file safely from PowerShell |
| `scripts/ConvertTo-ZshSingleQuoted.ps1` | Shared remote-safe single-quote escaping helper used by the other scripts |

## Golden rules

1. Prefer **PowerShell** on Windows and the target's native shell remotely.
2. Quote the whole remote command. Unquoted `&&`, `|`, `;`, `>` and `<` are interpreted locally.
3. Use PowerShell single quotes for simple remote commands that contain remote `$VARS`.
4. Use the base64 script pattern for multi-line commands, nested quotes, Chinese text, `$`, or long Git/SCP flows.
5. Normalize Windows CRLF to LF before a script reaches a Unix target.
6. Use `"${Target}:/remote/path"` rather than `"$Target:/remote/path"` in PowerShell; the latter can be parsed as a scoped variable.
7. Do not use `\"` as a PowerShell escape. PowerShell uses the backtick escape `` `" `` inside double-quoted strings; prefer single quotes or here-strings instead.
8. Check `$LASTEXITCODE` after `ssh`, `scp`, `git`, and other native commands.
9. Before destructive remote commands, verify `pwd`, target path, and `git status --short`.
10. Always specify `-p PORT` when connecting to devices with non-standard SSH ports (Unraid: 13322).

## Quick connectivity check

Use this before any real work (replace `$Target` with the device):

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 $Target 'printf "host=%s user=%s shell=%s\n" "$(hostname)" "$(whoami)" "$SHELL"'
if ($LASTEXITCODE -ne 0) { throw "SSH failed: $LASTEXITCODE" }
```

For Unraid: `ssh -o BatchMode=yes -o ConnectTimeout=10 -p 13322 root@192.168.31.98 'hostname && whoami'`

`BatchMode=yes` fails fast instead of hanging on password/passphrase prompts. Remove it only when the user expects an interactive login.

## SSH config

For repeated work, add host aliases in `C:\Users\<user>\.ssh\config`:

```sshconfig
Host macmini
  HostName 192.168.31.215
  User dht
  Port 22
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host unraid
  HostName 192.168.31.98
  User root
  Port 13322
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host router
  HostName 192.168.31.204
  User root
  Port 22
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host fnos
  HostName 192.168.31.147
  User letian
  Port 22
  ServerAliveInterval 30
  ServerAliveCountMax 4

Host windows
  HostName 192.168.31.148
  User lt
  Port 22
  ServerAliveInterval 30
  ServerAliveCountMax 4
```

Then commands can use aliases:

```powershell
ssh -o BatchMode=yes macmini 'hostname && whoami'
ssh -o BatchMode=yes unraid 'hostname && whoami'
```

## First connection and key errors

If SSH fails before running the remote command, diagnose connection/auth before debugging quotes:

| Symptom | Fix |
|---------|-----|
| Prompt asks to trust a host key | Run one interactive `ssh user@host` and accept only if the host is expected |
| `Permission denied (publickey)` | Verify the right user, key loaded, and `~/.ssh/authorized_keys` on target |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Verify the target really changed, then run `ssh-keygen -R <host>` |
| Hangs before output | Retry with `ssh -vvv -o ConnectTimeout=10 ...` |
| Works interactively but not in automation | Remove `BatchMode=yes` only for setup; restore it for unattended commands |
| `Connection refused` | Check target IP, port, and that SSH service is running |

## Simple remote commands

Good:

```powershell
ssh $Mac 'cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills" && git status -sb && git rev-parse --short HEAD'
if ($LASTEXITCODE -ne 0) { throw "Remote command failed: $LASTEXITCODE" }
```

Bad:

```powershell
ssh $Mac cd /Volumes/SDD2T/repo && git status
```

This runs `git status` locally after the SSH command, because `&&` was not inside the remote command string.

## Robust multi-line remote script (base64 pattern)

Use this as the default for non-trivial work on any Unix target:

```powershell
$Target = 'dht@192.168.31.215'  # or any device

$script = @'
set -e
set -u
set -o pipefail

cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills"
printf 'pwd=%s\n' "$PWD"
printf 'home=%s\n' "$HOME"
git status -sb
git rev-parse --short HEAD
'@

$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lf))
ssh -o BatchMode=yes -o ConnectTimeout=10 $Target "printf '%s' '$b64' | /usr/bin/base64 -D | /bin/zsh -s"
if ($LASTEXITCODE -ne 0) { throw "Remote script failed: $LASTEXITCODE" }
```

For non-Mac targets, adjust the decode command:
- **Linux** (Unraid, fnOS): `base64 -d` instead of `base64 -D`, and `/bin/bash` instead of `/bin/zsh`
- **Router** (busybox): `busybox base64 -d` and `/bin/sh`

Use this pattern when a command contains:

- both single and double quotes,
- remote variables such as `$HOME`, `$PWD`, `$target`,
- pipes, heredocs, `awk`, `sed`, `perl`, `jq`, or JSON,
- Chinese paths/text,
- more than one or two shell operators.

For very large scripts, write a temporary LF-only `.sh` file, `scp` it to `/tmp`, then run it.

## Clean remote environment (Mac)

When commands behave differently from an interactive Mac Terminal, suspect `~/.zshenv`, aliases, functions, or a different `PATH`. Use clean mode:

```powershell
& "$SkillDir\scripts\Invoke-MacZsh.ps1" -CleanEnv -Script @'
set -e
command -v git
git --version
'@
```

The clean runner uses `/bin/zsh -f` with a known `PATH`. It avoids user startup files while preserving essential variables such as `HOME` and `USER`.

## PowerShell here-string rules

PowerShell here-strings are safest for remote scripts, but the delimiters are strict:

```powershell
$script = @'
echo "remote double quotes survive"
echo 'remote single quotes survive'
printf 'remote variable: %s\n' "$HOME"
'@
```

Rules:

- `@'` must be the last characters on its opening line.
- `'@` must start at the beginning of the closing line.
- Single-quoted here-strings do not expand local PowerShell variables.
- Do not use PowerShell backtick line continuation for SSH scripts; it is fragile and invisible in reviews.

If local values must be injected, prefer placeholders and explicit replacement before base64 encoding:

```powershell
$script = @'
cd "__REMOTE_REPO__"
git status -sb
'@
$script = $script.Replace('__REMOTE_REPO__', '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills')
```

## Quoting cheat sheet

| Need | Use |
|------|-----|
| Remote `$HOME` or `$PWD` | PowerShell single-quoted remote command: `ssh $Target 'echo "$HOME"'` |
| Local PowerShell variable before SCP colon | `"${Target}:/remote/path"` |
| Literal `"` inside PowerShell double quotes | Use `` `" `` or avoid with a here-string |
| Literal `'` and `"` together | Use a single-quoted here-string or base64 script |
| Literal single quote inside simple remote command | Switch to base64 script pattern |
| Multi-line remote script | Single-quoted here-string + LF normalization + base64 |
| JSON or regex with many quotes | Base64 script pattern |
| Remote path with spaces | Quote inside remote shell: `cd "/Volumes/My Disk/repo"` |
| Windows local path with spaces | PowerShell quotes: `"C:\Users\lt\My Folder\file.txt"` |

## Line endings and encoding

Windows CRLF can break Unix shell scripts, especially files with shebangs (`/bin/sh^M`). Normalize before sending scripts:

```powershell
$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
```

If you must write a local temp script for `scp`, write UTF-8 without BOM and LF:

```powershell
$tmp = Join-Path $env:TEMP 'remote-task.sh'
$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
[System.IO.File]::WriteAllText($tmp, $lf, [System.Text.UTF8Encoding]::new($false))
scp -P 13322 $tmp "${Unraid}:/tmp/remote-task.sh"
ssh -p 13322 $Unraid '/bin/bash /tmp/remote-task.sh'
```

If a script already reached the target with CRLF, fix it remotely:

```powershell
ssh $Mac 'perl -pi -e "s/\r$//" /tmp/remote-task.sh && /bin/zsh /tmp/remote-task.sh'
```

For Chinese output in older Windows PowerShell, set UTF-8 before running long sessions:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

## Copying files

### Windows → Mac

```powershell
$Mac = 'dht@192.168.31.215'
$src = 'C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\ssh\artifacts'
$dest = '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/custom/ssh'
scp -r -- $src "${Mac}:$dest/"
if ($LASTEXITCODE -ne 0) { throw "SCP failed: $LASTEXITCODE" }
```

If paths contain spaces or SCP quoting becomes messy, use tar over SSH:

```powershell
$parent = Split-Path -Parent $src
$leaf = Split-Path -Leaf $src
tar -C $parent -cf - $leaf | ssh $Mac "cd '$dest' && tar -xf -"
if ($LASTEXITCODE -ne 0) { throw "tar-over-ssh copy failed: $LASTEXITCODE" }
```

### Mac → Windows

```powershell
$destLocal = 'C:\Users\lt\Desktop\from-mac'
New-Item -ItemType Directory -Force -Path $destLocal | Out-Null
scp -r "${Mac}:/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/path/on/mac" $destLocal
```

### To/From other devices

For Unraid (custom port), always use `-P` (uppercase) with `scp`:

```powershell
scp -P 13322 localfile.txt "${Unraid}:/mnt/user/data/"
```

### Copy semantics

- `Copy-ToMac.ps1 -LocalPath C:\dir -RemoteDirectory /tmp` copies the directory itself to `/tmp/dir`.
- `Copy-ToMac.ps1 -Replace` first removes `/tmp/dir`, guarded by destination-prefix checks.
- After copying important artifacts, verify file count and key hashes with `Compare-WindowsMacHash.ps1`.

## Git repo sync on Mac

Use a status-first flow. Do not discard remote work unless the user explicitly asks for reset/overwrite.

```powershell
$script = @'
set -e
set -u
set -o pipefail

cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills"
git status -sb
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
'@

$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($lf))
ssh $Mac "printf '%s' '$b64' | /usr/bin/base64 -D | /bin/zsh -s"
```

If the user asked to force Mac to match GitHub:

```powershell
$script = @'
set -e
set -u
set -o pipefail

cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills"
git fetch origin --prune
git reset --hard origin/main
git status -sb
git rev-parse HEAD
'@
```

Encode and run it with the same base64 pattern.

## Background jobs and logs (Mac)

For unattended Mac work, never rely on an interactive SSH session staying open. Start a detached job and print its PID/log path:

```powershell
& "$SkillDir\scripts\Start-MacBackgroundJob.ps1" -Label 'my-skills-maintenance' -Script @'
set -e
set -u
set -o pipefail
cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills"
git status -sb
sleep 5
git rev-parse HEAD
'@
```

Watch the log:

```powershell
& "$SkillDir\scripts\Watch-MacLog.ps1" -LogPath '/Users/dht/.cache/windows-mac-ssh/jobs/my-skills-maintenance.log' -Follow
```

Check whether a PID is still running:

```powershell
ssh $Mac 'ps -p 12345 -o pid=,stat=,command='
```

Search by label when only part of the command is known:

```powershell
ssh $Mac "pgrep -af 'my-skills-maintenance|windows-mac-ssh'"
```

If a background job fails, restart with a new label or after removing the old PID/script/log trio. Always inspect the previous log before restarting.

If a long job modifies a Git repo, require it to write a status file or final `git status -sb` to its log before claiming success.

If a command may outlive the current SSH session, do not keep it inline. Convert it into a background job first.

## Destructive command guard

Before `rm -rf`, `git reset --hard`, or replacing a directory, verify the path is exactly under the expected location:

```zsh
target="/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/custom/some/artifacts"
case "$target" in
  /Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/*)
    rm -rf "$target"
    ;;
  *)
    printf 'Refusing unsafe target: %s\n' "$target" >&2
    exit 2
    ;;
esac
```

Run this through the base64 pattern rather than trying to inline it inside nested quotes.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `The variable reference is not valid. ':' was not followed...` | Used `"$Target:/path"` | Use `"${Target}:/path"` |
| `ParserError: Unexpected token` near `\"` | Used Bash/JSON-style quote escaping in PowerShell | Use `` `" `` or a here-string |
| Remote `$HOME` became a Windows path | Used PowerShell double quotes | Use single quotes or base64 script |
| `zsh: parse error near done` | Nested quote broke before reaching target | Use base64 script |
| `bad interpreter: /bin/zsh^M` | CRLF script file | Normalize LF or run `perl -pi -e "s/\r$//"` |
| Command seems to run locally | Operators were outside remote quotes | Quote the whole remote command |
| SSH hangs | Waiting for password/passphrase/host key | Use `BatchMode=yes`, pre-authorize key, or run interactive once |
| `No such file or directory` under `/Volumes` | Disk not mounted or volume name differs | Run `ssh $Mac 'ls -la /Volumes'` |
| `Connection refused` on Unraid | Wrong port or SSH service down | Verify `-p 13322` and `ssh` service status |
| Busybox command not found on router | Not a GNU environment | Use busybox built-ins only |

## No-go patterns

Do not use these in future commands:

```powershell
ssh $Mac cd /repo && git status       # && runs locally
ssh $Mac "echo $HOME"                 # $HOME may expand locally or become empty
scp file "$Mac:/tmp/"                 # $Mac: can be parsed as a scoped variable
$cmd = "echo \"quoted\""              # \" is not PowerShell escaping
ssh $Mac "for f in ...; do ...; done" # fragile nested zsh; use base64
ssh $Mac "echo one" \                 # Bash-style \ line continuation is not PowerShell
ssh $Mac "echo one" ^                 # cmd.exe caret continuation is not PowerShell
scp -P 13322 $file $Unraid:/tmp/      # Missing ${} around variable with colon
```

Use the scripts/base64 pattern instead.

## Final verification pattern

When claiming Windows, GitHub, and Mac are consistent, verify with fresh command output:

```powershell
$win = git rev-parse HEAD
$origin = git rev-parse origin/main
$github = (git ls-remote origin refs/heads/main).Split()[0]
$macHead = ssh $Mac 'cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills" && git rev-parse HEAD'

"windows=$win"
"origin=$origin"
"github=$github"
"mac=$macHead"
if ($win -ne $origin -or $win -ne $github -or $win -ne $macHead.Trim()) {
  throw "Git SHA mismatch"
}
```

## Skill evals

Keep `evals/evals.json` aligned with real failure modes:

- simple SSH command should quote remote operators correctly,
- multi-line remote work should use base64 or `Invoke-MacZsh.ps1`,
- file copy should avoid `"$Target:/path"` and verify hashes,
- background jobs should detach and expose monitorable logs,
- non-standard ports (Unraid) must always be specified,
- device name resolution should match the known devices table.
