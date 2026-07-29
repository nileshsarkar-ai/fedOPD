# CODE_AUDIT.md — audit checklist for fedOPD

Specification for any reviewer (human or AI) auditing this repo. Adapted 2026-07-30 from an external draft;
every figure below was re-verified against stored notebook outputs on that date (corrections to the draft are
listed at the end). The rules being audited live in `CLAUDE.md` — this file does not restate them; it lists
the *checkable facts* that prove they held.

**Source of truth, in order:** stored outputs inside `src/*.ipynb` → result csvs under `data/processed/` →
docs (`README.md`, `docs/eda_rtt_summary.md`, `WORKLOG.md`). Docs make claims; notebooks are the evidence.
A doc figure with no matching stored output is a finding, full stop.

## How to audit (three mechanical steps)

1. **Re-run headless on real data** (the only accepted verification):
   `& ".\nhs_FL_agentic\Scripts\python.exe" -m nbconvert --to notebook --execute --inplace "src\<nb>.ipynb"`
   from the project root, using the `nhs_FL_agentic/` venv — never system Python.
2. **Claim check:** for each notebook, confirm every cell has an `execution_count`, zero `error` outputs,
   and the code strings listed per notebook below are present verbatim.
3. **Doc diff:** take each number in `docs/eda_rtt_summary.md` and `README.md` and find it in a stored
   print or a `data/processed/` csv. Any mismatch (beyond stated rounding) is a finding.

## Global invariants

- **Sealed test year FY 2025-26.** `TEST_START = pd.Timestamp("2025-04-01")` appears in every modelling
  notebook; no training, validation, or calibration row may have a target in the sealed year. Two mechanisms
  enforce it: 04/07/08/11 build targets inside `dev = panel[month < TEST_START]` and assert
  `val["month"].max() < TEST_START`; 09/10/12 build an explicit `target_month` and assert
  `d["target_month"].max() < TEST_START`. Absence of either assert in a modelling notebook is a finding.
- **Regime break declared once:** `COVID = pd.Timestamp("2020-03-01")`. Any other regime boundary
  (a proposal to move it to 2022 was rejected — WORKLOG 2026-07-30) is a finding.
- **Validation year FY 2024-25:** `VAL_START = pd.Timestamp("2024-04-01")`.
- **The 1,407-row protocol binds 04, 07, 08 and 11 only.** Each asserts `len(val) == 1407` and
  `round(naive_mae) == 153`. Notebooks 09, 10 and 12 have their **own declared cohorts** (listed below) —
  expecting 1,407 there is an auditor error, not a code error.
- **Persistence appears in every comparison table.** A summary table without the naive baseline is a finding.
- **Declared constants are weights and thresholds only** — pressure weights `0.2, 0.6, 0.2`; v1 thresholds
  `0.70, 0.40, 1.20, 1.05, 0.80`; v2 thresholds `0.80, 0.30`; flag thresholds `>= 48`, `>= 24`; `SEED = 42`.
  Each carries a "declared, pending supervisor ratification" comment.
  **Conformal bands are never constants:** every band must trace to an `np.quantile(..., 0.90)` computation
  on calibration rows. A band literal hardcoded in code is a finding (this exact defect was rejected once:
  an external draft hardcoded ±1,053 where notebook 10's own calibration gives ±1,171).
- **No silent tuning:** no loops over candidate thresholds/splits picking a best; eligibility, splits and
  horizons never chosen against the metric.
- **Denominator beside every rate** in code prints and docs.
- **All analysis code in `src/*.ipynb`.** The one standing exception is `docs/gentables.py`
  (report build script, decided 2026-07-28). Any other standalone `.py` with modelling logic is a finding.

## Per-notebook checkable facts (verified against stored outputs, 2026-07-30)

**01_fetch_dataset** — `raise_for_status`, `testzip`, `tmp.rename` (resume-safe `.part` downloads, the one
permitted data-serving exception); stored: **96** RTT monthly zips Apr18→Mar26 (`assert len(months) == 96`)
and **61** KH03 files.

**02_eda_dataset** — stored: two column schemas, **69 cols × 36 files** (Apr 2018–Mar 2021) and
**121 × 60** (Apr 2021 on); `C_999 = 4037223 = sum of real specialty rows` (the aggregate row is excluded
everywhere: `!= "C_999"`); Part_2A ⊂ Part_2; `assert panel["month"].nunique() == 96`; 96 files sha256-hashed
to `data/reference/rtt_manifest.csv`.

**03_provider_flags** — stored: 651 providers, 193 public (94.5% of the waiting list); `fl_client` **392**
of 651 (`>= 48` months + reporting in the final month); `fl_allocatable` **182** of 651 (public + `>= 24`);
output `(343441, 18)`.

**04_baseline_forecasting** — stored: dev 300,193 rows / sealed kept out 43,248; 130 providers;
9,024 train-full / 6,185 train-post / **1,407 validation rows**; naive MAE **153** RMSE **330**;
linear 156 (full) / 154 (post). Both never-beaten anchors asserted here.

**05_kh03_beds** — code reads `sheet_name="NHS Trust by Sector"` (fixed column positions, header at
skiprows=15); stored: 61 files → **60 quarters** 2011-04-01→2026-01-01 (duplicate Q4 2014-15: Revised wins,
`duplicated(["provider_code", "month"])` asserted empty); occupancy recomputed and `np.allclose`-checked
against the sheet's own % column; 12,453 provider-quarters, 2,117 with zero G&A beds (`-` → NaN).

**06_merge_canonical** — left join on provider_code × month preserves rows: `assert len(panel) == len(rtt)`,
output `(343441, 24)`; stored: 66.2% of rows carry capacity; public match rate 99.0% (13 public providers
have unmatched months — 2,207 of 229,600 public rows). Capacity is provider-level (KH03 has sectors, not
specialties) — any specialty-level capacity claim is a finding.

**07_beat_persistence** — same 1,407 rows as 04 (asserted, plus `naive on these rows ... matches 04`);
`HistGradientBoostingRegressor` on the one-month **change** (`target_delta`), NaN handled natively — any
imputation is a finding; stored: gbm-delta 155/336 (full), 158/338 (post); gbm-level 178/372, 174/368
(the extrapolation lesson: largest list in training 18,453 < largest in validation 18,758); drift 156,
seasonal-drift 158/162; permutation importance ends at `occupancy_ga 0.20`.

**08_part3_flows** — flows panel from all 96 raw files using `Total All` only (Part_3's count lives nowhere
else — band-summing Part_3 yields silent zeros), output `(338265, 5)`; stored: corr(net flow, actual change)
**0.74** (n=95 months); mean net flow 265,730 vs mean actual change 31,666 (the gap is removals);
net-flow identity 250/453; net-flow linear **154/328** — the only sub-naive RMSE in the project (naive
330); gbm+flows 155/335. Exactly one validation row lacks a flows return — guarded by
`np.where(val["net_flow"].notna(), ..., 0.0)` with the count asserted `== 1`.

**09_longer_horizons** — own cohort: **131 providers**, 10,562 provider-months; per-horizon n =
1,534/1,532/1,529/1,524 (h = 1/3/6/12); persistence wins everywhere: MAE **154/317/501/742**; 90% bands
**±298/±649/±1,053/±1,714**, calibrated on FY 2023-24 targets (1,524/1,524/1,519/1,512 rows), coverage on
FY 2024-25 **89.0/88.7/87.6/89.6%**. Calibrating and scoring on the same year is a finding.
Output `(23, 6)` → `val_horizons_c110.csv`.

**10_agent_logic** — own cohort: **150** public allocatable providers, 11,373 provider-months; components
ranked **within month** (stored maxima 1.0/1.0/1.0 prove max-normalization is the identity — its use is a
finding); band **recomputed ±1,171** (7,357 calibration rows, targets before Apr 2023 — not 09's ±1,053,
different cohort and window); simulation 2,337 provider-months, origins 2023-04-01→2024-09-01.
v1 stored counts: STATUS_QUO 2,003 / EXPAND_CAPACITY 334 (of 2,337); **REDISTRIBUTE_OUT is documented as
arithmetically dead in the header, not coded; REDISTRIBUTE_IN is coded and selects 0 rows** (its stability
test needs a list ≥ 23,420; the largest C_110 list is 18,758). Reality check: EXPAND median realized change
+0.5 vs STATUS_QUO +37.0 (n=334/2,003) — growth-risk triggers select no extra growth.
v2 stored counts: OUT 457 / IN 105 / STATUS_QUO 1,775; **13.6% of 457** OUT rows have an in-ICB receiver;
single-provider ICBs QR1 and QK1 auto-flag OUT (18 months each, 0 STATUS_QUO — known artifact, pending a
minimum-group rule). Output `(2337, 17)`.

**11_federated_learning** — same 1,407 rows as 04 (asserted); 128 clients; the one client with zero
training rows is pinned by name (`assert set(val["provider_code"]) - set(betas) == {"RJ8"}`). Stored table:
naive 153.5/330.1; pooled 153.8/330.3 (full), 155.4/331.9 (post); local-only 161.9/345.2, 166.5/350.5;
**fedavg (levels) 186.5/363.5 full, 228.8/401.4 post** — the non-IID failure; **fedavg-delta 154.0/332.0
full, 155.5/333.1 post** — the repair; fedavg-delta+local-a 155.3/334.3, 157.4/336.3. Per-client: fedavg
beats local at 41.4% of 128 clients; local beats naive at 46.1%; median MAE local 113 / fedavg 134 /
naive 113. Outputs `(11, 5)` and `(128, 6)`.

**12_coarser_grain** — constant membership `n_months_active == 96`: **115** providers; **35 ICB series +
ENGLAND** (shortest ICB series 84 months); persistence wins at every horizon at both grains — ICB MAE
**310/657/1,077/1,523** (n=420 each), national **3,777/5,652/8,928/9,580** (n=12 each); drift blows up at
national h=12 (48,009). Output `(30, 7)`.

**13_report_figures** — report-only notebook; it must:
- Read **only `data/processed/*.csv`** — never the raw `data/rtt_csv/` or `data/kh03/` files, never docs.
  Inputs: `rtt_incomplete_panel.csv` (national trend, long-wait shares, era tables),
  `rtt_kh03_canonical_panel.csv` (trust-name lookup only), `val_horizons_c110.csv` +
  `val_horizons_coarse_c110.csv` (MAE-by-horizon figure), `val_forecasts_c110_public_clients.csv`
  (by-month and per-provider persistence MAE), `agent_decisions_h6_c110.csv` (agent figure, per-provider/
  per-ICB tables, stress test), `fl_summary_c110.csv` (FL figure), `fl_neural_summary.csv` +
  `fl_scaleup_by_specialty.csv` (comparison figures).
- **Recompute nothing**: no forecast, band, split, threshold or decision — agent analysis slices the
  stored decisions; a second decision implementation here is a finding.
- Write only to `output/figures/` and `output/evals/`, filenames carrying cohort/grain/horizon
  (`c110`, `h1`/`h6`, `national`), plus `output/README.md` mapping every artifact to its source csv.
- **Never copy or rename an existing result csv into `output/`** — `data/processed/` stays the single
  source of truth.
- Pin the documented numbers by assert, not by retyping: panel shape (343441, 8); era months 23/73;
  headline era values (4,283k / 6,574k, 13.9% / 38.8%, 0.05% / 4.11%); 1,407 forecast rows with naive
  MAE rounding to 153 and **128** providers scored (the 130-provider cohort minus the two filing no
  FY 2024-25 rows — the same 128 clients as notebook 11; a first draft wrongly expected 130 and the
  assert caught it); decisions shape (2337, 17) with v2 counts 1,775/457/105 and
  the 13.6% receiver share; fl summary shape (11, 5); horizons shapes (23, 6) and (30, 7). Any assert
  firing means a stored csv no longer reproduces the documented result.
- Stress-test windows must be disjoint and partition the simulation exactly (asserted: window n's sum
  to 2,337) — overlapping windows double-count rows.
- First run verified 2026-07-30: 11 code cells executed, zero error outputs, all asserts passed;
  15 artifacts + `output/README.md` written; stress windows partition the 2,337 decisions (785/776/776);
  per-provider table has exactly 128 rows.
- **Extended 2026-07-30 (cross-model comparison section, four figures)**:
  `fig_c110_fl_linear_vs_neural_h1` (from `fl_neural_summary.csv` alone; C_110 n pinned to {1401},
  persistence rounding to 154.1), `fig_fl_neural_gap_by_specialty_h1` (win counts pinned by assert:
  11 of 23 below zero full, 12 of 23 post), `fig_fl_covid_regime_effect_h1` (scaleup shape (24, 22)
  pinned; each regime swing computed **within its own csv** — the chart never compares a 14 MAE against
  a 16 MAE), `fig_fl_neural_gap_vs_size_h1` (Pearson r computed in-notebook, not asserted; stored value
  0.128). Auditor rule: every direct linear-vs-neural number must come from `fl_neural_summary.csv`
  (identical eligible rows) — mixing csvs mixes denominators. Re-run verified headless 2026-07-30:
  15 code cells, zero errors, 19 artifacts in the manifest.
- **Correction 2026-07-30**: an earlier manifest description said "150 providers"; the stored decisions
  cover **132** (`assert len(prov_dec) == 132` now pins the recount; found while writing notebook 15).

**14_fl_scaleup** — notebook 11's delta-space FL protocol over every specialty; must: reuse the declared
dates unchanged; cohort = `fl_client` ∧ `is_public` per specialty (one loop, one model — any per-specialty
tuning is a finding); persistence in every results row; assert the C_110 row reproduces notebook 11
(`n_val == 1407`, naive rounding to 153, `fedavg_delta_full_mae` rounding to 154.0, exactly one cold-start
client); results only to `data/processed/fl_scaleup_by_specialty.csv` (24 × 22).
Sealed-year sentinel: `assert len(val) == 0 or val["month"].max() < TEST_START` per specialty (the
empty branch is X01, which has no validation rows in this pool). **Audit finding 2026-07-30:** the
first version lacked this sentinel (the dev cut still made sealed targets unreachable); found by
applying this document's own global invariant, reported in WORKLOG, then added — not fixed silently.
Verified 2026-07-30 (first run, pre-sentinel): 3 code cells, zero errors, asserts passed; pool 149
providers / 187,041 provider-months / 26,504 validation rows; stored verdicts — fedavg-delta − pooled
MAE gap median −0.08, worst +1.27 (X06), best −4.61 (C_140); a delta model edges persistence at 12 of
24 specialties (recounted independently from the csv); 13 cold-start provider-rows. Sentinel re-run
verified headless 2026-07-30 (3 cells, zero errors, all asserts passed). Note the local-model nuance: 11's "local-only" is level-space (C_110 161.9), 14's is
delta-space (154.5) — an auditor comparing them across notebooks is comparing different models. An
auditor must NOT read the 12-of-24 result as contradicting the C_110 closure — that claim was always
C_110-scoped and the docs say so explicitly. Complete FL inventory: `docs/fl_experiments_register.md`.

**15_agent_rules_frozen** — the freeze notebook (constants ratified 2026-07-30 **by the project owner**,
recorded in `docs/supervisor_decision_sheet.md` — an auditor must not read "ratified" as external
supervisor sign-off); must: change no value (constants identical to 10's declared block); recompute no
forecast, band or pressure score — it re-derives both decision columns from stored component columns
and **asserts bit-for-bit equality** with 10's stored decisions (any drift trips it); pin v1
2,003/334 (REDISTRIBUTE_IN dormant at 0), v2 1,775/457/105 and the 13.6% receiver share; prove the
arithmetic minimum group (`ceil(1/IN_THR) == 4`; min receiver ICB size ≥ 4 asserted); document the
rejected N=30 rule via `assert rows_per_provider.max() == 18`. Output `agent_frozen_summary.csv`
(5 × 6). Verified 2026-07-30 (headless, first run): 3 code cells, zero errors; new stored number —
246 of 457 OUT months (53.8%) in sub-4-provider ICBs, where no local receiver is arithmetically
possible.

**19_neural_c110_multiseed** — the declared robustness check; must: declare the seeds (42/123/999) and
the verdict rule **before** running; copy 16's implementation verbatim (any code change would confound
seed with implementation); retrain only C_110's two neural models; anchor to 16 by assert
(`val.sum() == 1401`, persistence rounding to 154.1); never retrain the linear models (deterministic —
read from the csv); report every seed, discard none. Verified 2026-07-30 (headless, first run): 3 code
cells, zero errors; verdict **CONFIRMED** full regime for both models (pooled 151.5 ± 0.9, FedAvg
152.4 ± 0.0 vs persistence 154.1), post regime pooled 2 of 3 — all stored in
`fl_neural_c110_multiseed.csv` (12 × 6). An auditor should expect seed-42 values near but not equal to
16's stored csv (cuDNN nondeterminism, disclosed in both notebooks); 16's csv remains the official
single-seed record.

**16_fl_neural_clients** — the only neural notebook; must: declare every hyperparameter a priori in the
constants cell (GRU hidden 32, `SEQ_LEN = 6`, `ROUNDS, LOCAL_EPOCHS = 10, 5`, `LR = 1e-3`, `SEED = 42`)
— any sweep, early stopping, or validation-based selection is a finding; use statistics-free input
transforms (log1p, /100 — a fitted scaler would be a leak surface); carry the sealed-year sentinel
`assert len(month) == 0 or month.max() < TEST_START`; rescore **all** baselines (persistence, linear
delta pooled/FedAvg) on the identical window-eligible rows with n stated — comparing its scores to the
1,407-row csv numbers of 11/14 is an auditor error (different denominators: C_110 here is 1,401 rows);
`r2_delta_secondary` is computed on deltas and must never be promoted to a headline (level-R² remains
rejected); cuDNN nondeterminism means late decimals may wobble across reruns — exact-decimal asserts on
neural scores would be a bug, and there are none.
Verified 2026-07-30 (headless, first run): 6 code cells, zero errors; X01 skipped (zero eligible
validation windows); stored verdicts — neural FedAvg beats linear FedAvg at 11 of 23 specialties (full;
median gap +0.15) and 55.2% of 2,441 client pairs; C_110 (n=1,401): neural pooled 150.6 / FedAvg 152.4
vs persistence 154.1 — **single-seed, one of 184 computed scores; an auditor must treat it as unconfirmed
until a declared multi-seed check runs**; best delta-R² +0.075. Outputs `fl_neural_summary.csv` (207 × 7),
`fl_neural_per_client.csv` (2,441 × 6), and `output/figures/fl_neural_vs_linear.png` (written by 16 on
explicit instruction — the one exception to 13 being the sole `output/` writer, recorded in WORKLOG).

**17_sealed_year_eval** — the one-shot; ran exactly once, 2026-07-30, on explicit user instruction
("run"). Must: declare everything before results exist (the intro cell is the pre-registration —
scope h=1 forecast layer, full-history regime, linear two cuts, neural final cut seed 42); read the
sealed year nowhere else in the repo; carry the replication anchors (`val_rep.sum() == 1401`,
validation persistence rounding to 154.1, 11 test origin months at C_110) and the boundary assert
(`not (train_fin & test).any()` — the Mar-2025-origin window belongs to neither set); join the
validation MAE from `fl_neural_summary.csv` rather than retyping it. One declared change from 16's
verbatim code: `build_windows` also returns target months, so the no-leakage split is asserted
directly. Output `sealed_year_eval.csv` (161 × 8). Verified 2026-07-30: 4 code cells, zero errors,
X01 skipped. Stored verdicts: sealed C_110 persistence 151.5 < neural pooled 151.6 (n=1,407) — the
validation neural edge did not replicate; aggregate counts improved (neural pooled 15 of 23).
**An auditor must treat any second execution of this notebook as a protocol violation** unless
WORKLOG records a pre-scores crash.

**18_extract_figures** — tooling notebook (numbering: 15 stays reserved for the post-ratification agent
rules, 17 for the sealed-year one-shot); must: read only the stored state of `src/*.ipynb`, execute and
recompute nothing, skip itself (its on-disk state predates its own run), and write only
`output/figures/from_notebooks/<stem>_cellNN_imgK.png` plus `manifest.csv` mapping each png to its
notebook, cell index and `# Goal:` line (flat naming — per-notebook subfolders were dropped 2026-07-30
on user instruction because most notebooks embed no images). `assert len(man) > 0` trips if the src notebooks ever lose
their stored outputs. Verified 2026-07-30 (headless, first run): 2 code cells, zero errors; **17 images
from 4 notebooks** (02: 5, 05: 1, 13: 10, 16: 1) — the modelling notebooks (04–12, 14) print tables and
save csvs, they never embed figures, so their zero-image entries are correct, not missing data. Images
reflect the **latest** stored run only; `nbconvert --inplace` keeps no history of earlier runs.

## What an auditor must not do

- Suggest tuning thresholds, regime boundaries or splits for metric gains.
- Treat negative results (FedAvg-on-levels hurts; growth triggers vacuous; seasonality fails) as problems
  to fix — they are the findings.
- Expect n=1,407 outside 04/07/08/11, or the 09 band values inside 10.
- Accept a doc number that cannot be produced from a stored output or `data/processed/` csv.

## Corrections made to the external draft (2026-07-30)

1. The draft listed bands ±298/649/1,053/1,714 among "declared constants". Bands are **computed**, never
   declared — hardcoding one is the defect this project already rejected (±1,053 vs 10's true ±1,171).
2. The draft required "the same validation set size" across all forecasting notebooks. n=1,407 binds
   04/07/08/11 only; 09/10/12 declare their own cohorts (131/150/115 providers).
3. The draft said "REDISTRIBUTE rules documented as dead". Precisely: OUT documented-not-coded;
   IN coded, selecting 0 of 2,337 (the stored count is the proof).
4. The draft banned standalone `.py` files without the standing `docs/gentables.py` exception.
5. The draft's "research conduct reminder" comment block was not adopted — it duplicates `CLAUDE.md`
   (same reason the earlier CONDUCT.md proposal was rejected, WORKLOG 2026-07-30).
