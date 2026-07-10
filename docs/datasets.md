# NHS RTT dataset — provenance & verified schema mapping

## Source

- **Collection:** Consultant-led Referral to Treatment (RTT) Waiting Times
- **Publisher:** NHS England
- **Landing page:** <https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/>
- **File used:** the monthly *"Full CSV data file"* (`.zip` containing one CSV)
- **Licence:** © Crown copyright, NHS England — Open Government Licence v3.0
- **Window fetched:** 2018-04 → 2026-03 (96 monthly files = 8 financial years)

The per-month download URLs contain unguessable hashes, so they are scraped from the
eight financial-year pages (2018-19 … 2025-26) by `fetch_scripts/build_rtt_manifest.py` and
recorded verbatim in `fetch_scripts/nhs_manifest.json`. **2018-04 is the floor:** it is the
earliest month in the modern RTT CSV layout — FY 2016-17 and 2017-18 use an older "SHA &
Self Trusts" structure (no `Period` / `RTT Part Type`) that this schema does not cover.

## Raw file shape

The file grows over the 8-year window — the wait-band columns and the provider roster both
expand — so the shape is **not** constant. Verified samples:

| month | rows | columns | providers | treatment functions |
|---|---|---|---|---|
| 2018-04 | ~196,340 | **69** | 417 | 20 |
| 2021-04 | ~160,251 | **121** | 431 | 24 |
| 2026-03 | ~183,400 | **121** | 533 | 24 |

The **9 canonical columns below are present and stable across all 96 months**; only the
weekly wait-band columns (which the loader ignores) and the provider set change. Each month
still includes a `C_999` `Total` aggregate treatment function that is dropped.
- Each row = one `Provider × Commissioner × RTT Part × Treatment Function` combination,
  with counts spread across weekly waiting-time bands.

### Key columns

| Column | Meaning |
|--------|---------|
| `Period` | Reporting month, e.g. `RTT-March-2026` |
| `Provider Org Code` / `Provider Org Name` | The hospital trust / site (the **federated client**) |
| `Commissioner Org Code` / `Name` | Purchasing organisation (not used for demand) |
| `Treatment Function Code` / `Name` | Clinical specialty (the **department**) |
| `RTT Part Type` / `RTT Part Description` | Which pathway measure the row reports (see below) |
| `Gt 00 To 01 Weeks SUM 1` … `Gt 104 Weeks SUM 1` | Patient counts per weekly wait band |
| `Total` | Sum of the wait-band columns (patients with a known clock start) |
| `Total All` | `Total` + patients with unknown clock start date |

### RTT Part types (verified distinct values)

| Part | Description | Total All, Mar 2026 |
|------|-------------|--------------------:|
| `Part_3` | **New RTT Periods – All Patients** (new referrals starting the clock) | 3,864,636 |
| `Part_2` | Incomplete Pathways (current waiting list) | 14,091,020 |
| `Part_2A` | Incomplete Pathways with DTA (decision to admit) | 2,356,984 |
| `Part_1B` | Completed Pathways for Non-Admitted Patients | 2,750,544 |
| `Part_1A` | Completed Pathways for Admitted Patients | 641,082 |

## Mapping to the canonical `[date, branch, dept, demand]` table

| Canonical field | RTT source | Notes |
|-----------------|-----------|-------|
| `date` | `Period` → month start (`2026-03-01`) | Parse `RTT-<Month>-<Year>` |
| `branch` | `Provider Org Code` | One federated client per provider |
| `dept` | `Treatment Function Code` | Exclude the `Total` (`C_999`) aggregate rows |
| `demand` | `Total All` where `RTT Part Type == 'Part_3'` | **New RTT periods** = incoming OPD demand |

**Why `Part_3` (New RTT Periods) is the demand signal:** it counts *new* referrals that
start an RTT clock each month — i.e. fresh demand entering the system — which is the
quantity a staffing/capacity forecast needs. `Part_2` (Incomplete) measures the standing
*waiting list* (a stock, not a flow) and is available as an alternative target for
waiting-list modelling.

### Extraction recipe

```python
import pandas as pd, glob, re

def load_canonical(demand_part="Part_3"):
    rows = []
    for f in sorted(glob.glob("data/nhs_rtt_referral_to_treatment/rtt_*.csv")):
        d = pd.read_csv(f, low_memory=False)
        d = d[d["RTT Part Type"] == demand_part]
        d = d[d["Treatment Function Code"] != "C_999"]   # drop the 'Total' specialty
        m = re.search(r"rtt_(\d{4})-(\d{2})", f)
        d = d.assign(date=f"{m.group(1)}-{m.group(2)}-01")
        rows.append(d.rename(columns={
            "Provider Org Code": "branch",
            "Treatment Function Code": "dept",
            "Total All": "demand",
        })[["date", "branch", "dept", "demand"]])
    return pd.concat(rows, ignore_index=True)
```

This yields the long-format `[date, branch, dept, demand]` table — up to **96** monthly
points per `(branch, dept)` series (fewer where a trust or department is not present for the
whole window; the balanced panel is computed, not assumed) — ready for per-provider
federated forecasting.
