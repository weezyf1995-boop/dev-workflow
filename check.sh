#!/usr/bin/env bash
# check.sh: run every check in checks/ and report one line per check.
#
# Run it before pushing. It needs only bash, python3 and git.
#
# Each check is one executable file in checks/, run from the repo root with
# REPO_ROOT exported. Exit 0 means pass; anything else means fail. Checks run
# in lexical order, so the numeric prefix sets the sequence:
#
#   10       syntax checks
#   20-29    document checks
#   30-39    hook tests
#   40-49    relay tests
#   50-59    installer test
#
# To add a check, add a file to checks/. Do not edit this script.
#
# Exit status is 0 when every check passes and 1 otherwise. The output of each
# failing check is printed after the summary, trimmed to its last lines.

set -u

REPO_ROOT=$(cd "$(dirname "$0")" && pwd)
export REPO_ROOT
cd "$REPO_ROOT" || exit 1

TAIL_LINES=30
LOG_DIR=$(mktemp -d "${TMPDIR:-/tmp}/check.XXXXXX") || exit 1
trap 'rm -rf "$LOG_DIR"' EXIT

pass=0
fail=0
failed=""

# Sort checks in plain byte order. LC_ALL=C applies only inside the subshell,
# so the checks themselves run in the caller's locale.
while IFS= read -r check; do
  [ -f "$check" ] || continue
  name=$(basename "$check")
  log="$LOG_DIR/$name.log"
  if [ ! -x "$check" ]; then
    echo "not executable: run chmod +x $check" > "$log"
    status=1
  else
    "./$check" > "$log" 2>&1 < /dev/null
    status=$?
  fi
  if [ "$status" -eq 0 ]; then
    pass=$((pass + 1))
    printf 'PASS  %s\n' "$name"
  else
    fail=$((fail + 1))
    failed="$failed $name"
    printf 'FAIL  %s (exit %s)\n' "$name" "$status"
  fi
done < <(LC_ALL=C; printf '%s\n' checks/*)

total=$((pass + fail))
if [ "$total" -eq 0 ]; then
  echo "No checks found in checks/."
  exit 1
fi

if [ "$fail" -eq 0 ]; then
  echo "All $total checks passed."
  exit 0
fi

echo "$fail of $total checks failed:$failed"
for name in $failed; do
  echo
  echo "--- $name (last $TAIL_LINES lines) ---"
  tail -n "$TAIL_LINES" "$LOG_DIR/$name.log"
done
exit 1
