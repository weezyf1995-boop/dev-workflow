#!/usr/bin/env bash
# Syntax-check every .sh file (and extensionless file with a shell shebang) with bash -n and every .py file by compiling it
# in memory, so no __pycache__ is written. Covers tracked files and untracked
# files that are not ignored. Prints each broken file and its error.

set -u
cd "${REPO_ROOT:-.}" || exit 1

broken=0
count=0

while IFS= read -r -d '' file; do
  [ -f "$file" ] || continue
  case "$file" in
    *.sh)
      count=$((count + 1))
      if ! out=$(bash -n "$file" 2>&1); then
        echo "$file: bash syntax error"
        echo "$out"
        broken=$((broken + 1))
      fi
      ;;
    *.py)
      count=$((count + 1))
      if ! out=$(python3 -c 'import sys, traceback
path = sys.argv[1]
with open(path, "rb") as f:
    source = f.read()
try:
    compile(source, path, "exec", dont_inherit=True)
except (SyntaxError, ValueError) as e:
    sys.stdout.write("".join(traceback.format_exception_only(type(e), e)))
    sys.exit(1)' "$file" 2>&1); then
        echo "$file: python syntax error"
        echo "$out"
        broken=$((broken + 1))
      fi
      ;;
    *.*) ;;
    *)
      # An extensionless file with a bash or sh shebang is a shell script too.
      case "$(head -n 1 "$file" 2>/dev/null)" in
        '#!'*bash*|'#!'*/sh|'#!'*' sh') ;;
        *) continue ;;
      esac
      count=$((count + 1))
      if ! out=$(bash -n "$file" 2>&1); then
        echo "$file: bash syntax error"
        echo "$out"
        broken=$((broken + 1))
      fi
      ;;
  esac
done < <(git ls-files -z --cached --others --exclude-standard)

if [ "$broken" -ne 0 ]; then
  echo "$broken of $count files have syntax errors."
  exit 1
fi
echo "$count files checked."
