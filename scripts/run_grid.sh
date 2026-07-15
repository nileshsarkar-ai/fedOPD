#!/usr/bin/env bash
# fedOPD Step-8 grid: seeds + ablations + sensitivity. Resumable: skips runs whose JSON exists.
# Usage: bash scripts/run_grid.sh [parallelism]   (run inside tmux: fedopd-grid)
set -u
cd "$(dirname "$0")/.."
source .venv/bin/activate
P="${1:-8}"
R=results

run() {  # run <outfile-stem> <args...>
  local stem="$1"; shift
  if [ -f "$R/${stem}.json" ]; then echo "skip ${stem} (exists)"; else
    echo "python -m src.fedopd.run $*"
  fi
}

{
# --- headline x 5 seeds (seed 0 already done for all four) --------------------------------
for s in 0 1 2 3 4; do
  run "local_delta_s${s}"                --method local   --target delta --seed "$s"
  run "central_delta_s${s}"              --method central --target delta --seed "$s"
  run "fedavg_ft3_delta_s${s}"           --method fedavg  --target delta --ft-epochs 3 --seed "$s"
  run "fedprox_mu0.001_ft3_delta_s${s}"  --method fedprox --mu 0.001 --target delta --ft-epochs 3 --seed "$s"
done
# --- ablations (seed 0): aggregation weighting + window 24 --------------------------------
run "fedavg_ft3_delta_wequal_s0" --method fedavg --target delta --ft-epochs 3 --weighting equal --seed 0
run "fedavg_ft3_delta_wsqrt_s0"  --method fedavg --target delta --ft-epochs 3 --weighting sqrt  --seed 0
run "fedavg_ft3_delta_win24_s0"  --method fedavg --target delta --ft-epochs 3 --window 24 --seed 0
run "central_delta_win24_s0"     --method central --target delta --window 24 --seed 0
# --- sensitivity (seed 0, central + fedavg+ft): roster and panel variants ------------------
# roster18 = stable18 incl. Neurosurgery (threshold below its 0.36 coverage)     [Q4]
run "central_delta_roster18_s0"  --method central --target delta --min-coverage 0.35 --tag roster18 --seed 0
run "fedavg_ft3_delta_roster18_s0" --method fedavg --target delta --ft-epochs 3 --min-coverage 0.35 --tag roster18 --seed 0
# all24 = every department incl. the X 'Other' family                            [Q5]
run "central_delta_all24_s0"     --method central --target delta --depts-mode all24 --min-coverage 0.0 --tag all24 --seed 0
run "fedavg_ft3_delta_all24_s0"  --method fedavg --target delta --ft-epochs 3 --depts-mode all24 --min-coverage 0.0 --tag all24 --seed 0
# panel strictness 139 (>=90 mo) and 146 (>=84 mo)                               [Q1]
run "central_delta_panel139_s0"  --method central --target delta --panel-min-months 90 --tag panel139 --seed 0
run "fedavg_ft3_delta_panel139_s0" --method fedavg --target delta --ft-epochs 3 --panel-min-months 90 --tag panel139 --seed 0
run "central_delta_panel146_s0"  --method central --target delta --panel-min-months 84 --tag panel146 --seed 0
run "fedavg_ft3_delta_panel146_s0" --method fedavg --target delta --ft-epochs 3 --panel-min-months 84 --tag panel146 --seed 0
} | grep -v '^skip' | xargs -P "$P" -I CMD sh -c 'CMD'
echo "GRID DONE"
