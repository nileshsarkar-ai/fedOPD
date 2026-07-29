# RTT EDA — results summary

Source: `src/01_fetch_dataset.ipynb` → `02_eda_dataset` → `03_provider_flags` → `04_baseline_forecasting` → `05_kh03_beds` → `06_merge_canonical` → `07_beat_persistence` → `08_part3_flows` → `09_longer_horizons` → `10_agent_logic` → `11_federated_learning` → `12_coarser_grain` → `13_report_figures` → `14_fl_scaleup` → `15_agent_rules_frozen` → `16_fl_neural_clients` → `17_sealed_year_eval` (the one-shot, run once 2026-07-30) → `18_extract_figures` → `19_neural_c110_multiseed`, all run headless on the full data via nbconvert.
Every figure below is read from the notebooks' stored outputs or recomputed from the saved csvs — none from memory. Last cross-checked against those outputs 2026-07-30.

## What was done → result

1. **Fetched the raw data** (`01_fetch_dataset.ipynb`): 96 monthly RTT Full-CSV zips scraped from the 8 NHS England year pages, each download verified (`raise_for_status` + `testzip` before rename) → 96 zips, 96 extracted csvs, plus the ODS trust→ICB reference (~544 trusts) and 61 KH03 spreadsheets.
2. **Audited every file before trusting it**: month coverage (96/96, no gaps), `Period`-inside-file vs filename (all 96 match), header-only schema audit (exactly 2 column sets, one break at Apr 2021), sha256 manifest saved for change detection.
3. **Proved the two double-counting traps** instead of assuming them: the `C_999` "Total" specialty row (equals the sum of the real rows, exactly) and `Part_2A` (the with-DTA subset of `Part_2`). Both excluded from the panel.
4. **Built the canonical panel**: 343,441 rows — one per (month, provider, specialty), incomplete pathways only, uniform 8 columns across both schema generations → `data/processed/rtt_incomplete_panel.csv`.
5. **Measured the system**: national list averaged 4.28M pre-Covid vs 6.57M post (+53.5%); the >52-week share rose ~80× (0.05% → 4.1% — corrected 2026-07-30, the earlier "~40×" came from 1-dp rounding of 0.05% up to 0.1%). 193 NHS trusts hold 94.5% of the list; 458 independent providers hold 5.5%. No specialty exceeds 11.6% of the list.
6. **Recorded the design decisions**: keep independents but flag them; derive long waits from week-band names (works in both schemas, keeps the post-2021 extended bands); modeling to compare full-history vs post-Covid training regimes.
7. **Built the flagged panel** (`03_provider_flags.ipynb`): ODS joined onto the panel → `is_public`, trust name, ICB, per-provider stability (median history 89 of 96 months), and declared flags: 392 `fl_client` providers (≥48 months + reporting in the final month), 182 `fl_allocatable` (public + ≥24 months) → `rtt_panel_with_provider_flags.csv` (343,441 × 18).
8. **Declared the sealed test year and ran first baselines** (`04_baseline_forecasting.ipynb`): FY 2025-26 sealed (43,248 rows kept out, asserted). One-month-ahead `total_waiting`, C_110 at 130 stable public providers, validated on 1,407 FY 2024-25 rows (forecast origins Apr 2024 – Feb 2025; the Mar 2025 origin drops because its target is the sealed Apr 2025): naive persistence MAE 153 / RMSE 330 beats both linear regimes (full-history MAE 156, post-Covid-only MAE 154). **Nothing beats persistence yet.**
9. **Built the KH03 capacity panel** (`05_kh03_beds.ipynb`): all 61 files share one layout; 60 unique quarters Apr 2011 → Q4 2025-26, 12,453 provider-quarters; column positions proven by asserting recomputed occupancy equals the sheet's own `% Occupied`. Three data traps handled: duplicate Q4 2014-15 (revised wins), a `"2013-15"` year typo (Q2 2013-14, one row), `-` markers where available = 0 (2,117 zero-G&A provider-quarters → NaN occupancy). Quarterly average-daily-beds upsampled to months → `kh03_monthly_panel.csv` (37,359 × 8).
10. **Merged the canonical panel** (`06_merge_canonical.ipynb`): capacity left-joined at provider × month (KH03 has sectors, not specialties, so capacity repeats across a provider's specialty rows). Row count preserved (343,441). Coverage: public trusts 99.0% of rows, independents 0.1% (KH03 is an NHS-trust return), 66.2% overall → **`rtt_kh03_canonical_panel.csv` (343,441 × 24)** — the single source of truth for modeling. Design record: `docs/idea_canonical_pipeline.md`.
11. **Tried to beat persistence with structure** (`07_beat_persistence.ipynb`): gradient-boosted trees predicting the one-month *change* (not the level — trees cannot output values beyond their training range, and validation contains a new all-time high: 18,758 vs 18,453 max in training). Same cohort, splits and validation rows as 04, asserted — the recomputed naive MAE matches 153 exactly. All variants, MAE on the same 1,407 FY 2024-25 rows: naive **153**; gbm-delta 155 (full-history) / 158 (post-Covid); gbm-level 178 / 174; drift 156 / 158; seasonal-drift 158 / 162. **Persistence still unbeaten.** Seasonal drift loses to plain drift — training-period calendar patterns do not transfer to FY 2024-25 — and occupancy carries near-zero importance (0.20 permutation MAE vs 10.18 for current level).
12. **Tried the flows** (`08_part3_flows.ipynb`): built the last unused raw signals — `Part_3` referral inflow and `Part_1A/1B` completion outflow — into `rtt_flows_panel.csv` (338,265 × 5, one row per month × provider × specialty; `Part_3` carries its count in `Total All` only, every week-band column empty — checked before building). National evidence: net flow correlates 0.74 with the actual monthly change (n=95 months) but overshoots ~8× (mean net flow 265,730/month vs mean actual change 31,666 — removals without treatment absorb the difference). On the same 1,407 validation rows: net-flow identity MAE 250; net-flow linear MAE 154 / **RMSE 328 — the best RMSE of any model yet** (naive: 330), fitted slope 0.08–0.13 (only ~a tenth of a marginal net-flow unit survives into the list); gbm-delta+flows 155 / 158. **Persistence still unbeaten on MAE** — every candidate signal in the raw RTT + KH03 data has now been measured at this grain and horizon.
13. **Tried longer horizons and built the uncertainty layer** (`09_longer_horizons.ipynb`): 1/3/6/12-month-ahead forecasts, splits by *target* month so no horizon can reach the sealed year (asserted). **Persistence wins at every horizon and its lead widens with distance**: MAE 154 (1m), 317 (3m), 501 (6m), 742 (12m) vs the best challenger at each horizon (drift-full 331 at 3m, 538 at 6m, 847 at 12m; gbm and seasonal further behind — same-month-last-year scores 742 at every horizon, identically 12-month persistence by construction, so waiting lists carry no usable seasonality at any horizon). The forecasting question at provider × C_110 grain is **closed for horizons 1–12 months**. New capability: conformal 90% bands around persistence, calibrated on FY 2023-24 targets and honestly covered on FY 2024-25 (87.6–89.6% vs nominal 90%): ±298 (1m), ±649 (3m), ±1,053 (6m), ±1,714 (12m) patients — the uncertainty input for the agent phase.
14. **Built the first agent prototype** (`10_agent_logic.ipynb`): pressure score with **declared weights 0.2/0.6/0.2** on within-month percentile ranks of (`pct_gt18`, `pct_gt52`, `occupancy_ga`) — declared 2026-07-30, pending supervisor ratification. Cohort: C_110 at 150 public allocatable providers, 2,337 decision provider-months (Apr 2023 – Sep 2024), every decision checked against its actual 6-month outcome. Results: EXPAND_CAPACITY fired on 334 of 2,337 rows (14.3%) at 30 providers; **two of the four proposed rules are arithmetically dead** with an absolute pooled band (REDISTRIBUTE_OUT needs the lower band edge above current — impossible under persistence; REDISTRIBUTE_IN's stability test needs a list ≥ 23,420, larger than any C_110 list). And the reality check is a finding in itself: EXPAND months did **not** precede larger growth (median realized change +0.5 vs +37 for status quo; 50.0% vs 53.5% grew) — consistent with the random-walk result: **future growth is unpredictable, so allocation triggers must be based on current measured pressure, not predicted growth**. Decisions saved to `agent_decisions_h6_c110.csv`.
15. **Added redistribution rules that can fire** (`10_agent_logic.ipynb` v2): the v1 lessons applied — growth conditions dropped, decisions from **within-ICB standing** (declared: OUT = pressure *and* occupancy rank ≥ 0.80 in the ICB-month; IN = both ≤ 0.30). On the same 2,337 simulated provider-months: OUT 457 (19.6%), IN 105 (4.5%), STATUS_QUO 1,775. The classes separate real populations (OUT median pressure 0.723 and realized 6-month change +81; IN 0.183 and +5). Two findings for the rule design: **only 13.6% of OUT flags have an IN receiver in their own ICB-month** — within-ICB redistribution mostly has nowhere to send (cross-ICB or independent-sector receivers needed) — and single-provider ICBs (e.g. QR1, QK1) auto-flag OUT every month because a group of one always ranks 1.0. ICB group sizes: min 1 / median 3 / max 10 over 648 (month, ICB) groups. Decisions csv now 2,337 × 17.
16. **Ran the first federated-learning experiment** (`11_federated_learning.ipynb`): 128 C_110 clients, linear model on (level, momentum), declared splits unchanged, same 1,407 validation rows (asserted; naive = 153 recomputed). MAE full-history regime: **pooled 153.8 ≈ persistence 153.5**, local-only 161.9, **FedAvg 186.5** (post-Covid: 155.4 / 166.5 / 228.8). **Naive FedAvg actively hurts** — sample-weighted coefficient averaging across clients whose list sizes span ~50 to ~18,000 breaks the intercept scale (the classic non-IID failure, measured on real data); FedAvg beats local at only 41.4% of 128 clients, local beats naive at 46.1%. Cold-start scenario measured: RJ8 filed its first C_110 return in May 2024 — zero training rows, so local-only falls back to persistence while the shared model can serve it. Design consequence: FL here needs per-client normalization / personalization (predict the *change*, or client-specific intercepts), not raw coefficient averaging → `fl_summary_c110.csv`, `fl_per_client_c110.csv`.
17. **FL phase 2 repaired the failure** (`11_federated_learning.ipynb`, extended): moving the federation into **delta space** — every client fits *change* = a + b·momentum, coefficients averaged — scores MAE **154.0** (full) / 155.5 (post), within 0.2 of centralized pooling (153.8) and 0.5 of persistence (153.5), recovering the 32.5 points naive level-FedAvg lost. Sharing only the slope with client-kept intercepts is slightly worse (155.3 / 157.4 — local intercepts overfit client noise). Conclusion: **privacy-preserving federation matches centralization once the shared quantity is scale-free**; nothing beats persistence, consistent with everything else.
18. **Closed the coarser grains** (`12_coarser_grain.ipynb`): the same C_110 series aggregated to ICB (35 series) and England level, constant membership only (115 of the stable providers present in all 96 months — aggregating a churning set would fabricate level jumps). **Persistence wins at every horizon at both grains**: ICB MAE 310 / 657 / 1,077 / 1,523 at 1/3/6/12 months (n=420 each), national 3,777 / 5,652 / 8,928 / 9,580 (n=12 each); seasonal and drift lose everywhere, and drift degrades catastrophically at long national horizons (48,009 at 12 months — it extrapolates training-era growth that stopped in FY 2024-25). **The forecasting question is now closed at every grain and every horizon measured.**
19. **Built the report artifact layer** (`13_report_figures.ipynb`): 6 figures + 9 evaluation tables + a provenance manifest under `output/`, generated **only from the stored csvs** in `data/processed/` — no model, split, band or decision recomputed, and every documented headline value pinned by assert rather than retyped (all passed: era means 4,283,000.48 / 6,574,295.78 and shares 13.89% / 38.76% / 0.05% / 4.11% reproduce the headline table's rounded values). New stored facts: **only 128 of the 130 cohort providers have FY 2024-25 validation rows** (the same 128 clients notebook 11 scores; a wrong expectation of 130 tripped the assert on the first run and was corrected — the assert doing its job); per-provider persistence MAE has a long tail over those 128 (worst: RXC 725.2, RDR 693.3, R0A 634.4 — n=11 rows each); by-origin-month persistence MAE spans 123.3 (Aug 2024) to 221.9 (Nov 2024) over the 11 origin months (n=127–128 per month); C_110's era-aggregate >52-week share rose 0.13% → 5.95% (denominators: 11,708,503 / 55,660,366 era patient-months). The **agent stress test** over three disjoint 6-month origin windows (785 / 776 / 776 rows — they partition the 2,337 exactly, asserted): class sizes stable (OUT 154/164/139, IN 35/33/37), pressure separation stable (OUT median 0.764/0.717/0.673 vs IN 0.179/0.181/0.198), while realized-change medians swing window to window (OUT +17.5 / +44.5 / +181.0) — **current pressure standing is a stable signal; realized growth is not** — the random walk restated in policy terms. Manifest: `output/README.md` maps all 15 artifacts to their source csvs.
20. **Scaled FL across every specialty** (`14_fl_scaleup.ipynb`): notebook 11's delta-space protocol run unchanged over all 24 specialties at the 149 public `fl_client` providers (187,041 provider-months in the pool; 26,504 FY 2024-25 validation rows; the C_110 row asserted to reproduce 11 exactly — 1,407 rows, naive 153, fedavg-delta 154.0, one cold-start client). Two results. **(a) Federation ≈ pooled everywhere**: fedavg-delta's MAE gap to pooled has median −0.08 and worst +1.27 across specialties (best −4.61 — sample-weighted client averaging can even beat the single pooled fit), so the privacy-preserving headline generalizes. **(b) The random-walk closure is C_110-scoped**: in 12 of 24 specialties a delta model edges persistence at 1 month — largest margins C_120 (165.1 vs persistence 171.6, n=1,265), C_330 (165.3 vs 171.3, n=1,147), C_301 (124.4 vs 128.4, n=1,320) — while persistence still wins at C_110 and 11 others (models worst at X02: 153.2 vs 144.2, n=1,409). Margins are small (≤6.5 MAE) but real; whether they justify a model layer at those specialties is a supervisor question. 13 cold-start provider-rows across all specialties; X01 has zero validation rows in this pool. → `fl_scaleup_by_specialty.csv` (24 × 22).
21. **Ran the first neural FL experiment** (`16_fl_neural_clients.ipynb`): a GRU client (1 layer, hidden 32, 6-month windows of level/momentum/wait-shares, all hyperparameters declared a priori — no sweeps, no early stopping, seed 42) predicting the 1-month change, federated by classic FedAvg (10 rounds × 5 local steps), across all 23 scored specialties (X01 skipped — zero eligible validation windows); every model rescored on identical window-eligible rows with n stated. **Aggregate verdict: neural ≈ linear** — neural FedAvg beats linear FedAvg at 11 of 23 specialties (full regime; median MAE gap +0.15, best −5.25, worst +3.06) and at 55.2% of 2,441 client-specialty pairs. **New crack at the anchor**: on C_110's 1,401 eligible rows, neural pooled scores **150.6** and neural FedAvg **152.4** vs recomputed persistence 154.1 — the project's first sub-persistence C_110 scores, at 1.7–3.5 MAE with one seed and no tuning; 184 scores were computed in this notebook, so isolated wins are expected by chance — a declared seed-robustness check is the honest follow-up (supervisor decision). Even the best model explains ≤7.5% of delta variance (`r2_delta_secondary`, computed on deltas because level-R² stays rejected). Federation costs neural models more than linear where signal exists (C_120: pooled 163.9 → FedAvg 168.6). → `fl_neural_summary.csv` (207 × 7), `fl_neural_per_client.csv` (2,441 × 6), `output/figures/fl_neural_vs_linear.png`.

Details and evidence for each point below.

## Dataset

96 monthly NHS England RTT "Full CSV" extracts, April 2018 → March 2026 (financial years 2018-19 to 2025-26), fetched by `src/01_fetch_dataset.ipynb`. Each file is one month, provider × commissioner × specialty, with waits banded by week.

## Integrity checks — all passed

| check | result |
|---|---|
| files on disk | 96 csvs (~92–95 MB each in 2018), 96 zips |
| month coverage | 96 of 96 months present, no gaps (assert) |
| `Period` inside file vs filename | matches in all 96 files (assert) |
| schema generations | exactly 2 column sets: 69 cols × 36 files, 121 cols × 60 files |
| schema break | one break only, at `20210430-RTT-APRIL-2021` (extended 52+ week bands added) |
| `C_999` aggregate proof | Apr 2018: C_999 row = 4,037,223 = sum of real specialty rows, exactly (assert) |
| file manifest | sizes + sha256 for all 96 files → `data/reference/rtt_manifest.csv` |

## Known traps, proven and handled

**C_999.** The files contain a `C_999` "Total" specialty row equal to the sum of the real specialty rows. Summing over all specialties without dropping it doubles every figure — Oct 2019: 8,928,070 with the row vs 4,464,035 without, and the without-figure matches the published national waiting list. The panel build excludes it.

**Part types.** Five part types exist in both schema eras (verified in the Apr 2018 and Mar 2026 files): `Part_1A`/`Part_1B` (completed admitted/non-admitted), `Part_2` (Incomplete Pathways — the waiting list), `Part_2A` (Incomplete Pathways *with a decision to admit*), `Part_3` (new RTT periods). National totals in Mar 2026 via the C_999 rows: Part_2 = 7,045,510 vs Part_2A = 1,178,492 — consistent with Part_2A being the with-DTA subset of Part_2, so the panel keeps only `Part_2` to avoid double counting.

## The panel

`data/processed/rtt_incomplete_panel.csv` — 343,441 rows × 8 columns. One row per (month, provider, specialty), incomplete pathways (`Part_2`) only: `month, provider_code, tfunc_code, total_waiting, gt18, gt52, pct_gt18, pct_gt52`. Long-wait columns sum every week band starting at ≥ 18 (resp. ≥ 52) weeks, which works across both schema generations.

Coverage: 96 months, 651 providers, 24 specialties. Provider count per month drifts over the period (trust mergers; independent providers entering/leaving) — see the providers-per-month and months-per-provider plots, section 9.

**Public vs independent split** (matched against the ODS RO197 trust list, `data/reference/trust_icb.csv`): 193 of the 651 provider codes are NHS trusts and they hold **94.5%** of the total waiting list (denominator: all patient-months in the panel); the other 458 are independent-sector providers holding 5.5%. Decision: keep independents, flagged (`is_public` = membership in the ODS trust list) — they matter for the private-capacity storyline but barely move national figures.

**Specialty concentration** (share of all patient-months): the list is spread widely — largest is C_110 Trauma & Orthopaedics at 11.6%, then C_130 Ophthalmology 9.1%, C_120 ENT 8.0%, C_502 Gynaecology 7.4%, C_100 General Surgery 6.4%; the remaining 19 specialties are each below 6%. No single specialty dominates.

## Headline numbers

Means of the England-wide monthly series. Denominator for the `%` columns: that month's total incomplete waiting list. Recomputed from `rtt_incomplete_panel.csv` 2026-07-30.

| era | mean waiting list | % > 18 weeks | % > 52 weeks |
|---|---|---|---|
| pre-Covid (Apr 2018 – Feb 2020, 23 months) | 4,283,000 | 13.9% | 0.05% |
| post-Covid (Mar 2020 – Mar 2026, 73 months) | 6,574,296 | 38.8% | 4.11% |

The list grew 53.5% post-Covid, but long waits grew far faster: the >52-week share rose from 0.05% to 4.11% — **81× on the era means** (an earlier "~40×" in this document came from rounding 0.05% up to 0.1%). Trend plots (national series, both long-wait shares, biggest provider × specialty cell) are stored in the notebook, sections 10–11.

## Forecasting vs the persistence bar (04 + 07 + 08 + 09)

Task: one-month-ahead `total_waiting`, C_110 (Trauma & Orthopaedics) at 130 stable public providers (`fl_client` ∧ `is_public`). Splits declared, not tuned: train to Mar 2024 (full-history from Apr 2018, 9,024 rows; post-Covid from Mar 2020, 6,185 rows), validate on 1,407 FY 2024-25 rows, sealed FY 2025-26 untouched. Notebooks 07 and 08 assert they score the *exact* rows 04 scored (`assert len(val) == 1407`; recomputed naive MAE = 153). One declared seed (42).

Every variant run, MAE / RMSE on the same 1,407 validation rows (from the notebooks' stored outputs):

| model | notebook | full-history | post-Covid |
|---|---|---|---|
| naive persistence (next = this month) | 04, 07, 08 | **153** / 330 | — |
| pooled linear (level, `pct_gt18/52`, month index) | 04 | 156 / 330 | 154 / 330 |
| gbm on the one-month change | 07 | 155 / 336 | 158 / 338 |
| gbm on the raw level | 07 | 178 / 372 | 174 / 368 |
| drift (training-mean change) | 07 | 156 / 330 | 158 / 331 |
| seasonal drift (per-calendar-month mean change) | 07 | 158 / 332 | 162 / 333 |
| net-flow identity (change = referrals − completions) | 08 | 250 / 453 | — |
| net-flow linear (change = a + b·net_flow) | 08 | 154 / **328** | 155 / 329 |
| gbm on the change + flow features | 08 | 155 / 335 | 158 / 338 |

What the stored outputs establish:

- **Persistence is unbeaten on MAE by every variant tried.** Monthly waiting lists at this grain behave near-random-walk. The one crack: net-flow linear beats naive on **RMSE** (328 vs 330) — the flow signal trims large errors slightly but not typical ones.
- **The flows are real but ~90% absorbed by removals.** Nationally net flow correlates 0.74 with the actual monthly change (n=95 months), yet the mean monthly net flow is 265,730 against a mean actual change of 31,666 — patients leaving without treatment (not counted by `Part_1`) absorb the rest. At provider level the fitted slope is 0.08 (full) / 0.13 (post-Covid): only ~a tenth of a marginal net-flow unit shows up in the next month's list. The unscaled identity forecast scores MAE 250 for exactly this reason.
- **Levels are the wrong target for trees**: validation contains a new all-time high (18,758 vs 18,453 max next-month list in training), and the level GBM loses by 20+ MAE — the measured reason 07/08 predict the change.
- **Seasonality does not transfer**: seasonal drift loses to plain drift in both regimes (158 vs 156; 162 vs 158) — training-period calendar patterns do not hold in FY 2024-25.
- **Occupancy adds ~nothing at this horizon.** Permutation importance of the post-Covid delta model in 07 (MAE increase when a feature is shuffled): `total_waiting` 10.18, `delta_1` 9.57, `delta_3` 4.39, `pct_gt18` 3.85, `pct_gt52` 3.06, `month_of_year` 2.76, `delta_2` 2.22, `occupancy_ga` 0.20. In 08's full-history model with flows, `delta_1` (7.67) and `total_waiting` (5.33) still lead; `net_flow_3m` is the best flow feature (3.67).
- Reporting gaps are negligible in this cohort: 0.10% of row-to-row steps span more than one calendar month; 99.6% of the 10,431 cohort provider-months carry a flows return (the one validation gap — R1A, Dec 2024 — falls back to persistence via an arithmetic guard).

Stored forecasts: `val_forecasts_c110_public_clients.csv` (04), `val_forecasts_c110_gbm.csv` (07), `val_forecasts_c110_flows.csv` (08).

### Longer horizons (09)

Splits by **target month** (training targets ≤ Mar 2024, validation targets in FY 2024-25; an origin split would let a 12-month forecast validate on the sealed year — asserted impossible here). The window is therefore 12 target months, so n ≈ 1,524–1,534 rather than 04's 1,407 origin-based rows; the fresh 1-month persistence MAE on this window is 154, consistent with the 153 anchor. Every figure from `val_horizons_c110.csv` / the stored outputs:

| horizon | persistence | best challenger | seasonal (same month last year) |
|---|---|---|---|
| 1-month (n=1,534) | **154** / 326 | gbm-delta+flows full 156 / 327 | 742 / 1,133 |
| 3-month (n=1,532) | **317** / 558 | drift full 331 / 560 | 742 / 1,133 |
| 6-month (n=1,529) | **501** / 799 | drift full 538 / 817 | 742 / 1,133 |
| 12-month (n=1,524) | **742** / 1,133 | drift full 847 / 1,193 | ≡ persistence |

- **Persistence wins at every horizon and the gap widens with distance** — the external hypothesis "seasonal naive or drift should beat naive at 6–12 months" is measured false.
- **No usable seasonality at any horizon**: same-month-last-year always forecasts the target from its own month−12 value, so it scores identically (742) at every horizon — and identically to 12-month persistence. Today's level beats last year's level even for a 12-month forecast.
- **Conformal 90% bands around persistence** (calibrated on FY 2023-24 targets, ~1,512–1,524 rows; coverage measured on FY 2024-25 — a year the calibration never saw): ±298 (1m), ±649 (3m), ±1,053 (6m), ±1,714 (12m) patients, with honest out-of-year coverage 89.0% / 88.7% / 87.6% / 89.6% against the nominal 90%. This is the uncertainty layer for allocation decisions.

Stored results: `val_horizons_c110.csv` (23 × 6).

### Coarser grains (12)

Same series aggregated to ICB (35 series) and England, **constant membership** (115 providers present in all 96 months — a declared composition rule; aggregating a churning set fabricates level jumps). The shortest ICB series spans 84 months rather than 96 (printed in the notebook — not every ICB code covers the full window), so ICB-level training windows are slightly uneven; validation is unaffected (n=420 = 35 series × 12 target months at every horizon). Same target-month splits; each grain judged against its own persistence. From `val_horizons_coarse_c110.csv`:

| horizon | ICB persistence (n=420) | ICB best challenger | national persistence (n=12) | national best challenger |
|---|---|---|---|---|
| 1-month | **310** | drift full 329 | **3,777** | drift full 4,322 |
| 3-month | **657** | drift full 738 | **5,652** | drift full 9,502 |
| 6-month | **1,077** | drift full 1,279 | **8,928** | seasonal 9,580 |
| 12-month | **1,523** | drift full 1,992 | **9,580** | drift full 48,009 |

Aggregation does not reveal usable structure: persistence wins everywhere, seasonal stays far behind, and drift blows up at long national horizons (48,009 vs 9,580 at 12 months — it extrapolates the training era's growth, which flattened in FY 2024-25). **The random walk holds at provider, ICB and national grain — the forecasting question is closed at every grain and horizon measured.**

## Agent prototype (10)

First Phase-B build, on top of persistence + bands. Every constant is **declared, not tuned** (2026-07-30; **ratified by the project owner 2026-07-30** — frozen in `15_agent_rules_frozen`, which proves the constants reproduce 10's stored decisions bit for bit; the decision record is `docs/supervisor_decision_sheet.md`, and the supervisor reviews the final draft): pressure weights 0.2/0.6/0.2 (>52-week share weighted highest — it is the component that moved 81× post-Covid); thresholds 0.70/0.40 (pressure), 1.20/1.05 (band-upper vs current), 0.80 (occupancy slack).

Design decisions the data forced (all measured in the notebook's stored outputs):

- **Within-month percentile ranks, not max-normalization.** All three component maxima are exactly 1.0 (printed), so dividing by the max is the identity, and pooled-over-time ranks would measure the era (81× shift), not the provider. Allocation compares providers at the same moment.
- **Band recomputed, not copied**: ±1,171 patients for this cohort (150 allocatable providers; calibrated on 7,357 rows with targets before Apr 2023) — *not* the ±1,053 of notebook 09's 130-provider `fl_client` cohort. Hardcoding the remembered number would have been wrong.
- **Two of the four proposed rules are arithmetically dead** under a persistence forecast with an absolute pooled band: REDISTRIBUTE_OUT requires the lower band edge ≥ 1.1 × current (lower edge = current − band, always below current); REDISTRIBUTE_IN's stability test (`upper ≤ 1.05 × current`) requires current ≥ band/0.05 = 23,420 patients — no C_110 list is that large (largest seen: 18,758). REDISTRIBUTE_OUT is documented in the notebook header instead of coded; REDISTRIBUTE_IN is coded in the v1 rule and selects 0 of 2,337 provider-months (stored counts: STATUS_QUO 2,003 + EXPAND 334 = 2,337) — the stored proof of the arithmetic.

Pressure-score distribution across the cohort (denominator: 11,373 provider-months): mean 0.504, quartiles 0.344 / 0.486 / 0.676, range 0.024–0.994 — centred on 0.5 by construction (weighted percentile ranks), so the 0.70 threshold sits just above the upper quartile.

Simulation (2,337 provider-months, origins Apr 2023 – Sep 2024, all outcomes inside the development window): EXPAND_CAPACITY 334 rows (14.3%), STATUS_QUO 2,003; 30 providers ever trigger, the top ten triggering in all 18 possible months (persistent pressure, not spikes). **Reality check**: EXPAND months preceded *no more* growth than status-quo months (median realized 6-month change +0.5 vs +37 patients; 50.0% vs 53.5% of rows grew — denominators 334 / 2,003). This is the random-walk result showing up in policy: growth-risk triggers built from available signals cannot select rows that go on to grow, so **allocation rules should condition on current measured pressure, not predicted growth** — the central input for the supervisor discussion on final rule design.

**v2 — redistribution on within-ICB standing** (same notebook, declared thresholds OUT ≥ 0.80 / IN ≤ 0.30 on within-ICB pressure and occupancy ranks): OUT 457 / IN 105 / STATUS_QUO 1,775 of the same 2,337 rows. The classes separate real populations — OUT: median pressure 0.723, median realized 6-month change +81; IN: 0.183, +5; STATUS_QUO: 0.471, +14. **Only 13.6% of the 457 OUT flags have at least one IN receiver in their own ICB-month** (ICB groups are small: min 1 / median 3 / max 10 providers across 648 month-ICB groups), so within-ICB redistribution mostly lacks a destination — the receiving side needs cross-ICB pooling or the independent sector. Known artifact for the supervisor list: a single-provider ICB always ranks 1.0 and so auto-flags OUT (QR1 and QK1 fire in all 18 months with zero STATUS_QUO).

Stored decisions: `agent_decisions_h6_c110.csv` (2,337 × 17).

## Federated learning (11)

The FL question is not "beat persistence" (closed) but the collaboration question itself: does FedAvg recover what central pooling learns, and does either beat local-only training? 128 C_110 clients, linear on (level, momentum), declared splits and regimes unchanged, all scored on the same 1,407 validation rows (asserted; naive MAE = 153 recomputed).

| model | full-history MAE / RMSE | post-Covid MAE / RMSE |
|---|---|---|
| naive persistence | **153.5** / 330.1 | — |
| pooled (centralised) | 153.8 / 330.3 | 155.4 / 331.9 |
| **fedavg-delta** (phase 2: change = a + b·momentum, coefficients averaged) | **154.0** / 332.0 | 155.5 / 333.1 |
| fedavg-delta + local intercept (share slope only) | 155.3 / 334.3 | 157.4 / 336.3 |
| local-only | 161.9 / 345.2 | 166.5 / 350.5 |
| FedAvg on levels (phase 1) | 186.5 / 363.5 | 228.8 / 401.4 |

- **Pooled ≈ persistence** — the centralised linear model rediscovers the random walk, consistent with 04.
- **Naive FedAvg actively hurts** (worse than never collaborating): averaging raw-scale coefficients across clients whose lists span ~50 to ~18,000 patients breaks the intercept — the classic non-IID heterogeneity failure, measured on real data. Per client, FedAvg beats local at only 41.4% of 128 clients (local beats naive at 46.1%; median per-client MAE local 113 / fedavg 134 / naive 113).
- **Cold start measured**: RJ8's C_110 series begins May 2024 (96 months active in other specialties), so it has zero training rows — local-only must fall back to persistence for it, while the shared model can serve it. This is the FL value proposition in miniature, even when averaging otherwise hurts.
- **Phase 2 repairs the failure**: federating in delta space (each client fits *change* = a + b·momentum; coefficients averaged) recovers the entire 32.5-point loss — 154.0 vs 186.5 — and lands within 0.2 MAE of centralized pooling while raw data never leaves the client. Sharing only the slope with client-kept intercepts is slightly worse (155.3): local intercepts overfit client noise. The federated headline: **once the shared quantity is scale-free, privacy-preserving federation matches centralization on this data** — and, like everything else, does not beat persistence.

Stored results: `fl_summary_c110.csv` (11 × 5), `fl_per_client_c110.csv` (128 × 6).

### Scale-up across specialties (14)

The same protocol, one loop, no per-specialty tuning: all 24 specialties at the 149 public `fl_client` providers, 26,504 FY 2024-25 validation rows in total. From `fl_scaleup_by_specialty.csv` (24 × 22) and the stored prints — MAE, full-history regime, n beside each rate:

| specialty | n_val | persistence | pooled | fedavg-delta | verdict |
|---|---|---|---|---|---|
| C_120 | 1,265 | 171.6 | 167.4 | **165.1** | delta models win by 6.5 |
| C_330 | 1,147 | 171.3 | 165.5 | **165.3** | win by 6.0 |
| C_301 | 1,320 | 128.4 | 125.1 | **124.4** | win by 4.0 |
| C_110 | 1,407 | **153.5** | 153.7 | 154.0 | persistence holds (= notebook 11, asserted) |
| X02 | 1,409 | **144.2** | 152.6 | 153.2 | persistence wins by 9.0 — worst case for models |

- **Federation ≈ pooled at every specialty**: fedavg-delta − pooled MAE gap median −0.08, worst +1.27, best −4.61. The delta-space federation result is not a C_110 artifact.
- **The random-walk closure is C_110-scoped**: a 1-month delta model edges persistence in 12 of 24 specialties (X01 has zero validation rows in this pool). The margins are small (≤6.5 MAE) — a supervisor question whether they justify a model layer at those specialties; the C_110 closure (04–09, 12) is unaffected.
- Cold starts (series starting inside FY 2024-25, the RJ8 case generalized): 13 provider-rows across all specialties, neutral zero momentum.
- **Training regimes, measured across specialties**: full-history training gives lower fedavg-delta MAE than post-Covid-only at 17 of the 18 C-specialties (the exception is C_300: 37.42 post vs 37.51 full); the five X-codes score identically under both regimes — they have no pre-Covid training rows in this pool. Delta-space models lose nothing from keeping the pre-Covid years: the shared quantity is scale-free, so the regime break matters far less than it does for level models.

### Neural clients (16)

One declared architecture, no tuning (GRU hidden 32, 6-month windows, FedAvg 10 × 5, Adam 1e-3, seed 42; the pooled reference gets the identical step budget). All models — persistence, linear delta pooled/FedAvg (11's model recomputed), neural pooled/FedAvg — scored on identical window-eligible rows. From `fl_neural_summary.csv` (207 × 7):

| specialty (n eligible) | persistence | linear pooled / fedavg | neural pooled / fedavg |
|---|---|---|---|
| C_110 (1,401) | 154.1 | 154.4 / 154.7 | **150.6** / **152.4** |
| C_120 (1,265) | 171.6 | 167.9 / 165.5 | **163.9** / 168.6 |
| C_130 (1,221) | 144.3 | 141.5 / 141.5 | **140.1** / 142.9 |

- **Aggregate: a coin flip.** Neural FedAvg beats linear FedAvg at 11 of 23 specialties (full; median gap +0.15 MAE) and 55.2% of 2,441 client-specialty pairs; it beats persistence at 11 of 23. No material improvement over the linear delta layer.
- **But the C_110 anchor cracks for the first time**: neural pooled 150.6 and neural FedAvg 152.4 vs persistence 154.1 on the same 1,401 rows — small (1.7–3.5 MAE), single-seed, untuned, and one of 184 computed scores, so chance is a live explanation; a declared multi-seed check is the honest follow-up. **Update 2026-07-30 — confirmed by that check (`19_neural_c110_multiseed`, from `fl_neural_c110_multiseed.csv`, 12 × 6)**: seeds 42/123/999, declared with the verdict rule before running, all beat persistence in the full regime for both models — pooled 151.5 ± 0.9 MAE (150.6 / 152.2 / 151.9), FedAvg 152.4 ± 0.0 (152.4 / 152.3 / 152.4) vs 154.1 on the same 1,401 rows. Post regime reported as-is: FedAvg 3 of 3 seeds, pooled 2 of 3 (seed 123 lands exactly on 154.1).
- **Federation is costlier for neural clients than linear ones** where signal exists: C_120 pooled 163.9 vs FedAvg 168.6 (linear FedAvg 165.5 — the weight average hurts more than the coefficient average).
- **The signal stays tiny everywhere**: best `r2_delta_secondary` = +0.075 (C_120 neural pooled) — deltas are ≥ 92.5% unexplained variance even at their most predictable. R² is computed on deltas and labelled secondary; level-R² remains rejected.
- **Dataset size does not decide the winner** (13's comparison figures, stored 2026-07-30): Pearson r = 0.128 between a specialty's validation size and its relative neural−linear FedAvg gap; the four biggest relative neural wins are the X-codes (X03 −8.3% of persistence MAE, X05 −3.8%, X02 −3.6%, X04 −2.6%) — exactly the specialties with no pre-Covid history — and the biggest loss is C_170 (+5.3%). Figures: `fig_c110_fl_linear_vs_neural_h1`, `fig_fl_neural_gap_by_specialty_h1`, `fig_fl_covid_regime_effect_h1`, `fig_fl_neural_gap_vs_size_h1` under `output/figures/`.

## Sealed-year one-shot (17, run once 2026-07-30)

FY 2025-26 was read for the first and only time, on explicit instruction, with everything declared in
17's pre-registration cell before execution: h=1 forecast layer only (the agent simulation and band
coverage were deliberately excluded — each is its own future decision); full-history regime; linear in
two cuts (**val-frozen** — the exact fits validation scored — and **final** — refit on targets through
Mar 2025); neural final cut only, seed 42; test rows = windows with origins Apr 2025 – Feb 2026
(targets May 2025 – Mar 2026, the mirror of validation's 11 origins); X01 skipped (zero sealed
windows). The window build replicated 16's validation rows exactly before touching a sealed row
(1,401 / 154.1, asserted). From `sealed_year_eval.csv` (161 × 8, validation-year MAE joined beside
every sealed score):

- **The C_110 anchor returns to persistence.** Sealed C_110 (n=1,407): persistence **151.5**, neural
  pooled 151.6, neural FedAvg 152.1, linear final 153.0, linear val-frozen 153.3. The
  validation-confirmed neural edge (150.6 / 152.4 vs 154.1, 3-seed confirmed in 19) did **not**
  replicate prospectively — persistence won by 0.1 MAE. FY 2025-26 was a slightly easier year for
  C_110 persistence (−1.7% vs validation).
- **In aggregate the delta models strengthened**: neural pooled beats persistence at 15 of 23 scored
  specialties (13 on validation), neural FedAvg at 14 (11 on validation), linear FedAvg final at 14;
  the val-frozen linear at 10 of 23. Margins remain small everywhere.
- **The year moves more than the models**: per-specialty persistence MAE changed by a median +4.6%
  vs the validation year (23 specialties, from −51.1% at X03 to +38.2% at C_150) — year-to-year
  drift in the target itself dwarfs every model margin in this project.
- Figures (13, from the sealed csv): `fig_c110_sealed_one_shot_h1`, `fig_sealed_gap_by_specialty_h1`,
  `fig_sealed_persistence_drift_h1`; the generated headline list is `output/RESULTS.md`.

## Goals vs evidence (verified 2026-07-30)

Verification basis: all nineteen notebooks (01–19) re-checked programmatically — every code cell executed (8, 23, 5, 6, 5, 4, 8, 9, 4, 8, 4, 3, 19, 3, 3, 6, 4, 2, 3 cells respectively), zero stored error outputs, and every claim in this document has its implementing code line present in the notebook it cites.

| goal (README) | status | evidence |
|---|---|---|
| Clean, audited RTT panel (milestone 1) | **met** | assert chain in 02; canonical panel on disk; row counts preserved through every join |
| Forecast at provider × specialty | **closed for C_110 at every grain measured**: persistence + calibrated bands | 04 + 07–09 + 12: persistence unbeaten on MAE at every horizon 1–12 months and at provider, ICB and national grain; the deliverable is persistence with conformal 90% bands (±298 to ±1,714, out-of-year coverage 87.6–89.6%). Scope note from 14: at 12 of 24 *other* specialties a 1-month delta model edges persistence by ≤6.5 MAE — the closure claim is C_110-scoped |
| Full-history vs post-Covid regimes | met, verdict unsettled | the advantage flips by model class: post-Covid wins for linear (154 vs 156) but full-history wins for gbm-delta (155 vs 158) and drift (156 vs 158) — neither regime dominates |
| Agent policies (pressure, redistribution, private capacity) | v1 + v2 built; constants pending ratification | 10: declared-weight pressure score; v1 EXPAND 334/2,337 at 30 trusts (growth-risk triggers select no extra growth — rules must condition on current pressure); v2 within-ICB OUT 457 / IN 105, but only 13.6% of OUT flags have an in-ICB receiver — redistribution needs cross-ICB or independent-sector receivers |
| Federated learning | phases 1 + 2, multi-specialty scale-up, neural clients — all run | 11: naive level-FedAvg hurts (186.5 vs local 161.9 — non-IID failure); **delta-space federation fixes it** (154.0, within 0.2 of pooled 153.8); 14: the repair generalizes across all 24 specialties (fedavg-delta − pooled MAE gap median −0.08, worst +1.27); 16: neural clients ≈ linear in aggregate (11 of 23 specialties, 55.2% of client pairs), with the first sub-persistence C_110 scores (neural pooled 150.6 vs 154.1, n=1,401 — single-seed, pending a declared robustness check) |
| Capacity at department level | **trimmed by evidence** | KH03 publishes availability by sector only — capacity is provider-level, documented in the design record |

## Status: done vs not done

**Done (all verified by headless runs on the real data, outputs stored):**

- `01_fetch_dataset.ipynb` — download of all 96 RTT months, ODS trust reference, 61 KH03 files; idempotent and rerunnable.
- `02_eda_dataset.ipynb` — single-file EDA (structure, dtypes, missingness, numeric summary), file inventory, month-coverage assert, header-only schema audit, Period-vs-filename assert, C_999 aggregate proof, part-type evidence, sha256 manifest, panel build with three asserts, coverage + churn plots, national trends, specialty shares, pre/post-Covid comparison, saved core panel.
- `03_provider_flags.ipynb` — ODS join onto the panel: `is_public` (193 public / 458 independent; public trusts hold 94.5% of patient-months), stability columns (median 89 months active of 96), and declared flags: `fl_client` (≥48 months + reporting in the final month) = 392 providers; `fl_allocatable` (public + ≥24 months) = 182 → `data/processed/rtt_panel_with_provider_flags.csv` (343,441 × 18).
- `04_baseline_forecasting.ipynb` — **sealed test year declared: FY 2025-26 (43,248 rows kept out, asserted)**. One-month-ahead `total_waiting` for C_110 at stable public providers (130 providers, 10,431 provider-months; train-full 9,024 rows, train-post 6,185), validated on 1,407 FY 2024-25 rows (forecast origins Apr 2024 – Feb 2025 — the Mar 2025 origin drops because its target is the sealed Apr 2025 value): naive persistence MAE 153 / RMSE 330; pooled linear full-history MAE 156; post-Covid-only MAE 154. **Persistence is the bar and nothing beats it yet** — monthly waiting lists are near-random-walk, so a useful model must exploit structure beyond current level + trend. Forecasts saved to `data/processed/val_forecasts_c110_public_clients.csv` (1,407 × 6).
- `05_kh03_beds.ipynb` — KH03 audit and monthly capacity panel: 60 quarters (Apr 2011 → Q4 2025-26), 12,453 provider-quarters, occupancy cross-checked against the sheet's own `% Occupied` column (asserted); three data traps handled (duplicate quarter, year typo, `-` markers) → `kh03_monthly_panel.csv` (37,359 × 8).
- `06_merge_canonical.ipynb` — the canonical panel: RTT demand + provider flags + provider-level capacity, one row per (month, provider, specialty), row count preserved by the left join (asserted); public-trust capacity coverage 99.0% → `rtt_kh03_canonical_panel.csv` (343,441 × 24).
- `07_beat_persistence.ipynb` — first structured models against the MAE-153 bar, same 1,407 validation rows as 04 (asserted; recomputed naive MAE = 153 exactly). Gradient boosting on the one-month change: MAE 155 (full-history) / 158 (post-Covid); raw-level variant 178 / 174 (trees cannot reach the validation year's new high — 18,758 vs 18,453 max in training); drift 156 / 158; seasonal-drift 158 / 162. Permutation importance: current level 10.18 and 1-month momentum 9.57 dominate; occupancy 0.20 ≈ nothing. **Persistence still unbeaten** — seasonality, momentum and occupancy measurably do not add one-month-ahead value on FY 2024-25. Forecasts saved to `data/processed/val_forecasts_c110_gbm.csv` (1,407 × 6).
- `08_part3_flows.ipynb` — the flows panel (`rtt_flows_panel.csv`, 338,265 × 5: `Part_3` referrals in, `Part_1A/1B` completions out, per month × provider × specialty) plus the forecast test on the same 1,407 validation rows (asserted; recomputed naive MAE = 153). National: corr(net flow, actual change) = 0.74 (n=95 months) but mean net flow 265,730 vs mean actual change 31,666 — removals absorb ~90%. Validation: net-flow identity MAE 250; net-flow linear 154 / RMSE 328 (best RMSE yet; naive 330), slope 0.08–0.13; gbm+flows 155 / 158. **Persistence still unbeaten on MAE.** Forecasts saved to `val_forecasts_c110_flows.csv` (1,407 × 7).
- `09_longer_horizons.ipynb` — 1/3/6/12-month horizons, target-month splits (sealed year unreachable, asserted). Persistence wins everywhere and its lead widens: 154 / 317 / 501 / 742 MAE vs best challengers 156 / 331 / 538 / 847; same-month-last-year scores 742 at every horizon (no usable seasonality). Conformal 90% bands calibrated on FY 2023-24, coverage 87.6–89.6% on FY 2024-25: ±298 / ±649 / ±1,053 / ±1,714 patients → `val_horizons_c110.csv` (23 × 6).
- `10_agent_logic.ipynb` — agent prototype v1 + v2: declared-weight pressure score (0.2/0.6/0.2 on within-month ranks), 6-month persistence band recomputed for the allocatable cohort (±1,171, calibrated on 7,357 pre-Apr-2023 rows), 2,337 simulated provider-months with known outcomes. v1: EXPAND 334 rows / 30 providers; growth-risk triggers select no extra realized growth (median +0.5 vs +37) → rules must condition on current pressure. v2: within-ICB OUT/IN (457 / 105); only 13.6% of OUT flags have an in-ICB receiver → `agent_decisions_h6_c110.csv` (2,337 × 17).
- `11_federated_learning.ipynb` — 128-client FL experiment on the standard validation rows, phases 1 + 2: naive level-FedAvg 186.5/228.8 (heterogeneity breaks coefficient averaging; local-only 161.9, pooled 153.8 ≈ persistence 153.5); **delta-space federation repairs it** — fedavg-delta 154.0/155.5, within 0.2 of pooled; slope-only sharing 155.3/157.4; RJ8 cold-start case measured → `fl_summary_c110.csv` (11 × 5), `fl_per_client_c110.csv` (128 × 6).
- `12_coarser_grain.ipynb` — ICB (35 series) and England aggregation, constant membership (115 providers × 96 months): persistence wins at every horizon at both grains (ICB 310/657/1,077/1,523, n=420; national 3,777/5,652/8,928/9,580, n=12); drift blows up at long national horizons (48,009 at 12m) → `val_horizons_coarse_c110.csv` (30 × 7).
- `13_report_figures.ipynb` — the report artifact layer: 6 figures + 9 eval tables + provenance manifest under `output/`, built strictly from `data/processed/` csvs (nothing recomputed; documented values pinned by assert). Includes the persistence stability tables (by origin month, by provider) and the three-window agent stress test. Audit spec and verification record: `CODE_AUDIT.md`.
- `14_fl_scaleup.ipynb` — 11's delta-space FL protocol over all 24 specialties × 149 public `fl_client` providers (26,504 validation rows; C_110 row asserted to reproduce 11). Federation ≈ pooled everywhere (median MAE gap −0.08, worst +1.27); a delta model edges persistence at 12 of 24 specialties (largest −6.5 MAE at C_120) — the random-walk closure is C_110-scoped → `fl_scaleup_by_specialty.csv` (24 × 22).
- `16_fl_neural_clients.ipynb` — the first neural FL experiment: GRU clients (declared a priori, seed 42, no tuning), FedAvg over weights, all 23 scored specialties on identical window-eligible rows. Neural ≈ linear in aggregate (11 of 23; per-client 55.2%); first sub-persistence C_110 scores (pooled 150.6 / FedAvg 152.4 vs 154.1, n=1,401 — single-seed, chance not excluded); best delta-R² anywhere +0.075 → `fl_neural_summary.csv` (207 × 7), `fl_neural_per_client.csv` (2,441 × 6).
- `docs/eda_rtt_summary.md` — this document; `docs/idea_canonical_pipeline.md` — the pipeline design record.

**Not done yet:**

- Beating persistence — now measured impossible at every grain (provider, ICB, national; 07/08/09/12) and horizon (1–12 months) with every available signal. **Persistence + calibrated conformal bands is the forecast layer, final.**
- Final agent rule set — all declared constants (weights 0.2/0.6/0.2; v1 thresholds 0.70/0.40; v2 thresholds 0.80/0.30) await supervisor ratification, plus the v2 lessons: the receiving side needs cross-ICB pooling or the independent sector (only 13.6% of OUT flags have an in-ICB receiver), and single-provider ICBs need a minimum-group rule.
- FL frontier — linear scale-up (14), neural clients (16) and the multi-seed check (19, **confirmed** for the full regime) all measured; remaining: widening the pool beyond the 149 public `fl_client` providers (the other 243 `fl_client` providers are independents — RTT series but no KH03 capacity).
- The one-shot final evaluation on the sealed FY 2025-26 — happens once, at the end.
