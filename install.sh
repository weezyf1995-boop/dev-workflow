#!/usr/bin/env bash
# Installs the dev-workflow stack for Claude Code at user level (~/.claude), so every project gets it.
# Safe to re-run: it reinstalls the third-party skills and backs up anything of ours it replaces.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP="$CLAUDE_DIR/skills-backup/$(date +%Y%m%d-%H%M%S)"

command -v npx >/dev/null || { echo "Node.js (npx) is required: https://nodejs.org"; exit 1; }
mkdir -p "$CLAUDE_DIR/skills"

# Matt Pocock's skills, by name, so in-progress and deprecated folders in his repo stay out.
POCOCK=(grill-with-docs grill-me grilling handoff to-spec to-tickets implement tdd code-review
  codebase-design domain-modeling diagnosing-bugs prototype research triage wayfinder
  improve-codebase-architecture setup-matt-pocock-skills resolving-merge-conflicts wizard
  ask-matt to-questionnaire wait-what teach writing-for-agents)

# Only six of Addy Osmani's skills: the rest of his pack overlaps the Pocock flow.
ADDY=(shipping-and-launch observability-and-instrumentation security-and-hardening
  deprecation-and-migration ci-cd-and-automation performance-optimization)

add() { # $1 repo, rest: skill names
  local repo="$1"; shift
  local args=(); for s in "$@"; do args+=(--skill "$s"); done
  npx -y skills@latest add "$repo" "${args[@]}" -g -a claude-code -y
}

echo "1/4 Matt Pocock's skills (github.com/mattpocock/skills)"
add mattpocock/skills "${POCOCK[@]}"

echo "2/4 Addy Osmani's post-commit skills (github.com/addyosmani/agent-skills)"
add addyosmani/agent-skills "${ADDY[@]}"

# Backups go outside skills/, or Claude Code would load the old copy as a second skill.
backup() { mkdir -p "$BACKUP"; mv "$1" "$BACKUP/"; echo "   backed up old $(basename "$1") to $BACKUP"; }

echo "3/4 changeable-software"
[ -e "$CLAUDE_DIR/skills/changeable-software" ] && backup "$CLAUDE_DIR/skills/changeable-software"
cp -R "$HERE/skills/changeable-software" "$CLAUDE_DIR/skills/"

echo "4/4 Workflow, loaded into every session through ~/.claude/CLAUDE.md"
[ -e "$CLAUDE_DIR/dev-workflow.md" ] && backup "$CLAUDE_DIR/dev-workflow.md"
cp "$HERE/workflow/dev-workflow.md" "$CLAUDE_DIR/dev-workflow.md"
F="$CLAUDE_DIR/CLAUDE.md"
if [ -L "$F" ]; then
  echo "   $F is a symlink, so it was left alone. Add this line to it yourself: @~/.claude/dev-workflow.md"
else
  touch "$F"
  grep -qxF "@~/.claude/dev-workflow.md" "$F" || printf "\n@~/.claude/dev-workflow.md\n" >> "$F"
fi

echo
echo "Done. Next, in each repo you build in, open Claude Code and run /setup-matt-pocock-skills once."
echo "To confirm the workflow loaded, run /memory in a session and look for dev-workflow.md."
