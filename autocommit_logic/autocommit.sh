#!/usr/bin/env bash
# Auto-snapshot the repo on an interval, but only when there are changes.
#
# Commits and (when AUTOCOMMIT_PUSH=1) pushes each snapshot to origin/HEAD. It
# ONLY acts when `git status` is dirty, so it never makes empty commits or
# redundant pushes. It never force-pushes: if the remote has moved on, the push
# fails softly, the commit is kept locally, and it retries next cycle.
#
# Runtime files (the log + pid) live OUTSIDE the repo, under
# ~/.cache/fedopd-autocommit/, so the daemon can never dirty the tree with its
# own output (a self-triggering commit loop). Nothing it writes is inside git.
#
#   Start (commit + push):
#     AUTOCOMMIT_PUSH=1 nohup setsid bash autocommit_logic/autocommit.sh &
#   Stop:
#     kill "$(cat ~/.cache/fedopd-autocommit/autocommit.pid)"
#   Watch:
#     tail -f ~/.cache/fedopd-autocommit/autocommit.log
#   Tune:
#     AUTOCOMMIT_INTERVAL=600   # seconds; default 1200 = 20 min
#     AUTOCOMMIT_PUSH=1         # also push each snapshot (default 0 = local only)
set -uo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
INTERVAL="${AUTOCOMMIT_INTERVAL:-1200}"   # seconds
PUSH="${AUTOCOMMIT_PUSH:-0}"
# Non-interactive SSH so an auth prompt can never hang the daemon.
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=15"

# Runtime state kept out of the working tree on purpose (see header).
STATE_DIR="${AUTOCOMMIT_STATE:-$HOME/.cache/fedopd-autocommit}"
mkdir -p "$STATE_DIR"
PIDFILE="$STATE_DIR/autocommit.pid"
LOG="$STATE_DIR/autocommit.log"

# If not already redirected to a file, send our own output to the state log.
[ -t 1 ] && exec >>"$LOG" 2>&1

echo $$ > "$PIDFILE"
echo "[autocommit] started $(date '+%Y-%m-%d %H:%M:%S') (pid $$, every ${INTERVAL}s, push=${PUSH}) in $(pwd)"

cleanup() { echo "[autocommit] stopping (pid $$)"; rm -f "$PIDFILE"; exit 0; }
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
