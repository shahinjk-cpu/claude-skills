#!/bin/bash
# oc-build.sh <worktree> <brief-file> [log-file] [provider/model]
# Runs ONE opencode builder on EASY work inside a git worktree, with cloud credentials and tokens removed from its
# environment and the deny-list config opencode-guard.json applied. The caller reviews the diff, runs the tests,
# commits and pushes. Never give it secrets, production data, or money/auth/security/infra/migration work.
set -uo pipefail
WT=${1:?worktree}; BRIEF=${2:?brief file}; LOG=${3:-$WT/.oc-build.log}; MODEL=${4:-opencode/deepseek-v4.1-flash-free}
[ -e "$WT/.git" ] || { echo "STOP: $WT is not a git worktree"; exit 2; }
[ -f "$WT/.git" ] || { echo "STOP: $WT looks like a main checkout, not a worktree; make one with git worktree add"; exit 2; }
D=$(cd "$(dirname "$0")" && pwd)
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    -u GOOGLE_APPLICATION_CREDENTIALS -u AZURE_CLIENT_SECRET -u GH_TOKEN -u GITHUB_TOKEN \
    -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u OPENROUTER_API_KEY -u NPM_TOKEN \
    AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null OPENCODE_CONFIG="$D/opencode-guard.json" \
    opencode run -m "$MODEL" --dir "$WT" "$(cat "$BRIEF")" > "$LOG" 2>&1
rc=$?; echo "oc-build rc=$rc model=$MODEL log=$LOG"; exit $rc
