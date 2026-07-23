# FedOPD

Federated OPD demand forecasting + agentic capacity allocation — an operations-research
prototype on real NHS data.

**Thesis: hospitals can jointly learn a demand forecaster without sharing raw data, and the
resulting forecasts can drive real capacity decisions.**

Full problem statement (group-HQ concept ↔ NHS instantiation): [docs/PROBLEM.md](docs/PROBLEM.md).
Complete decision/finding trail: [WORKLOG.md](WORKLOG.md).

## The system

Two planes with one strict boundary:

- **Federated plane** — 35 NHS trusts (top-5 per region by volume, rule-derived and audited)
  train one demand forecaster via FedAvg/FedProx/FedAdam. Model weights travel; raw activity
  data never leaves a trust.
- **Agentic plane** — decision agents consume only forecasts and aggregates: monitoring
  (GREEN/AMBER/RED per trust×specialty, thresholds from the NHS 18-week standard), planning
  (flow-identity backlog projection, capacity gaps), orchestration (drift → retrain trigger),
  and allocation (branch requests → ICB board ranks under budget → approve → verify).

## Data

NHS England RTT full extracts, monthly, 2021-04 → 2026-03 (60 months; the `a100/` pipeline
extends to 96). One raw row = provider × commissioner × RTT part × specialty; ~121 columns.
Key facts: counts live in `Total All`; Part_3 = demand, Part_2 = backlog (+ waiting-band
histogram), Part_1A/1B = throughput.

Source: <https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/>
([Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)).
Raw data is not in git.

## Pipeline (`notebooks/`, all executed end-to-end)

| # | notebook | what it does |
|---|---|---|
| 00 | `00_audit_selection` | re-derives the 35-trust network from raw + NHS ODS registry — **AUDIT PASSED** |
| 01 | `01_process_rtt` | 60 raw CSVs (5 GB) → `data/processed/rtt_long.csv` (210k rows, 0 reconciliation mismatches) |
| 02 | `02_eda` | trend, seasonality (Dec trough / Mar peak), 3.4× trust spread, backlog story |
| 03 | `03_client_datasets` | leak-proof per-client tables: 694 series, time split 30/6/12 months, train-only normalization |
| 04 | `04_federated_train` | the ladder: naive → local → FedAvg → +fine-tune → centralized; persists models |
| 05 | `05_agentic` | monitoring / planning / retrain-trigger agents on live data |
| 06 | `06_a100_sweep` | multi-seed × multi-algorithm harness (laptop smoke mode) |
| 07 | `07_allocation` | the closed loop: requests → ICB budget allocation → board memo → backtested verification |

`a100/` contains the same pipeline (00 fetch → 08 allocation) prepared for the 8-year
(96-month) full run — see [a100/README.md](a100/README.md).

## Results so far (single seed — the powered sweep is the A100 run)

- Ladder (test MAE, mean per-trust): local-only **106.9** · fed+fine-tune 108.1 · FedAvg 110.9
  · naive 111.2 · centralized 114.2. Federation-vs-local is genuinely open at single-seed
  resolution; the 5-seed × 8-algorithm sweep decides it.
- Allocation backtest (workflow run as-of 2025-03, judged on 12 months of actuals):
  **100% request precision** — every funded unit truly had demand exceed capacity.
- Reported as found: on 12-month recursive rollouts the naive forecast still beats the
  federated one (106 vs 117 MAE) — the forecaster, not the mechanism, is the improvement
  target (levers pre-registered in WORKLOG §2).

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cd notebooks
jupyter nbconvert --to notebook --execute --inplace 00_audit_selection.ipynb   # then 01..07 in order
```

Torch uses CUDA automatically when available; everything also runs on CPU.
