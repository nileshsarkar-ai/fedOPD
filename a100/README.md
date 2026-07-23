# a100/ — full pipeline for the extended (8-year) run

Self-contained, ordered pipeline for the A100 server. Same repo layout (`../data`, `../config`),
same artifacts — only the data span grows (60 → 96 months) and the sweep runs at full power.

## Goal (from docs/PROBLEM.md)

**Thesis: hospitals can jointly learn a demand forecaster without sharing raw data, and the
resulting forecasts can drive real capacity decisions.**

| stage | notebook | goal it serves |
|---|---|---|
| 00 | `00_fetch_data.ipynb` | complete the raw panel: 96 monthly RTT files (manifest-driven, resumable) |
| 01 | `01_audit_selection.ipynb` | prove the 35-client network is rule-derived (selection window frozen) |
| 02 | `02_process_rtt.ipynb` | 96 raw CSVs → one tidy `rtt_long.csv` |
| 03 | `03_eda.ipynb` | the demand / non-IID / backlog evidence, now over 8 years |
| 04 | `04_client_datasets.ipynb` | leak-proof per-client training tables (frozen panel, longer history) |
| 05 | `05_federated_train.ipynb` | single-seed ladder sanity + persist models for the agents |
| 06 | `06_agentic.ipynb` | monitoring / planning / retrain-trigger agents (learning → decisions) |
| 07 | `07_sweep.ipynb` | **the main event**: 5 seeds × 8 algorithms, mean ± std — the federation verdict |
| 08 | `08_allocation.ipynb` | request → ICB budget allocation → board memo → backtested verification |

## Pre-registered decisions (fixed before the run — do not tune after)

1. **Network frozen**: the 35 trusts in `config/nhs_network.json`. Extended history deepens
   clients; it never re-selects them. The audit (01) therefore evaluates the selection rule on
   the frozen window 2021-04..2026-03 regardless of extra files.
2. **Series panel frozen**: client series = those complete on 2021-04..2026-03 (the 694).
   Pre-2021 months are extra history where available, nothing more.
3. **Split boundaries are dates**: train ≤ 2024-09 · val ≤ 2025-03 · test ≤ 2026-03.
   With 96 months the train window grows (targets from 2019-04 where history allows);
   val/test are unchanged → results comparable to the laptop run.
4. Seeds 0–4; FedProx μ=0.1; FedAdam server-lr grid {0.03, 0.1} on val (smoke test flagged 0.1
   as possibly unstable); all model selection on val; test touched once per rung.

## Run order

```bash
tmux new -s fedopd
cd <repo>/a100
jupyter nbconvert --to notebook --execute --inplace 00_fetch_data.ipynb      # ~minutes (36 downloads)
jupyter nbconvert --to notebook --execute --inplace 01_audit_selection.ipynb # ~5 min, needs internet
jupyter nbconvert --to notebook --execute --inplace 02_process_rtt.ipynb     # ~8 min (96 files)
jupyter nbconvert --to notebook --execute --inplace 03_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace 04_client_datasets.ipynb
jupyter nbconvert --to notebook --execute --inplace 05_federated_train.ipynb # ~15 min
jupyter nbconvert --to notebook --execute --inplace 06_agentic.ipynb
jupyter nbconvert --to notebook --execute --inplace 07_sweep.ipynb           # hours; resumable
jupyter nbconvert --to notebook --execute --inplace 08_allocation.ipynb
```

07 appends each finished run to `../data/processed/sweep_results.jsonl` — kill and rerun
resumes where it stopped. GPU is used automatically when available.
