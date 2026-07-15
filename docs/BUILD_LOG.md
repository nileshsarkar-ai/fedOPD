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
