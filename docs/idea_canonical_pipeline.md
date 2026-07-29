# fedOPD — Canonical Panel Pipeline (RTT + ODS + KH03)

Design record for the pipeline implemented in `src/01`–`src/06`. Written 2026-07-30, after the pipeline ran; every claim below is backed by stored notebook outputs.

## Goal

One model-ready panel: monthly, per provider × specialty, carrying demand (RTT), provider context (ODS), and capacity (KH03). Single source of truth for forecasting, agent rules, and federated learning.

## The pipeline as built

| step | notebook | output |
|---|---|---|
| fetch raw | `01_fetch_dataset` | 96 RTT zips/csvs, ODS trust list (544), 61 KH03 files |
| audit + RTT panel | `02_eda_dataset` | `rtt_incomplete_panel.csv` (343,441 × 8) |
| provider flags | `03_provider_flags` | `rtt_panel_with_provider_flags.csv` (343,441 × 18) |
| baselines + sealed year | `04_baseline_forecasting` | `val_forecasts_c110_public_clients.csv` (1,407 × 6) |
| KH03 capacity | `05_kh03_beds` | `kh03_monthly_panel.csv` (37,359 × 8) |
| merge | `06_merge_canonical` | **`rtt_kh03_canonical_panel.csv` (343,441 × 24)** |

## Deviations from the original plan — and why

The drafted plan assumed KH03 could be mapped to RTT specialties. The data says otherwise:

1. **KH03 has no specialty dimension for capacity.** Its `NHS Trust by Sector` sheet reports four sectors (General & Acute, Learning Disability, Maternity, Mental Illness). An `Occupied by Specialty` sheet exists, but *Available* does not exist by specialty — so occupancy rate is only computable at sector level. Decision: capacity joins at **provider level** and repeats across a provider's specialty rows. A KH03-specialty→TFC mapping table was therefore **not** built.
2. **Units are average daily beds** open/occupied over the quarter — not bed-days as the plan assumed.
3. **No intersection-of-columns loader for RTT.** Long waits are derived from week-band *names* (`Gt 18 To 19 …`), which works in both the 69- and 121-column schema generations and keeps the post-2021 extended bands instead of discarding them.

## Data facts the pipeline had to handle (all proven in stored outputs)

- RTT `C_999` "Total" specialty row = sum of the real rows → excluded (kept in would double every figure).
- RTT `Part_2A` (with-DTA) ⊂ `Part_2` → excluded.
- RTT schema break at Apr 2021 (69 → 121 columns), the only break.
- KH03 Q4 2014-15 published twice (original + Revised-Nov15) → revised wins, same rule as RTT.
- KH03 Q2 2013-14 contains a `"2013-15"` year typo on one row (Camden & Islington) → tolerated explicitly, one off-year row max.
- KH03 prints `-` where available beds = 0 → coerced to NaN; zero-G&A providers (2,117 of 12,453 provider-quarters — mental-health/community trusts) get NaN occupancy, not 0.
- Column-position trust check: occupancy recomputed from raw Available/Occupied must equal the sheet's own `% Occupied` column (asserted, passed for all 12,453 rows).

## Final panel

`data/processed/rtt_kh03_canonical_panel.csv` — 343,441 rows × 24 columns, one row per (month, provider, specialty), Apr 2018 – Mar 2026:

- keys/time: `month`, `provider_code`, `tfunc_code`
- demand: `total_waiting`, `gt18`, `gt52`, `pct_gt18`, `pct_gt52` (denominator: that row's `total_waiting`)
- provider context: `trust_name`, `status`, `icb_code`, `postcode`, `is_public`, `n_months_active`, `first_month`, `last_month`, `fl_client`, `fl_allocatable`
- capacity (provider-level, quarterly upsampled to monthly): `avail_ga`, `occ_ga`, `occupancy_ga`, `avail_total`, `occ_total`, `occupancy_total`

Match rates (denominator: rows in each group): public trusts 99.0% of rows carry capacity, independents 0.1% (KH03 is an NHS-trust return — expected), overall 66.2%. Only 13 public providers have unmatched months (2,207 of 229,600 public rows).

## Standing rules

- Raw data immutable; everything derived writes to `data/processed/`.
- Sealed test year FY 2025-26 — untouched until the one-shot final evaluation.
- KH03 quarterly values are levels (average daily beds), so quarters upsample to months by repetition; RTT is never downsampled.
- Independents stay in the panel, flagged, with empty capacity columns.
