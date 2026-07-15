# CLAUDE.md — project context: **fedOPD**

Context primer for Claude / Claude Code. Read this first; it captures the project end-to-end
and the decisions that are locked. Repo: <https://github.com/nileshsarkar-ai/fedOPD> (branch `master`).

---

## 1. One line
**Cross-silo federated forecasting of NHS outpatient demand** — each NHS trust is a federated
*client* that helps train a shared, per-department demand-forecast model **without its raw data
leaving the site**. Forecasts feed an **agentic layer** that turns them into capacity / staffing /
allocation decisions.

## 2. Framing (important)
- This is **operations research + distributed ML, not clinical/biomed**. The learnable object is a
  *demand forecaster*; the goal is capacity planning under uncertainty; the data is *operational*
  (referral counts by department), never patient records.
- **Two coupled planes over one hierarchy:** the **FL plane** learns the forecast (global model
  flows down, model updates flow up); the **agentic plane** acts (allocations flow down, resource
  requests flow up).

## 3. Domain — how the NHS is structured (this drives the design)
Purchaser–provider split, **not** one owned hospital chain:
`NHS England (HQ) → regions (7) → ICBs (~42; = "Provider Parent" in the data) → providers`.
- **NHS trust** (public): inside the NHS — receives *allocated* capital/workforce, is directable.
- **Independent** (private): outside the NHS — *paid per activity only*; can only be *bought from*.
- Both report RTT data upward — the shared thread → **why federated learning fits**.
- **Consequence:** the forecasting plane treats every provider uniformly (each is a client), but the
  **agentic plane branches on provider type** — *allocate* to trusts, *commission (buy)* from independents.

## 4. Locked scope
| decision | value |
|---|---|
| Datasets | **RTT only** (dropped the earlier A&E / DM01 idea) |
| Providers | **NHS trusts only** (`R##` codes); exclude independents |
| Demand signal | **`Part_3`** (New RTT Periods), column `Total All` |
| Client / node | one **NHS trust** = one federated client |
| Grain | trust × treatment function × month |
| Canonical table | **`[date, branch, dept, demand]`** |
| Hierarchy | NHS England → region → ICB (`Provider Parent`) → trust → department |
| Drop | `C_999` (the `Total` specialty) |

## 5. Data — DONE & VERIFIED
- **96 monthly RTT "Full CSV" files, Apr 2018 → Mar 2026** (8 financial years). 0 missing, 0 dupes.
  Extended from 5→8 years on 2026-07-11 to capture the **COVID dip** (2020-04 national new-RTT
  fell to ~31% of baseline). **2018-04 is the floor** — earlier FYs use an incompatible older
  "SHA & Self Trusts" layout. The file is **not static**: ~160–196k rows, **69→121 columns**,
  **417→533 providers**, **20→24 treatment functions** across the window. The 9 canonical
  columns are stable throughout.
- Pipeline: `fetch_scripts/build_rtt_manifest.py` scrapes NHS pages → `fetch_scripts/nhs_manifest.json`;
  `fetch_scripts/fetch_nhs.py` downloads + unzips (idempotent, stdlib-only). CSVs at
  `data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv` (~7.7 GB, **git-ignored**, re-fetchable).
- **Canonical mapping:** `date` = `Period` (`RTT-March-2026` → `2026-03-01`, parse **case-insensitively**),
  `branch` = `Provider Org Code`, `dept` = `Treatment Function Code`, `demand` = `Total All` where
  `RTT Part Type == 'Part_3'`.
- **Filter rules:** keep `Part_3`; keep trusts (`Provider Org Code` = 3-char starting `R`; independents
  are 5-char); drop `C_999`; group by `[date, branch, dept]` summing over commissioner.
- **Quirks:** July-2022 CCG→ICB + file-format step (row counts stable → **anchor the hierarchy on the
  provider side, not commissioner**). `Period` month case differs pre/post 2023-04 (`APRIL` vs `April`).
- Full schema write-up: `docs/datasets.md`.

## 6. End-to-end pipeline
1. **NHS England RTT data** — 96 CSVs (2018-04 → 2026-03), fetched + verified.
2. **Canonical table** — keep `Part_3` · NHS trusts (`R##`) · drop `C_999` · sum commissioner → `[date, branch, dept, demand]`.
3. **EDA (8 steps)** — coverage · scale (~100× trust spread) · seasonality / COVID ramp · sparsity · hierarchy counts · stability.
4. **Client selection** — balanced panel (present across the 96-month window) × within a region / ICB × overlapping departments → federation client set.
5. **Federated forecasting (cross-silo)** — each trust trains a local model; Flower coordinator aggregates (FedAvg / FedProx + personalisation); **raw data never leaves the trust**.
6. **Agentic decisions** — forecasts → capacity / staffing / service-line allocation; allocate to trusts, buy from independents.

## 7. Architecture
- **Swappable forecaster** behind `get_params` / `set_params` (NumPy → PyTorch **without touching the
  FL loop**). Small windowed neural forecaster: window of past months + calendar features → next month.
- **Cross-silo, client-per-trust.** Coordinator aggregates (**FedAvg / FedProx**) with optional
  per-client **personalisation**. Optional hierarchical aggregation (trust → ICB / region → HQ).
- **Region tier is not in the files** → attach via a `provider → region` lookup (ODS NHS-Trusts list /
  NHS England Trust-ICB attribution; postcode fallback). ICB = `Provider Parent` (already in the file).
- **Agentic plane** (later): forecasts → strategic decisions, with the trust-vs-independent branching above.

> **STANDING RULE — always log.** Every work session (EDA, selection, modelling, FL,
> agentic) gets a dated entry in **`docs/WORKLOG.md`** (*what · why · finding · decision ·
> output*). No work is "done" until it's recorded there. Code lives in **`.ipynb` notebooks only**.

## 8. EDA — plan + status  (register: `docs/WORKLOG.md`; **single consolidated notebook `src/eda/EDA.ipynb`**; figures → `reports/figures/`)

> **Clean slate (2026-07-10).** All previously generated notebooks, `src/rtt.py`, `config/`,
> `previews/` and `reports/` were **deleted on purpose**: the owner writes the analysis code
> himself (advisor's requirement). Only data acquisition + docs remain. Statuses below are the
> *plan*, not work in hand. Recoverable from git history at `a77abda` if ever needed.

> **Convention update (2026-07-11).** The original "one notebook per stage in `notebooks/`" plan was
> **superseded by the owner's instruction** to keep all of stages 2–8 in a single notebook,
> **`src/eda/EDA.ipynb`** (sectioned by stage, commented). Stages 2–8 are **complete** and pass
> restart-and-run-all; the write-up lives in `reports/eda_report.{pdf,epub}` (rebuild: `make -C reports all`).
> On **2026-07-14** the notebook and report were revised to close an advisor review (see `docs/WORKLOG.md`):
> seasonality de-artefacted (mean over complete years), honest trust-scale spread (~9× on the balanced
> panel, not 66×), leakage-safe (trailing) outlier flags, forecastability baselines (F-27), a department
> taxonomy audit (F-28), and a 2023-strike regime. Note: `src/eda/EDA.ipynb` is AI-authored under an
> **explicit owner override** of §12 for this file only — the write-code rule still holds everywhere else.

| # | stage | status |
|---|---|---|
| 1 | Understand problem & data | ✅ |
| 2 | Input & inspect (load 60 → canonical; `R##` filter; dtypes/`Period`) | — |
| 3 | Handle missing (true-missing vs structural zeros vs partial history) | — |
| 4 | Characteristics (volume, **balanced panel**, trusts-per-ICB-per-region) | — |
| 5 | Transform (monthly series, log/scale, per-client normalise, train/back-test split) | — |
| 6 | Visualise (series per trust×dept, seasonality, COVID ramp, correlation) | — |
| 7 | Outliers (COVID shocks, reporting spikes, zero-blips → cap/flag/keep) | — |
| 8 | Communicate (report + recommended client panel) | — |

Six analytical questions: coverage (balanced panel) · scale · seasonality/trend · sparsity ·
hierarchy counts (trusts/ICB, ICBs/region) · stability (confirm July-2022 break is provider-safe).

## 9. Environment
- **Dev box (Windows 11):** RTX 4060 (8 GB) · Python 3.12 venv (`.venv`) · PyTorch 2.11 + CUDA 12.8.
  PowerShell gotcha: `$env:PYTHONUTF8="1"` before scripts that print unicode.
- **Server (Linux, A100 80 GB):** Python 3.10 venv (`.venv`) · `requirements.txt` pins
  `torch==2.11.0+cu128`. **GPU working** via a MIG `7g.80gb` instance (the card ships with MIG
  on but no instances → CUDA saw nothing; one was created 2026-07-11 via privileged docker,
  since this account has no `sudo`). `.venv/bin/activate` auto-sets `CUDA_VISIBLE_DEVICES` to
  the MIG UUID. **Not persistent across reboot** — recreate per `docs/PROJECT.md` §12 (full
  detail there).
- Libs (both): transformers, datasets, accelerate, **flwr (Flower)**, langgraph/langchain
  (+anthropic/openai), jupyterlab, pandas, scikit-learn, matplotlib, seaborn.
- git SSH to GitHub verified.

## 10. Repo layout
```
README.md · CLAUDE.md (this) · requirements.txt
docs/{PROJECT.md, WORKLOG.md, datasets.md, nhs_structure.png}
fetch_scripts/{fetch_nhs.py, build_rtt_manifest.py, nhs_manifest.json}
data/ (git-ignored, re-fetchable — 96 CSVs, ~7.7 GB, present)
```
`notebooks/` and `reports/figures/` are to be **created by hand** as the work proceeds.

## 11. Status + next steps (updated 2026-07-16)

**Done end-to-end (tags `eda-v2` → `build-v1` → `system-v1`):** EDA (F-01..28, D-01..08) · federated
forecaster (117 clients × 17 depts; fed+ft **16.24±0.07** vs naive bar **16.34** vs local 16.90 vs
central 15.81; Flower parity 0.004) · agentic plane (flow table + Little's-law capacity policy;
2026-03: 969 RED / 322 AMBER / 218 GREEN, 216k extra pathways/mo, ICB ranking; validated) · reports
(`reports/{eda_report,system_report,project_report}.pdf`) · live dashboard (`dashboard/`, serve +
ngrok — see `docs/OPS.md`). Notebooks: `src/eda/EDA.ipynb`, `src/fedopd/build.ipynb`,
`src/fedopd/agentic.ipynb`; reusable logic in `src/fedopd/*.py`; gates in `docs/BUILD_LOG.md`.

**NEXT SESSION — pre-registered improvement roadmap (implement Tier 1→4 in order, measure every
change against the same 16.34 bar, 5 seeds, same 18,191 points):**
- **Tier 1 (optimization, closes the fed→central ~0.4 gap):** (1) more FL rounds (100–200) + server
  optimizer (FedAdam/momentum) — loss was still descending at 40; (2) **blend** with naive
  ŷ=α·model+(1−α)·naive, α fitted on train-tail (selection failed at 16.83, blending is the robust
  form); (3) align loss with metric (train log1p/MAE, not MSE-on-z vs sMAPE-on-raw).
- **Tier 2 (new features from the SAME dataset — forecaster currently sees only Part_3 lags):**
  (4) flow-state features per series: lagged backlog / completions / >18wk share (already in
  `reports/tables/rtt_flow.parquet`); (5) last month's **national/ICB per-dept demand** as input
  (co-movement 0.63 is the strongest measured structure; public data → FL-safe); (6) working-days /
  bank-holidays-in-month feature (explains Dec/Apr/Aug troughs).
- **Tier 3 (model & evaluation):** (7) comparator families: ridge-AR + gradient-boosted trees
  (linear often matches MLP on 84-point series); (8) direct multi-horizon (1–12 mo — the agentic
  burn-down needs it); (9) **quantile forecasts** → agent plans against P90, not the mean (biggest
  decision-quality win).
- **Tier 4 (beyond the dataset):** GP-referrals upstream data · population/IMD per ICB ·
  provider→region lookup (ODS) · flu/weather seasonality.
- Honest ceiling: with demand-history-only, naive is near-optimal for many monthly series — gains
  come from added information (Tier 2) and changing what is predicted (Tier 3), not bigger nets.

## 12. How to help (for Claude)
- **The owner writes the analysis code himself** — advisor's requirement, and it is not negotiable.
  Do **not** author notebooks, the canonical loader, EDA, the forecaster or the FL loop for him.
  Explain, review, check logic, and answer questions instead. *Data-acquisition tooling
  (`fetch_scripts/`) and docs are the exception — those may be written/fixed directly.*
- Respect the **locked scope** (§4). Keep the canonical table exactly `[date, branch, dept, demand]`.
- It is **operations research, not clinical** — treat provider/department demand, never patient data.
- **Verify code** (mock-run the logic) before proposing it. Prefer **minimal, transparent code the
  owner types himself**, one stage at a time, with "what to expect" notes.
- The owner values directness and dislikes cognitive overload — keep chat tight; put detail in files.