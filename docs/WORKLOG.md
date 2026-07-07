# Work Log — fedOPD (NHS RTT)

**Standing rule:** this is the project's running record. *Every* work session — EDA,
selection, modelling, FL, agentic — gets a dated entry here (**what · why · finding ·
decision · output**), so every decision is auditable and reportable. Started as the EDA
log; now covers the whole project.

Dataset: NHS England Consultant-led RTT waiting times, **NHS trusts only**, 60 months
(2021-04 → 2026-03).

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
| 3 | Handle missing data | ✅ done | `notebooks/eda/03_missing.ipynb` + coverage figure/CSVs |
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

### Design session — federation scope + compute + deliverable — 2026-07-07
- **What:** Locked the client-panel design, department-selection method, and compute target;
  produced a supervisor-facing HTML brief.
- **Decisions:**
  - **Hierarchy corrected:** NHS England → **Region (7 official)** → ICB (~42, `Provider Parent`)
    → Trust (`R##`) → Department. Region sits *above* ICB; use the 7 official NHS regions (don't
    invent N/S/E/W). Region tier not in files → needs a `trust → region` lookup (prerequisite for Step 4).
  - **Panel:** 7 regions × **10 trusts** × **10 departments** ≈ 700 series × 60 months (floor 5–6
    trusts where a small region can't field 10 balanced-panel trusts). Selection is stratified &
    purposive, **not random**.
  - **Department method:** ubiquity (`months_present ≥ 57`) + volume (median monthly demand) as
    **gates**; **regional variation** (spread of a dept's per-region demand *share* — max−min /
    CoV / JS-divergence contribution) as the **ranker** → top 10. Output = auditable ranked table
    + region×dept heatmap = the non-IID justification. Note: no "Oncology" treatment function exists
    in RTT — measure which specialties vary regionally, don't assume.
  - **Compute:** MacBook Air M4 (16 GB) runs the whole project. MLP ~11.5k params, ~33.6k samples,
    full FL run ~10–30 min, peak mem <4 GB. CPU beats GPU dispatch at this size; MPS/MLX only matter
    if the forecaster grows. Run FL in-notebook / Flower sim **without Ray**. Nvidia laptop = burst only.
- **Output:** HTML brief (Artifact) — hierarchy flowchart, EDA results, selection method, pipeline,
  compute. Renamed `docs/EDA_LOG.md` → `docs/WORKLOG.md`; added the always-log standing rule to CLAUDE.md.

### Step 3 — Handle missing data — ✅ 2026-07-07
- **What:** On the trust-only parquet, classified absence into partial-history trusts, true gaps,
  and structural zeros. Notebook `notebooks/eda/03_missing.ipynb` (run on Mac M4, kernel FedOPD).
- **Data note:** a 61st month appeared — data now spans **2021-04 → 2026-04 (61 months)**, one past
  the locked "60". Parquet rebuilt on Mac: 150,350 rows · 61 months · 172 trusts · 23 depts.
- **Findings:**
  - **Balanced panel = 138 of 172 trusts** present in all 61 months (34 partial, mostly 34–60 months).
  - Series (trust×dept) = 2,739: **2,056 full · 416 true-gap** (4,267 internal missing months) **· 267 short-history**.
  - **Structural zeros = 24.1%** of balanced trust×dept cells (trust doesn't offer that specialty) — not imputed.
  - Dept ubiquity: **13 depts offered with full history by ≥70% of balanced trusts** → selecting 10 is feasible.
    Rare/specialist (Neurosurgery, Cardiothoracic, Mental Health) naturally drop.
- **Bug caught by running it:** merging the time-varying `icb` column double-counted trusts (CCG→ICB
  July-2022 rename) → "331 balanced". Fixed by taking each trust's most-recent ICB (`'last'`). Confirms
  the value of executing, not eyeballing.
- **Decision:** balanced panel = the 138; hold out partial trusts unless a region is short; gap-filling
  policy deferred to Step 5; department set will be chosen (not all 23) in Step 4.
- **Output:** `notebooks/eda/03_missing.ipynb`, `results/{balanced_panel_trusts,series_coverage,dept_ubiquity}.csv`,
  `reports/figures/03_missing_coverage.png`.

### Region lookup — attach trust → region — ✅ 2026-07-07
- **What:** Resolved the missing region tier from the **NHS ODS ORD API** (`directory.spineservices.nhs.uk`),
  via each ICB's `RE2 / RO209` relationship → region. Notebook `notebooks/eda/00_region_lookup.ipynb` (cached).
- **Finding:** all **42 current ICBs → the 7 official NHS regions**, 0 unresolved; **172/172 trusts mapped**.
  Balanced trusts per region: Midlands 27 · London 21 · NE&Y 21 · NW 21 · SE 20 · EoE 15 · SW 13 —
  **all ≥10**, so the 7×10×10 panel is feasible in every region.
- **Note:** ODS direct download (`files.digital.nhs.uk/etr.zip`) returns 403 from here; the ORD REST API
  works. Region = the trust's parent-ICB region (standard NHS attribution). Cached to `icb_region_lookup.csv`.
- **Output:** `notebooks/eda/00_region_lookup.ipynb`, `results/{icb_region_lookup,trust_region_lookup}.csv`,
  `reports/figures/00_trusts_per_region.png`.

### Step 4 — Explore characteristics + selection — ⬜ (unblocked; region attached)
- Trusts-per-region ✅ (above). Next: dept **volume** + **regional variation** → lock the 7×10×10 panel.

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
