# EDA Log — fedOPD (NHS RTT)

Running register of the exploratory data analysis. **One entry per step**, so every
decision is auditable and reportable. Dataset: NHS England Consultant-led RTT waiting
times, **NHS trusts only**, 60 months (2021-04 → 2026-03).

- **Objective:** per-department **federated demand forecast**.
- **Demand signal:** `Part_3` — New RTT Periods (new referrals starting the clock).
- **Client / node:** one NHS trust = one federated client.
- **Grain:** trust × treatment function × month → canonical `[date, branch, dept, demand]`.
- **Data dictionary:** see [docs/datasets.md](docs/datasets.md).

Figures/tables are saved under `reports/figures/`. Notebooks under `notebooks/`.

---

## Progress checklist (8 steps)

| # | Stage | Status | Output |
|---|-------|--------|--------|
| 1 | Understand problem & data | ✅ done | this header + data dictionary |
| 2 | Input & inspect (+ provider split) | ✅ done | `notebooks/eda/01_inspect.ipynb`, `notebooks/provider_split/` |
| 3 | Handle missing data | ⬜ todo | missingness table + rules |
| 4 | Explore characteristics | ⬜ todo | summary tables |
| 5 | Transform | ⬜ todo | transform list + rationale |
| 6 | Visualise relationships | ⬜ todo | figures |
| 7 | Handle outliers | ⬜ todo | outlier register |
| 8 | Communicate | ⬜ todo | findings report |

---

## Step log

Record each working session as a row. Keep it short: **what · why · finding · decision · output**.

### Step 1 — Understand problem & data — ✅ 2026-07-06
- **What:** Fixed the objective, grain, demand signal, and client definition (above).
- **Why:** Everything downstream (filtering, panel selection, model) depends on these.
- **Finding:** RTT carries 5 pathway types; `Part_3` (New RTT Periods) is the demand flow.
  Provider hierarchy: trust → ICB (`Provider Parent`) → NHS region.
- **Decision:** RTT only; NHS trusts only; demand = `Part_3`; drop aggregate rows.
- **Output:** this log + `docs/datasets.md` + `docs/nhs_structure.png`.

### Step 2 — Input & inspect — ✅ 2026-07-06
- **What:** Loaded the data, verified schema, built the canonical loader (`src/rtt.py`), and
  split providers into NHS trusts vs independents.
- **Finding:**
  - `Part_3` (New RTT Periods) confirmed present = demand signal.
  - Provider codes: 3-char `R##` = NHS trusts; 5-char = independents.
  - `C_999 = Total` aggregate specialty confirmed → dropped.
  - **598 providers** across 60 months → **172 NHS trusts (92.2% of demand)** vs
    **426 independents (7.8%)**.
  - Canonical (all providers): 211,428 rows. **Trust-only: 147,986 rows · 60 months · 172 trusts · 23 depts.**
- **Decision:** Filter to NHS trusts (`R##`); drop `C_999`; demand = `Part_3` `Total All`
  summed across commissioners. Downstream EDA uses `data/processed/rtt_trusts_canonical.parquet`.
- **Output:** `notebooks/eda/01_inspect.ipynb`, `notebooks/provider_split/01_split_providers.ipynb`
  (+ `results/trusts.csv`, `results/independents.csv`), `src/rtt.py`.

### Step 3 — Handle missing data — ⬜
- **What:** On trust-only data, separate true-missing vs structural zeros (dept a trust doesn't
  offer) vs partial-history trusts (months_present < 60).
- **Finding:** _..._
- **Decision:** _..._

### Step 4 — Explore characteristics — ⬜
- Coverage (balanced 60-month panel), scale per trust/dept, trusts-per-ICB-per-region.

### Step 5 — Transform — ⬜
- Monthly series build, skew handling, per-client normalisation, train/back-test split.

### Step 6 — Visualise relationships — ⬜
- Time series per trust×dept, seasonality, COVID-recovery ramp, cross-trust/dept correlation.

### Step 7 — Handle outliers — ⬜
- COVID shock months, reporting spikes, zero-blips → cap / flag / keep.

### Step 8 — Communicate — ⬜
- Summary report + flowchart + recommended client panel for supervisor.

---

## Open questions / notes
- July 2022: CCG → ICB switch (commissioner side) and a file-format step (size drop, row counts stable). Confirm provider side is unaffected.
- Month case differs pre/post 2023-04 in the `Period` string (`APRIL` vs `April`) — parse case-insensitively.
