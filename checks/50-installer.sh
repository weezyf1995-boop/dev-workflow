#!/usr/bin/env bash
# Installer test: runs install.sh twice against a temporary HOME with a stub
# npx first on PATH (tests/installer/bin/npx), so it touches neither the real
# ~/.claude nor the network. Asserts the file tree a user would find, that the
# second run backs up replaced files outside skills/, and (via
# tests/installer/calls.py) that npx was asked for exactly the named skills
# listed in install.sh. Prints one FAIL line per failed assertion.

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

failures=0
fail() { echo "FAIL: $*"; failures=$((failures + 1)); }
ok() { echo "ok:   $*"; }
check() { # $1 description, rest: command
  local desc="$1"; shift
  if "$@"; then ok "$desc"; else fail "$desc"; fi
}

# Guard rails before anything runs.
[ "$TEST_HOME" != "$REAL_HOME" ] || { echo "FAIL: test HOME is the real HOME"; exit 1; }
found=$(PATH="$TEST_PATH" command -v npx)
[ "$found" = "$STUB_DIR/npx" ] || { echo "FAIL: npx on test PATH is $found, not the stub"; exit 1; }

run_installer() { # $1 run number
  local log="$WORK/npx-calls-$1"
  mkdir -p "$log"
  if env HOME="$TEST_HOME" PATH="$TEST_PATH" NPX_STUB_LOG="$log" \
      bash "$REPO_ROOT/install.sh" > "$WORK/run-$1.out" 2>&1; then
    ok "run $1: install.sh exited 0"
  else
    fail "run $1: install.sh exited non-zero; output:"
    sed 's/^/      /' "$WORK/run-$1.out"
  fi
  if python3 "$CALLS" "$log" "$REPO_ROOT/install.sh"; then
    ok "run $1: npx asked for exactly the named skills in install.sh"
  else
    fail "run $1: npx call assertions (see above)"
  fi
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

run_installer 1
assert_tree 1
check "run 1: nothing backed up on a fresh install" test ! -e "$C/skills-backup"

# Mark installed files so the backups can be told apart from fresh copies.
echo "MARKER-OLD-WORKFLOW" >> "$C/dev-workflow.md"
echo "MARKER-OLD-SKILL" >> "$C/skills/changeable-software/SKILL.md"
for s in context_guard.py context_report.py relay.sh; do
  echo "# MARKER-OLD-$s" >> "$C/scripts/$s"
done

run_installer 2
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

if [ "$failures" -ne 0 ]; then
  echo "$failures installer assertion(s) failed."
  exit 1
fi
echo "All installer assertions passed."
