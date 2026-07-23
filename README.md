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

## Pipeline (`src/`, decision-first, all executed end-to-end)

| # | notebook | what it does |
|---|---|---|
| 00 | `00_network_and_data` | the group (35 branches, 7 regions, 29 boards) + the operational panel (210k rows, 0 mismatches) |
| 01 | `01_pressure` | who needs staff: GREEN/AMBER/RED per branch×department, shortfall in WTE |
| 02 | `02_federated_forecaster` | the shared instrument + its honesty certificate (naive/local/FedAvg/+ft/centralized ladder) |
| 03 | `03_staffing_requests` | branch agents raise WTE staffing requests to their boards |
| 04 | `04_board_allocation` | boards fund under a 2% budget + ENHANCE / EXPAND / centre- & region-wise views |
| 05 | `05_verification` | backtest vs 12 months of actuals: recall, precision, access, coverage + policy test |
| 06 | `06_selection_audit` | appendix — the network re-derived from raw + NHS ODS registry (**AUDIT PASSED**) |

`a100/` mirrors this pipeline for the 8-year (96-month) full run with the powered multi-seed
sweep — see [a100/README.md](a100/README.md). Results figure: [docs/results_summary.png](docs/results_summary.png).

## Results so far (single seed — the powered sweep is the A100 run)

- **Decision loop verified** (backtest as-of 2025-03 vs 12 months of actuals): detection
  recall **82%**, request precision **95%**, access rate 10% and need coverage 8.1% under the
  2% budget — the budget, not the loop, is the binding constraint.
- **Key finding**: with identical budgets, forecast-driven allocation places **89%** of granted
  staff on true future need vs **83%** for backlog-driven — the federated forecast improves
  the *decision* even though its 12-month rollout MAE is worse than naive (117 vs 106).
  Decision value ≠ forecast MAE.
- Forecaster ladder (test MAE, mean per-branch): local-only **106.9** · fed+fine-tune 108.1 ·
  FedAvg 110.9 · naive 111.2 · centralized 114.2. Federation-vs-local is open at single-seed
  resolution; the 5-seed × 8-algorithm sweep decides it.

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cd src
jupyter nbconvert --to notebook --execute --inplace 00_network_and_data.ipynb   # then 01..06 in order
```

Torch uses CUDA automatically when available; everything also runs on CPU.
