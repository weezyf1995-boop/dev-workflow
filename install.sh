#!/usr/bin/env bash
# Installs the dev-workflow stack for Claude Code at user level (~/.claude), so every project gets it.
# Safe to re-run: it reinstalls the third-party skills and backs up anything of ours it replaces.
#
#   bash install.sh           install the third-party skills at the commits in install/skills.lock
#   bash install.sh --update  install their newest upstream commits and rewrite install/skills.lock
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP="$CLAUDE_DIR/skills-backup/$(date +%Y%m%d-%H%M%S)"

# The skills CLI (github.com/vercel-labs/skills), pinned so two installs weeks apart behave the same.
SKILLS_VERSION=1.7.4

# Upstream commits the workflow was last verified against. One line per skill: name, repo, commit.
REPO_LOCK="$HERE/install/skills.lock"
# Where each install records what it installed, next to a copy of the CLI's own lockfile.
LOCK_DIR="$CLAUDE_DIR/skills-lock"
# The CLI's lockfile for global (-g) installs.
CLI_LOCK="${XDG_STATE_HOME:+$XDG_STATE_HOME/skills}"
CLI_LOCK="${CLI_LOCK:-$HOME/.agents}/.skill-lock.json"

UPDATE=0
case "${1:-}" in
  "") ;;
  --update) UPDATE=1 ;;
  *) echo "Usage: bash install.sh [--update]" >&2; exit 2 ;;
esac

command -v npx >/dev/null || { echo "Node.js (npx) is required: https://nodejs.org"; exit 1; }
if [ "$UPDATE" = 1 ]; then
  command -v git >/dev/null || { echo "git is required for --update: https://git-scm.com"; exit 1; }
else
  [ -f "$REPO_LOCK" ] || { echo "$REPO_LOCK is missing. Restore it from git, or run: bash install.sh --update"; exit 1; }
fi
mkdir -p "$CLAUDE_DIR/skills"
NEW_LOCK="$(mktemp "${TMPDIR:-/tmp}/skills-lock.XXXXXX")"
trap 'rm -f "$NEW_LOCK"' EXIT

# Matt Pocock's skills, by name, so in-progress and deprecated folders in his repo stay out.
POCOCK=(grill-with-docs grill-me grilling handoff to-spec to-tickets implement tdd code-review
  codebase-design domain-modeling diagnosing-bugs prototype research triage wayfinder
  improve-codebase-architecture setup-matt-pocock-skills wizard
  ask-matt to-questionnaire wait-what teach writing-for-agents)

# Only six of Addy Osmani's skills: the rest of his pack overlaps the Pocock flow.
ADDY=(shipping-and-launch observability-and-instrumentation security-and-hardening
  deprecation-and-migration ci-cd-and-automation performance-optimization)

commit_for() { # $1 repo: its commit in the repo lockfile or, with --update, its upstream HEAD
  local c
  if [ "$UPDATE" = 1 ]; then
    c=$(git ls-remote "https://github.com/$1.git" HEAD | awk '$2 == "HEAD" { print $1 }')
  else
    c=$(awk -v r="$1" '!/^#/ && $2 == r { print $3; exit }' "$REPO_LOCK")
  fi
  if ! printf '%s\n' "$c" | grep -Eq '^[0-9a-f]{40}$'; then
    if [ "$UPDATE" = 1 ]; then echo "Could not read the upstream HEAD of github.com/$1." >&2
    else echo "$REPO_LOCK has no commit for $1. Run: bash install.sh --update" >&2; fi
    return 1
  fi
  echo "$c"
}

# The CLI installs a GitHub source at a commit given as repo#sha, and records that commit as the ref.
add() { # $1 repo, rest: skill names
  local repo="$1"; shift
  local commit; commit=$(commit_for "$repo")
  local args=(); for s in "$@"; do args+=(--skill "$s"); done
  echo "   at commit $commit"
  npx -y "skills@$SKILLS_VERSION" add "$repo#$commit" "${args[@]}" -g -a claude-code -y
  for s in "$@"; do printf '%s %s %s\n' "$s" "$repo" "$commit" >> "$NEW_LOCK"; done
}

if [ "$UPDATE" = 1 ]; then
  echo "Updating: installing the newest third-party skills and writing a fresh $REPO_LOCK"
else
  echo "Installing the third-party skills at the commits in $REPO_LOCK"
fi

echo "1/6 Matt Pocock's skills (github.com/mattpocock/skills)"
add mattpocock/skills "${POCOCK[@]}"

echo "2/6 Addy Osmani's post-commit skills (github.com/addyosmani/agent-skills)"
add addyosmani/agent-skills "${ADDY[@]}"

echo "3/6 Lockfile, into $LOCK_DIR"
mkdir -p "$LOCK_DIR"
{
  echo "# Third-party skills installed by dev-workflow's install.sh with skills@$SKILLS_VERSION."
  echo "# bash install.sh installs these commits. bash install.sh --update rewrites this file."
  echo "# skill repo commit"
  cat "$NEW_LOCK"
} > "$LOCK_DIR/skills.lock"
if [ -f "$CLI_LOCK" ]; then
  cp "$CLI_LOCK" "$LOCK_DIR/skills-cli-lock.json"
  echo "   copied the skills CLI's lockfile ($CLI_LOCK) to $LOCK_DIR/skills-cli-lock.json"
else
  echo "   the skills CLI wrote no lockfile at $CLI_LOCK, so there was nothing to copy"
fi
if [ "$UPDATE" = 1 ]; then
  cp "$LOCK_DIR/skills.lock" "$REPO_LOCK"
  echo "   wrote $REPO_LOCK. Try the new skills, then commit it."
fi
echo "   $LOCK_DIR/skills.lock:"
sed 's/^/     /' "$LOCK_DIR/skills.lock"

# Backups go outside skills/, or Claude Code would load the old copy as a second skill.
backup() { mkdir -p "$BACKUP"; mv "$1" "$BACKUP/"; echo "   backed up old $(basename "$1") to $BACKUP"; }

echo "4/6 changeable-software"
[ -e "$CLAUDE_DIR/skills/changeable-software" ] && backup "$CLAUDE_DIR/skills/changeable-software"
cp -R "$HERE/skills/changeable-software" "$CLAUDE_DIR/skills/"

echo "5/6 Workflow, loaded into every session through ~/.claude/CLAUDE.md"
[ -e "$CLAUDE_DIR/dev-workflow.md" ] && backup "$CLAUDE_DIR/dev-workflow.md"
cp "$HERE/workflow/dev-workflow.md" "$CLAUDE_DIR/dev-workflow.md"
F="$CLAUDE_DIR/CLAUDE.md"
if [ -L "$F" ]; then
  echo "   $F is a symlink, so it was left alone. Add this line to it yourself: @~/.claude/dev-workflow.md"
else
  touch "$F"
  grep -qxF "@~/.claude/dev-workflow.md" "$F" || printf "\n@~/.claude/dev-workflow.md\n" >> "$F"
fi

echo "6/6 Context-budget and relay scripts, into ~/.claude/scripts"
mkdir -p "$CLAUDE_DIR/scripts"
for s in context_guard.py context_report.py relay.sh; do
  [ -e "$CLAUDE_DIR/scripts/$s" ] && backup "$CLAUDE_DIR/scripts/$s"
  cp "$HERE/scripts/$s" "$CLAUDE_DIR/scripts/$s"
done
chmod +x "$CLAUDE_DIR/scripts/relay.sh"
echo "   The context guard only runs once its hooks are in ~/.claude/settings.json; see the README's Hooks section."

echo
echo "Done. Next, in each repo you build in, open Claude Code and run /setup-matt-pocock-skills once."
echo "To confirm the workflow loaded, run /memory in a session and look for dev-workflow.md."
