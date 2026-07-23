# FedOPD — Worklog

Running record of what was done, what was found, and why each choice was made.

## Mission (fixed 2026-07-23)

**Show that hospitals can jointly learn a demand forecaster without sharing raw data, and that
the resulting forecasts drive real capacity decisions.** End-state workflow: a trust's agentic
layer detects backlog pressure from forecasts → raises a capacity request → its ICB's
allocation agent prioritizes requests under a budget → board/human approves → allocation is
executed and monitored next month (closed loop). Trust = hospital; ICB = the board that
allocates; the federation = how the forecaster is learned.

## Honest improvement levers (pre-registered — no gamification)

Ranked by expected value; all selection on val, test touched once per final config:

1. **More data — the 8-year extension (96 months)**: 30 → 66 training target months per series
   (~2.2×). The single biggest lever. Includes the COVID regime break — a robustness test, not
   a nuisance.
2. **Multi-seed error bars** (A100 sweep): doesn't improve results, makes them *true*.
3. **Working-day calendar feature**: months have 19–23 working days and referrals only happen
   on working days — a deterministic, leakage-free feature that explains real monthly variance.
4. **Model class**: GBT (LightGBM-style) and a small GRU over the raw series vs the lag-MLP;
   small tabular data often favors trees. Same ladder, same protocol.
5. **Hyperparameter budget on val** inside the sweep (lr, hidden, local epochs, rounds, μ,
   server-lr) — legitimate tuning, pre-registered grids.
6. **Quantile heads (P50/P90)**: operations need the upper tail (capacity planning), not just
   point MAE — adds pinball loss as a second metric.
7. NOT levers (won't do): training past convergence (curve is flat from ~round 40); bigger
   nets on 33k rows; any decision made by looking at test.

## 2026-07-23 — Data pipeline rebuilt as notebooks (00 → 02)

### What exists now

- `notebooks/00_audit_selection.ipynb` — re-derives the 35-trust network from raw + NHS ODS registry. **AUDIT PASSED.**
- `notebooks/01_process_rtt.ipynb` — 60 raw CSVs (5.1 GB) → `data/processed/rtt_long.csv` (210,328 rows × 11 cols). All reconciliations 0.
- `notebooks/02_eda.ipynb` — 7 charts: trend, seasonality, regions, trusts, departments, region×dept mix, backlog.
- All three executed end-to-end, 0 errors, outputs embedded. No loose .py scripts — notebooks are the pipeline.

### The network selection ("pickup") rule — audited

1. NHS trusts only (3-char `R`-prefixed org codes) → excludes private/independent providers.
2. Part_3 (new RTT periods = demand) reported in **all 60 months** (2021-04 → 2026-03).
3. Region = trust's ICB at anchor month **2025-12**, resolved live from the NHS ODS registry.
4. Top 5 per region by mean monthly new RTT periods → 7 regions × 5 = **35 federated clients**.

Audit: 172 NHS trusts seen → 139 eligible → derived top-5s match `config/nhs_network.json`
exactly (all regions, rank order, names, specialty counts, ICBs; volume deviation ≤ 0.48%).
Config bug fixed: it claimed 61 months / 2026-04; data is 60 months ending 2026-03.

### Key data learnings

- **Counts live in `Total All`.** The raw `Total` column is EMPTY for Part_2/2A/3 — using it
  would make every demand number zero. Found by per-part reconciliation, now asserted in 01.
- Raw grain is `(provider × commissioner × part × specialty)` — must **sum across commissioners**,
  not just drop the columns.
- Parts: Part_3 = demand (inflow), Part_2 = backlog (stock, with 105-band waiting histogram
  compressed to ≤18w / 18–52w / >52w), Part_1A/1B = throughput (outflow, 1B ≈ 4× 1A → OPD-heavy).
  Flow identity: backlog(t) ≈ backlog(t−1) + inflow − outflow.
- NHS trust count shrank 170 → 149 over 5 years (mergers); independent providers grew ~260 → ~384.

### EDA findings

- Demand trends up; seasonality: **December trough (~597k), March peak (~721k) — 21% swing**.
- Trust scale spread **3.4×** (RAJ ~40k/mo … RXN ~11.7k/mo) and region×department mix varies
  → the non-IID heterogeneity that motivates per-series normalization and FedProx/FedAdam.
- 23 departments; T&O and Ophthalmology largest named ones.
- Backlog peaked **~3.2M pathways late 2023**, falling since; >52w share squeezed ~10% → ~2%;
  >18w share still ~35–40% — recovery real, 18w standard far from restored.

### Environment

- Laptop `.venv`: torch 2.11+cu128 on RTX 4060 (CUDA works), Flower 1.32.1, jupyter.
  Full 5 GB processing runs locally in minutes. A100 reserved for big sweeps.
- Git: no ngrok/dashboard URL ever committed (whole-history check); old A100-era work reachable
  at `654c22c` but superseded.

## 2026-07-23 (later) — 03 built; 04 v1 result honest: naive won; v2 fixes applied

### 03_client_datasets.ipynb — executed, all checks pass

- 694 of 760 `(trust, specialty)` series kept (complete: demand > 0 in all 60 months — same
  completeness principle as trust selection). 16–23 series per trust.
- Features (all known before target month): demand lags 1/2/3/12, backlog & throughput at t−1,
  month sin/cos. Per-series z-score of log1p, stats from TRAIN months only.
- Targets 2022-04..2026-03 (lag-12 warmup eats first 12 months). Split by time:
  train 30 mo (20,820 rows) / val 6 mo (4,164) / test 12 mo (8,328).
- Built-in asserts: lag alignment, train-only normalization (leakage), series in every split.

### 04_federated_train.ipynb v1 — reported as found

Model: specialty-embedding MLP (~1.8k params), MSE on standardized logs, FedAvg 60 rounds.
Test MAE (mean per-trust | pooled): naive **111.2 | 111.7** beat everything — local-only
113.9, fed+ft 114.6, centralized 117.4, FedAvg 118.5 (best round 59/60 = not converged);
seasonal-naive 144.9 (year-old levels + strong trend). Centralized < local-only ordering also
inverted — consistent with global underfitting.

**Diagnosis:** (1) FedAvg not converged; (2) train loss (MSE, z-log space) mismatched the
report metric (MAE, referral units); (3) monthly demand is highly persistent, and a
level-predicting model must re-learn persistence from scratch.

**v2 changes (standard forecasting practice, not tuned-on-test hacks):** residual head —
model predicts lag1 + MLP(...), so it starts AT the naive baseline; L1 loss to match MAE;
100 rounds. Caveat recorded honestly: v1 test numbers were observed before deciding v2, so
test is re-touched once; the clean confirmation is the planned multi-seed A100 sweep.

### 04 v2 results — reported as found

Test MAE (mean per-trust | pooled): **local-only 106.9 | 107.3** · fed+fine-tune 108.4 | 109.0
· FedAvg 110.9 | 111.4 (best round 47/100 — properly converged) · naive 111.2 | 111.7 ·
centralized 114.2 | 114.7 · seasonal-naive 144.9. Convergence curve clean (122 → 105 val MAE,
plateau ~round 40).

**v2 verdict:** learned models now beat naive (fixes worked), BUT at this data scale the
federation does NOT beat local-only — local wins by 1.5 MAE over fed+ft. Honest reading:
per-series normalization + residual head already absorb the shared structure (scale,
persistence), and the remaining series-specific dynamics favor local specialization; one
global correction function underfits 35 heterogeneous clients (also why centralized ranks
below local here).

**Known asymmetry to fix before concluding:** local-only gets val-selected early stopping
(40 epochs, best epoch kept) but fed+fine-tune uses a fixed 5 epochs with no val selection —
the comparison currently favors local. Fix = give fine-tuning the same val selection.
Gaps are ~1.5–3.5 MAE on a single seed — need multi-seed error bars before any claim.

### 04 v3 — fairness fix applied (rerun in progress)

Change: `fit_with_val()` gained an `init` parameter; fed+fine-tune now uses the IDENTICAL
protocol as local-only — val-selected early stopping, same 40-epoch budget, same seed — with
the only difference being initialization (global federated weights vs random). The rung now
isolates exactly one question: does starting from the federation help a trust?
(v2's fed+ft used a blunt fixed 5 epochs with no selection — that asymmetry favored local.)

### 04 v3 results — reported as found

Fair protocol changed only fed+fine-tune: 108.4 → **108.1 | 108.6** (other rungs identical,
same seeds). Final single-seed ladder: **local-only 106.9** · fed+ft 108.1 · FedAvg 110.9 ·
naive 111.2 · centralized 114.2 · seasonal-naive 144.9.

**Standing verdict (single seed):** even under an identical training protocol, local-only
beats fed+fine-tune by 1.2 MAE. The federation's value at this data scale is not yet
demonstrated — mechanism: per-series normalization + residual head absorb the shared
structure, leaving series-specific dynamics where local specialization wins (centralized
ranking below local corroborates). Gap is small; whether it survives multi-seed noise is
THE open question for the A100 sweep.

## 2026-07-23 (evening) — agentic plane built (05); A100 sweep harness ready (06)

### 05_agentic.ipynb — executed, 0 errors, 2 charts

Three agent roles as concrete decision rules over aggregates only (privacy boundary holds):

- **Monitoring** (flags at 2026-03, thresholds from the NHS constitution — GREEN = ≤8% waiters
  past 18w; RED = missing standard AND 3-month inflow > outflow):
  **482 RED / 170 AMBER / 42 GREEN** of 694 units. RED dominates every region.
- **Planning** (flow identity, do-nothing scenario: throughput frozen at 6-month mean, demand =
  last year's shape × recent growth): **514 of 694 units' backlogs grow**; network capacity gap
  **132,456 extra treatments/month** to hold backlogs flat. Biggest single gaps: RAL·X02 (2,151),
  RAL·X05 (2,002), R1H·X02 (1,661), RJ1·C_130 ophthalmology (1,627).
- **Orchestration** (retrain trigger: share of series with |z|>2 vs own calendar-month history):
  **151/694 = 21.8% drifted > 10% threshold → DECISION: RETRAIN federation.** Largest drifts:
  RYJ·X06 z=23.7, RM1·X05 z=14.3, RDE·C_100 z=−9.7 (a demand collapse — likely service change).
- Demand forecaster inside planning is a stated stand-in, swappable for the sweep winner.

### 06_a100_sweep.ipynb — the powered ladder, A100-ready

Pre-registered before any big run: network frozen at the 35 config trusts even on 8-year data;
date-based splits (train ≤2024-09 grows 30→66 target months at 96 files; val/test unchanged);
seeds 0–4; algorithms local / central / FedAvg / FedProx(μ=0.1) / FedAdam(server-lr 0.1) /
+val-selected fine-tune on each fed variant. Results append per-run to sweep_results.jsonl
(kill-and-resume safe). On the A100: extend data to 96 monthly files, rebuild 01→03, flip
SMOKE=False, run via nbconvert in tmux.

### 06 smoke test (laptop, SMOKE=True: 1 seed, 15 rounds, 10-epoch budgets) — PASSED, 0 errors

All 8 rungs ran end-to-end; jsonl append + resume mechanics verified. Smoke numbers (NOT
comparable to 04 — reduced budgets, single seed; recorded only as a plumbing check):
fedprox_ft 107.5 · fedavg_ft 107.6 · fedadam_ft 109.3 · local 109.6 · fedprox 110.7 ·
fedavg 111.0 · central 112.2 · fedadam 143.4.

Two observations for the full run (both val-decidable, noted BEFORE the A100 sweep):
1. Under a squeezed local budget, fed+ft beat local — consistent with federation helping
   when per-client optimization is constrained. The full sweep tests whether this holds
   at full budgets.
2. FedAdam at server-lr 0.1 looks unstable at 15 rounds (143.4 pre-fine-tune). Pre-register
   a tiny server-lr grid {0.03, 0.1} selected on val within the sweep, rather than a
   post-hoc change.

## 2026-07-23 (night) — problem statement fixed; the loop closed (07)

### Gap analysis vs docs/PROBLEM.md → fixes

The learning plane (00–04) matched the problem statement; the decision plane didn't exist.
Fixed: 04 now persists trained models (`models_04.pt`, global + 35 fine-tuned — agents run on
FEDERATED forecasts, not stand-ins); new `07_allocation.ipynb` closes request → allocate →
approve → verify. Pre-registered rules: request = RED ≥2 of last 3 months + positive 12-month
forecast gap (recursive rollout, context frozen); board = ICB, budget = 2% of its trusts'
monthly throughput; priority = gap × (1 + share>52w); ENHANCE = RED ≥9 of 12 months;
EXPAND = deferred gap > 25% of trust throughput.

### 07 results — executed, 0 errors

**Current cycle (as-of 2026-03):** 423 requests; boards funded 29 + 27 partial, 367 deferred;
granted 11,875 of 95,371 requested slots/month (the 2% budget covers ~12% — scarcity is real).
Decision mix: 321 ENHANCE / 56 ALLOCATE / 46 monitor. Expansion candidates: RAJ (11.9k
deferred slots), RC9, RDE, RTE, RX1, RXN. Region segregation: East of England leads
(27.8k requested), driven by RAJ (14.4k alone).

**Backtest (workflow run as-of 2025-03, judged on 12 months of actuals):**
- **Request precision 100%** — every funded unit truly had demand > capacity over the next
  year. (Caveat: the sustained-RED rule itself selects persistent pressure — precision partly
  reflects persistence of NHS backlogs; still, zero false-positive funding decisions.)
- Forecast quality on requested units, 12-month-mean MAE: **federated 117 vs naive 106** —
  reported as found: the naive forecast is still better on long rollouts; the allocation
  MECHANISM is validated, the FORECASTER is the improvable part (exactly the A100 levers).

## 2026-07-23 (late night) — a100/ folder: the full pipeline, server-ready

New `a100/` folder = the complete ordered pipeline (00 fetch → 08 allocation) optimized for
the A100's 8-year run, goals mapped to docs/PROBLEM.md in its README. Key pieces:
- `nhs_manifest.json` recovered from the old A100-era commit (`1a86ba3`): 96 verified NHS
  URLs + byte sizes, 2018-04..2026-03 → manifest-driven, resumable `00_fetch_data`.
- Pre-registered freeze rules baked into the adapted stages: selection window frozen
  (01_audit), completeness asserted on frozen window only (02_process), **frozen panel** —
  same 694 series, pre-2021 months are extra history only (04_client_datasets).
- 03/05/06/08 verbatim copies of proven laptop notebooks (outputs stripped);
  07_sweep = SMOKE=False (5 seeds × 8 algorithms, resumable jsonl).
- Verification: all 36 code cells parse-checked; adapted stages (02, 04) EXECUTED on the
  60-month laptop data and reproduced the laptop artifacts EXACTLY (210,328 rows ·
  694 series · 33,312 feature rows · identical splits · 0 mismatches) — the frozen-window
  logic degrades gracefully as designed. 00_fetch/01_audit not executed on laptop
  (fetch would download 36 extra months; audit unchanged except file-window filter).

## 2026-07-23 (v2 of the pipeline) — src/: the decision-first rewrite

Per user direction: the goal is not demand prediction per se but *"a branch that needs more
staff can access it"* — pipeline rewritten from that POV in `src/` (6 notebooks, all executed,
0 errors; `notebooks/` kept as the committed record). Staffing expressed in WTE via stated
assumption SLOTS_PER_WTE = 200 appointments/month. One bug found in the rewrite: icb_of as a
pandas Series broke `.values()` in allocate() — fixed by `.to_dict()`.

### Structure
00 network+data (org chart + panel) · 01 pressure (flags + WTE shortfall; ops_panel.csv) ·
02 federated forecaster (ladder = instrument certificate; models_src.pt) · 03 staffing
requests (WTE asks per branch/dept to its board) · 04 board allocation (budget, memo,
ENHANCE/EXPAND/segregation) · 05 verification (decision metrics, policy test).

### Results
- 01: 482 RED units; current staffing shortfall ≈ **517 WTE** group-wide.
- 02: ladder reproduced EXACTLY (local 106.9 · fed+ft 108.1 · FedAvg 110.9 · naive 111.2 ·
  central 114.2) — determinism held through the rewrite.
- 03/04 (as-of 2026-03): 423 requests = **477 WTE asked**; boards granted **59 WTE**
  (29 funded / 27 partial / 367 deferred under the 2% budget); EXPAND candidates: RAJ
  (60 WTE deferred), RC9/RX1 (24), RDE/RTE (20), RXN (12); 321 ENHANCE service lines.
- **05 verification (backtest as-of 2025-03, judged on 12 months of actuals):**
  - **Detection recall 82%** — 519 of 694 units were in true need; 451 requests captured
    most; 92 silent needs = only **37 of 646 WTE** (misses are small units).
  - **Request precision 95%** (unit basis — stricter than the funded-only 100% figure).
  - **Access rate 10% / need coverage 8.1%** — honest: the 2% budget, not the loop,
    is the binding constraint.
  - **Policy test: forecast-driven allocation beats backlog-driven** — useful-grant share
    89% vs 83%, coverage 8.1% vs 7.5%, same budgets. KEY FINDING: the federated forecast
    adds decision value even though its 12-month rollout MAE (117) is worse than naive
    (106) — decision value ≠ forecast MAE. This is the paper's argument in one number.

### Next
- A100: run a100/ 00→08 (README runbook); consider mirroring the src/ POV there after.
- Sensitivity over stated knobs (8% standard, 2-of-3 rule, 2% budget, SLOTS_PER_WTE).
- Commit src/ + WORKLOG (pending user go).
