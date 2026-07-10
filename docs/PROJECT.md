# fedOPD — Project Overview

*Federated forecasting of NHS outpatient / departmental demand, with an agentic
capacity-planning layer on top.* This document explains what the project is, what we
intend to build, and exactly what data is on disk. It is the human-facing companion to
[`CLAUDE.md`](../CLAUDE.md) (the terse machine primer) and
[`datasets.md`](datasets.md) (the schema reference).

Last updated: **2026-07-11**.

---

## 1. In one line

Each NHS **trust** acts as a federated *client* that helps train a shared, per-department
**demand-forecasting** model **without its raw activity data ever leaving the site**. The
forecasts then feed an **agentic layer** that turns them into capacity / staffing /
allocation decisions.

## 2. The problem — why bother

Hospital networks want accurate, per-department demand forecasts to plan staffing and
capacity. But activity data is operationally sensitive and, in the general case, cannot be
freely pooled into one central table. **Federated learning** lets every trust contribute
to a shared forecasting model while keeping its own records local — only model *updates*
travel, never rows.

## 3. Framing (important)

This is **operations research + distributed ML — not clinical / biomedical work.**
- The learnable object is a **demand forecaster**, not a diagnostic model.
- The goal is **capacity planning under uncertainty**.
- The data is **operational** — referral counts by department — *never* patient records.

Two coupled planes run over one NHS hierarchy:
- **FL plane** — learns the forecast. The global model flows *down*; model updates flow *up*.
- **Agentic plane** — acts on it. Allocations flow *down*; resource requests flow *up*.

## 4. The NHS domain (this drives the design)

The NHS is a **purchaser–provider split**, not one owned hospital chain:

```
NHS England (HQ) → regions (7) → ICBs (~42, = "Provider Parent" in the data) → providers
```

- **NHS trust** (public): inside the NHS — receives *allocated* capital / workforce, is
  directable.
- **Independent** (private): outside the NHS — *paid per activity only*; can only be
  *bought from*.

Both report RTT data upward — that shared reporting thread is exactly **why federated
learning fits**. Consequence for the design: the **forecasting** plane treats every
provider uniformly (each is a client), but the **agentic** plane branches on provider type
— *allocate* to trusts, *commission (buy)* from independents.

## 5. End-to-end pipeline

1. **NHS England RTT data** — monthly CSVs, fetched + verified (see §7).
2. **Canonical table** — reduce each 69–121-column file to `[date, branch, dept, demand]`:
   keep `Part_3` · NHS trusts (`R##`) · drop `C_999` · sum across commissioners.
3. **EDA (8 steps)** — coverage · scale (~100× spread across trusts) · seasonality /
   COVID ramp · sparsity · hierarchy counts · stability.
4. **Client selection** — a balanced panel (trusts present across the window) within a
   region / ICB, over overlapping departments → the federation client set.
5. **Federated forecasting (cross-silo)** — each trust trains a local forecaster; a
   Flower coordinator aggregates (FedAvg / FedProx + optional personalisation). Raw data
   never leaves the trust.
6. **Agentic decisions** — forecasts → capacity / staffing / service-line allocation;
   allocate to trusts, buy from independents.

## 6. Locked scope

| decision | value |
|---|---|
| Dataset | **RTT only** (Referral to Treatment waiting times) |
| Providers | **NHS trusts only** (`R##` codes); independents excluded from training |
| Demand signal | **`Part_3`** (New RTT Periods = new referrals), column `Total All` |
| Client / node | one **NHS trust** = one federated client |
| Grain | trust × treatment function × month |
| Canonical table | **`[date, branch, dept, demand]`** |
| Hierarchy | NHS England → region → ICB (`Provider Parent`) → trust → department |
| Drop | `C_999` (the `Total` aggregate specialty) |

---

## 7. The dataset — what's on disk

**Source:** NHS England, Consultant-led *Referral to Treatment (RTT) Waiting Times*,
monthly "Full CSV data files". © Crown copyright, Open Government Licence v3.0.
<https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/>

### Window: 8 financial years — **96 months, 2018-04 → 2026-03**

Extended on 2026-07-11 from the original 5 years (which started 2021-04, *after* the COVID
dip). **2018-04 is the floor:** it is the earliest month in the *modern* RTT CSV layout.
Financial years 2016-17 and 2017-18 exist but use an older "SHA & Self Trusts" structure
with no `Period` / `RTT Part Type` columns — the canonical loader cannot read them without
a separate parser, so they are deliberately excluded.

### Footprint (verified 2026-07-11)

| | |
|---|---|
| Extracted CSVs | **96 / 96 months**, `data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv` |
| Extracted size | **~7.7 GB** |
| Raw archives | ~329 MB, `data/archives/rtt/rtt-YYYY-MM.zip` (transient, re-fetchable) |
| Total under `data/` | ~8.0 GB (**git-ignored**, re-fetchable from the manifest) |

The dataset is **not a static panel** — it grows over the window:

| month | rows | columns | providers | treatment functions |
|---|---|---|---|---|
| 2018-04 | 196,340 | 69 | 417 | 20 |
| 2021-04 | 160,251 | 121 | 431 | 24 |
| 2026-03 | 183,400 | 121 | 533 | 24 |

Only the **9 canonical columns** are stable across all 96 months; the wait-band columns
(69 → 121) and the provider roster change over time. Trusts enter and leave — the balanced
panel must be computed, not assumed.

### The COVID dip is now captured

National new-RTT demand (Part_3, NHS trusts, excluding `C_999`), verified from the fetched
files:

| month | national new-RTT periods | note |
|---|---|---|
| 2018-04 | 1,544,011 | pre-COVID baseline |
| 2019-04 | 1,544,406 | pre-COVID baseline |
| 2020-02 | 1,490,691 | last normal month |
| **2020-04** | **474,295** | **first lockdown — collapse to ~31% of baseline** |
| 2020-05 | 603,068 | still deeply depressed |
| 2021-04 | 1,394,578 | recovering |
| 2026-03 | 1,783,457 | above baseline (backlog era) |

The previous 5-year window began at 2021-04 (1.39M) and would have missed the entire
collapse. The new window gives ~2 years of pre-COVID baseline → the April-2020 crash →
the full recovery/backlog, which is what a seasonal + shock-aware forecaster needs to see.

### Canonical mapping (per the modern layout)

| canonical | source column | rule |
|---|---|---|
| `date` | `Period` | `RTT-APRIL-2020` → `2020-04-01`; parse **case-insensitively** (month case differs pre/post 2023-04) |
| `branch` | `Provider Org Code` | keep 3-char codes starting `R` (trusts); 5-char = independents (excluded) |
| `dept` | `Treatment Function Code` | drop `C_999` (the `Total` aggregate) |
| `demand` | `Total All` where `RTT Part Type == 'Part_3'` | sum across commissioners → provider × dept |

Enrichment columns carried for hierarchy/labels: `Provider Parent Org Code`/`Name` (= ICB
from 2022; a CCG/STP-era parent before that), `Provider Org Name`, `Treatment Function
Name`. Full schema write-up: [`datasets.md`](datasets.md).

### Known quirks

- **Format break at ~2018.** 2016-17/2017-18 use the old SHA-era layout (excluded, see
  above). The whole 96-month window is the uniform modern layout.
- **`Period` month case** differs pre/post 2023-04 (`APRIL` vs `April`) → always parse
  case-insensitively.
- **CCG→ICB switch, July 2022** changed the *commissioner* side and the file format; row
  counts stay stable → **anchor the hierarchy on the provider side, not the commissioner.**
- **Region tier is not in the files** → attach via a `provider → region` lookup, rebuilt
  from the NHS **ODS ORD REST API** (`directory.spineservices.nhs.uk`; the direct
  `etr.zip` download 403s from some networks). ICB = `Provider Parent`, already in the file.

## 8. Architecture (target)

- **Swappable forecaster** behind a small `get_params` / `set_params` interface, so the
  model can go NumPy → PyTorch **without touching the FL loop**. A small windowed neural
  forecaster: a window of past months + calendar features → next month.
- **Cross-silo, client-per-trust.** A coordinator aggregates updates (**FedAvg / FedProx**)
  with optional per-client **personalisation**. Optional hierarchical aggregation
  (trust → ICB / region → HQ).
- **Agentic plane** (later): forecasts → strategic decisions, with the trust-vs-independent
  branching from §4.

## 9. Reproduce it

```bash
# 1. environment  (Python 3.10+, ~3 GB of CUDA wheels)
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name fedopd --display-name "fedOPD"

# 2. data  (96 months, idempotent — re-running touches only what's missing)
.venv/bin/python fetch_scripts/fetch_nhs.py --dataset rtt --list    # show the plan
.venv/bin/python fetch_scripts/fetch_nhs.py --dataset rtt           # download + unzip
.venv/bin/python fetch_scripts/fetch_nhs.py --prune-archives        # reclaim ~329 MB (optional)

# 3. check GPU (see Environment note below)
.venv/bin/python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

To extend the window later (e.g. new months as NHS publishes them), edit `FY_PAGES` in
`fetch_scripts/build_rtt_manifest.py`, re-run it to regenerate the manifest, then re-run
`fetch_nhs.py`.

## 10. Repo layout

```
README.md · CLAUDE.md · requirements.txt
docs/
  PROJECT.md           this document
  datasets.md          NHS RTT provenance + verified schema mapping
  WORKLOG.md           dated register of every work session (standing rule)
  nhs_structure.png    provider-governance flowchart
fetch_scripts/
  fetch_nhs.py         idempotent, manifest-driven downloader + unzipper (stdlib only)
  build_rtt_manifest.py  scrapes NHS FY pages → nhs_manifest.json
  nhs_manifest.json    verified source URLs + byte sizes for all 96 monthly files
data/                  git-ignored, re-fetchable — 96 CSVs (~8 GB)
```

The canonical loader, EDA, forecaster and federated loop are **written by hand** — they are
not scaffolded (an academic requirement; see `CLAUDE.md` §12). `notebooks/` and
`reports/figures/` are created as that work proceeds.

## 11. Status & next steps

**Done:** data acquisition (96 months, verified) · dataset documentation · Python
environment.

**Next:**
1. `notebooks/01_inspect.ipynb` — load one month, inspect the columns, confirm the `Period`
   case quirk; log Step 2 in `docs/WORKLOG.md`.
2. Canonical loader across all 96 months → `[date, branch, dept, demand]` (§6 rules).
3. Balanced panel (trusts present across the window) + trusts-per-ICB-per-region → the
   day-1 client shortlist.
4. Rebuild the `provider → region` lookup from the ODS ORD API.
5. Forecaster interface (`get_params` / `set_params`) → Flower federated loop.

## 12. Environment

- **Linux · Python 3.10 · NVIDIA A100 80 GB.** `requirements.txt` pins
  `torch==2.11.0+cu128` against PyTorch's CUDA 12.8 index.
- **GPU: working, via a MIG instance.** The A100 has MIG mode enabled but shipped with **no
  MIG instances**, so CUDA saw no device (`torch.cuda.is_available()` was `False` even though
  `nvidia-smi` showed the card). Fixed on 2026-07-11 by creating one full-card instance —
  `nvidia-smi mig -cgi 7g.80gb -C` — run as root via a privileged docker container (this
  account has no `sudo`, but is in the `docker` group). `torch` now trains on the A100:
  `torch.cuda.get_device_name(0)` → `NVIDIA A100 80GB PCIe MIG 7g.80gb`.
- `.venv/bin/activate` auto-resolves the MIG UUID into `CUDA_VISIBLE_DEVICES` on activation,
  so torch finds the GPU with no manual steps (and falls back to CPU cleanly if the instance
  is gone).
- ⚠️ **The MIG instance is not persistent** — a server reboot or GPU reset removes it.
  Recreate it with:
  ```bash
  docker run --rm --privileged -v /:/host nvidia/cuda:12.2.2-base-ubuntu22.04 \
    chroot /host nvidia-smi mig -cgi 7g.80gb -C
  ```
  The venv's dynamic lookup picks up the new UUID automatically. It is **one shared 79 GB
  instance** — concurrent jobs (e.g. a second session on the same server) contend for its
  memory and SMs. Cleaner long term: ask the admin to persist the MIG config or disable MIG.
