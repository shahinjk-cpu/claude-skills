#!/bin/sh
# run-slot.sh <command...>: run a heavy local command (a test suite, a type check, a build) in one of SLOTS shared
# slots, first come first served across every agent and window on this machine. Each waiter writes a ticket; only
# the oldest SLOTS waiting tickets may try a slot. Tickets move to an archive folder when their run exits, and the
# queue scan forks nothing per ticket, so a hundred waiters stay cheap.
# If a step also needs a single shared resource (one local database, one port), take the slot FIRST and the
# resource lock INSIDE: run-slot.sh lockf -k /path/resource.lock <command...>
D="${RUN_SLOT_DIR:-$HOME/.agent-runs/run-slot}"
Q="$D/queue"; A="$D/archive"; SLOTS="${RUN_SLOTS:-2}"
mkdir -p "$Q" "$A"
# macOS has lockf (busy = exit 75); Linux has flock (told to use 75 for busy too).
if command -v lockf >/dev/null 2>&1; then LOCK="lockf -s -t 0 -k"; else LOCK="flock -n -E 75"; fi
ME="$(printf '%010d-%08d' "$(date +%s)" "$$")"
: > "$Q/$ME"
trap 'mv -f "$Q/$ME" "$A/" 2>/dev/null; mv -f "$Q/$ME.run" "$A/" 2>/dev/null' EXIT
trap 'exit 130' INT TERM HUP
waiting() {
  now=$(date +%s)
  for f in "$Q"/*; do
    [ -e "$f" ] || continue
    n=${f##*/}
    [ "${n%.run}" != "$n" ] && continue
    [ -e "$Q/$n.run" ] && continue
    t=${n%%-*}; t=${t#"${t%%[!0]*}"}; p=${n##*-}; p=${p#"${p%%[!0]*}"}; t=${t:-0}; p=${p:-0}
    [ $((now - t)) -lt 21600 ] || continue
    kill -0 "$p" 2>/dev/null || continue
    echo "$n"
  done | sort | head -n "$SLOTS"
}
while :; do
  if waiting | grep -qx "$ME"; then
    i=1
    while [ "$i" -le "$SLOTS" ]; do
      $LOCK "$D/slot-$i.lock" sh -c ': > "$0.run"; exec "$@"' "$Q/$ME" "$@"
      rc=$?
      [ "$rc" -ne 75 ] && exit "$rc"
      i=$((i + 1))
    done
  fi
  sleep 3
done
