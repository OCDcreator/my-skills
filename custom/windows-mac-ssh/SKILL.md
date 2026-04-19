---
name: windows-mac-ssh
description: Use when Windows PowerShell or Codex CLI needs to SSH/SCP into a Mac/Mac Mini/macOS host, including “SSH 连接 Mac”, “连 mac mini”, “把文件复制到 Mac”, “scp 到 Mac”, “在 Mac 上执行命令”, “Windows 到 macOS 同步仓库/artifacts”, or “远程跑无人值守任务”, and when avoiding quoting, CRLF/LF, `$Mac:`, zsh, remote `$HOME`, and PowerShell escape mistakes.
---

# Windows → Mac SSH

Use this when the local machine is Windows and the target is a Mac reached through OpenSSH. Treat every command as passing through **two shells**: PowerShell parses the local command first, then the Mac shell parses the remote command.

## Default profile

If the user refers to the known Mac Mini from this environment, start with:

```powershell
$Mac = 'dht@192.168.31.215'
$MacRepo = '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills'
```

Do not “correct” `SDD2T` to `SSD2T` unless you verify the mounted volume name:

```powershell
ssh $Mac 'ls -la /Volumes'
```

## First decision

Pick the least fragile route before writing a command:

| Situation | Use |
|-----------|-----|
| One simple command, no tricky quotes | `ssh $Mac 'remote command'` |
| Multi-line command, pipes, JSON, regex, Chinese, nested quotes, or remote `$VARS` | `scripts/Invoke-MacZsh.ps1` or the base64 pattern |
| Copy a file/directory from Windows to Mac | `scripts/Copy-ToMac.ps1` or tar-over-ssh |
| Verify copied artifacts | `scripts/Compare-WindowsMacHash.ps1` |
| Start unattended work that must continue after the session | `scripts/Start-MacBackgroundJob.ps1` |
| Watch a long-running job log | `scripts/Watch-MacLog.ps1` |
| Reset, delete, or overwrite remote data | Base64 pattern + destructive guard + status check |

If a command is longer than one line, prefer the bundled script instead of hand-rolled nested quotes.

## Bundled scripts

When this skill is available from the `my-skills` repo, prefer these scripts over retyping wrappers:

```powershell
$SkillDir = 'C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\windows-mac-ssh'

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

## Golden rules

1. Prefer **PowerShell** on Windows and `/bin/zsh` on macOS.
2. Quote the whole remote command. Unquoted `&&`, `|`, `;`, `>` and `<` are interpreted locally.
3. Use PowerShell single quotes for simple remote commands that contain remote `$VARS`.
4. Use the base64 script pattern for multi-line commands, nested quotes, Chinese text, `$`, or long Git/SCP flows.
5. Normalize Windows CRLF to LF before a script reaches macOS.
6. Use `"${Mac}:/remote/path"` rather than `"$Mac:/remote/path"` in PowerShell; the latter can be parsed as a scoped variable.
7. Do not use `\"` as a PowerShell escape. PowerShell uses the backtick escape `` `" `` inside double-quoted strings; prefer single quotes or here-strings instead.
8. Check `$LASTEXITCODE` after `ssh`, `scp`, `git`, and other native commands.
9. Before destructive remote commands, verify `pwd`, target path, and `git status --short`.

## Quick connectivity check

Use this before any real work:

```powershell
$Mac = 'dht@192.168.31.215'
ssh -o BatchMode=yes -o ConnectTimeout=10 $Mac 'printf "host=%s user=%s shell=%s\n" "$(hostname)" "$(whoami)" "$SHELL"; ls -1 /Volumes'
if ($LASTEXITCODE -ne 0) { throw "SSH failed: $LASTEXITCODE" }
```

`BatchMode=yes` fails fast instead of hanging on password/passphrase prompts. Remove it only when the user expects an interactive login.

## SSH config

For repeated work, add a host alias in `C:\Users\<user>\.ssh\config`:

```sshconfig
Host macmini
  HostName 192.168.31.215
  User dht
  Port 22
  ServerAliveInterval 30
  ServerAliveCountMax 4
```

Then commands can use:

```powershell
$Mac = 'macmini'
ssh -o BatchMode=yes $Mac 'hostname && whoami'
```

Keep the alias boring and stable. Do not mix aliases and raw `user@host` in the same verification report unless you print what each one resolves to.

## First connection and key errors

If SSH fails before running the remote command, diagnose connection/auth before debugging quotes:

| Symptom | Fix |
|---------|-----|
| Prompt asks to trust a host key | Run one interactive `ssh dht@192.168.31.215` and accept only if the host is expected |
| `Permission denied (publickey)` | Verify the right user, key loaded, and `~/.ssh/authorized_keys` on Mac |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Verify the Mac really changed, then run `ssh-keygen -R 192.168.31.215` |
| Hangs before output | Retry with `ssh -vvv -o ConnectTimeout=10 ...` |
| Works interactively but not in automation | Remove `BatchMode=yes` only for setup; restore it for unattended commands |

## Simple remote commands

Good:

```powershell
ssh $Mac 'cd "/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills" && git status -sb && git rev-parse --short HEAD'
if ($LASTEXITCODE -ne 0) { throw "Remote command failed: $LASTEXITCODE" }
```

Why this works:

- PowerShell single quotes pass `$SHELL`, `$HOME`, `&&`, `|`, and `"` through unchanged.
- The remote zsh then expands remote variables and executes the operators on the Mac.

Bad:

```powershell
ssh $Mac cd /Volumes/SDD2T/repo && git status
```

This runs `git status` locally after the SSH command, because `&&` was not inside the remote command string.

## Robust multi-line remote script

Use this as the default for non-trivial work. It avoids most quoting, CRLF, and nested-shell problems.

```powershell
$Mac = 'dht@192.168.31.215'

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
ssh -o BatchMode=yes -o ConnectTimeout=10 $Mac "printf '%s' '$b64' | /usr/bin/base64 -D | /bin/zsh -s"
if ($LASTEXITCODE -ne 0) { throw "Remote script failed: $LASTEXITCODE" }
```

Use this pattern when a command contains:

- both single and double quotes,
- remote variables such as `$HOME`, `$PWD`, `$target`,
- pipes, heredocs, `awk`, `sed`, `perl`, `jq`, or JSON,
- Chinese paths/text,
- more than one or two shell operators.

For very large scripts, write a temporary LF-only `.zsh` file, `scp` it to `/tmp`, then run `/bin/zsh /tmp/file.zsh`.

## Clean remote environment

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
| Remote `$HOME` or `$PWD` | PowerShell single-quoted remote command: `ssh $Mac 'echo "$HOME"'` |
| Local PowerShell variable before SCP colon | `"${Mac}:/remote/path"` |
| Literal `"` inside PowerShell double quotes | Use `` `" `` or avoid with a here-string |
| Literal `'` and `"` together | Use a single-quoted here-string or base64 script |
| Literal single quote inside simple remote command | Switch to base64 script pattern |
| Multi-line zsh script | Single-quoted here-string + LF normalization + base64 |
| JSON or regex with many quotes | Base64 script pattern |
| Remote path with spaces | Quote inside remote shell: `cd "/Volumes/My Disk/repo"` |
| Windows local path with spaces | PowerShell quotes: `"C:\Users\lt\My Folder\file.txt"` |

## Line endings and encoding

Windows CRLF can break macOS shell scripts, especially files with shebangs (`/bin/zsh^M`). Normalize before sending scripts:

```powershell
$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
```

If you must write a local temp script for `scp`, write UTF-8 without BOM and LF:

```powershell
$tmp = Join-Path $env:TEMP 'remote-task.zsh'
$lf = $script -replace "`r`n", "`n" -replace "`r", "`n"
[System.IO.File]::WriteAllText($tmp, $lf, [System.Text.UTF8Encoding]::new($false))
scp $tmp "${Mac}:/tmp/remote-task.zsh"
ssh $Mac '/bin/zsh /tmp/remote-task.zsh'
```

If a script already reached the Mac with CRLF, fix it remotely:

```powershell
ssh $Mac 'perl -pi -e "s/\r$//" /tmp/remote-task.zsh && /bin/zsh /tmp/remote-task.zsh'
```

For Chinese output in older Windows PowerShell, set UTF-8 before running long sessions:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

## Copying files

Basic Windows → Mac copy:

```powershell
$Mac = 'dht@192.168.31.215'
$src = 'C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\knowledge-to-print-html\artifacts'
$dest = '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/custom/knowledge-to-print-html'
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

Mac → Windows copy:

```powershell
$destLocal = 'C:\Users\lt\Desktop\from-mac'
New-Item -ItemType Directory -Force -Path $destLocal | Out-Null
scp -r "${Mac}:/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/path/on/mac" $destLocal
```

Copy semantics:

- `Copy-ToMac.ps1 -LocalPath C:\dir -RemoteDirectory /tmp` copies the directory itself to `/tmp/dir`.
- `Copy-ToMac.ps1 -Replace` first removes `/tmp/dir`, guarded by destination-prefix checks.
- For “copy directory contents only”, make that explicit and test with a temporary directory first; most mistakes happen when the caller means contents but writes the parent directory.
- After copying important artifacts, verify file count and key hashes with `Compare-WindowsMacHash.ps1`.

Artifact verification example:

```powershell
& "$SkillDir\scripts\Compare-WindowsMacHash.ps1" `
  -LocalPath 'C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\knowledge-to-print-html\artifacts' `
  -RemotePath '/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/custom/knowledge-to-print-html/artifacts'
```

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

## Background jobs and logs

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

Raw tail also works when a helper script is unavailable:

```powershell
ssh $Mac 'tail -f /Users/dht/.cache/windows-mac-ssh/jobs/my-skills-maintenance.log'
```

If a background job fails, restart with a new label or after removing the old PID/script/log trio. Always inspect the previous log before restarting:

```powershell
ssh $Mac 'tail -n 120 /Users/dht/.cache/windows-mac-ssh/jobs/my-skills-maintenance.log'
ssh $Mac "pgrep -af 'my-skills-maintenance'"
```

If a long job modifies a Git repo, require it to write a status file or final `git status -sb` to its log before claiming success.

## Destructive command guard

Before `rm -rf`, `git reset --hard`, or replacing a directory, verify the path is exactly under the expected repo:

```zsh
target="/Volumes/SDD2T/obsidian-vault-write/custom-project/my-skills/custom/knowledge-to-print-html/artifacts"
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
| `The variable reference is not valid. ':' was not followed...` | Used `"$Mac:/path"` | Use `"${Mac}:/path"` |
| `ParserError: Unexpected token` near `\"` | Used Bash/JSON-style quote escaping in PowerShell | Use `` `" `` or a here-string |
| Remote `$HOME` became a Windows path | Used PowerShell double quotes | Use single quotes or base64 script |
| `zsh: parse error near done` | Nested quote broke before reaching Mac | Use base64 script |
| `bad interpreter: /bin/zsh^M` | CRLF script file | Normalize LF or run `perl -pi -e "s/\r$//"` |
| Command seems to run locally | Operators were outside remote quotes | Quote the whole remote command |
| SSH hangs | Waiting for password/passphrase/host key | Use `BatchMode=yes`, pre-authorize key, or run interactive once |
| `No such file or directory` under `/Volumes` | Disk not mounted or volume name differs | Run `ssh $Mac 'ls -la /Volumes'` |

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
- file copy should avoid `"$Mac:/path"` and verify hashes,
- background jobs should detach and expose monitorable logs.
