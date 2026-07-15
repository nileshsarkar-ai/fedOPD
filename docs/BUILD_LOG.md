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
