#!/usr/bin/env bash
# Watch one reviewed landing. Install updates by renaming a complete new file.
set -euo pipefail

usage() {
  echo 'Usage: merge-when-green.sh <pr-number> <reviewed-head-sha> <ruling-file> [config-file]' >&2
  exit 2
}
invalid() { printf '%s\n' "$*" >&2; exit 2; }
(( $# == 3 || $# == 4 )) || usage
pr=$1
reviewed_head=$2
ruling=$3
[[ $pr =~ ^[1-9][0-9]*$ && $reviewed_head =~ ^[0-9a-f]{40}$ ]] || usage
[[ -f $ruling && -r $ruling ]] || invalid 'missing or unreadable ruling file'

config=$(jq -ce '
  def positive: type == "number" and . == floor and . > 0;
  def string_value: type == "string" and length > 0 and (contains("\u0000") | not);
  def clock: type == "string" and test("^([01][0-9]|2[0-3]):[0-5][0-9]$");
  def window:
    (.days | type == "array" and length > 0 and all(.[]; positive and . <= 7)) and
    (.start_utc | clock) and (.end_utc | clock) and (.start_utc != .end_utc);
  .merge_queue | select(
    (.repository | string_value and test("^[^/]+/[^/]+$")) and (.main_branch | string_value) and
    (.merge_when_green | (.min_workflows | positive) and (.poll_seconds | positive) and
      (.deploy_workflow | string_value) and (.log_file | string_value) and
      (.advisory_workflow_paths | type == "array" and all(.[]; string_value)) and
      (.freeze_windows | type == "array" and all(.[]; window)) and
      (.deploy_lead_minutes | type == "number" and . == floor and . >= 0 and . < 10080)))
' "${4:-conductor.config.json}") || invalid 'invalid merge_queue config'

endpoint=repos/$(jq -r '.repository' <<< "$config")
main_branch=$(jq -r '.main_branch' <<< "$config")
main_ref=$(jq -rn --arg branch "$main_branch" '$branch | @uri')
settings=$(jq -c '.merge_when_green' <<< "$config")
deploy_workflow=$(jq -r '.deploy_workflow | @uri' <<< "$settings")
advisory=$(jq -c '.advisory_workflow_paths' <<< "$settings")
minimum=$(jq -r '.min_workflows' <<< "$settings")
poll_seconds=$(jq -r '.poll_seconds' <<< "$settings")
log_file=$(jq -r '.log_file' <<< "$settings")
mkdir -p -- "$(dirname -- "$log_file")" || invalid 'cannot create queue log directory'
: >> "$log_file" || invalid 'cannot open queue log'

log() {
  printf '%s merge-when-green #%s %.10s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$pr" "$reviewed_head" "$*" |
    tee -a -- "$log_file"
}
retry() { log "$*; retrying"; sleep "$poll_seconds"; }
stop() { local code=$1; shift; log "$*"; exit "$code"; }

# Parse the optional exception as data. Never source a ruling file.
read_override() {
  local line override=
  while IFS= read -r line || [[ -n $line ]]; do
    line=${line%$'\r'}
    if [[ $line == ALLOW_RED_DEPLOY=* ]]; then
      [[ -z $override && $line =~ ^ALLOW_RED_DEPLOY=([1-9][0-9]*:[1-9][0-9]*)$ ]] || return 1
      override=${BASH_REMATCH[1]}
    fi
  done < "$ruling" || return 1
  printf '%s' "$override"
}

read_pr() {
  gh api "$endpoint/pulls/$pr" | jq -ce '
    select((.head.sha | strings | test("^[0-9a-f]{40}$")) and
      (.base.ref | type == "string") and (.state | . == "open" or . == "closed") and
      (.draft | type == "boolean")) | {head: .head.sha, base: .base.ref, state, draft}'
}
check_pr() {
  [[ $(jq -r '.head' <<< "$1") == "$reviewed_head" ]] || stop 4 'PR head changed'
  [[ $(jq -r '.base' <<< "$1") == "$main_branch" ]] || stop 4 'PR base branch changed'
  [[ $(jq -r '.state' <<< "$1") == open ]] || stop 4 'PR is closed'
}
read_main() {
  gh api "$endpoint/commits/$main_ref" | jq -er '.sha | strings | select(test("^[0-9a-f]{40}$"))'
}

read_workflows() {
  gh api --paginate --slurp "$endpoint/actions/runs?head_sha=$reviewed_head&per_page=100" |
    jq -ce --arg head "$reviewed_head" --argjson advisory "$advisory" '
      # GitHub may append a ref to the path. Compare the complete file path.
      def file: sub("(?<extension>\\.ya?ml)@.*$"; "\(.extension)");
      def valid_run: .head_sha == $head and
        (all(.id, .workflow_id, .run_number, .run_attempt; type == "number" and . > 0)) and
        (.status | type == "string" and length > 0) and
        (.status != "completed" or (.conclusion | type == "string" and length > 0));
      select(type == "array" and length > 0 and all(.[]; .workflow_runs | type == "array")) |
      [.[].workflow_runs[]] | select(all(.[]; .path | type == "string" and length > 0)) |
      map(select((.path | file) as $path | $advisory | index($path) == null)) |
      select(all(.[]; valid_run)) |
      group_by(.workflow_id) | map(max_by([.run_number, .id, .run_attempt])) |
      {count: length, completed: (map(select(.status == "completed")) | length),
       red: [ .[] | select(.status == "completed" and .conclusion != "success" and .conclusion != "skipped") |
         "\(.path | file) \(.id):\(.run_attempt) \(.conclusion)" ]}'
}

read_deploy() {
  gh api --method GET "$endpoint/actions/workflows/$deploy_workflow/runs" -f "branch=$main_branch" -f per_page=1 |
    jq -ce --arg branch "$main_branch" '
      .workflow_runs | select(type == "array" and length <= 1) |
      if length == 0 then {status: "missing"} else .[0] |
        select(.head_branch == $branch and (all(.id, .run_attempt; type == "number" and . > 0)) and
          (.status | type == "string" and length > 0) and
          (.status != "completed" or (.conclusion | type == "string" and length > 0))) |
        {status, conclusion, run: "\(.id):\(.run_attempt)"}
      end'
}

freeze_reason() {
  local day time
  read -r day time <<< "$(date -u '+%u %H:%M')"
  jq -r --argjson day "$day" --arg time "$time" '
    def mins: split(":") | map(tonumber) | .[0] * 60 + .[1];
    (($day - 1) * 1440 + ($time | mins)) as $now | .deploy_lead_minutes as $lead |
    [ .freeze_windows[] | (.start_utc | mins) as $start |
      (((.end_utc | mins) - $start + 1440) % 1440) as $duration |
      .days[] as $day | (($day - 1) * 1440 + $start) as $begin |
      if ($now - $begin + 10080) % 10080 < $duration then "freeze is open"
      elif ($begin - $now + 10080) % 10080 <= $lead then "deploy may reach the next freeze"
      else empty end ] | first // ""
  ' <<< "$settings"
}

while true; do
  log 'checking ruling, PR, CI, deploy and freeze'
  [[ -f $ruling && -r $ruling ]] || stop 2 'ruling file went away'
  override=$(read_override) || stop 2 'invalid ALLOW_RED_DEPLOY in ruling'
  if ! candidate=$(read_pr); then retry 'could not read PR'; continue; fi
  check_pr "$candidate"
  if ! main=$(read_main); then retry 'could not read main'; continue; fi
  if ! relation=$(gh api "$endpoint/compare/$main...$reviewed_head" | jq -er '.status'); then
    retry 'could not compare main and PR head'; continue
  fi
  case "$relation" in
    ahead|identical) ;;
    behind|diverged) stop 5 'main is not under the reviewed head. Rebase needed' ;;
    *) retry 'unreadable compare status'; continue ;;
  esac

  if ! workflows=$(read_workflows); then retry 'could not read workflows'; continue; fi
  red=$(jq -r '.red | join(", ")' <<< "$workflows")
  [[ -z $red ]] || stop 3 "RED workflow: $red"
  count=$(jq -r '.count' <<< "$workflows")
  complete=$(jq -r '.completed' <<< "$workflows")

  if ! deploy=$(read_deploy); then retry 'could not read newest main deploy'; continue; fi
  deploy_status=$(jq -r '.status' <<< "$deploy")
  if [[ $deploy_status == completed ]]; then
    conclusion=$(jq -r '.conclusion' <<< "$deploy")
    run=$(jq -r '.run' <<< "$deploy")
    if [[ $conclusion != success ]]; then
      [[ $conclusion == failure && $run == "$override" ]] || stop 3 "RED main deploy: $run $conclusion"
      log "ruling allows failed main deploy $run"
    fi
  fi

  if (( count < minimum || complete != count )) || [[ $deploy_status != completed || $(jq -r '.draft' <<< "$candidate") == true ]]; then
    log "holding: $complete/$count workflows complete (floor $minimum), main deploy $deploy_status, draft $(jq -r '.draft' <<< "$candidate")"
    sleep "$poll_seconds"
    continue
  fi

  # This endpoint cannot pin main. Keep other writers out until the merge returns.
  if ! candidate=$(read_pr); then retry 'could not recheck PR'; continue; fi
  check_pr "$candidate"
  if [[ $(jq -r '.draft' <<< "$candidate") == true ]]; then retry 'PR became draft'; continue; fi
  if ! final_main=$(read_main); then retry 'could not recheck main'; continue; fi
  [[ $final_main == "$main" ]] || stop 5 'main moved during the checks. Rebase needed'
  [[ -f $ruling && -r $ruling ]] || stop 2 'ruling file went away'
  final_override=$(read_override) || stop 2 'invalid ALLOW_RED_DEPLOY in ruling'
  if [[ $final_override != "$override" ]]; then retry 'deploy exception changed'; continue; fi
  if ! hold=$(freeze_reason); then retry 'could not check freeze'; continue; fi
  if [[ -n $hold ]]; then
    log "holding: $hold"
    sleep "$poll_seconds"
    continue
  fi

  if ! result=$(gh api --method PUT "$endpoint/pulls/$pr/merge" -f merge_method=rebase -f "sha=$reviewed_head"); then
    stop 1 'merge request failed. Check PR state before retrying'
  fi
  merged=$(jq -er 'select(.merged == true) | .sha | strings | select(test("^[0-9a-f]{40}$"))' <<< "$result") ||
    stop 1 'merge result could not be confirmed. Check PR state before retrying'
  stop 0 "merged $merged (ruling: $ruling)"
done
