#!/usr/bin/env bash
# Auto-snapshot the repo on an interval, but only when there are changes.
#
# Local commits only by default (nothing is pushed). Set AUTOCOMMIT_PUSH=1 to
# also push each snapshot to origin/HEAD.
#
#   Start:  nohup setsid bash autocommit_logic/autocommit.sh >> autocommit.log 2>&1 &
#   Stop:   kill "$(cat .autocommit.pid)"
#   Tune:   AUTOCOMMIT_INTERVAL=600  (seconds; default 1200 = 20 min)
#           AUTOCOMMIT_PUSH=1        (also push each snapshot)
#
# Snapshots are marked "auto: snapshot <timestamp>" so they're easy to spot and
# squash later. data/, .venv/ and previews/ are git-ignored, so they're never
# committed.
set -uo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
INTERVAL="${AUTOCOMMIT_INTERVAL:-1200}"   # seconds
PUSH="${AUTOCOMMIT_PUSH:-0}"

echo $$ > .autocommit.pid
echo "[autocommit] started (pid $$, every ${INTERVAL}s, push=${PUSH}) in $(pwd)"

cleanup() { echo "[autocommit] stopping (pid $$)"; rm -f .autocommit.pid; exit 0; }
trap cleanup INT TERM

while true; do
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    if git commit -q -m "auto: snapshot $ts"; then
      echo "[autocommit] committed $ts"
      if [ "$PUSH" = "1" ]; then
        git push -q origin HEAD && echo "[autocommit] pushed $ts"
      fi
    fi
  else
    echo "[autocommit] no changes $(date '+%Y-%m-%d %H:%M:%S')"
  fi
  sleep "$INTERVAL"
done
