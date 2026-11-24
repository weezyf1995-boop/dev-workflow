"""Tests for scripts/check_settings_templates.py, driven through its process boundary.

Each test writes a small repository root (a README with the deny list block and
the two templates) into a temp directory, runs the checker on it, and checks
the exit code and output. The checker's functions are never imported.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CHECKER = os.path.join(REPO, "scripts", "check_settings_templates.py")

DENY = [
    "Read(.env)", "Edit(.env)",
    "Read(.env.local)", "Edit(.env.local)",
    "Read(~/.ssh/**)", "Edit(~/.ssh/**)",
]

README = """# repo

## Guardrails

Both templates deny these:

<!-- guardrails-deny-list:start -->
```text
{rules}
```
<!-- guardrails-deny-list:end -->
"""

SANDBOX = {
    "enabled": True,
    "allowUnsandboxedCommands": True,
    "credentials": {"files": [{"path": "~/.ssh", "mode": "deny"}]},
    "filesystem": {"denyRead": ["~/**/.env", "~/**/.env.local"]},
}

USER = {
    "permissions": {"deny": list(DENY)},
    "sandbox": SANDBOX,
    "autoMode": {"environment": ["$defaults"], "hard_deny": ["$defaults"]},
}

PROJECT = {
    "permissions": {"deny": list(DENY)},
    "sandbox": SANDBOX,
}


class SettingsTemplatesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.readme = README.format(rules="\n".join(DENY))
        self.user = copy.deepcopy(USER)
        self.project = copy.deepcopy(PROJECT)

    def run_check(self, user_text=None, project_text=None):
        with open(os.path.join(self.root, "README.md"), "w", encoding="utf-8") as f:
            f.write(self.readme)
        os.makedirs(os.path.join(self.root, "templates"), exist_ok=True)
        for name, data, text in (("user-settings.json", self.user, user_text),
                                 ("project-settings.json", self.project, project_text)):
            with open(os.path.join(self.root, "templates", name), "w", encoding="utf-8") as f:
                f.write(text if text is not None else json.dumps(data, indent=2))
        return subprocess.run([sys.executable, CHECKER, self.root],
                              capture_output=True, text=True)

    def assertFails(self, result, *needles):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        out = result.stdout + result.stderr
        for n in needles:
            self.assertIn(n, out)

    def test_complete_templates_pass(self):
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_user_template_missing_a_readme_entry_fails(self):
        self.user["permissions"]["deny"].remove("Edit(.env.local)")
        self.assertFails(self.run_check(), "user-settings.json", "Edit(.env.local)")

    def test_project_template_with_auto_mode_fails(self):
        self.project["autoMode"] = {"allow": ["$defaults"]}
        self.assertFails(self.run_check(), "project-settings.json", "autoMode")

    def test_permission_rule_that_denies_env_example_fails(self):
        self.project["permissions"]["deny"].append("Read(.env.*)")
        self.assertFails(self.run_check(), "project-settings.json", "Read(.env.*)", ".env.example")

    def test_sandbox_path_that_denies_env_example_fails(self):
        self.user["sandbox"] = copy.deepcopy(SANDBOX)
        self.user["sandbox"]["filesystem"]["denyRead"].append("~/**/.env*")
        self.assertFails(self.run_check(), "user-settings.json", "~/**/.env*", ".env.example")

    def test_template_that_does_not_parse_fails(self):
        self.assertFails(self.run_check(project_text='{"permissions": {'),
                         "project-settings.json", "JSON")

    def test_readme_without_the_deny_list_block_fails(self):
        self.readme = "# repo\n\n## Guardrails\n\nNo list here.\n"
        self.assertFails(self.run_check(), "README.md", "deny list")

    def test_sandbox_missing_a_credentials_deny_fails(self):
        self.project["sandbox"] = copy.deepcopy(SANDBOX)
        self.project["sandbox"]["credentials"]["files"] = []
        self.assertFails(self.run_check(), "project-settings.json", "credentials.files", "~/.ssh")

    def test_sandbox_missing_an_env_deny_read_fails(self):
        self.user["sandbox"] = copy.deepcopy(SANDBOX)
        self.user["sandbox"]["filesystem"]["denyRead"].remove("~/**/.env.local")
        self.assertFails(self.run_check(), "user-settings.json", "denyRead", ".env.local")

    def test_sandbox_not_enabled_fails(self):
        self.user["sandbox"] = copy.deepcopy(SANDBOX)
        self.user["sandbox"]["enabled"] = False
        self.assertFails(self.run_check(), "user-settings.json", "sandbox.enabled")

    def test_rules_that_spare_env_example_pass(self):
        extra = ["Read(.env.*.local)", "Read(.env.production)", "Read(**/secrets/**)", "Read(~/.aws/**)"]
        self.readme = README.format(rules="\n".join(DENY + extra))
        sandbox = copy.deepcopy(SANDBOX)
        sandbox["credentials"]["files"].append({"path": "~/.aws", "mode": "deny"})
        sandbox["filesystem"]["denyRead"] += ["~/**/.env.*.local", "~/**/.env.production"]
        for t in (self.user, self.project):
            t["permissions"]["deny"] += extra
            t["sandbox"] = sandbox
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
