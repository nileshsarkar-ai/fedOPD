# BUILD LOG — fedOPD forecaster + federated loop

Successor to the EDA (`docs/WORKLOG.md`, closed at tag `eda-v2`). One entry per **step**, written
when the step ends. Steps run in order; each ends in a **GATE**. A red gate STOPS the line — a red
gate downstream of a silently wrong step is how a week gets thrown away.

- **Findings** are `R-xx` (results); **decisions** continue the EDA's `D-xx` series from **D-06**.
- Build code is one notebook, **`src/fedopd/build.ipynb`** (owner instruction: notebook-only; this
  overrides the runbook's own "modules + CLI" proposal — recorded as D-06 below). §12 write-code rule
  is overridden by the owner for this artifact, same as the EDA notebook (accepted risk).
- Device: **CPU by default** (A100 shared/busy; whole grid is ~7 TFLOP = CPU-minutes). See `docs/OPS.md`.
- Long jobs run in **tmux**. How-to-run + directory map: `docs/OPS.md`.

Entry format:
```
## Step N · <name> · YYYY-MM-DD HH:MM · <git sha>
Ran:      <exact command>
Numbers:  <the figures the step produced>
Gate:     PASS | FAIL — <criterion> → <observed>
Decision: D-xx / R-xx <if any>
Next:     step N+1 unblocked | BLOCKED: <reason>
```

---

## Decisions carried into the build

- **D-06 — build in a notebook (owner override).** The runbook proposed modules + CLI for
  reproducibility of the 8×5 sweep; the owner instructed notebook-only. Build lives in
  `src/fedopd/build.ipynb`, sectioned by step, with the config grid parametrised in-notebook and
  swept via a loop (seeds/configs varied by cell parameters), every run writing `results/*.json`.

---

## Step 0 · Preflight · 2026-07-15 20:44 · 0c91096
Ran:      jupyter nbconvert --to notebook --execute --inplace src/fedopd/build.ipynb  (tmux fedopd-build)
Numbers:  device=cpu (gpu free 6.6 GB, A100 busy → CPU, untouched); canonical 227,344 rows · 96 months
          2018-04..2026-03 · 7 expected cols; env → results/env.json (py 3.10.12, torch 2.11.0+cu128).
Gate:     PASS — row/month/column asserts pass; env.json written.
Decision: D-06 build-in-notebook (owner override, see header).
Next:     Step 1 unblocked.

## Step 1 · Freeze panel + roster + eligible series · 2026-07-15 20:44 · 0c91096
Ran:      same notebook, Step 1 cell → results/panel.json (hash c106fd0afe4baeb3)
Numbers:  panel = 125 trusts (variants: 139 @≥90, 146 @≥84). Roster = 17 of 18 stable-18 departments
          (F-28; one dropped by the ≥50% panel-coverage filter, Q4). Eligible series = 1,528 under
          window W=12, ≥24 train windows + ≥1 test window (D-02 validity). Informative drops within
          panel×roster: 155 no-test-window, 16 few-train-windows (remainder are structural zeros —
          pairs never offered — so absent, not dropped).
Gate:     PASS — 125 trusts; series + drop ledger logged; panel.json written and hashed.
Decision: D-07 (pending supervisor Q5) — default roster EXCLUDES the X 'Other' family (stable18);
          alternatives all24 / no_x are parametrised (DEPTS_MODE) for the supervisor's answer.
Next:     Step 2 (build datasets: windowing, per-series scalers on TRAIN-only excl. outlier-flagged
          months, leakage asserts). NOTE for supervisor before Step 2 builds on it: confirm the roster
          (Q5 X-codes, Q4 coverage threshold) — Step 2 tensors inherit whatever panel.json freezes.

## Step 1 (revised) · no-test-window handling + named the roster drop · 2026-07-15 21:xx · 1e0b9e5
Change (advisor): the blanket "drop no-test-window series" was too blunt. The 155 no-test series split
into 34 with >=24 train windows (usable) + 121 too short. Of the 34: **16 are active interior-gaps**
(still report in 2025-04+, last report mostly 2026-01..03) -> KEPT as **train-only** (train signal, not
evaluated); **18 went stale** (no report after 2025-03) -> dropped. Roster drop now has a name+number:
**C_150 Neurosurgery @ 0.360 panel coverage** (next-lowest is Cardiothoracic @ 0.512, so any threshold
in [0.37,0.51] yields the same 17 depts — Q4 is "exclude Neurosurgery y/n", not "pick a number").
Numbers:  eval 1528 + train-only 16 = **1544 training series** · **117 client trusts** (8 of 125 panel
          trusts contribute no roster series) · drops {few-train-windows 137, stale-closed 18} ·
          panel.json hash e3aa353ecef2cbcb.
Rule:     every method trains on the identical 1544-series set; only the 1528 eval series are scored.

## Step 2 · Build datasets · 2026-07-15 21:xx · 1e0b9e5
Ran:      src/fedopd/build.ipynb (tmux fedopd-build2) -> results/dataset_stats.json
Numbers:  X_train (108065, 33) · X_test (18191, 33) · **33 features** (12 scaled lags + [sin,cos,covid,
          strike] + 17 dept one-hots — 33 not the runbook's 34 because roster=17, not 18) · window 12
          horizon 1 · per-series scalers on TRAIN-only excl. outlier-flagged months (D-04/D-05), std
          floored 1e-6 · 117 clients · min train-windows/client 54.
Gate:     PASS — all 5 leakage asserts (scaler-fit <= 2025-03; test months in [2025-04,2026-03]; 0 NaN;
          every test trust also trains; totals logged).
Next:     Step 3 (metric + bar R-01). NOTE: at **Step 4** decide the module refactor — keep build.ipynb
          as narrative but move model/data/fed into src/fedopd/*.py so Step 8's 40-run grid is a thin
          resumable run.py (a kernel crash must not kill the sweep). (Advisor guidance.)

## Step 3 · Metric + operative bar (R-01) · 2026-07-15 21:30 · b76a8f7
Ran:      src/fedopd/build.ipynb (tmux fedopd-build3) -> results/baselines.json
Metric:   sMAPE on RAW counts (models inverse-transform first), per series then aggregated, scored on
          EXACTLY the 18,191 model test points (te_df 1:1 with X_test; asserted len==18191).
Numbers:  R-01 naive-t1: macro-mean 16.34% | median 12.92% | vol-weighted 12.35% (1,528 eval series).
                seasonal-t12: 23.26 / 16.39 / 17.23. F-27 reproduction (EDA scope, 1,412 complete,
                median): naive 12.59% seasonal 15.65%.
Gate:     PASS — F-27 reproduced within +-0.2 (metric/aggregation verified against the EDA).
Finding:  R-01 = the operative bar. Macro-mean (16.34%) > EDA median (12.6%) because sMAPE is
          right-skewed and the panel adds small/gappy series; big series are easy (vol-weighted 12.35%).
          THE NUMBER TO BEAT: naive-t1 macro-mean 16.34% (median 12.92%), scored identically for models.
Next:     Step 4 (forecaster behind get_params/set_params) + the module-refactor decision.

---

## Findings (R) and pre-registrations

- **R-00 — 125 balanced-panel trusts -> 117 federated clients.** Eight panel trusts contribute no
  eligible series once the 17-dept roster + window minimums bite, because their departments are
  off-roster: REN Clatterbridge Cancer Centre (cancer specialist), RP4 Great Ormond Street (paediatric),
  and six mental-health/community partnership trusts (RPG Oxleas, RT1 Cambs & Peterborough, RWX Berkshire
  Healthcare, RX4 Northumberland Tyne & Wear, RXG SW Yorkshire, RJ8 Cornwall). Consistent with F-14
  (min 1 dept/trust) and F-17 (specialist concentration). **Quote "117 federated clients" (not 125) in
  the results table;** 125 stays the EDA balanced-panel fact (D-03).

- **H1 (pre-registered, before any model runs) — federation rescues the data-poor.** The FL and
  personalisation margin over local-only is *inversely related to a client's train-window count*
  (thinnest 54 windows, mean ~924, vs a ~4.3k-param model). If it holds it is a prediction from data
  shape confirmed, not a post-hoc story. **Fair-fight requirement:** local-only gets early stopping on a
  train-tail split, weight decay, and a sensible small-client batch — no strawman. **Corollary:** cap
  fine-tune epochs for thin clients or personalisation overfits them right back.

- **Sensitivity plan (compute is NOT a constraint: ~230k samples max, ~4.3k params, minutes on CPU).**
  Panel strictness (125/139/146) x roster (17/18/24, incl. Neurosurgery and the X-codes) run as a
  **sensitivity table at Steps 5 and 8**, not chosen now — turning Q1/Q4/Q5 from "decide blind" into
  "here are the numbers". Full frozen panel used throughout; never subset for compute; all gates blocking.

- **Backlog (not for modelling; needed before the agentic layer).** Extract Part_1A/1B (incomplete
  pathways) and Part_2 (decision-to-admit) alongside Part_3 demand — the agentic plane needs a
  waiting-list state to decide *against*, not just incoming demand.

## Step 4 · Forecaster + interface + module refactor · 2026-07-15 · cffa350
Ran:      src/fedopd/{data,model,fed,evaluate,run}.py written; gates run inline.
Decision: **D-08a module refactor (advisor, decided at Step 4 as planned):** build.ipynb stays the
          narrative; model/data/fed/evaluate live in src/fedopd/*.py imported by both the notebook
          and a thin src/fedopd/run.py (one process = one run = one results/*.json), so the Step-8
          grid is resumable and a kernel crash cannot kill a sweep. data.py reproduces the frozen
          tensors EXACTLY (108065x33 / 18191x33 / 117 clients / R-01 16.34) — asserted.
Model:    MLP 33->64->32->1, ReLU, Adam, MSE on scaled targets; **4,289 params**; weight decay 1e-4;
          torch threads=2. Interface: get_params/set_params/train_epochs(mu,global_params)/predict.
          Both targets: level and delta (naive-anchored: zero-delta == naive t-1, verified to
          float32 noise, max dev 1.55e-04 raw).
Gate:     PASS — (a) round-trip bit-identical; (b) overfit RP6 series 200 epochs -> scaled-MSE
          0.00024 (<2% equivalent); (c) determinism: same seed twice -> identical loss;
          (d) delta anchor exact; (e) module/notebook data parity.
Next:     Step 5 (local-only fair-fight + centralised, both targets -> D-08 target choice).

## Step 5 · Baselines: local-only + centralised (both targets) · 2026-07-15 · 77c1138
Ran:      python -m src.fedopd.run --method {central,local} --target {level,delta} --seed 0 (tmux fedopd-step5, 4-way parallel)
Numbers:  vs bar R-01 macro-mean 16.34% —
            central delta 15.62 (R-04, BEATS bar by 0.72) | central level 15.74
            local   delta 16.99 (R-03, loses by 0.65)     | local   level 18.38
          Local-only had the FAIR FIGHT (train-tail early stopping, weight decay, small-client batch)
          and still loses: thin clients (median ~72 windows/series-group) overfit a 4,289-param model.
          Centralised = privacy-ignoring upper bound, beats naive modestly — the expected shape, no
          leakage smell (predictions inverse-transformed, scored on the identical 18,191 points).
Gate:     PASS — both recorded with per-run JSONs; NOT everything loses to naive (central wins), so
          no STOP; target formulation decided.
Decision: **D-08 target = delta** (naive-anchored) — wins on both methods (15.62<15.74, 16.99<18.38),
          exactly as F-27's persistence-domination predicted. All later steps use delta.
Next:     Step 6 FedAvg / Step 7 FedProx+personalisation (running); the interesting question is
          whether federation closes the local->central gap (16.99 -> 15.62) without pooling data.

## Step 6 · FedAvg · 2026-07-15 · (tmux fedopd-step67)
Ran:      python -m src.fedopd.run --method fedavg --target delta --ft-epochs 3 --seed 0
Numbers:  R-05 fedavg_delta: macro 16.43% | median 11.20% (bar 16.34/12.92). Loss history monotone
          0.838 -> 0.511 over 40 rounds, still descending (more rounds may help; seeds first).
Gate:     PASS — non-divergent; recorded vs R-03 (local 16.99) / R-04 (central 15.62). FedAvg beats
          local-only but not the bar on macro-mean; on MEDIAN it beats naive by 1.7pts. Honest note:
          macro-mean is dominated by the small/volatile-series tail where naive is hard to beat —
          exactly the heterogeneity motivation for Step 7.

## Step 7 · FedProx + personalisation · 2026-07-15 · (tmux fedopd-step67)
Ran:      fedprox mu in {0.001, 0.01, 0.1}, all +ft3, delta, seed 0
Numbers:  fedprox macro: mu.001 16.41 | mu.01 16.42 | mu.1 16.49 (mild prox ~ fedavg; strong prox
          hurts — expected under full-participation cross-silo). Personalisation (+ft3, tail-val
          early-stopped): all pulled to ~16.34 = exactly the bar; fedavg+ft 16.34.
Gate:     PASS — full comparison table (seed 0, macro / median):
            naive 16.34/12.92 · seasonal 23.26/16.39 · local 16.99/12.11 · central 15.62/11.06 ·
            fedavg 16.43/11.20 · fedavg+ft 16.34/– · fedprox(.001) 16.41/11.21 · fedprox+ft 16.34/–
          Ranking vs R-01: central beats the bar; fed+ft ties it; fed > local > seasonal. Median
          tells the complementary story (all neural << naive). Seed noise quantified at Step 8.
