#!/usr/bin/env bash
# Installer test: runs install.sh twice, then a copy of the repo's install.sh
# with --update, against a temporary HOME with stub npx and git first on PATH
# (tests/installer/bin), so it touches neither the real ~/.claude, the repo's
# install/skills.lock, nor the network. Asserts the file tree a user would
# find, that the second run backs up replaced files outside skills/, the
# lockfiles each run writes, and (via tests/installer/calls.py) that npx ran
# the pinned skills CLI for exactly the named skills in install.sh, at the
# commits in the lockfile. Prints one FAIL line per failed assertion.

set -u
REPO_ROOT=${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$REPO_ROOT" || exit 1

STUB_DIR="$REPO_ROOT/tests/installer/bin"
CALLS="$REPO_ROOT/tests/installer/calls.py"
REAL_HOME=$HOME

WORK=$(mktemp -d "${TMPDIR:-/tmp}/installer-test.XXXXXX") || exit 1
WORK=$(cd "$WORK" && pwd -P)
trap 'rm -rf "$WORK"' EXIT
TEST_HOME="$WORK/home"
mkdir -p "$TEST_HOME"
C="$TEST_HOME/.claude"
TEST_PATH="$STUB_DIR:$PATH"
REPO_LOCK="$REPO_ROOT/install/skills.lock"
# The commit the stub git reports as every upstream HEAD during --update.
STUB_HEAD=1111111111111111111111111111111111111111

failures=0
fail() { echo "FAIL: $*"; failures=$((failures + 1)); }
ok() { echo "ok:   $*"; }
check() { # $1 description, rest: command
  local desc="$1"; shift
  if "$@"; then ok "$desc"; else fail "$desc"; fi
}

# Guard rails before anything runs.
[ "$TEST_HOME" != "$REAL_HOME" ] || { echo "FAIL: test HOME is the real HOME"; exit 1; }
for tool in npx git; do
  found=$(PATH="$TEST_PATH" command -v "$tool")
  [ "$found" = "$STUB_DIR/$tool" ] || { echo "FAIL: $tool on test PATH is $found, not the stub"; exit 1; }
done

no_latest() { ! grep -n latest "$REPO_ROOT/install.sh"; }
check "install.sh never asks for the latest CLI" no_latest
committed() { git -C "$REPO_ROOT" ls-files --error-unmatch "$1" > /dev/null 2>&1; }
check "install/skills.lock is committed" committed install/skills.lock

run_installer() { # $1 run number, $2 installer to run, rest: its arguments
  local n="$1" installer="$2"; shift 2
  local log="$WORK/npx-calls-$n"
  mkdir -p "$log"
  if env -u XDG_STATE_HOME HOME="$TEST_HOME" PATH="$TEST_PATH" NPX_STUB_LOG="$log" \
      GIT_STUB_HEAD="${GIT_STUB_HEAD:-}" GIT_STUB_LOG="$WORK/git-calls-$n" \
      bash "$installer" "$@" > "$WORK/run-$n.out" 2>&1; then
    ok "run $n: install.sh $* exited 0"
  else
    fail "run $n: install.sh $* exited non-zero; output:"
    sed 's/^/      /' "$WORK/run-$n.out"
  fi
}

assert_calls() { # $1 run number, $2 lockfile the commits must come from, rest: calls.py flags
  local n="$1" lock="$2"; shift 2
  if python3 "$CALLS" "$WORK/npx-calls-$n" "$REPO_ROOT/install.sh" "$lock" "$@"; then
    ok "run $n: pinned CLI asked for exactly the named skills in install.sh, at the commits in $lock"
  else
    fail "run $n: npx call assertions (see above)"
  fi
}

# The commits in a lockfile, one "repo commit" line per repo.
lock_commits() { awk '!/^#/ && NF == 3 { print $2, $3 }' "$1" | sort -u; }

assert_restore() { # $1 run number: a default install, restored from install/skills.lock
  local r="run $1"
  assert_calls "$1" "$REPO_LOCK"
  check "$r: did not ask git for upstream commits" test ! -e "$WORK/git-calls-$1"
  check "$r: recorded what it installed in ~/.claude/skills-lock/skills.lock" \
    test "$(lock_commits "$C/skills-lock/skills.lock")" = "$(lock_commits "$REPO_LOCK")"
  check "$r: copied the CLI's lockfile to ~/.claude/skills-lock/" \
    cmp -s "$TEST_HOME/.agents/.skill-lock.json" "$C/skills-lock/skills-cli-lock.json"
  local first; first=$(lock_commits "$REPO_LOCK" | head -n 1)
  check "$r: printed the lockfile" grep -qF "${first#* }" "$WORK/run-$1.out"
}

assert_tree() { # $1 run number
  local r="run $1"
  check "$r: workflow file installed" cmp -s "$REPO_ROOT/workflow/dev-workflow.md" "$C/dev-workflow.md"
  for s in context_guard.py context_report.py relay.sh; do
    check "$r: scripts/$s installed" cmp -s "$REPO_ROOT/scripts/$s" "$C/scripts/$s"
  done
  check "$r: scripts/relay.sh executable" test -x "$C/scripts/relay.sh"
  check "$r: changeable-software skill copied" \
    diff -r "$REPO_ROOT/skills/changeable-software" "$C/skills/changeable-software"
  local n
  n=$(grep -cxF "@~/.claude/dev-workflow.md" "$C/CLAUDE.md" 2>/dev/null)
  check "$r: CLAUDE.md import line present exactly once (found ${n:-0})" test "${n:-0}" -eq 1
  check "$r: existing CLAUDE.md content kept" grep -qxF "# my own notes" "$C/CLAUDE.md"
  check "$r: no backup folder inside skills/" test ! -e "$C/skills/skills-backup"
}

# A user who already has a CLAUDE.md of their own.
mkdir -p "$C"
echo "# my own notes" > "$C/CLAUDE.md"

run_installer 1 "$REPO_ROOT/install.sh"
assert_restore 1
assert_tree 1
check "run 1: nothing backed up on a fresh install" test ! -e "$C/skills-backup"

# Mark installed files so the backups can be told apart from fresh copies.
echo "MARKER-OLD-WORKFLOW" >> "$C/dev-workflow.md"
echo "MARKER-OLD-SKILL" >> "$C/skills/changeable-software/SKILL.md"
for s in context_guard.py context_report.py relay.sh; do
  echo "# MARKER-OLD-$s" >> "$C/scripts/$s"
done

run_installer 2 "$REPO_ROOT/install.sh"
assert_restore 2
assert_tree 2

# Backups from run 2: one or more skills-backup/YYYYmmdd-HHMMSS folders
# (runs in the same second share one), holding the marked old copies.
backup_dirs=$(ls "$C/skills-backup" 2>/dev/null)
check "run 2: backup folder created at ~/.claude/skills-backup/" test -n "$backup_dirs"
for d in $backup_dirs; do
  case "$d" in
    [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]) ;;
    *) fail "run 2: unexpected backup folder name $d" ;;
  esac
done
backed_up() { # $1 name, $2 marker: some backup folder holds $1 containing $2
  local d
  for d in $backup_dirs; do
    local f="$C/skills-backup/$d/$1"
    [ -d "$f" ] && f="$f/SKILL.md"
    grep -qF "$2" "$f" 2>/dev/null && return 0
  done
  return 1
}
check "run 2: old dev-workflow.md backed up" backed_up dev-workflow.md MARKER-OLD-WORKFLOW
check "run 2: old changeable-software backed up" backed_up changeable-software MARKER-OLD-SKILL
for s in context_guard.py context_report.py relay.sh; do
  check "run 2: old $s backed up" backed_up "$s" "MARKER-OLD-$s"
done
stray=$(grep -rlF MARKER-OLD "$C/skills" "$C/scripts" "$C/dev-workflow.md" 2>/dev/null)
check "run 2: no old copy left under skills/, scripts/ or the workflow file${stray:+ ($stray)}" test -z "$stray"

# --update runs from a copy of the repo, so the lockfile it rewrites is not ours,
# and in a fresh HOME, so its backups cannot collide with run 2's in the same second.
TEST_HOME="$WORK/home-update"
C="$TEST_HOME/.claude"
mkdir -p "$C"
echo "# my own notes" > "$C/CLAUDE.md"
COPY="$WORK/repo"
mkdir -p "$COPY"
for p in install.sh install skills workflow scripts; do cp -R "$REPO_ROOT/$p" "$COPY/"; done
GIT_STUB_HEAD=$STUB_HEAD run_installer 3 "$COPY/install.sh" --update
assert_calls 3 "$COPY/install/skills.lock" --exact-lock
assert_tree 3
r="run 3 (--update)"
asked=$(sort "$WORK/git-calls-3" 2>/dev/null | tr '\n' ' ')
check "$r: asked git for each upstream HEAD (asked: $asked)" test "$asked" = \
  "https://github.com/addyosmani/agent-skills.git https://github.com/mattpocock/skills.git "
check "$r: rewrote install/skills.lock with the upstream HEAD commits" \
  test "$(lock_commits "$COPY/install/skills.lock" | cut -d' ' -f2 | sort -u)" = "$STUB_HEAD"
differs() { ! cmp -s "$1" "$2"; }
check "$r: the new lockfile differs from the committed one" differs "$REPO_LOCK" "$COPY/install/skills.lock"
check "$r: ~/.claude/skills-lock/skills.lock matches the new lockfile" \
  cmp -s "$COPY/install/skills.lock" "$C/skills-lock/skills.lock"
check "$r: the CLI's lockfile copy records the new commits" \
  grep -qF "\"ref\": \"$STUB_HEAD\"" "$C/skills-lock/skills-cli-lock.json"
check "$r: the repo's own lockfile is untouched" git -C "$REPO_ROOT" diff --quiet -- install/skills.lock

if [ "$failures" -ne 0 ]; then
  echo "$failures installer assertion(s) failed."
  exit 1
fi
echo "All installer assertions passed."
