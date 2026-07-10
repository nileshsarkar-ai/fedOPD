#!/usr/bin/env bash
# Auto-snapshot the repo on an interval, but only when there are changes.
#
# Commits locally and (when AUTOCOMMIT_PUSH=1) pushes each snapshot to
# origin/HEAD. It ONLY acts when `git status` is dirty, so it never makes empty
# commits or redundant pushes. It never force-pushes: if the remote has moved
# on, the push fails softly, the commit is kept locally, and it retries next
# cycle.
#
#   Start (commit + push):
#     AUTOCOMMIT_PUSH=1 nohup setsid bash autocommit_logic/autocommit.sh >> autocommit.log 2>&1 &
#   Stop:
#     kill "$(cat .autocommit.pid)"
#   Tune:
#     AUTOCOMMIT_INTERVAL=600   # seconds; default 1200 = 20 min
#     AUTOCOMMIT_PUSH=1         # also push each snapshot (default 0 = local only)
#
# data/, .venv/, previews/ and the runtime files (autocommit.log,
# .autocommit.pid) are git-ignored, so they are never committed.
set -uo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
INTERVAL="${AUTOCOMMIT_INTERVAL:-1200}"   # seconds
PUSH="${AUTOCOMMIT_PUSH:-0}"
# Non-interactive SSH so an auth prompt can never hang the daemon.
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=15"

echo $$ > .autocommit.pid
echo "[autocommit] started (pid $$, every ${INTERVAL}s, push=${PUSH}) in $(pwd)"

cleanup() { echo "[autocommit] stopping (pid $$)"; rm -f .autocommit.pid; exit 0; }
trap cleanup INT TERM

while true; do
  if [ -n "$(git status --porcelain)" ]; then          # only when there's a real diff
    git add -A
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    if git commit -q -m "FedOPD research commit — $ts"; then
      echo "[autocommit] committed $ts"
      if [ "$PUSH" = "1" ]; then
        if git push -q origin HEAD 2>/dev/null; then
          echo "[autocommit] pushed $ts"
        else
          echo "[autocommit] push FAILED — kept locally, will retry next cycle ($ts)"
        fi
      fi
    fi
  else
    echo "[autocommit] no changes $(date '+%Y-%m-%d %H:%M:%S')"
  fi
  sleep "$INTERVAL"
done
