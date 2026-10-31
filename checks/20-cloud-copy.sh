#!/usr/bin/env bash
# Fail when the committed cloud skill copy or template.sha differs from what
# scripts/build_cloud_skill.sh would produce from workflow/dev-workflow.md.
# Runs the generator into a temp directory and diffs each file against the
# copy in the repo, so a hand edit to either is caught.

set -u
cd "${REPO_ROOT:-.}" || exit 1

generator=scripts/build_cloud_skill.sh
if [ ! -f "$generator" ]; then
  echo "$generator: missing"
  exit 1
fi

out=$(mktemp -d "${TMPDIR:-/tmp}/cloud-copy.XXXXXX") || exit 1
trap 'rm -rf "$out"' EXIT

if ! bash "$generator" "$out"; then
  echo "$generator: failed"
  exit 1
fi

drift=0
for file in cloud/dev-workflow/SKILL.md template.sha; do
  if [ ! -f "$file" ]; then
    echo "$file: missing; run $generator"
    drift=1
  elif ! diff -u "$file" "$out/$file" > "$out/diff.txt"; then
    echo "$file: differs from generator output; edit workflow/dev-workflow.md and run $generator"
    head -n 20 "$out/diff.txt"
    drift=1
  fi
done

[ "$drift" -eq 0 ] || exit 1
echo "cloud copy and template.sha match the generator."
