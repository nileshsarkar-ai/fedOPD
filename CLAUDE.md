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

## 8. EDA — plan + status  (register: `docs/WORKLOG.md`; one notebook per stage in `notebooks/`; figures → `reports/figures/`)

> **Clean slate (2026-07-10).** All previously generated notebooks, `src/rtt.py`, `config/`,
> `previews/` and `reports/` were **deleted on purpose**: the owner writes the analysis code
> himself (advisor's requirement). Only data acquisition + docs remain. Statuses below are the
> *plan*, not work in hand. Recoverable from git history at `a77abda` if ever needed.

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
  `torch==2.11.0+cu128`. ⚠️ GPU currently unusable — **MIG mode enabled with no instances**, so
  `torch.cuda.is_available()==False`; needs a sysadmin to run `sudo nvidia-smi -mig 0`. CPU-only
  meanwhile (fine for pandas EDA). Full detail in `docs/PROJECT.md` §12.
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

## 11. Immediate next steps
1. Write `notebooks/01_inspect.ipynb` by hand: load one month, inspect the 121 columns,
   confirm the `Period` case quirk (`APRIL` vs `April`); log Step 2 in `docs/WORKLOG.md`.
2. Write the canonical loader across all 96 months → `[date, branch, dept, demand]` (§4 rules).
3. Step 4: balanced panel (trusts present across the 96-month window) + trusts-per-ICB-per-region → day-1 client shortlist.
4. Rebuild the `provider → region` lookup (**not** in the RTT files — see §7; ODS / Trust-ICB attribution).
5. Forecaster interface (`get_params`/`set_params`) → Flower federated loop.

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