#!/bin/bash
# Hands work to a fresh Claude Code session: the Fable-to-Opus build start and the 400k relaunch.
# Rules live in ~/.claude/dev-workflow.md ("Who can fire what", step 4, "Context budget").
# On macOS it opens a new Code session in the desktop app with the prompt typed in; the user confirms the
# folder and presses Enter (a deep link never sends on its own). Anywhere else it prints what to paste.
# Usage: relay.sh <absolute folder> <prompt...>
set -euo pipefail

[[ $# -ge 2 ]] || { echo "usage: relay.sh <absolute folder> <prompt...>" >&2; exit 2; }
folder="$1"; shift; prompt="$*"
[[ "$folder" == /* && -d "$folder" ]] || { echo "relay: not an absolute folder: $folder" >&2; exit 2; }
(( ${#prompt} <= 5000 )) || { echo "relay: prompt over 5,000 characters; put it in the handoff file and pass the path" >&2; exit 2; }

if [[ "$(uname)" != Darwin ]]; then
  echo "relay: no desktop app here. Start a fresh session in $folder and send:"
  echo "$prompt"
  exit 0
fi

url=$(python3 -c 'import sys, urllib.parse as u; print("claude://code/new?folder=" + u.quote(sys.argv[1], safe="") + "&q=" + u.quote(sys.argv[2], safe=""))' "$folder" "$prompt")
open "$url"
echo "relay: opened a new Code session in $folder with the prompt typed in. Confirm the folder and press Enter there; this session stops here."
