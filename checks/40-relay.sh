#!/usr/bin/env bash
# Tests scripts/relay.sh through its real entry point (argv, PATH, stdout,
# stderr, exit status). A stub `open` is first on PATH and records its calls,
# so no real application is ever launched. Branches that need Darwin or a
# non-Darwin machine are skipped where they do not apply.

set -u
cd "${REPO_ROOT:-.}" || exit 1
RELAY="$PWD/scripts/relay.sh"

T=$(mktemp -d "${TMPDIR:-/tmp}/relay-test.XXXXXX") || exit 1
trap 'rm -rf "$T"' EXIT

STUB="$T/stub"
mkdir -p "$STUB" "$T/dir with space"
cat > "$STUB/open" <<'STUBEOF'
#!/bin/sh
printf '%s\n' "$1" >> "$OPEN_LOG"
STUBEOF
chmod +x "$STUB/open"
OPEN_LOG="$T/open.log"
export OPEN_LOG

FOLDER="$T/dir with space"
fails=0

fail() { echo "FAIL [$CASE]: $*"; fails=$((fails + 1)); }

# run_relay <args...>: sets RC and fills $T/out, $T/err; resets the open log.
run_relay() {
  : > "$OPEN_LOG"
  PATH="$STUB:$PATH" bash "$RELAY" "$@" > "$T/out" 2> "$T/err"
  RC=$?
}

expect_rc() { [ "$RC" -eq "$1" ] || fail "exit $RC, expected $1"; }
expect_open_not_called() { [ ! -s "$OPEN_LOG" ] || fail "open was called: $(cat "$OPEN_LOG")"; }
expect_stdout_empty() { [ ! -s "$T/out" ] || fail "stdout not empty: $(cat "$T/out")"; }
expect_stderr_has() { grep -qF -- "$1" "$T/err" || fail "stderr lacks '$1': $(cat "$T/err")"; }
expect_stderr_empty() { [ ! -s "$T/err" ] || fail "stderr not empty: $(cat "$T/err")"; }

# The limit comes from relay.sh's own source.
LIMIT=$(sed -n 's/.*\${#prompt} <= \([0-9][0-9]*\).*/\1/p' "$RELAY" | head -n 1)
case "$LIMIT" in
  ''|*[!0-9]*) echo "could not read the prompt limit from scripts/relay.sh"; exit 1 ;;
esac

make_prompt() { python3 -c 'import sys; sys.stdout.write("a" * int(sys.argv[1]))' "$1"; }

# ---- argument validation (every platform) ----

CASE="no arguments"
run_relay
expect_rc 2; expect_stdout_empty; expect_stderr_has "usage:"; expect_open_not_called

CASE="missing prompt"
run_relay "$FOLDER"
expect_rc 2; expect_stdout_empty; expect_stderr_has "usage:"; expect_open_not_called

CASE="relative folder"
run_relay "relative/dir" "hello"
expect_rc 2; expect_stdout_empty; expect_stderr_has "not an absolute folder"; expect_open_not_called

CASE="folder does not exist"
run_relay "$T/no such dir" "hello"
expect_rc 2; expect_stdout_empty; expect_stderr_has "not an absolute folder"; expect_open_not_called

CASE="folder is a file"
: > "$T/afile"
run_relay "$T/afile" "hello"
expect_rc 2; expect_stdout_empty; expect_stderr_has "not an absolute folder"; expect_open_not_called

CASE="prompt at limit+1"
run_relay "$FOLDER" "$(make_prompt $((LIMIT + 1)))"
expect_rc 2; expect_stdout_empty; expect_stderr_has "handoff file"; expect_open_not_called

CASE="prompt at the limit passes validation"
run_relay "$FOLDER" "$(make_prompt "$LIMIT")"
expect_rc 0; expect_stderr_empty

# ---- non-macOS path ----

PROMPT="it's a \"test\" & 100% done: héllo wörld ✓ 日本語"

if [ "$(uname)" != Darwin ]; then
  CASE="non-macOS valid call"
  run_relay "$FOLDER" "$PROMPT"
  expect_rc 0; expect_stderr_empty; expect_open_not_called
  printf '%s\n%s\n' \
    "relay: no desktop app here. Start a fresh session in $FOLDER and send:" \
    "$PROMPT" > "$T/expected"
  cmp -s "$T/expected" "$T/out" || fail "stdout differs from expected instruction + prompt"

  CASE="non-macOS multiple prompt words are joined"
  run_relay "$FOLDER" one two "three four"
  expect_rc 0; expect_stderr_empty; expect_open_not_called
  [ "$(tail -n 1 "$T/out")" = "one two three four" ] || fail "prompt not joined: $(cat "$T/out")"
else
  echo "skip: non-macOS branch (running on Darwin)"
fi

# ---- macOS path ----

if [ "$(uname)" = Darwin ]; then
  CASE="macOS valid call"
  run_relay "$FOLDER" "$PROMPT"
  expect_rc 0; expect_stderr_empty
  EXPECTED=$(python3 -c 'import sys, urllib.parse as u; print("claude://code/new?folder=" + u.quote(sys.argv[1], safe="") + "&q=" + u.quote(sys.argv[2], safe=""))' "$FOLDER" "$PROMPT")
  case "$(cat "$OPEN_LOG")" in
    "claude://code/new?folder="*) ;;
    *) fail "URL does not start with claude://code/new?folder=: $(cat "$OPEN_LOG")" ;;
  esac
  [ "$(wc -l < "$OPEN_LOG" | tr -d ' ')" = 1 ] || fail "open not called exactly once"
  [ "$(cat "$OPEN_LOG")" = "$EXPECTED" ] || fail "URL mismatch: got $(cat "$OPEN_LOG") expected $EXPECTED"
  grep -qF "opened a new Code session" "$T/out" || fail "stdout does not confirm the session opened: $(cat "$T/out")"
else
  echo "skip: macOS branch (not Darwin)"
fi

if [ "$fails" -ne 0 ]; then
  echo "$fails relay assertion(s) failed."
  exit 1
fi
echo "relay: all cases passed."
