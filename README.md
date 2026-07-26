# fedOPD

**Federated forecasting and agentic capacity allocation for NHS outpatient demand.**

Every hospital helps train one shared demand model without surrendering a row of data, and an
agent turns the resulting forecasts into evidenced capacity requests that escalate up the real
NHS hierarchy — trust → ICB → national — to a human board.

---

## The operational problem

A multi-site health system has to decide, month by month, where capacity is short and where to
direct it: which service at which hospital is falling behind, whether the shortfall is a blip or
a trend, and whether to fix it internally or buy it in. Today that judgement is manual, slow, and
made from stale local views.

This project builds the decision loop that does it systematically: **sense demand → compare
against capacity → project the queue → raise an evidenced request → let a human board decide →
allocate → release when recovered.**

Hospital networks must plan capacity department by department, which requires a demand forecast
for each — but a single central model is both impossible and inadequate. Sites will not pool raw
activity data, and they differ widely in size and casemix, yet their demand moves together, so
there is shared structure worth learning jointly. That is exactly the cross-silo federated
learning regime.

---

## The two engines

| | **Federated forecaster** (perception) | **Agentic layer** (decision) |
|---|---|---|
| What it does | Every trust helps train one shared neural demand model per department without surrendering raw data, then fine-tunes locally | Holds the operational state of each trust × department and turns forecast vs capacity into an action |
| Why federated | Sites won't pool data; they differ in size and casemix but their demand co-moves — shared structure worth learning jointly, local level worth preserving | — |
| State it carries | — | forecast demand in, trailing throughput out, backlog stock, the bed-linked admission queue, the >18-week count |
| The glue | — | `backlog(t+1) ≈ backlog(t) + demand − completions` |
| Output | A per-site forecast informed by the whole system's experience | A capacity gap in **treatments per month** (admitted vs non-admitted, never literal beds), classified transient / sustained / regime change |

On a sustained gap the agent raises a structured request up the real hierarchy: **trust → ICB →
national**.

### The human stays where judgement lives

The ICB tier is human-in-the-loop. The agent proposes with evidence — forecast trajectory,
backlog trend, months in breach, the ask — and the board approves, refuses, or defers. The
board's view is two-sided because the data is: internal trust capacity, plus the independent
sector's aggregate volume in that ICB as revealed, purchasable substitution capacity. That is the
allocate-or-buy decision made concrete. De-escalation is symmetric: gaps that stay closed release
their allocation.

**Independent providers are private companies delivering NHS-funded care, not NHS bodies.** That
distinction is the whole reason the project carries two separate flags rather than one: an ICB can
*buy* capacity from an independent provider, but it cannot *direct* NHS staff and capital into one.
So `fl_client` marks who trains the forecaster (the 150 eligible public sites) and `allocatable` marks who
can receive capacity (public only). Neither implies the other.

**Measured constraint on how fast the buy side responds.** The intuitive mechanism, namely public backlog
rises, so work is bought from independents that month, was tested and **is not present in the
data**. Correlating the monthly change in independent share against the change in public backlog
across the 18 named specialties gives +0.08 contemporaneously and essentially zero at 3, 6 and 12
months (7 of 18 specialties positive at 6 months, i.e. chance). What is real is the *slow* shift:
independent share of ophthalmology moved 6.2% → 19.65% across the window. Substitution operates on a
multi-year contracting timescale, consistent with NHS's own encouragement of "long-term contractual
relationships" with the sector. **The agent must therefore treat independent volume as a standing
stock of purchasable capacity, not as a lever that responds inside a monthly decision loop.**

---

## The testbed

England's NHS Referral-to-Treatment return, **96 monthly files, April 2018 – March 2026**,
spanning the COVID shock.

| RTT concept | Project role |
|---|---|
| NHS trust | a federated client |
| Treatment function | a department |
| New RTT periods (`Part_3`) | the demand signal — the forecast target |
| Incomplete pathways (`Part_2`) | the backlog |
| Completed pathways (`Part_1A`/`1B`) | throughput |

Reduced to a single validated table of trust × department × month. The framing is operations
research plus distributed machine learning, not clinical work.

Success is measured honestly, against three baselines:

1. **Persistence** — a hard naive baseline, not a strawman.
2. **Isolated per-hospital training** — does federation actually beat going it alone?
3. **Pooled central training** — the privacy-violating ceiling.

### COVID is the built-in stress test

The shock sits inside the window on purpose. The forecaster has to be robust to it; the agent
gets *evaluated* on it — detect the collapse as an anomaly, escalate through the sustained
recovery, normalise when it settles. That arc, demand signal to board decision and back down,
with no raw data ever leaving a site, is the project.

---

## Scope, deliberately bounded

- **The currency is operational, not financial** — treatments, queues, waiting-time standards,
  human factor, efficiency. Expansion and revenue are out, because the data has no money in it.
- **The clients are the 150 public sites still reporting with at least 48 months of history.** The
  earlier rule of full 96-month history gave 126 sites but discarded 20% of public demand.
  Independents stay in the data —
  they absorb a real and growing slice of demand, ophthalmology fastest — but enter as context,
  not as clients.
- **The forecastable universe is 18 named specialties plus one merged `X_OTHER`**, so the tiers
  reconcile to 100% of demand and the escalation arithmetic actually adds up.

---

## Repository

Each notebook is named for exactly what it does, and does only that.

| Notebook | Responsibility |
|---|---|
| [`src/01_fetch_dataset.ipynb`](src/01_fetch_dataset.ipynb) | **Acquisition only.** Scrapes the eight NHS RTT financial-year pages, downloads the 96 monthly Full CSV archives, extracts them, builds the provider→ICB reference from the ODS ORD API, and fetches the KH03 bed workbooks. Idempotent: reruns resume rather than restart. |
| [`src/02_inspect_dataset.ipynb`](src/02_inspect_dataset.ipynb) | **Validation and inspection only.** Proves the download is intact, then establishes what is in the data — provider census, department roster, hierarchy, per-region and per-department averages, the independent-sector gate, and the eight-year format-drift audit. Transforms nothing. |
| [`src/03_data_processing.ipynb`](src/03_data_processing.ipynb) | **Transformation.** Merges the 96 monthly files into one canonical table on an explicit column contract, reconciles the April 2021 schema break, resolves the ICB escalation key, and builds the federation panel. |
| [`src/04_eda.ipynb`](src/04_eda.ipynb) | **Exploration.** The 18-week series across the window, the independent-substitution lag test, and the accounting identity worked through one real trust. Reads the canonical table, writes nothing back. |
| [`src/05_baselines.ipynb`](src/05_baselines.ipynb) | **The bar.** Four baselines, the three-way train/validation/test split, MASE / RMSE / the two R² values, the growth-detection scoring, and the normalised dataset export. Nothing downstream may skip this. |
| [`src/06_federated_forecast.ipynb`](src/06_federated_forecast.ipynb) | **The federation plane.** FedAvg over the site silos, hand-implemented in torch, against `local`, `central` and post-training baselines. Scores point accuracy and the up/flat/down direction call. |
| [`src/07_agentic_layer.ipynb`](src/07_agentic_layer.ipynb) | **The agentic plane.** State vector, split removal term, backlog projection, gap classification, site → region → group escalation, and a back-test of the projection against months that already happened. |

### Results so far

The full account, written for a reader starting from zero, is
**[`docs/fedOPD_report.pdf`](docs/fedOPD_report.pdf)** — 20 pages, 13 figures, every number traceable
to a stored notebook output.

Everything below is scored on the **validation** year (2024-04 to 2025-03). The test year
(2025-04 to 2026-03) is sealed and has never been opened.

**1. The backlog identity leaks, and correcting it matters.** The standard
`backlog + demand − treatments` projection over-predicts in **95 of 95** months. Splitting the leak by
NHS England's own recorded reasons — 49% of it is treatment that happened and was filed late — and
adding that half back to capacity, then back-tested six months forward on 2,046 services:

| Projection | Per-service MAE | Bias | Group total projected | Actual |
|---|---|---|---|---|
| **With removal term** | **682** | **−16** | 7.05m | 7.08m |
| Naive identity | 990 | +565 | 8.24m | 7.08m |

31% lower error, and the systematic bias disappears.

**2. A federated neural forecaster does not beat repeating last month.** 2,085 series, median MASE:
`naive` **0.510**, `mean12` 0.512, `fedavg` 0.553, `fedavg_ft` 0.568, `central` 0.665. Only **9.3%** of
services achieve a within-series R² above zero. Reported as the null it is.

**3. The metric decides the winner.** Scored on the question a board actually asks — is this department
growing? — the ordering inverts. `drift`, *worst* on MASE, is the best broad detector (66.3% direction
accuracy). `mean12`, second-best on MASE, has **zero recall** — it never calls growth at all. And the
post-trained federated model becomes a selective, high-precision detector:

| Model | Precision on "growing" | Lift over 45.9% base rate | Coverage |
|---|---|---|---|
| `fedavg_ft` | **67.3%** | +21.4pp | 13.1% of services |
| `local` (no sharing) | 55.5% | +9.6pp | 23.8% |

Sharing weights buys roughly **ten points of precision** over each site working alone — and it shows up
on the decision metric, not on forecast error.

**4. There is no internal slack to reallocate.** At the decision month, 80.3% of services are in
crisis and 51 have slack. Total ask **419,220** treatments/month against a total offer of **657** —
0.16%. The first two escalation tiers have almost nothing to settle, which inverts the intuition the
tiered design was built on.

**Two things that must not be read from these numbers.** `central` coming last is a training-budget
artefact — it receives 1.54m sample-updates against FedAvg's 4.63m — so federation-versus-pooling has
**not** been tested. And growth *magnitude* is not predicted; only direction, and only modestly.

What NHS England says about the collection, read from their own documents with every claim cited, is
in [`RTT_SOURCE_DOSSIER.md`](RTT_SOURCE_DOSSIER.md). The reasoning behind every decision, including
the failures and dead ends, is in [`WORKLOG.md`](WORKLOG.md). Working conventions are in
[`CLAUDE.md`](CLAUDE.md).

### Data layout

```
data/
  rtt_csv/      96 monthly RTT full extracts (~7.7 GB) — the source of truth
  reference/    provider_census.csv, trust_icb.csv, provider_types.csv,
                monthly_summary.csv, tf_month_demand.csv, findings.csv
  canonical/    rtt_canonical.parquet   the merged RTT table, 15 columns
                rtt_normalised.csv      raw + z-scored measures, scaler fitted on train only
                rtt_panel.parquet       the 150 x 19 x 96 federation cube
                provider_dim.csv        one row per provider
                national_monthly.csv    national series + identity residual
  kh03/         61 quarterly overnight bed workbooks
```

The downloaded archives are deleted once `02_inspect_dataset.ipynb` has CRC-verified them against
the extracted files; the CSVs are the only copy retained.

### The canonical table

One row per **provider × department × month**. 121 raw columns reduce to 15, and a column is kept
only if some part of the system above consumes it — the contract, with the measurement justifying
every drop, is a section of `03_data_processing.ipynb`.

| Column | Meaning | Consumed by |
|---|---|---|
| `month`, `provider_code`, `dept` | the key | one series per client × department |
| `demand` | new RTT periods | **the forecast target** |
| `completed_admitted`, `completed_nonadmitted` | completed pathways, split | the capacity ask, in treatments per month |
| `completed` | their sum | throughput term of the accounting identity |
| `waiting` | incomplete pathways | backlog stock |
| `waiting_gt18` | of those, past 18 weeks | the standard the agent projects against |
| `waiting_gt52` | of those, past 52 weeks | breach severity |
| `waiting_dta` | of those, with a decision to admit | the bed-linked admission queue |
| `sector` | `public` / `independent` | independents as purchasable substitution capacity |
| `icb` | resolved commissioner parent | the escalation key |
| `panel_member` | in the balanced 126 | selects federation clients — a flag, never a filter |

---

## Facts about the data that shape the build

Measured in `02_inspect_dataset.ipynb` and `03_data_processing.ipynb`, not assumed. Full detail, with
the numbers and the reasoning, is in `WORKLOG.md`.

- **`C_999` is an aggregate row, not a department.** The `Treatment Function Code` column contains
  a code named "Total" that is the exact sum of the other specialties, published as extra rows in
  the same table. Verified exact across every month, part type and provider. Failing to exclude
  it doubles the England waiting list.
- **The schema changes in April 2021.** 69 columns before, 121 after: the single `Gt 52 Weeks`
  column is replaced by weekly bands running to 104 weeks. The bands below 52 weeks are identical
  in both eras, so the >18-week metric the agentic layer uses is era-stable; only the >52 tail
  needs reconciling.
- **Treatment function *names* changed at the same break, codes did not.** 18 of 24 were renamed.
  Every join is on code; grouping by name silently splits each specialty into two partial
  histories.
- **`Part_3` carries no waiting-time bands, by design** — a new referral has waited ~0 weeks.
  Demand is the `Total All` column alone.
- **The RTT return covers independent-sector providers as well as NHS trusts.** The canonical
  table keeps every provider with a `sector` column; sector filtering is a downstream panel
  decision, not baked into the data. `sector = public` covers ODS primary roles RO197 (NHS Trust)
  and RO107 (Care Trust), the criterion being allocability rather than the role label.
- **The parent organisation stated in the RTT file is not a stable ICB.** It is an NHS *region*
  before 2020 and an ICB after, so the escalation key comes from the ODS `RE5` relationship
  instead, with a fallback only where ODS has no answer.
- **The accounting identity leaks.** `backlog + demand − completions` over-predicts the waiting
  list every month for 95 of 95 months. The residual survives being recomputed on all 653
  providers, so it is genuine attrition — removals, transfers out of RTT, validation, deaths,
  declines — and the decision layer needs an explicit removal term.
- **Every provider count in the project is derivable from `provider_census.csv`** — one row per
  provider code ever seen in RTT, with ODS role, active/retired status, first and last month,
  months present, ICB parent, sector and panel membership.

---

## Environment

Python 3.10 virtualenv at `fed_learning/` (`torch 2.13.0+cu130`, `flwr 1.30.0`, pandas stack,
Jupyter kernel **fed_learning (CUDA)**). The GPU is an A100 80GB reachable only through a MIG
instance. Long jobs run detached under `tmux`. See `CLAUDE.md` for working conventions.
