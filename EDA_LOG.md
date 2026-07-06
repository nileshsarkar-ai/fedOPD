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
| 2 | Input & inspect | 🟡 in progress | `notebooks/01_inspect.ipynb` |
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

### Step 2 — Input & inspect — 🟡 in progress
- **What:** Load one month, verify schema assumptions before building the full loader.
- **Why:** Confirm `Part_3` exists, how to separate NHS trusts (`R##` codes), what to drop (`C_999` Total).
- **Finding:** _(fill in: provider-code length split, #trusts vs independents, Part types seen)_
- **Decision:** _(fill in: trust filter = 3-char code starting `R`; drop `Treatment Function = C_999`)_
- **Output:** `notebooks/01_inspect.ipynb`

### Step 3 — Handle missing data — ⬜
- **What:** _..._
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
