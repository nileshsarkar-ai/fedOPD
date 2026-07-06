# fedOPD — Session Handoff / Context Transfer

Paste this into a new chat (or hand to a supervisor) to resume with full context.
Last updated: **2026-07-06**.

---

## 1. Project in one line
**Cross-silo federated forecasting of NHS outpatient demand** — each NHS trust is a
federated client that trains a shared per-department demand-forecast model **without
pooling raw patient data**. Repo: <https://github.com/nileshsarkar-ai/fedOPD> (branch `master`).

## 2. Scope decisions (locked)
- **RTT only** (dropped the earlier ae / dm01 idea).
- **NHS trusts only** — exclude independent (private) hospitals; a federation needs
  stable, resourced clients from day one.
- **Demand signal = `Part_3` (New RTT Periods)** — new referrals starting the clock.
- **Client = NHS trust**; **grain = trust × treatment function × month**.
- **Canonical table:** `[date, branch, dept, demand]`.
- **Hierarchy:** NHS England → ICB (`Provider Parent`) → NHS region → trust.

## 3. Environment (Windows 11, already set up)
- **Python 3.12** in project venv `.venv/` (activate: `.\.venv\Scripts\Activate.ps1`).
- **GPU:** NVIDIA RTX 4060 Laptop (8 GB). **PyTorch 2.11 + CUDA 12.8** — GPU verified working.
- Libs: transformers, datasets, accelerate, **flwr (Flower)**, langgraph/langchain, anthropic,
  jupyterlab, pandas, scikit-learn, matplotlib. (`pip check` clean.)
- **git** configured: `nileshsarkar-ai` / `nileshsarkar.cs@gmail.com`; **SSH auth to GitHub verified**.
- Sleep disabled while on AC power (long downloads/training won't be interrupted).

## 4. Data — DONE & VERIFIED
- **60 monthly RTT "Full CSV" files, 2021-04 → 2026-03** (exactly 5 years). 0 missing, 0 dupes.
- Fetched via `scripts/fetch_nhs.py` (manifest-driven, idempotent) from
  `scripts/nhs_manifest.json` (built by `scripts/build_rtt_manifest.py`, which scrapes NHS pages).
- Extracted CSVs (~5 GB) in `data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv`.
  Raw zips in `data/archives/rtt/`. **All of `data/` is git-ignored.**

### Verified data facts
- ~183k rows/month, **121 columns**.
- **533 providers** (mix of NHS trusts + independents), **24 treatment functions** (incl. a `Total`).
- Pathway types: `Part_1A/1B` (completed), `Part_2/2A` (incomplete = waiting list), **`Part_3` (new periods = demand)**.
- **NHS trust filter:** `Provider Org Code` = 3-char starting `R`. Independents = longer 5-char codes.
- **Drop aggregate rows:** `Treatment Function Code = C_999` (Total).
- **July 2022 break:** CCG→ICB commissioner switch + file-format step (size drops, rows stable).
  Anchor the federated hierarchy on the **provider** side (stable), not commissioner.
- `Period` month case differs pre/post 2023-04 (`APRIL` vs `April`) — parse case-insensitively.

## 5. EDA — STARTING NOW
8-step plan tracked in [EDA_LOG.md](EDA_LOG.md):
1 Understand ✅ · 2 Input & inspect 🟡 · 3 Missing · 4 Characteristics · 5 Transform ·
6 Visualise · 7 Outliers · 8 Communicate.
- **Convention:** one Jupyter notebook per stage in `notebooks/`; running register in `EDA_LOG.md`;
  figures/tables saved to `reports/figures/`.
- **Current task:** `notebooks/01_inspect.ipynb` — inspect one month to confirm `Part_3`, the
  `R##` trust filter, and the `C_999` drop. Next: build the canonical loader across all 60 months.

## 6. Target architecture
- **Swappable forecaster** behind `get_params` / `set_params` (NumPy → PyTorch without touching the FL loop).
- **Cross-silo, client-per-trust**; coordinator aggregates (FedAvg / FedProx) with optional personalisation.
- **Client selection** = trusts with full 60-month history × chosen region/ICB × overlapping departments.

## 7. Repo layout
```
README.md
CHAT_TRANSFER.md        this file
EDA_LOG.md              EDA register
docs/
  datasets.md           provenance + verified schema mapping
  nhs_structure.png/html  flowchart: NHS trust vs independent governance
scripts/
  fetch_nhs.py          downloader/unzipper (stdlib only)
  build_rtt_manifest.py scrapes NHS pages -> nhs_manifest.json
  nhs_manifest.json     60 verified RTT URLs
notebooks/              EDA, one per stage (to be created)
data/                   git-ignored (re-fetchable from manifest)
```

## 8. Immediate next steps
1. Run `notebooks/01_inspect.ipynb`; record findings in `EDA_LOG.md` Step 2.
2. Build canonical loader → trusts-only `[date, branch, dept, demand]` for all 60 months.
3. Step 4: balanced-panel (all-60-month trusts) + trusts-per-ICB-per-region counts → client shortlist.
