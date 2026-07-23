# a100/ — the decision-first pipeline at full power (8-year run)

Mirror of `src/` for the A100 server: same decision-first stages, same artifacts, same
pre-registered rules — the data span grows to **96 months (2018-04 → 2026-03)** and the
forecaster comparison runs at full statistical power.

## Goal (docs/PROBLEM.md)

**Thesis: hospitals can jointly learn a demand forecaster without sharing raw data, and the
resulting forecasts can drive real capacity decisions** — a branch that needs more staff can
access it, through request → board allocation → approval → verification.

| # | notebook | goal it serves |
|---|---|---|
| 00 | `00_fetch_data` | complete the raw panel: 96 monthly files (manifest-driven, resumable) |
| 01 | `01_selection_audit` | provenance: the 35-branch network re-derived from raw + ODS registry (frozen window) |
| 02 | `02_network_and_data` | the group (branches, boards, departments) + the operational panel over 96 months |
| 03 | `03_pressure` | who needs staff, where, how much (flags + WTE shortfall; frozen panel) |
| 04 | `04_federated_forecaster` | the shared instrument, learned without data sharing; single-seed ladder + persisted models |
| 05 | `05_sweep` | **the powered verdict**: 5 seeds × 8 algorithms (FedAvg/FedProx/FedAdam ±fine-tune), mean ± std |
| 06 | `06_staffing_requests` | branch agents raise WTE staffing requests to their boards |
| 07 | `07_board_allocation` | boards fund under a 2% budget + ENHANCE / EXPAND / segregation |
| 08 | `08_verification` | did needy branches get access? recall, precision, access, coverage + policy test |

## Pre-registered decisions (fixed before the run — do not tune after)

1. **Network frozen**: the 35 branches in `config/nhs_network.json`; selection audited on the
   frozen window 2021-04..2026-03. Extra history never re-selects branches.
2. **Panel frozen**: units/series = those complete on the frozen window (the same 694 as the
   laptop run); pre-2021 months are extra training history only.
3. **Splits are dates**: train ≤ 2024-09 · val ≤ 2025-03 · test ≤ 2026-03 — identical to the
   laptop run, so 60-vs-96-month results are directly comparable.
4. Seeds 0–4; FedProx μ=0.1; FedAdam server-lr {0.03, 0.1} on val; selection on val only;
   test touched once per rung. Sweep results append to `sweep_results.jsonl` (resumable).
5. Decision knobs (stated assumptions): SLOTS_PER_WTE = 200; request = RED ≥2 of last 3 months
   + positive forecast gap; board budget = 2% of throughput; priority = gap × (1 + share>52w).

## Run order

```bash
tmux new -s fedopd
cd <repo>/a100
for nb in 00_fetch_data 01_selection_audit 02_network_and_data 03_pressure \
          04_federated_forecaster 05_sweep 06_staffing_requests 07_board_allocation \
          08_verification; do
  jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=100000 "$nb.ipynb" || break
done
```

00 downloads ~36 missing months (resumable); 05 is the long stage (hours; kill-and-rerun
resumes from `sweep_results.jsonl`). GPU used automatically when available.
