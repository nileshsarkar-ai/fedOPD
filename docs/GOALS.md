# FedOPD — goals for the training phase

*Written 2026-07-23, after the supervisor meeting. This is the plan we agree before any
training runs. Nothing here is a result; results go to `WORKLOG.md`.*

Baseline being improved on: [`docs/SRC_BASELINE.md`](SRC_BASELINE.md) — the complete
specification and results of the existing 5-year `src/` run.

---

## 0. What the system is

Two planes over one hierarchy — **hospital → board (ICB) → region**:

- **Federated plane (the instrument).** Every hospital trains the *same* demand-forecasting
  neural network on its own data. Only model weights travel to the server; patient activity
  never leaves the hospital. The server averages the weights and sends the shared model back.
- **Agentic plane (the decisions).** A hospital agent watches its own department queues,
  detects sustained pressure, and uses the federated forecast to raise a staffing request to
  its board. The board agent ranks all its hospitals' requests under a fixed budget, funds
  what it can, and the next cycle's data shows whether the pressure eased.

The forecaster exists to serve the decision. The thesis is not "we forecast well" — it is
**"hospitals can learn together without sharing data, and those forecasts make better
allocation decisions than what they'd do otherwise."**

## 1. The inventory model (what the data actually is)

Each `(hospital, department, month)` is an inventory / queueing system. This is the
conceptual spine of the whole project:

| inventory concept | RTT field | what it means |
|---|---|---|
| **stock on hand** | `Part_2` incomplete pathways | **patients currently waiting** for treatment |
| **stock ageing** | waiting bands 0–18w / 18–52w / >52w | how long those patients have waited |
| **inflow** | `Part_3` new RTT periods | new referrals arriving ← **the forecast target** |
| **outflow** | `Part_1A + Part_1B` completed pathways | patients treated = delivered capacity |
| **stockout** | breaching the 18-week standard | the NHS constitutional failure condition |
| **replenishment** | staff granted by the board | the decision the agents make |

Flow identity: `backlog(t) ≈ backlog(t−1) + inflow(t) − outflow(t)`. This is what lets an
agent project next year's queue from a forecast of inflow.

**The backlog is patients, not staff, and not physical stock.** It is a *count of waiting
pathways* — no patient identity, no clinical detail, nothing below an aggregate monthly
number per department. One patient referred to two specialties counts twice, so the unit is
"pathway", not "person". There is no consumables/beds/equipment inventory anywhere in RTT.

## 2. Locked decisions

| decision | value | why |
|---|---|---|
| **Data window** | **2021-04 → 2026-03** (60 months) | see §3 |
| **Modelled span** | targets 2022-04 → 2026-03 (**4 years**) | `lag12` warm-up consumes the first 12 months |
| **8-year extension** | **DROPPED** | see §3 |
| Network | 35 NHS trusts (top-5 × 7 regions), audited | unchanged from `src/` |
| Panel | 694 (trust × specialty) complete series | unchanged from `src/` |
| Splits | train ≤ 2024-09 · val ≤ 2025-03 · test ≤ 2026-03 | dates, not counts |
| Holdout | **2026-04, 2026-05** fetched, quarantined | see §3 |
| Code lives in | Jupyter notebooks, `src/`-style: short, plain, effective | owner's requirement |
| `src/` notebooks | **frozen — not modified** | they are the reference baseline |

## 3. Goal 1 — a COVID-free dataset (SETTLED)

Supervisor's requirement: COVID must not poison training.

**Measured** (network demand vs its own calendar-month pre-COVID mean, 2018-04…2020-02 base):
COVID trough **2020-04 at 0.35×**; level restored **2021-03 (1.06×)**; growth dynamics
stationary from **2022-04** (year-on-year falls from +209%/+141%/+79% into ±10% noise; FY means
flatten at +1.7%, +2.1%, +1.1%).

**Finding: the existing window is already COVID-free.** `src/` starts at 2021-04 and `lag12`
eats 12 months, so the first predicted month is **2022-04** — the exact month demand became
stationary. The earliest value any feature touches is 2021-04, already at 1.07×. There is
**no COVID-collapse data in the pipeline, as target or as input.**

**Second, independent reason to stop at 2021-04:** a reporting break. Specialties go 19 → 23
and reporting units 608 → 727 at exactly 2021-04; ~30% of the panel series **do not exist**
before it, and 4 specialty codes have no earlier history at all.

Two independent justifications, one date. **Action: keep 2021-04. Delete the 2018-04…2021-03
files (done). Drop the 8-year extension permanently.**

**New months.** 2026-04 and 2026-05 are published and now fetched. They are **quarantined as a
true out-of-sample holdout** — not in train, val, or test, not looked at during development.
They are spent once, at the very end, to show the system works on months that did not exist
when it was built. Extending the main window instead would invalidate every `src/` comparison.

## 4. Goal 2 — a properly trained model

The baseline was **never tuned**: one seed, one arbitrary hyperparameter point, no grid.
Fixing that — not running longer — is the actual work.

Note the baseline **already converged**: val MAE 122 → 105, plateau ~round 40, best round
47/100. "More epochs" alone will not help and invites the question "did you check convergence?"

1. **Capacity search.** The current net is 1,597 parameters, never compared to anything.
   Grid `hidden ∈ {32, 64, 128, 256}`, `layers ∈ {2, 3}`, `emb ∈ {4, 8, 16}` — spanning
   ~1.6k to ~140k parameters. Whatever wins on validation, wins.
2. **Optimizer/schedule search.** `lr ∈ {3e-4, 1e-3, 3e-3}`, `batch`, `local_epochs ∈ {1,2,4}`,
   `rounds ∈ {100, 200}`.
3. **Algorithms.** FedAvg · **FedProx** (μ grid) · **FedAdam** (server-lr grid), each ±
   val-selected fine-tuning. FedProx and FedAdam never actually ran in `src/`.
4. **5 seeds**, mean ± std, paired across seeds. The current local-vs-federated gap is 1.2 MAE
   on one seed — not a result without error bars.
5. **Comparator model classes** so "you only tried one architecture" cannot be asked:
   a GRU over the raw sequence, and gradient-boosted trees.
6. **Equal budget for every rung.** Local-only, centralized, and every federated variant get
   the *same* search budget. Anything else biases the ladder by construction.

**Recovering training data (proposal, needs a decision):** the 12 months 2021-04…2022-03 are
post-recovery and perfectly clean, but are burned entirely on `lag12` warm-up. Relaxing the
maximum lag for those early rows would take training months **30 → 42 (+40%)** with zero COVID
exposure. This is the only honest way left to add data.

## 5. Goal 3 — evaluation the supervisor asked for

The baseline reports **MAE only**. No R², no RMSE, no diagnostic plots anywhere.

**Metrics — compute and report all of them:**

| metric | note |
|---|---|
| MAE | the existing headline |
| **RMSE** | disclose that training uses L1, so RMSE is off-objective |
| **R², per-series, then averaged** | the honest form |
| **skill score vs naive** = `1 − MSE_model/MSE_naive` | "is this better than doing nothing?" |
| sMAPE | scale-free, comparable across hospitals of very different size |

> **Never report pooled R².** Across 694 series with ~100× scale spread it lands at ~0.98–0.99
> because the model is rewarded for knowing one hospital is bigger than another. It measures
> nothing about forecast skill and will not survive scrutiny.

**Selection stays on validation MAE alone**, pre-registered. Reporting five metrics must not
become choosing whichever metric the federation happens to win on.

**Figures:**
1. Ladder bar chart **with 5-seed error bars**
2. Convergence curves (val MAE vs round) per algorithm
3. Predicted vs actual scatter + 45° line
4. Residual distribution, and residuals vs fitted
5. Forecast vs actual time series for representative units
6. Error by horizon h = 1…12
7. Error vs series scale (does it fail on small departments?)
8. Full metric table: MAE / RMSE / R² / skill / sMAPE × every rung

Decision-plane metrics stay as they are: detection recall, request precision, access rate,
need coverage, and the forecast-driven vs backlog-driven policy test.

## 6. Goal 4 — the honest gap: we have no capacity data

**Every staffing number in the system rests on one invented constant: `SLOTS_PER_WTE = 200`.**
RTT contains no staff, no beds, no clinics, no equipment, no money. When the system says
"RAJ needs +12.3 WTE", what it measured was "RAJ needs 2,461 more appointments/month"; the
÷200 is an assumption.

What saves it: the constant is a **single global divisor**. Requests, budgets, and grants are
all computed in appointment-slots and only *displayed* in WTE. So every ranking, every
funded/deferred decision, and every reported ratio is **completely invariant** to its value —
only the labels change. State this explicitly rather than letting a reviewer find it.

**The real fix:** NHS England publishes monthly workforce statistics per trust. Wiring those in
would replace the assumption with measured staff counts and let the agent *observe* throughput
per staff member instead of assuming it. Scoped as a separate workstream — it should not block
the training run.

## 7. What we will not do

- Not extend to 8 years. Not model around COVID with a regime dummy.
- Not tune anything on test; test is touched once per rung, at the val-selected config.
- Not report a metric selectively because it flatters the federation.
- Not train past convergence and call it an improvement.
- Not modify the `src/` notebooks — they are the frozen reference baseline.
- Not claim WTE figures are validated staffing estimates.

## 8. Open decisions

1. Recover the 12 warm-up months (train 30 → 42) by relaxing the max lag? **Recommended.**
2. Grid breadth vs GPU time — how wide before it stops being worth it.
3. Do the GRU and GBT comparators go in this run or a later one?
4. Scope the NHS workforce data now, or after the training run?
