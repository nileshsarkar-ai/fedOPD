# Note to supervisor — open decisions before the federated experiments

The EDA is closed (tag `eda-v2`; 25-page report `reports/eda_report.pdf`, findings F-01..F-28,
decisions D-01..D-05). The build has started: the panel, department roster and windowed datasets are
frozen and leakage-checked (`results/panel.json`, `results/dataset_stats.json`). Six questions remain.
None of them block the build — each is parametrised, and Steps 1–2 are minutes of CPU — so rather than
ask you to choose blind, I will **run the roster/threshold variants as a sensitivity check by Step 5**
(local-only and centralised baselines are cheap) and bring you the comparison. This note is so the
questions are on the table now, with the numbers I already have.

## The six questions

1. **Panel strictness.** Default = **125 trusts** present in all 96 months. Relaxing to ≥90 months
   gives 139, ≥84 gives 146. Cost of relaxing: raggeder histories. *My lean: keep 125 for the headline,
   report 139/146 as robustness.*

2. **Regime spans.** COVID flagged as **2020-03 → 2021-03**; the 2023 NHS industrial action as
   **2022-12 → 2023-12**. Both are model features, not deletions. *Confirm or adjust the windows.*

3. **Small-trust inclusion.** The smallest early-exit trusts inflate the raw max/min spread but are
   already down-weighted by size-aware aggregation. *Keep as clients, or drop? My lean: keep.*

4. **Department coverage threshold — sharper than it first looked.** The default (≥50% of the 125 panel
   trusts) drops exactly **one** window-complete specialty: **C_150 Neurosurgery, at 36% coverage** —
   which is still **~45 silos**. That is nowhere near data-starved: F-17's whole point was that no
   department is starved at the *federation* level, and the shared model already handles non-overlap
   through the department one-hot features. So Neurosurgery is **not** a taxonomy artefact like the
   X-codes — it is a real tertiary specialty that only major centres perform. The honest question is
   therefore whether a coverage threshold solves **any** problem here at all; **excluding a real
   specialty is a much harder sell than excluding a catch-all bucket.** I will answer it empirically:
   the Step-5 sensitivity reports roster 17 (exclude) vs 18 (include Neurosurgery) so the cost is
   visible. *Current lean: likely include it (i.e. drop the threshold), pending that number.*

5. **The X-code "Other" family (D-07).** `X01` ("Other", 36 months) was recoded into five service-line
   buckets `X02`–`X06` at 2021-04 (F-28). Ranking them across the window double-represents one bucket,
   and a catch-all is not a department the agentic layer could allocate staff to. Three options:
   (a) map `X01` → its successors for a continuous series; (b) model the family as one merged series;
   (c) **exclude the X-codes from the roster** (current default). *My lean: (c); I will also report
   `all24` and `no_x` variants at Step 5 so the cost of the choice is visible.*

6. **Region lookup.** The region tier (NHS England → region → ICB → trust) is **not in the RTT files**.
   A provider → region mapping (ODS / Trust–ICB attribution) must be attached before the two-plane
   hierarchy can aggregate at region level. Not needed for the trust/ICB experiments; flagged so it is
   not forgotten.

## One decision I made rather than asked (please sanity-check)

**No-test-window series.** 155 series in the frozen panel×roster have no valid 12-month test window.
Of these, only 34 have ≥24 training windows; the rest are too short. Of the 34: **16 are still active**
(interior gap, last report in 2026-01..03) and **18 have gone stale** (no report after 2025-03). I kept
the 16 active ones as **train-only** — they contribute gradient signal to the shared model (and sit in
exactly the gappier trusts federation is meant to help) but cannot be evaluated — and dropped the 18
stale ones. Every method trains on the identical 1,544-series set; only the 1,528 evaluable series are
scored. *If you disagree (e.g. drop all 155 for a cleaner story), it is a one-line change.*

## Frozen numbers (for reference)

125 panel trusts → 117 client trusts with eligible series · 17-department roster (Neurosurgery excluded)
· 1,528 eval + 16 train-only = 1,544 training series · 108,065 train / 18,191 test windows · 33 features.
The bar every model must beat is the F-27 baseline, **naive-t-1 ≈ 12.6% sMAPE** (recomputed on this exact
panel at Step 3).
