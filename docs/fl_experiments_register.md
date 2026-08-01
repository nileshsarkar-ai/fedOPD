# FL experiments register — every federated/collaborative experiment actually run

Written 2026-07-30 in response to a full-audit request. This is the complete inventory: if an experiment
is not on this page, it has not been run in this repo. Every number below traces to
`data/processed/fl_summary_c110.csv`, `data/processed/fl_scaleup_by_specialty.csv`, or a stored print in
`src/11_federated_learning.ipynb` / `src/14_fl_scaleup.ipynb`, all re-read on the date above.

## The one explicit statement first

**Exactly one neural FL architecture exists: notebook 16, first run headless 2026-07-30** (see its
section below), plus its declared multi-seed robustness check in notebook 19 (2026-07-30; same
architecture, budget and pool — a check on 16's C_110 result, not a new experiment family). Before
16's run, no neural architecture of any kind had ever been trained in this repo — the statement in
earlier versions of this file. There is still no FedProx or any FL algorithm beyond
sample-weighted weight/coefficient averaging (one round for the exact linear fits, ten declared rounds
for the neural clients). `torch 2.11.0+cu128` CUDA was verified during environment setup (2026-07-29,
a matmul-on-device check).

## Complete experiment inventory

Shared protocol for every row: training origins before `VAL_START = 2024-04-01` (full-history regime
from Apr 2018; post-Covid regime from `COVID = 2020-03-01` — no other regime boundary exists anywhere);
training targets therefore end Apr 2024. Validation origins Apr 2024 – Feb 2025, targets May 2024 –
Mar 2025 (FY 2024-25). The sealed year is unreachable by construction — the dev cut
`month < TEST_START = 2025-04-01` happens **before** target construction, so a sealed-year target is
NaN and dropped — and the origin-month sentinel assert is present in every modelling notebook
(added to 14 on 2026-07-30 after an audit found it missing there; reported as a finding in WORKLOG,
not fixed silently). All fits are exact least squares (`np.linalg.lstsq`).

| # | notebook | model space | variant | what leaves the client | cohort | validation |
|---|---|---|---|---|---|---|
| 1 | 11 (phase 1) | level: next = β₀ + β₁·level + β₂·momentum | local-only | nothing | 128 C_110 public `fl_client` clients | 1,407 rows |
| 2 | 11 (phase 1) | level | pooled (centralised reference) | all raw rows | same | same |
| 3 | 11 (phase 1) | level | FedAvg: sample-weighted average of (β₀, β₁, β₂) | 3 coefficients + n | same | same |
| 4 | 11 (phase 2) | delta: change = a + b·momentum | fedavg-delta: average of (a, b) | 2 coefficients + n | same | same |
| 5 | 11 (phase 2) | delta | fedavg-delta + local intercept: b averaged, a stays local | 1 coefficient + n | same | same |
| 6 | 14 | delta | local-only, pooled, fedavg-delta, fedavg-delta+local-a — per specialty | as above | 24 specialties × 149 public `fl_client` providers | 26,504 rows total |

One subtlety an auditor should not miss: **"local-only" means different model spaces in 11 and 14.**
Notebook 11's local model is level-space (C_110 full-history MAE 161.9); notebook 14's local model is
delta-space (C_110 full-history MAE 154.5). Both numbers are correct — the delta reformulation helps
local models too. 14's asserts pin persistence, n, cold-starts and fedavg-delta against 11, not local.

## Hyperparameters and fine-tuning

There are none, and there was none:

- `np.linalg.lstsq` exact least squares — no regularisation, no learning rate, no epochs, no batching,
  no early stopping, no feature scaling, no standardisation.
- No imputation except two arithmetic guards, both commented in code with the real input that fires
  them: cold-start validation rows (a provider's series in a specialty starting inside FY 2024-25 —
  RJ8 in C_110; 13 rows across all specialties in 14) get neutral zero momentum; clients with zero
  training rows have no local model and fall back to persistence locally (intercept 0 in the
  slope-only variant).
- No hyperparameter, threshold, split or regime was ever adjusted after seeing a metric. The one
  design change made in response to a result — reformulating from level space to delta space between
  11's phases — is the *reported finding* of phase 1, and phase 1's failing numbers remain in
  `fl_summary_c110.csv` and every document. Nothing was discarded.
- One round of averaging only (linear least squares makes multi-round FedAvg pointless — the average
  of exact solutions does not improve by iterating).

## Per-run metrics (MAE / RMSE; R² deliberately absent — rejected 2026-07-30, size variance dominates it)

C_110, both regimes, all on the same 1,407 validation rows (`fl_summary_c110.csv`, 11 × 5):

| model | full-history | post-Covid |
|---|---|---|
| naive persistence | **153.5** / 330.1 | — |
| pooled (centralised) | 153.8 / 330.3 | 155.4 / 331.9 |
| fedavg-delta | 154.0 / 332.0 | 155.5 / 333.1 |
| fedavg-delta + local intercept | 155.3 / 334.3 | 157.4 / 336.3 |
| local-only (level-space) | 161.9 / 345.2 | 166.5 / 350.5 |
| FedAvg on levels | 186.5 / 363.5 | 228.8 / 401.4 |

Per-client (11's stored print, `fl_per_client_c110.csv` 128 × 6): fedavg beats local at 41.4% of 128
clients; local beats naive at 46.1%; median per-client MAE local 113 / fedavg 134 / naive 113.

Multi-specialty (`fl_scaleup_by_specialty.csv`, 24 × 22 — full per-specialty MAE+RMSE, both regimes):
fedavg-delta − pooled MAE gap across specialties: median −0.08, worst +1.27 (X06: 91.84 vs 90.56),
best −4.61 (C_140: 95.89 vs 100.50). A delta model beats persistence in 12 of 24 specialties
(C_320, C_340, C_410, C_301, C_430, C_101, C_120, C_130, C_140, C_330, C_400, C_170 — recomputable
from the csv row by row); persistence wins at C_110 and the rest; X01 has zero validation rows in
this pool. Largest margins either way: C_120 165.1 vs persistence 171.6 (n=1,265); X02 153.2 vs
144.2 (n=1,409, persistence wins).

## Neural clients (`src/16_fl_neural_clients.ipynb`, run headless 2026-07-30)

| item | value (all declared a priori 2026-07-30, nothing tuned) |
|---|---|
| architecture | one GRU layer (input 4, hidden 32) + linear head → next month's change/100 |
| inputs | 6-month windows of (log1p level, delta/100, >18w share, >52w share) — statistics-free transforms |
| federation | classic FedAvg: 10 rounds × 5 local full-batch Adam steps (lr 1e-3), sample-weighted weight average |
| pooled reference | identical total step budget (50 epochs) |
| seed | 42 (single); cuDNN training is not bit-reproducible — late decimals may wobble across reruns |
| cohort | every specialty in the public `fl_client` pool; X01 skipped (zero eligible validation windows) |
| eligibility | a window needs 6 prior rows, so n < the standard counts (C_110: 1,401 of 1,407); **all** models rescored on the identical eligible rows |
| metrics | MAE + RMSE on levels; `r2_delta_secondary` = R² on the deltas, explicitly secondary (level-R² stays rejected) |

Stored verdicts (`fl_neural_summary.csv` 207 × 7, `fl_neural_per_client.csv` 2,441 × 6,
`output/figures/fl_neural_vs_linear.png`):

- **Aggregate: neural ≈ linear.** Full regime: neural FedAvg beats linear FedAvg at 11 of 23 scored
  specialties and beats persistence at 11 of 23; MAE gap to linear median +0.15 (best −5.25, worst
  +3.06). Post regime: 12 of 23 and 10 of 23, median −0.06. Per client: neural beats linear at 55.2%
  of 2,441 client-specialty pairs — a coin flip.
- **The C_110 anchor shows the project's first sub-persistence scores** (n=1,401 identical rows):
  neural pooled **150.6** and neural FedAvg **152.4** vs persistence 154.1 (linear: 154.4/154.7).
  Margin 1.7–3.5 MAE, one architecture, one seed, no tuning — but 184 model-regime-specialty scores
  were computed, so isolated sub-persistence results are expected by chance; a declared seed-robustness
  check is the honest follow-up, a supervisor decision.
- **Federation costs neural models more than linear ones where signal exists**: C_120 neural pooled
  163.9 vs neural FedAvg 168.6 (linear FedAvg 165.5); C_130 140.1 vs 142.9.
- **The deltas stay ~93%+ noise everywhere**: the best `r2_delta_secondary` anywhere is +0.075 (C_120
  neural pooled); C_110's best is +0.013.
- **Comparison figures (notebook 13, from the same csvs, 2026-07-30)**: `fig_c110_fl_linear_vs_neural_h1`,
  `fig_fl_neural_gap_by_specialty_h1`, `fig_fl_covid_regime_effect_h1`, `fig_fl_neural_gap_vs_size_h1`
  under `output/figures/`. New stored number: dataset size does not decide the neural−linear gap
  (Pearson r = 0.128 across 23 specialties); the four biggest relative neural wins are the X-codes —
  the specialties with no pre-Covid history.
- **Multi-seed check (notebook 19, 2026-07-30, `fl_neural_c110_multiseed.csv` 12 × 6)**: seeds
  42/123/999 and the verdict rule declared before running; C_110 only, implementation verbatim from 16.
  **CONFIRMED in the full regime for both models** — pooled 151.5 ± 0.9 MAE (150.6/152.2/151.9),
  FedAvg 152.4 ± 0.0 (152.4/152.3/152.4), all below persistence 154.1 on the same 1,401 rows. Post
  regime: FedAvg 3 of 3 seeds, pooled 2 of 3 (seed 123 lands exactly on 154.1). The C_110
  sub-persistence result is no longer single-seed.

## Sealed-year one-shot (`src/17_sealed_year_eval.ipynb`, run exactly once 2026-07-30)

The final prospective test of every model family above, pre-registered in 17's intro cell (scope,
cuts, regime, seed all fixed before execution) and never to be re-run. From `sealed_year_eval.csv`
(161 × 8): at C_110 (n=1,407) **persistence 151.5 edged neural pooled 151.6** — the 3-seed-confirmed
validation edge did not replicate prospectively; neural FedAvg 152.1, linear final 153.0, linear
val-frozen 153.3. Aggregate: neural pooled beats persistence at 15 of 23 scored specialties (13 on
validation), neural FedAvg 14, linear FedAvg final 14, val-frozen 10. Median per-specialty
persistence drift vs the validation year: +4.6% — the target year moves more than any model margin.

## Non-gamification confirmation

For every experiment above: no FY 2025-26 data touched training, validation, calibration or any
decision — with three exceptions, each named. (1) By design: notebook 17, the declared one-shot
sealed-year evaluation (section above), which read FY 2025-26 exactly once after rules and models
were frozen. (2) **A protocol defect found by the 2026-08-01 independent audit**: notebook 03's
`fl_client` eligibility rule requires reporting in the panel's final month (March 2026, inside the
sealed year) and counts history over all 96 months — so cohort selection itself used sealed-year
information (selection look-ahead; no future value entered any model). Quantified in notebook 21
and `cohort_sensitivity.csv`: a strictly prospective rule moves the validation anchor from 153.49
(n=1,407) to 154.71 (n=1,418) and the sealed anchor from 151.50 to 151.34; model ordering and all
structural conclusions are unchanged; the sealed 0.1-MAE anchor verdict is a tie within this
sensitivity. (3) Notebook 21's sensitivity itself re-read FY 2025-26 (persistence only), after and
because of the audit; 17's csv stands verbatim as the pre-registered record. Otherwise: the only
regime boundary anywhere is Mar 2020; no threshold/split/horizon loop exists in any FL notebook
(grep-checkable: no candidate sweeps); no experiment was dropped for performing badly — the two
worst results in the project (level-FedAvg 228.8, X02 models losing by 9 MAE) are in the csvs, the
docs and this register.
