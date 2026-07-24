# fedOPD

Hospital networks must plan capacity department by department, which requires a demand
forecast for each, but a single central model is both impossible and inadequate: sites
will not pool raw activity data, and they differ widely in size and casemix, yet their
demand moves together, so there is shared structure worth learning jointly. fedOPD
addresses exactly this regime with cross-silo federated learning: each hospital is a
client that trains a shared neural demand forecaster by exchanging model updates, never
raw data, with per-client fine-tuning so the global model does not flatten local
differences. The testbed is England's NHS Referral-to-Treatment data, 96 monthly files
(2018-2026) spanning the COVID shock, where each NHS trust is a real federated client,
each treatment function a department, and new referrals the demand signal, reduced to a
single validated table of trust × department × month. The framing is operations research
plus distributed machine learning, not clinical work, and success is measured honestly:
against a hard persistence baseline, against isolated per-hospital training, and against
the privacy-violating ceiling of pooling all data.

A forecast alone plans nothing, so the second half is an agentic decision layer that
converts forecasts into action. From the same files the system recovers each service's
operational state, throughput, waiting-list backlog and the bed-linked admission queue,
which obey a simple accounting identity (backlog ≈ previous backlog + demand −
completions). A per-service agent compares forecast demand against trailing throughput,
projects the backlog against the 18-week standard, classifies shortfalls as transient,
sustained or regime change, and raises a structured, evidence-backed capacity request in
treatments per month; requests flow up the real NHS hierarchy (trust → ICB → national)
into a human-in-the-loop board queue where they are approved, refused or deferred, and
allocations are released again once a service recovers. COVID serves as the built-in
stress test: the forecaster must be robust to the shock while the agent is evaluated on
it, detecting the collapse, escalating through the recovery, and normalising afterwards.
The result is a system that demonstrates, on public data and real institutions, that
privacy-preserving federation plus transparent agentic decision-making can drive
operational efficiency in a multi-site health system.

---

## Repository

Each notebook is named for exactly what it does, and does only that.

| Notebook | Responsibility |
|---|---|
| `src/fetch_dataset.ipynb` | **Acquisition only.** Scrapes the eight NHS RTT financial-year pages, downloads the 96 monthly Full CSV archives, extracts them, builds the provider→ICB reference from the ODS ORD API, and fetches the KH03 bed workbooks. Idempotent: reruns resume rather than restart. |
| `src/inspect_dataset.ipynb` | **Validation and inspection only.** Proves the download is intact, then establishes what is in the data — provider census, department roster, hierarchy, per-region and per-department averages, and the blocking verification gate on the independent sector. Transforms nothing. |
| `src/data_processing.ipynb` | **Transformation.** Builds the canonical table from the raw monthly files, including the April 2021 waiting-time band reconciliation and the panel construction. |
| `src/eda/EDA.ipynb` | Exploratory analysis on the processed table. |

### Data layout

```
data/
  rtt_csv/      96 monthly RTT full extracts (~7.7 GB) — the source of truth
  reference/    provider_census.csv, trust_icb.csv, provider_types.csv,
                monthly_summary.csv, tf_month_demand.csv, findings.csv
  kh03/         61 quarterly overnight bed workbooks
```

The downloaded archives are deleted once `inspect_dataset.ipynb` has CRC-verified them
against the extracted files; the CSVs are the only copy retained.

### Facts about the data that shape the build

These are measured in `inspect_dataset.ipynb`, not assumed. Full detail, with the numbers
and the reasoning, is in `WORKLOG.md`.

- **`C_999` is an aggregate row, not a department.** The `Treatment Function Code` column
  contains a code named "Total" that is the exact sum of the other specialties, published
  as extra rows in the same table. It is verified exact across every month, part type and
  provider. Failing to exclude it doubles the England waiting list.
- **The schema changes in April 2021.** 69 columns before, 121 after: the single
  `Gt 52 Weeks` column is replaced by weekly bands running to 104 weeks. The bands below
  52 weeks are identical in both eras, so the >18-week metric the agentic layer uses is
  era-stable; only the >52 tail needs reconciling, and that reconciliation belongs to
  `data_processing.ipynb`.
- **`Part_3` carries no waiting-time bands, by design** — a new referral has waited ~0
  weeks. Demand is the `Total All` column alone.
- **The RTT return covers independent-sector providers as well as NHS trusts.** The
  canonical table keeps every provider with a `sector` column; sector filtering is a
  downstream panel decision, not baked into the data. `sector = public` covers ODS primary
  roles RO197 (NHS Trust) and RO107 (Care Trust), the criterion being allocability rather
  than the role label.
- **Every provider count in the project is derivable from `provider_census.csv`** — one
  row per provider code ever seen in RTT, with ODS role, active/retired status, first and
  last month, months present, ICB parent, sector and panel membership.

### Environment

Python 3.10 virtualenv at `fed_learning/` (`torch 2.13.0+cu130`, `flwr`, pandas stack,
Jupyter kernel `fed_learning (CUDA)`). The GPU is an A100 80GB reachable only through a
MIG instance. Long jobs run detached under `tmux`. See `CLAUDE.md` for working
conventions.