# OPS — how fedOPD runs (operator cheat-sheet)

Practical notes so anyone (you, or Claude) can **pick the work up manually** without
re-discovering the environment. Research decisions live in `docs/WORKLOG.md`; per-step build
gates live in `docs/BUILD_LOG.md`; **this file is the "how do I run it / where is everything"
map.** Kept current as work proceeds.

Last updated: 2026-07-15.

---

## 0. TL;DR to resume manually

```bash
cd /home/garima/fedOPD
source .venv/bin/activate                 # Python 3.10, torch 2.11.0+cu128, pandas, numpy, flwr
jupyter lab                               # or: code . / open src/eda/EDA.ipynb
```
- **EDA** is one notebook: [`src/eda/EDA.ipynb`](../src/eda/EDA.ipynb) (stages 2–8, restart-and-run-all clean).
- **Report** (PDF+EPUB) rebuilds with `make -C reports all` (needs `tectonic` on PATH — see §3).
- **Canonical data** is `reports/tables/rtt_canonical.parquet` (548 KB) — the single input; never re-read the 7.7 GB of raw CSVs.

---

## 1. Machine

| | |
|---|---|
| host | `ubuntu-Standard-PC-Q35-ICH9-2009` (Linux A100 server) |
| CPU | 42 cores |
| RAM | 62 GB total (~37 GB free typical) |
| GPU | 1× NVIDIA A100 80 GB PCIe |
| project root | `/home/garima/fedOPD` |
| shell | bash |

---

## 2. GPU policy — **do not disrupt running GPU work**

**Check GPU status (read-only, always safe):**
```bash
nvidia-smi                                                   # full view
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv # who is using it
```

**Current reality (2026-07-15):** the A100 is **~91 % full (≈74 GB / 80 GB used)** by other
work on this box (see the `arc3-*` tmux sessions in §4). So the GPU is *effectively
unavailable* for us right now.

**Rules:**
- **Never** kill, reset, or `fuser -k` the GPU, and never touch the `arc3-*` tmux sessions —
  they are someone else's running job.
- The forecaster/FL build is **tiny** (~4 K-param MLP, whole grid ≈ 7 TFLOP = CPU-minutes), so
  **CPU is the default and blocks nothing.** Device selection is auto: use CUDA *only if*
  `torch.cuda.is_available()` **and** there is comfortable free memory (>20 GB); otherwise CPU.
  With the card at 91 % this resolves to **CPU**, which is correct and non-disruptive.
- On CPU, cap threads so parallel configs don't thrash: `torch.set_num_threads(2)` and
  `OMP_NUM_THREADS=2` per process; parallelise *across* configs/seeds, not within a run.
- MIG note (from `CLAUDE.md` §9): the card can be sliced into MIG instances; `.venv/bin/activate`
  may auto-set `CUDA_VISIBLE_DEVICES` to a MIG UUID. MIG instances are **not persistent across
  reboot**. We are **not** relying on the GPU, so none of this is on our critical path.

---

## 3. Environment & the exact commands used

**Activate:** `source /home/garima/fedOPD/.venv/bin/activate`
(Python 3.10.12 · torch 2.11.0+cu128 · pandas 2.3.3 · numpy 2.2.6 · flwr · jupyterlab)

**Re-run the EDA notebook (restart-and-run-all, writes outputs back in place):**
```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=1800 src/eda/EDA.ipynb
# ~3–4 min: the Stage-2b cell reads all 96 raw CSVs once, then later stages use the parquet.
```
Strip outputs (e.g. to make the .ipynb small enough to diff/edit):
```bash
.venv/bin/jupyter nbconvert --clear-output --inplace src/eda/EDA.ipynb
```

**Rebuild the report (PDF + EPUB):**
```bash
export PATH="$HOME/.local/bin:$PATH"     # tectonic 0.15.0 lives here (glibc-2.35 build), not on PATH by default
make -C reports all                      # = tectonic PDF + python build_epub.py (EPUB)
make -C reports pdf                       # PDF only
make -C reports epub                      # EPUB only (needs the .aux tectonic emits)
```

**Preview the PDF visually (render pages to PNG):**
```bash
pdftoppm -r 110 -png reports/eda_report.pdf /tmp/pg     # then open /tmp/pg-*.png
```

**Verify the notebook ran clean (cells + error count):**
```bash
.venv/bin/python -c "import json;nb=json.load(open('src/eda/EDA.ipynb'));\
print('cells',len(nb['cells']),'errors',sum(1 for c in nb['cells'] for o in c.get('outputs',[]) if o.get('output_type')=='error'))"
```

**Fetch raw data (only if `data/` is missing — it is git-ignored, ~7.7 GB):**
```bash
python fetch_scripts/fetch_nhs.py --dataset rtt
```

---

## 4. Background / tmux sessions

```bash
tmux ls            # list; tmux attach -t <name> to view (read-only if you just look)
```
Currently present (as of 2026-07-15):

| session | what it is | action |
|---|---|---|
| `arc3-autocommit` | auto-commit daemon: commits `FedOPD research commit — <ts>` to `master` every ~20 min and pushes | leave running; it captures our work |
| `arc3-finalize-pb`, `arc3-full-pb`, `arc3-snapshot-pb`, `arc3-watchdog-pb` | **other project's** jobs (likely the GPU workload) | **DO NOT TOUCH** |

Our own long jobs (notebook re-runs, report builds) are launched as background shell commands,
not tmux; they self-notify on completion. If you run them manually, prefer a named tmux:
`tmux new -s fedopd-build`.

**Autocommit caveat:** because the daemon commits every ~20 min, a milestone can land in a
`research commit` rather than a titled one. For milestones, commit + **tag** explicitly (e.g.
`git tag eda-v2`) so the point-in-time deliverable is pinned to exact code.

---

## 5. Directory structure — what's where and what each file holds

```
fedOPD/
├── README.md                     project overview + EDA headline results + setup/fetch instructions
├── CLAUDE.md                     project context primer (scope, decisions, conventions) — read first
├── requirements.txt              pinned deps (torch==2.11.0+cu128, pandas, flwr, …)
├── .gitignore                    ignores data/, .venv/, LaTeX aux, EPUB intermediates
│
├── docs/
│   ├── PROJECT.md                long-form project design + environment/MIG recovery detail
│   ├── WORKLOG.md                dated research register — every session (what·why·finding·decision·output); F-/D- ids
│   ├── OPS.md                    THIS FILE — how to run things, GPU policy, commands, dir map
│   ├── BUILD_LOG.md              (build phase) per-step gate log — created at build Step 0
│   ├── datasets.md               NHS RTT provenance + verified 9-column schema mapping
│   └── nhs_structure.png         NHS purchaser–provider hierarchy diagram
│
├── fetch_scripts/                data acquisition (stdlib only; the only re-runnable data tooling)
│   ├── fetch_nhs.py              idempotent downloader + unzipper (manifest-driven)
│   ├── build_rtt_manifest.py     scrapes NHS FY pages → nhs_manifest.json
│   └── nhs_manifest.json         verified source URLs + byte sizes for all 96 monthly files
│
├── data/                         GIT-IGNORED, re-fetchable — 96 raw CSVs (~7.7 GB). Never read directly in analysis.
│   └── nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv
│
├── src/
│   ├── eda/EDA.ipynb             THE EDA — 59 cells, stages 2–8, F-01..F-28, D-01..D-05 (AI-authored under owner override)
│   └── fedopd/                   (build phase) forecaster + federated loop — created at build Step 0
│
├── reports/
│   ├── eda_report.tex            EDA report source (LaTeX article; 25 pp, 10 tables, 7 figures, F-01..28 register)
│   ├── eda_report.pdf            compiled report (tectonic) — supervisor deliverable
│   ├── eda_report.epub           EPUB edition (pandoc via build_epub.py)
│   ├── build_epub.py             reproducible EPUB builder (reads .aux for cross-refs, lowers math to Unicode)
│   ├── Makefile                  `make pdf | epub | all`
│   ├── figures/                  7 PNGs consumed by the report (03_presence, 04_demand_dist, 04_trust_volume,
│   │                             05_acf_busiest, 06_sample_series, 06_month_of_year, 06_crosstrust_corr)
│   └── tables/
│       ├── rtt_canonical.parquet canonical [date,branch,branch_name,icb,dept,dept_name,demand] — 227,344 rows (THE input)
│       └── 07_outlier_register.csv  every |z|>4 flag with class (covid/spike/strike/drop) — 5,630 rows
│
├── results/                      (build phase) panel.json · dataset_stats.json · one JSON per run · tables
├── scripts/                      (build phase) run_grid.sh etc.
└── autocommit_logic/autocommit.sh   the auto-commit daemon script (runs in the arc3-autocommit tmux session)
```

**Notebook editing gotcha:** `src/eda/EDA.ipynb` with outputs is >25 K tokens; clear outputs
(`--clear-output`) before diffing/editing programmatically, then re-run to restore them.

---

## 6. Where the numbers come from (traceability)

- Every EDA figure/decision → `docs/WORKLOG.md` (F-/D- ids) → `reports/eda_report.tex` register.
- `rtt_canonical.parquet` is rebuilt by `EDA.ipynb` Stage 2b and re-validated 4/4 against external
  NHS national totals in the same run — if it disagrees with 227,344 rows / 96 months, stop.
- Build phase: each run writes `results/<config>_<seed>.json` (config, metrics, seed, git sha,
  duration); every reported number must trace to one.
