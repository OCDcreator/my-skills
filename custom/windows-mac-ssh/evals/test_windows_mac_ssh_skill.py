import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsMacSshSkillTests(unittest.TestCase):
    def test_skill_contains_high_risk_triggers_and_decision_flow(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in [
            "SSH/SCP",
            "Mac Mini",
            "SSH 连接 Mac",
            "连 mac mini",
            "把文件复制到 Mac",
            "scp 到 Mac",
            "Windows 到 macOS 同步仓库/artifacts",
            "远程跑无人值守任务",
            "在 Mac 上执行命令",
            "background jobs",
            "CRLF/LF",
            "$Mac:",
            "First decision",
            "Bundled scripts",
        ]:
            self.assertIn(phrase, skill)

    def test_skill_documents_known_power_shell_quoting_failures(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in [
            'Use `"${Mac}:/remote/path"`',
            'Do not use `\\"` as a PowerShell escape',
            "zsh: parse error near done",
            "Command seems to run locally",
            "No-go patterns",
            "Bash-style \\ line continuation is not PowerShell",
            "cmd.exe caret continuation is not PowerShell",
        ]:
            self.assertIn(phrase, skill)

    def test_skill_covers_background_monitor_and_restart_patterns(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

        for phrase in [
            "Start-MacBackgroundJob.ps1",
            "Watch-MacLog.ps1",
            "pgrep -af",
            "tail -f",
            "inspect the previous log before restarting",
        ]:
            self.assertIn(phrase, skill)

    def test_required_scripts_exist_and_use_hardening_patterns(self):
        scripts = {
            "Invoke-MacZsh.ps1": ["base64", "BatchMode=yes", "ConnectTimeout", "CleanEnv"],
            "Copy-ToMac.ps1": ["tar -C", "Refusing unsafe destination", "BatchMode=yes"],
            "Compare-WindowsMacHash.ps1": ["Get-FileHash", "shasum -a 256", "Compare-Object"],
            "Start-MacBackgroundJob.ps1": ["nohup", ".cache/windows-mac-ssh/jobs", "pid=%s"],
            "Watch-MacLog.ps1": ["tail -n", "BatchMode=yes"],
        }

        for script_name, required_phrases in scripts.items():
            path = ROOT / "scripts" / script_name
            self.assertTrue(path.exists(), script_name)
            text = path.read_text(encoding="utf-8")
            for phrase in required_phrases:
                self.assertIn(phrase, text, f"{script_name} missing {phrase}")

    def test_eval_prompts_cover_real_failure_modes(self):
        data = json.loads((ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        prompts = "\n".join(item["prompt"] for item in data["evals"])

        for phrase in ["&&", "$HOME", "artifacts", "$Mac:/path", "无人值守", "误删"]:
            self.assertIn(phrase, prompts)

    def test_power_shell_scripts_parse(self):
        script_paths = sorted((ROOT / "scripts").glob("*.ps1"))
        self.assertGreaterEqual(len(script_paths), 5)

        for path in script_paths:
            command = (
                "$errors = $null; "
                f"$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content -Raw -LiteralPath '{path}'), [ref]$errors); "
                "if ($errors.Count -gt 0) { $errors | Format-List | Out-String | Write-Error; exit 1 }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, f"{path.name}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
