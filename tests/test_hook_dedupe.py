"""Tests for the user-level copy of each hook standing aside for a project copy.

Users install the hooks at user level (~/.claude/scripts/) and a project repo can carry copies in
.claude/hooks/, wired through $CLAUDE_PROJECT_DIR. Claude Code runs both entries, so the user-level
copy exits 0 silently when the project carries a file of its name, and the project copy acts.

Each test copies the real scripts into a temp HOME and a temp project, feeds each one a payload that
makes it act (print or block), and checks whether it acted. The scripts' functions are never
imported.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPTS = ("context_guard.py", "frozen_tripwire.py", "suite_tripwire.py")
GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]
SILENT = (0, "", "")


def git(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def copy(name, directory):
    os.makedirs(directory, exist_ok=True)
    shutil.copy(os.path.join(REPO, "scripts", name), os.path.join(directory, name))
    return os.path.join(directory, name)


def payload(name, cwd):
    """A payload on which script `name` acts inside the repository at cwd."""
    base = {"session_id": "s1", "transcript_path": os.path.join(cwd, "t.jsonl"), "cwd": cwd,
            "permission_mode": "default"}
    if name == "context_guard.py":    # cold-cache warning
        return dict(base, hook_event_name="SessionStart", source="resume", context_tokens=10 ** 6,
                    prompt_cache_likely_expired=True)
    if name == "frozen_tripwire.py":  # usage reply to a bare override
        return dict(base, hook_event_name="UserPromptSubmit", prompt="frozen override")
    return dict(base, hook_event_name="Stop", stop_hook_active=False)  # red `full` blocks


class DedupeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="hook-dedupe-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.user_dir = os.path.join(self.home, ".claude", "scripts")
        self.project = self.make_project(os.path.join(self.tmp, "project"))

    def make_project(self, path):
        """A git repository with a commit on main and a red `full` in its .claude/checks.json."""
        os.makedirs(path, exist_ok=True)
        git(path, "init", "-q")
        write(os.path.join(path, "app.py"), "x = 1\n")
        git(path, "add", "app.py")
        git(path, "commit", "-q", "-m", "fixture")
        write(os.path.join(path, ".claude", "checks.json"), json.dumps({"full": "exit 1"}))
        return path

    def run_hook(self, script, project_dir, cwd=None):
        """Run script with HOME at the temp home, as Claude Code would: by its path as written in
        the settings entry, with CLAUDE_PROJECT_DIR set (or unset when project_dir is None)."""
        env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        env.pop("CLAUDE_PROJECT_DIR", None)
        if project_dir:
            env["CLAUDE_PROJECT_DIR"] = project_dir
        d = payload(os.path.basename(script), cwd or project_dir or self.project)
        p = subprocess.run([sys.executable or "python3", script], input=json.dumps(d), env=env,
                           cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=60)
        return p.returncode, p.stdout, p.stderr

    def assert_acts(self, result):
        self.assertNotEqual(result, SILENT, "the hook stood aside")

    def for_each_script(self):
        for name in SCRIPTS:
            with self.subTest(script=name):
                yield name

    # -- the user-level copy ---------------------------------------------

    def test_user_copy_acts_when_the_project_has_no_copy(self):
        for name in self.for_each_script():
            self.assert_acts(self.run_hook(copy(name, self.user_dir), self.project))

    def test_user_copy_acts_without_a_project_dir(self):
        for name in self.for_each_script():
            self.assert_acts(self.run_hook(copy(name, self.user_dir), None))

    def test_user_copy_stands_aside_for_a_project_copy_of_its_name(self):
        hooks = os.path.join(self.project, ".claude", "hooks")
        for name in self.for_each_script():
            copy(name, hooks)
            self.assertEqual(self.run_hook(copy(name, self.user_dir), self.project), SILENT)

    def test_a_project_copy_of_another_hook_does_not_count(self):
        hooks = os.path.join(self.project, ".claude", "hooks")
        for name in self.for_each_script():
            other = next(n for n in SCRIPTS if n != name)
            copy(other, hooks)
            self.assert_acts(self.run_hook(copy(name, self.user_dir), self.project))
            shutil.rmtree(hooks)

    def test_user_copy_reached_through_a_symlinked_scripts_dir_stands_aside(self):
        real = os.path.join(self.tmp, "dotfiles", "scripts")
        os.makedirs(os.path.dirname(self.user_dir))
        os.makedirs(real)
        os.symlink(real, self.user_dir)
        hooks = os.path.join(self.project, ".claude", "hooks")
        for name in self.for_each_script():
            copy(name, real)
            copy(name, hooks)
            self.assertEqual(self.run_hook(os.path.join(self.user_dir, name), self.project), SILENT)
            self.assertEqual(self.run_hook(os.path.join(real, name), self.project), SILENT)

    # -- the project copy ------------------------------------------------

    def test_project_copy_acts_beside_a_user_copy(self):
        hooks = os.path.join(self.project, ".claude", "hooks")
        for name in self.for_each_script():
            copy(name, self.user_dir)
            self.assert_acts(self.run_hook(copy(name, hooks), self.project))

    def test_project_hooks_dir_linked_to_the_user_scripts_acts_once(self):
        """With .claude/hooks a symlink to ~/.claude/scripts, both entries run the same file: the
        run through the user path stands aside and the run through the project path acts."""
        os.makedirs(self.user_dir)
        os.symlink(self.user_dir, os.path.join(self.project, ".claude", "hooks"))
        for name in self.for_each_script():
            copy(name, self.user_dir)
            self.assertEqual(self.run_hook(os.path.join(self.user_dir, name), self.project), SILENT)
            self.assert_acts(self.run_hook(
                os.path.join(self.project, ".claude", "hooks", name), self.project))

    def test_a_project_that_is_the_claude_dir_itself_acts_once(self):
        """CLAUDE_PROJECT_DIR=~/.claude: its project copies live in ~/.claude/.claude/hooks/."""
        project = self.make_project(os.path.join(self.home, ".claude"))
        hooks = os.path.join(project, ".claude", "hooks")
        for name in self.for_each_script():
            user = copy(name, self.user_dir)
            self.assert_acts(self.run_hook(user, project))
            proj = copy(name, hooks)
            self.assertEqual(self.run_hook(user, project), SILENT)
            self.assert_acts(self.run_hook(proj, project))


if __name__ == "__main__":
    unittest.main()
