#!/usr/bin/env bash
# Check one candidate before a push or ready toggle. Start from a frozen script.
set -eo pipefail

if [[ ${1:-} != --frozen ]]; then
  frozen=$(mktemp "${TMPDIR:-/tmp}/conductor-push-gate.XXXXXX")
  trap 'rm -f -- "$frozen"' EXIT
  cp -- "${BASH_SOURCE[0]}" "$frozen"
  bash "$frozen" --frozen "$@"
  exit
fi
shift

fail() { printf 'GATE FAIL: %s\n' "$*" >&2; exit 1; }
usage() {
  echo 'Usage: push-gate.sh <worktree> <pr-number-or-body-file> <base-ref> [config-file]' >&2
  exit 2
}
(( $# == 3 || $# == 4 )) || usage

caller=$PWD
pr_body=$2
base_ref=$3
config_file=${4:-}
if [[ -n $config_file && $config_file != /* ]]; then
  config_file=$caller/$config_file
fi
cd -P -- "$1" || fail 'cannot open worktree'
[[ $(git rev-parse --show-toplevel) == "$PWD" ]] || fail 'use the worktree root'

scratch=$(mktemp -d "${TMPDIR:-/tmp}/conductor-push-checks.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
config=$(jq -ce '.merge_queue' "${config_file:-conductor.config.json}") || fail 'cannot read merge_queue config'
jq -e '
  def argument: type == "string" and (contains("\u0000") | not);
  def strings: type == "array" and all(.[]; argument and length > 0);
  def nonempty: strings and length > 0;
  def command: type == "array" and (.[0] | argument and length > 0) and all(.[]; argument);
  def positive: type == "number" and . == floor and . > 0;
  .push_gate |
  (.pr_description_command | command) and (.secret_scan_command | command) and
  (.history_walk_command | . == [] or command) and (.test_command | command) and (.test_paths | nonempty) and
  (.test_families | type == "array" and length > 0 and all(.[];
    (.name | type == "string" and length > 0) and (.paths | nonempty) and (.min_files | positive))) and
  (.reader_path_prefixes | strings and all(.[]; endswith("/"))) and
  (.module_test_names | strings and all(.[]; split("{module}") | length == 2)) and
  (.blocking_suites | type == "array" and all(.[];
    (.name | type == "string" and length > 0) and (.inputs | nonempty) and (.command | command)))
' <<< "$config" >/dev/null || fail 'invalid push_gate config'
gate=$(jq -c '.push_gate' <<< "$config")

export CONDUCTOR_WORKTREE=$PWD
CONDUCTOR_BASE=$(git rev-parse --verify --end-of-options "${base_ref}^{commit}") || fail 'cannot read base'
CONDUCTOR_HEAD=$(git rev-parse --verify 'HEAD^{commit}') || fail 'cannot read head'
CONDUCTOR_RANGE=$CONDUCTOR_BASE..$CONDUCTOR_HEAD
git merge-base --is-ancestor "$CONDUCTOR_BASE" "$CONDUCTOR_HEAD" || fail 'base must be under the candidate head'
export CONDUCTOR_BASE CONDUCTOR_HEAD CONDUCTOR_RANGE
check_worktree() {
  local status head
  status=$(git status --porcelain --untracked-files=no) || fail 'cannot read worktree status'
  head=$(git rev-parse --verify 'HEAD^{commit}') || fail 'cannot read head'
  [[ -z $status && $head == "$CONDUCTOR_HEAD" ]] || fail 'candidate head or tracked files changed'
}
check_worktree

CONDUCTOR_PR_BODY=$scratch/pr-body
export CONDUCTOR_PR_BODY
if [[ $pr_body =~ ^[1-9][0-9]*$ ]]; then
  repository=$(jq -er '.repository | select(test("^[^/]+/[^/]+$"))' <<< "$config") || fail 'set merge_queue.repository'
  gh pr view "$pr_body" --repo "$repository" --json body --jq '.body' > "$CONDUCTOR_PR_BODY" || fail 'cannot read PR description'
else
  [[ $pr_body == /* ]] || pr_body=$caller/$pr_body
  cp -- "$pr_body" "$CONDUCTOR_PR_BODY" || fail 'cannot read local PR description'
fi

git rev-list --parents "$CONDUCTOR_RANGE" > "$scratch/commits" || fail 'cannot read commit range'
CONDUCTOR_COMMIT_COUNT=$(wc -l < "$scratch/commits")
CONDUCTOR_COMMIT_COUNT=$((CONDUCTOR_COMMIT_COUNT))
(( CONDUCTOR_COMMIT_COUNT > 0 )) || fail 'candidate has no commits above the base'
export CONDUCTOR_COMMIT_COUNT
while read -r commit parent rest; do
  if git diff-tree --quiet "$parent" "$commit" --; then
    fail "empty commit $commit"
  else
    [[ $? == 1 ]] || fail "cannot compare the tree of $commit to its first parent"
  fi
done < "$scratch/commits"

# Use NUL separators to preserve multiple arguments and paths with spaces.
decode_arguments() {
  local filter=$1 json=$2 argument
  jq -j "$filter | ., \"\u0000\"" <<< "$json" > "$scratch/argv" || fail 'cannot decode config arguments'
  decoded=()
  while IFS= read -r -d '' argument; do
    decoded+=("$argument")
  done < "$scratch/argv"
}

run_check() {
  local label=$1 command=$2
  shift 2
  decode_arguments '.[]' "$command"
  if (( ${#decoded[@]} > 0 )); then
    printf 'Checking %s\n' "$label"
    ("${decoded[@]}" "$@") || fail "$label"
  fi
}
run_check 'PR description' "$(jq -c '.pr_description_command' <<< "$gate")"
run_check 'range secret scan' "$(jq -c '.secret_scan_command' <<< "$gate")"
run_check 'history walk' "$(jq -c '.history_walk_command' <<< "$gate")"

# Keep both sides of renames so suites that read the old path also run.
git diff --name-only --no-renames -z "$CONDUCTOR_RANGE" -- > "$scratch/changed" || fail 'cannot list changed paths'
git ls-files -z -- > "$scratch/tracked" || fail 'cannot list tracked tests'

matches() {
  local path=$1 pattern
  shift
  for pattern in "$@"; do
    [[ $path == $pattern ]] && return 0
  done
  return 1
}

decode_arguments '.test_paths[]' "$gate"
test_patterns=("${decoded[@]}")
decode_arguments '.reader_path_prefixes[]' "$gate"
prefixes=("${decoded[@]}")
decode_arguments '.module_test_names[]' "$gate"
module_patterns=("${decoded[@]}")

changed=()
modules=()
: > "$scratch/reader-paths"
while IFS= read -r -d '' path; do
  changed+=("$path")
  if matches "$path" "${test_patterns[@]}"; then
    continue
  fi
  [[ $path != *$'\n'* ]] || fail 'a changed path contains a newline'
  printf '%s\n' "$path" >> "$scratch/reader-paths"
  for prefix in "${prefixes[@]}"; do
    [[ $path == "$prefix"* ]] && printf '%s\n' "${path#"$prefix"}" >> "$scratch/reader-paths"
  done
  module=${path##*/}
  modules+=("${module%.*}")
done < "$scratch/changed"

tests=()
while IFS= read -r -d '' path; do
  if matches "$path" "${test_patterns[@]}"; then
    [[ -f $path ]] || fail "tracked test is missing: $path"
    tests+=("$path")
  fi
done < "$scratch/tracked"

# Record each family separately so changed tests cannot satisfy a broken glob.
: > "$scratch/selected"
jq -c '.test_families[]' <<< "$gate" > "$scratch/families"
while IFS= read -r family; do
  name=$(jq -r '.name' <<< "$family")
  floor=$(jq -r '.min_files' <<< "$family")
  decode_arguments '.paths[]' "$family"
  count=0
  for path in "${tests[@]}"; do
    if matches "$path" "${decoded[@]}"; then
      printf '%s\n' "$path" >> "$scratch/selected"
      count=$((count + 1))
    fi
  done
  (( count >= floor )) || fail "family $name selected $count files, needs $floor"
  printf 'Family %s selected %s files\n' "$name" "$count"
done < "$scratch/families"

named_for_module() {
  local filename=${1##*/} module pattern before after
  for module in "${modules[@]}"; do
    for pattern in "${module_patterns[@]}"; do
      before=${pattern%%\{module\}*}
      after=${pattern#*\{module\}}
      [[ $filename == $before"$module"$after ]] && return 0
    done
  done
  return 1
}

for path in "${tests[@]}"; do
  [[ $path != *$'\n'* ]] || fail 'a test path contains a newline'
  for changed_path in "${changed[@]}"; do
    if [[ $path == "$changed_path" ]]; then
      printf '%s\n' "$path" >> "$scratch/selected"
      continue 2
    fi
  done
  if named_for_module "$path"; then
    printf '%s\n' "$path" >> "$scratch/selected"
  elif [[ -s $scratch/reader-paths ]]; then
    if grep -Fq -f "$scratch/reader-paths" -- "$path"; then
      printf '%s\n' "$path" >> "$scratch/selected"
    else
      [[ $? == 1 ]] || fail "cannot inspect test: $path"
    fi
  fi
done

jq -c '.blocking_suites[]' <<< "$gate" > "$scratch/suites"
while IFS= read -r suite; do
  decode_arguments '.inputs[]' "$suite"
  for path in "${changed[@]}"; do
    if matches "$path" "${decoded[@]}"; then
      run_check "$(jq -r '.name' <<< "$suite")" "$(jq -c '.command' <<< "$suite")"
      break
    fi
  done
done < "$scratch/suites"

LC_ALL=C sort -u "$scratch/selected" > "$scratch/tests"
selected=()
while IFS= read -r path; do selected+=("./$path"); done < "$scratch/tests"
(( ${#selected[@]} > 0 )) || fail 'no test files selected'
printf 'Selected %s distinct tests\n' "${#selected[@]}"
run_check 'selected tests' "$(jq -c '.test_command' <<< "$gate")" "${selected[@]}"
check_worktree
printf 'GATE PASS: %s\n' "$CONDUCTOR_RANGE"
