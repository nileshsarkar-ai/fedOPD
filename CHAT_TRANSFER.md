# fedOPD — Full Session Handoff / Context Transfer

A complete record of everything discussed and done so far. Paste into a new chat (or hand
to a supervisor) to resume with full context. **Last updated: 2026-07-06.**

Repo: <https://github.com/nileshsarkar-ai/fedOPD> · default branch **`master`**.

---

## 0. Project in one line
**Cross-silo federated forecasting of NHS outpatient (OPD) demand** — each NHS trust is a
federated *client* that helps train a shared, per-department demand-forecast model **without
its raw patient data ever leaving the site**. Forecasts feed an agentic layer that turns them
into staffing / capacity / allocation decisions.

---

## 1. What has been done (chronological)

1. **Machine set up from scratch** (Windows 11, no Python/git initially):
   - Installed Python 3.12, git, created project venv, installed the full DL/FL/agentic stack.
   - Confirmed the **NVIDIA RTX 4060 GPU** works with PyTorch + CUDA.
2. **GitHub configured** — identity + SSH key, verified auth, force-pushed this codebase over the
   old `master`.
3. **Data acquired** — 60 months of NHS RTT "Full CSV" files, downloaded + extracted + verified.
4. **Project scoped** — narrowed from 3 datasets to **RTT only**, and to **NHS trusts only**.
5. **NHS structure understood & documented** — how NHS funding/governance differs from a
   single-owner hospital chain; produced a flowchart.
6. **EDA planned** — 8-step framework with a supervisor-facing log; started Step 2 (inspect).

---

## 2. Environment (already working)

- **OS:** Windows 11, PowerShell. Machine: laptop with **NVIDIA RTX 4060 (8 GB VRAM)**.
- **Python:** 3.12 in project venv `.venv/`.
  Activate: `.\.venv\Scripts\Activate.ps1` (if blocked once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).
- **PyTorch 2.11 + CUDA 12.8** — GPU verified (`torch.cuda.is_available() == True`). `.to("cuda")` works.
- **Libraries:** transformers, datasets, accelerate, torchmetrics, tensorboard, **flwr (Flower)** with
  simulation extras, langgraph / langchain (+ anthropic, openai), jupyterlab, pandas, scikit-learn,
  matplotlib, seaborn. `pip check` is clean.
- **git:** identity `nileshsarkar-ai` / `nileshsarkar.cs@gmail.com`; **SSH to GitHub verified**
  (`Hi nileshsarkar-ai! You've successfully authenticated`).
- **Power:** sleep disabled on AC power so long downloads/training runs aren't interrupted
  (battery sleep left at 3 min). Revert with `powercfg /change standby-timeout-ac 5`.
- **Windows gotcha:** console is cp1252; when running scripts that print unicode, set
  `$env:PYTHONUTF8="1"` first.

---

## 3. Data — DONE & VERIFIED

- **60 monthly RTT "Full CSV" files, 2021-04 → 2026-03** — exactly 5 years / 5 financial years.
  Cross-checked: **0 missing, 0 duplicates, every month valid** (160k–190k rows each).
- **Pipeline (reproducible, idempotent, stdlib-only downloader):**
  - `scripts/build_rtt_manifest.py` — scrapes NHS England's 5 financial-year pages (the download
    URLs carry unguessable hashes) → writes `scripts/nhs_manifest.json`.
  - `scripts/fetch_nhs.py` — reads the manifest, downloads each zip → unzips the CSV. Resumable;
    `--prune-archives` reclaims the raw-zip space; `--list` shows the plan.
- **Locations (all of `data/` is git-ignored, re-fetchable from the manifest):**
  - Working CSVs: `data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv` (~5 GB total).
  - Raw zips: `data/archives/rtt/` (~217 MB, optional).

### Verified data facts (checked against real files)
- ~183k rows/month, **121 columns**.
- **533 providers** (NHS trusts **+** independents mixed), **24 treatment functions** (incl. a `Total`).
- **RTT pathway types** (`RTT Part Type` / `Description`):
  - `Part_1A` Completed – Admitted, `Part_1B` Completed – Non-Admitted
  - `Part_2` Incomplete Pathways (= current **waiting list**, a stock), `Part_2A` Incomplete with DTA
  - **`Part_3` New RTT Periods — All Patients (= new referrals / demand flow) ← our target**
- **Demand column:** `Total All` where `RTT Part Type == 'Part_3'`.
- **Canonical mapping** `[date, branch, dept, demand]`:
  - `date` = `Period` (e.g. `RTT-March-2026` → `2026-03-01`)
  - `branch` = `Provider Org Code` (the trust / site)
  - `dept` = `Treatment Function Code` (specialty)
  - `demand` = `Total All` on `Part_3`
- **NHS trust filter:** `Provider Org Code` = **3-char code starting `R`** (NHS trust / foundation trust).
  Independents = longer **5-char** codes.
- **Drop aggregate rows:** `Treatment Function Code = C_999` (the `Total` specialty).
- **July 2022 structural break:** commissioners switched **CCG → ICB**, and the file format stepped
  (size drops from ~100 MB to ~80 MB, row counts stable). Provider side is stable → **anchor the
  federated hierarchy on the provider columns, not the commissioner ones.**
- **`Period` month case** differs pre/post 2023-04 (`APRIL` vs `April`) → parse case-insensitively.
- Full schema write-up: `docs/datasets.md`.

---

## 4. NHS structure — the key domain insight

The NHS is **not** one owned hospital chain. It runs a **purchaser–provider split**, and this
reshapes the agentic layer. (Diagram: `docs/nhs_structure.png`.)

- **NHS England** (national HQ) → **ICBs** (~42 Integrated Care Boards = the "regions",
  = `Provider Parent`) → **providers**.
- Two provider types, governed by **different levers**:
  - **NHS Trust (public):** *inside* the NHS. Receives **allocated** capital, national procurement
    (NHS Supply Chain), workforce; performance-managed. HQ can **direct** it. (solid edge)
  - **Independent hospital (private):** *outside* the NHS. Gets **paid per activity only** — owns its
    own estate/staff/supplies and runs itself. HQ can only **buy** capacity from it. (dashed edge;
    resource link absent)
  - **Both** report RTT data upward — the one shared thread (→ why federated learning fits).
- **Consequence for design:** the forecasting plane treats all providers uniformly (each is a
  client), but the **agentic/resource plane must branch on provider type** — *allocate* to trusts,
  *commission (buy)* from independents.

### Why NHS-trusts-only for the federation
A federation needs **stable, resourced, directly-governed** clients from day one. Independents come
and go by contract and can't be allocated resources, so they're excluded from the client set.
(They remain relevant later as a "buy capacity" option in the agentic layer.)

---

## 5. Scope decisions (LOCKED)

| Decision | Value |
|----------|-------|
| Datasets | **RTT only** (dropped earlier ae / dm01 plan) |
| Providers | **NHS trusts only** (`R##` codes); exclude independents |
| Demand signal | **`Part_3`** New RTT Periods (`Total All`) |
| Client / node | one **NHS trust** = one federated client |
| Grain | trust × treatment function × month |
| Canonical table | `[date, branch, dept, demand]` |
| Hierarchy | NHS England → ICB (`Provider Parent`) → NHS region → trust |
| Aggregates | drop `C_999` (Total specialty) + provider-parent totals |

---

## 6. Target architecture

- **Swappable forecaster** behind a small `get_params` / `set_params` interface, so the model can be
  replaced (NumPy → PyTorch) without touching the federated loop.
- **Cross-silo, client-per-trust.** A coordinator aggregates updates (**FedAvg / FedProx**) with
  optional per-client personalisation.
- **Client selection method** (falls out of EDA):
  1. trusts with **complete 60-month history** (balanced panel),
  2. within a chosen **region / ICB** (geographic coherence),
  3. covering **overlapping departments** (so one shared model makes sense);
  optionally top-N by volume or stratified by size.
- **Agentic plane** (later): forecasts → strategic decisions (capacity expansion, staff allocation,
  service-line changes), with the trust-vs-independent branching noted above.

---

## 7. EDA — plan + status

Tracked in **`docs/EDA_LOG.md`** (supervisor-facing register: one row per step —
*what · why · finding · decision · output*). Convention: **one Jupyter notebook per stage** in
`notebooks/`; figures/tables saved to `reports/figures/`.

### 8-step plan → RTT actions
| # | Stage | What we do on RTT | Log output |
|---|-------|-------------------|-----------|
| 1 | Understand problem & data | objective, grain, demand=`Part_3`, provider=client | problem statement + data dictionary — **✅ done** |
| 2 | Input & inspect | load 60 CSVs → canonical table; filter `R##`; check shapes/dtypes/`Period` | counts of rows/trusts/depts — **🟡 in progress** |
| 3 | Handle missing data | true-missing vs structural zeros (dept not offered) vs partial-history trusts | missingness table + rules |
| 4 | Explore characteristics | volume per trust/dept, **balanced panel (all 60 mo)**, trusts-per-ICB-per-region | summary tables |
| 5 | Transform | monthly series, log/scale for skew, per-client normalisation, train/back-test split | transform list + rationale |
| 6 | Visualise relationships | time series per trust×dept, seasonality, COVID-recovery ramp, cross-trust/dept correlation | figures |
| 7 | Handle outliers | COVID shock months, reporting spikes, zero-blips → cap / flag / keep | outlier register |
| 8 | Communicate | summary + flowchart + recommended client panel | findings report |

### Six analytical questions to answer (from earlier discussion)
- **Coverage:** which trusts appear in all 60 months → the balanced panel; flag intermittent ones.
- **Scale:** demand per trust & specialty — big vs small trusts differ ~100× → matters for FL weighting.
- **Seasonality/trend:** monthly curves per trust×dept; spot the COVID-recovery ramp.
- **Sparsity:** which specialties a trust doesn't offer (structural zeros).
- **Hierarchy counts:** trusts per ICB, ICBs per region.
- **Stability:** confirm the July-2022 format break doesn't disturb the provider side.

---

## 8. Code delivered so far — Step 2 inspection

To go in `notebooks/01_inspect.ipynb` (run `jupyter lab` from the activated `.venv`). Inspect **one**
month first, before building the full loader.

```python
# Cell 1: setup
from pathlib import Path
import pandas as pd
DATA_DIR = Path(r"C:\Users\heave\Documents\FedOPD\data\nhs_rtt_referral_to_treatment")
files = sorted(DATA_DIR.glob("rtt_*.csv"))
print(len(files), "files:", files[0].name, "->", files[-1].name)

# Cell 2: load ONE month and look
df = pd.read_csv(files[-1], low_memory=False)   # 2026-03
print("rows, cols:", df.shape); df.head()

# Cell 3: pathway types (confirm Part_3 = demand)
df[["RTT Part Type", "RTT Part Description"]].drop_duplicates()

# Cell 4: NHS trusts vs independents by code shape
codes = df["Provider Org Code"].dropna().unique()
print(pd.Series([len(c) for c in codes]).value_counts())
is_trust = lambda c: len(c) == 3 and c[0] == "R"
print(sum(is_trust(c) for c in codes), "of", len(codes), "look like NHS trusts")

# Cell 5: treatment functions incl. the 'Total' (C_999) to drop
df[["Treatment Function Code", "Treatment Function Name"]].drop_duplicates()
```

**Expected:** Cell 3 shows `Part_3 = New RTT Periods`; Cell 4's `R##` count = rough trust set;
Cell 5 shows `C_999 = Total` (drop it). Record findings in `docs/EDA_LOG.md` Step 2.

---

## 9. Immediate next steps
1. Run `notebooks/01_inspect.ipynb`; fill in `docs/EDA_LOG.md` Step 2 (code-length split, #trusts, Part types).
2. Build the **canonical loader** → trusts-only `[date, branch, dept, demand]` across all 60 months
   (parse `Period` case-insensitively; drop `C_999`; keep `R##`; demand = `Part_3` `Total All`).
3. Step 4: compute the **balanced panel** (trusts present all 60 months) + trusts-per-ICB-per-region
   → shortlist the day-1 federation client set.
4. Then: forecaster interface (`get_params`/`set_params`) → Flower federated loop.

---

## 10. Repo layout
```
README.md               RTT-only project overview
CHAT_TRANSFER.md        this handoff
docs/
  EDA_LOG.md            8-step EDA register
  datasets.md           provenance + verified schema mapping
  nhs_structure.png     flowchart: NHS trust vs independent governance
scripts/
  fetch_nhs.py          downloader/unzipper (stdlib only)
  build_rtt_manifest.py scrapes NHS pages -> nhs_manifest.json
  nhs_manifest.json     60 verified RTT source URLs
notebooks/              EDA, one notebook per stage (to be created)
reports/figures/        saved figures/tables (to be created)
data/                   git-ignored (re-fetchable from manifest)
```
