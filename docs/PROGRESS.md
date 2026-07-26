# fedOPD: state of the project

**A handover briefing, written to be defended rather than skimmed.**

Two kinds of statement appear below and they are marked differently, because keeping them apart is
the whole discipline of the project:

- **[NHS]** is a fact about the data, taken from an NHS England document. It can be cited.
- **[measured]** is a number this project computed from the data. Every one is reproducible by
  running a notebook in `src/`: the build figures come from `02_inspect_dataset.ipynb` and
  `03_data_processing.ipynb`, the analytical ones from `04_eda.ipynb`. Where a figure exists in two
  notebooks on two bases, both are given with the basis named.
- Anything that is neither is labelled as inference or as an open question. There are only a few, and
  they are marked.

---

## Status

| | |
|---|---|
| **Phase** | Data pipeline complete and verified. No modelling started. |
| **Raw data** | 96 monthly CSVs, 8,224,108,956 bytes, April 2018 to March 2026 |
| **Clean table** | `data/canonical/rtt_canonical.csv` and `.parquet`, **322,531 rows x 15 columns** |
| **Training panel** | `data/canonical/rtt_panel.parquet`, **126 trusts x 19 specialties x 96 months = 229,824 rows** |
| **Integrity** | sha256 manifest of all 96 files, 96 distinct fingerprints |
| **Notebooks** | 4 in `src/`, all executed headless, 0 cell errors |
| **Not built** | forecaster, agent |
| **Next** | exploratory analysis, then the persistence baseline, before any model |
| **Compute** | this laptop is Python 3.12.10, no GPU. Training belongs on the A100 box described in `CLAUDE.md`. |

---

# 1. What RTT measures

**Referral to Treatment.** A waiting-times measurement for consultant-led elective care. It is not a
beds dataset, and it contains no beds, money or staffing.

### The clock

A care professional refers a patient to a consultant-led service, and a **waiting-time clock starts**
on the date the provider receives the referral **[NHS: guidance §3.2.1]**. It runs until one of two
kinds of event:

- **Rule 4, a clock stop for treatment.** "A clock stops when first definitive treatment starts"
  **[NHS: §4.3]**, where first definitive treatment is "an intervention intended to manage a
  patient's disease, condition or injury and avoid further intervention" **[NHS: §4.3.1]**.
- **Rule 5, a clock stop for non-treatment.** A communicated clinical decision not to treat, the
  start of **active monitoring** (a period of watching without intervention), a qualifying
  did-not-attend, the patient declining, or the patient dying **[NHS: §4.4]**.

**That two-route structure is load-bearing.** The published "completed pathways" counts are dominated
by rule 4. Pathways leaving by rule 5, or recorded late, are why the obvious backlog arithmetic fails.
See trap 3.

### The standard

Patients have a **legal right**, under the NHS Constitution, to start consultant-led non-emergency
treatment within a maximum of 18 weeks from referral **[NHS: §1.1]**. The operational standard is that
**92% of incomplete pathways are within 18 weeks**, and since 2015 this incomplete-pathway measure is
"the sole measure of patients' constitutional right" **[NHS: §1.1]**. The separate admitted (90%) and
non-admitted (95%) standards were abolished in October 2015.

Note carefully: the standard is measured on people **still waiting**, not on people treated.

England has not met it since **November 2015, with the single exception of February 2016**
**[NHS: RTT Annual Report 2019/20 §3.2]**.

### What the standard has actually done in our window

All **[measured]** from `rtt_canonical.parquet`, all-provider basis:

| Month | Waiting list | Within 18 weeks |
|---|---|---|
| Apr 2018 (window opens) | 4.04m | 87.5% |
| Feb 2020 (last pre-COVID) | 4.44m | 83.1% |
| **Jul 2020 (performance trough)** | 4.07m | **46.8%** |
| Mar 2022 | 6.39m | 62.1% |
| **Aug 2023 (list peak)** | **7.78m** | 58.0% |
| Mar 2024 | 7.57m | 57.2% |
| Mar 2026 (window closes) | 7.05m | 65.2% |

**Two observations that should shape how you model this.**

First, **the list peak and the performance trough are 3.1 years apart** **[measured]**. The list
peaked August 2023 at 7.78m; performance bottomed July 2020 at 46.8%. Best performance in the window
is May 2018 at 88.1%, already below the 92% standard. These are not the same phenomenon, and a single
"how bad is it" metric will conflate them.

Second, **in July 2020 the list was 4.07m, essentially the same size as April 2018's 4.04m, while
performance had fallen from 87.5% to 46.8%.** COVID suppressed referrals and treatment
simultaneously, so the queue did not lengthen much but the people in it stopped moving. Queue length
and queue age are independent quantities. The canonical table carries both, `waiting` and
`waiting_gt18`, for that reason.

*(Beds are a separate NHS return, KH03. 61 quarterly workbooks are downloaded and validated. Nothing
consumes them. See open questions.)*

---

# 2. What the dataset physically is

**96 monthly CSV files, April 2018 to March 2026, 8.22 GB extracted** **[measured]**. No gaps, no
duplicate months, verified against the eight NHS financial-year index pages directly.

### It is an aggregate return, not patient records

The single most important structural fact. NHS states it plainly: "The national data collection looks
at RTT waiting times in weeks, split by treatment function. Returns are submitted by providers, split
by commissioner" **[NHS: §10.1.1.2]**.

Providers download a spreadsheet from NHS England's **Strategic Data Collection Service (SDCS)**,
fill it in, and upload it **[NHS: §10.1.2]**. So **one row is a count of clocks in one state**, for
one provider x commissioner x treatment function x part type, spread across weekly-band columns. It
is never a patient.

**Grain:** provider x commissioner x treatment function x part type.

**[measured]** the March 2026 file holds **184,184 rows x 121 columns**. Excluding the `C_999`
aggregate rows leaves **143,342**, which collapse to **16,363** provider x treatment-function x
part-type groups once the commissioner axis is summed over: an **8.8x row multiplier**. The April
2018 file is the same shape at a different width: **151,746 rows excluding `C_999` collapsing to
15,762 groups, a 9.6x multiplier** **[measured]**.

That multiplier *is* the size of the axis being discarded, and it is the reason dropping the
commissioner columns needs the justification in section 4 rather than a shrug.

### The five part types, quoted

From **[NHS: §10.1.1.2]**, verbatim:

| Part | NHS definition | Project role | Stock or flow |
|---|---|---|---|
| `Part_1A` | "cases where patients completed their RTT pathway during the month with an inpatient or day case admission" | throughput, admitted | flow |
| `Part_1B` | "cases where patients completed their RTT pathway during the month for reasons other than an inpatient or day case admission" | throughput, non-admitted | flow |
| `Part_2` | "cases where patients are still waiting to start treatment at the end of the reporting month. This is a 'snapshot' on the last day of the reporting period" | **the backlog** | **stock** |
| `Part_2A` | "cases where patients are still waiting ... where a clinical decision to admit to a hospital bed for treatment has been made" | bed-linked queue | **stock**, subset of `Part_2` |
| `Part_3` | "Number of new RTT periods during the month" | **demand, the forecast target** | flow |

Three consequences that are easy to get wrong:

1. **`Part_2A` is a subset of `Part_2`, not an addition.** NHS states the arithmetic: the difference
   between them "equates to the number of incomplete pathways without a decision to admit"
   **[NHS: SPN §4]**. So `waiting_dta <= waiting` must hold. **[measured]** it fails in **47 of
   322,531 rows**, and it fails in the raw NHS file too, so those are published upstream defects and
   are deliberately not clamped.
2. **`Part_3` is gross, not net.** "RTT pathways where the clock start date is within the reporting
   month. This will include those where the clock also stopped within the reporting month"
   **[NHS: SPN §4]**. A pathway opened and closed in the same month still counts as demand.
3. **Stocks and flows must not be added.** Nothing in the file prevents it.

### The waiting-time bands, exactly

Do not infer the boundary convention. NHS defines it in days **[NHS: §10.1.7]**:

- "0 to 1 weeks includes patients waiting/having waited 0, 1, 2, 3, 4, 5, 6 and 7 days", so **eight**
  day-values sit in the first band.
- "17 to 18 weeks includes ... 120, 121, 122, 123, 124, 125 and 126 days."
- **"A patient who has waited exactly 18 weeks (126 days) is included in the 17-18 weeks time band."**

**Therefore exactly 18 weeks is *within* standard, not a breach.** The >18-week count is the sum of
bands strictly above the 17-18 band, that is 127 days and over. An off-by-one here silently
mis-defines the agent's headline metric across all 96 months.

### Who reports

**653 distinct provider codes appear across the eight years** **[measured]**, but only **410 to 533
appear in any single month** **[measured, `monthly_summary.csv`, any-row basis]**. The census records
**525 reporting in March 2026**, of which **150 are public** **[measured, `provider_census.csv`]**.

Those are three different numbers for "how many providers are there", and they differ because they
ask different questions: ever-seen, present-in-this-month, and reporting-on-a-given-definition. **Every
provider count in this project must come from `provider_census.csv` on its stated definition.** A
count computed ad hoc from another table is a different question wearing the same words, and that has
already produced a wrong number here.

Split by sector **[measured]**, using ODS primary roles rather than code shape:

- **196 public**: 194 NHS Trusts (role RO197) plus 2 Care Trusts (RO107)
- **457 independent**: private providers delivering NHS-funded care

### Specialties

The return does not collect every specialty. NHS lists on the form exactly **18 named treatment
functions**, chosen because they "were high volume areas with a large volume of RTT pathways"
**[NHS: §10.1.4]**, plus catch-all "Other" lines for everything else.

**The number of Other lines changed at April 2021.** Before it, one bucket (`X01`). From it, **five**:
`X02` Other Medical, `X03` Other Mental Health, `X04` Other Paediatric, `X05` Other Surgical, `X06`
Other Other **[NHS: §10.1.4]**. So the current form is 18 named + 5 Other = 23 lines, the pre-2021
form was 18 + 1 = 19, and **[measured]** the union across the window is 24 codes.

**[measured]** the Other buckets carry **25.6% of all demand**, so an analysis restricted to the 18
named specialties covers only **74.4%** of activity. The project therefore carries a 19th merged
`X_OTHER` series, which makes the hierarchy reconcile exactly. NHS's own pre-2021 description of its
structure is "19 treatment functions (including 'Other')" **[NHS: Annual Report §7]**, so this is not
an invention.

**Some codes are absent by rule, not omission** **[NHS: §10.1.4]**. Spinal Surgery (108), Orthopaedic
(111) and Trauma Surgery (115) are reported inside Trauma & Orthopaedics (110); Maxillofacial (144)
and Oral & Maxillofacial (145) inside Oral Surgery (140). So the named specialties are **already
aggregates** at their reported level.

### Pathways are not patients

"NHS England often uses the term 'RTT pathway' ... this is the same as an 'RTT period'", and "a person
may therefore have multiple RTT periods ... along one patient pathway" **[NHS: §13]**. NHS's March
2026 figures are **7.1m pathways against about 6.0m unique patients** **[NHS: SPN]**. `demand` counts
clock starts, not people. No per-patient claim is supportable from this data alone.

*(Our table gives 7,045,510 for March 2026 while NHS publishes 7.1m. Both are correct. Ours is the raw
submitted total; the published headline adds an estimate for trusts that did not submit, and Sheffield
Teaching Hospitals submitted nothing that month **[NHS: SPN]**. The gap is by construction.)*

---

# 3. What the project is building

### Engine 1: the federated forecaster

Predict next month's `demand` for each trust x specialty. The constraint that makes this a research
problem rather than a regression exercise: **trusts will not pool raw activity data**, yet they differ
widely in size and casemix while their demand co-moves, so there is shared structure worth learning
jointly. That is precisely the **cross-silo federated learning** regime: few, large, institutional
clients.

Each client trains locally, only model updates are exchanged, and clients fine-tune locally afterwards
so the shared model does not flatten local differences.

**It must be measured against three baselines, and a result that skips one is not a result:**

1. **Persistence.** Next month equals this month. Monthly hospital demand is highly autocorrelated,
   so this is a hard baseline and not a strawman.
2. **Isolated per-trust training.** Does federating actually beat each site going it alone?
3. **Pooled central training.** The privacy-violating ceiling. Federation should approach it, not
   exceed it.

**A pre-registration that must be honoured.** The intuitive hypothesis is "federation rescues the
small, data-poor client". On an earlier run of this project that hypothesis was pre-registered and
**refuted**: gains sat in mid-size clients, and the thinnest clients did *better* trained alone. Do
not quietly re-adopt the intuitive version.

### Engine 2: the agentic decision layer

Per trust x specialty x month, the state is: forecast demand in, trailing throughput out, backlog
stock, the bed-linked admission queue, and the >18-week breach count. The agent compares forecast
demand against capacity, projects the backlog against the 18-week standard, classifies any shortfall
as **transient, sustained or regime change**, and on a sustained gap raises a structured request up
the real hierarchy: **trust to ICB to national**.

The ICB tier is human-in-the-loop. The board sees the evidence and approves, refuses or defers, and
its view is two-sided: internal trust capacity, plus independent-sector volume as purchasable
substitution capacity. De-escalation is symmetric.

### Scope bounds, and they are hard

- **The currency is operational, not financial.** Treatments, queues, waiting-time standards. There is
  no money in this data, so there are no cost claims.
- **Capacity is requested in treatments per month**, split admitted and non-admitted, **never in
  beds**. The data has no beds per specialty.
- **"Expanding" or "upgrading" a trust is not measurable here.** No estate, no staffing, no capital.

---

# 4. What has been built

All code is in Jupyter notebooks under `src/`. All three executed headless, 0 cell errors, outputs
stored in the files.

| Notebook | Responsibility |
|---|---|
| `01_fetch_dataset.ipynb` | **Acquisition only.** Scrapes the eight NHS financial-year pages, downloads 96 archives, extracts, builds the provider-to-ICB reference from the ODS ORD API, fetches KH03. Idempotent: writes to a `.part` name and renames on completion, so a finished filename always means a finished file. |
| `02_inspect_dataset.ipynb` | **Validation and inspection only. Transforms nothing.** Integrity checks, the sha256 manifest, the provider census, the specialty roster, the column dossier, and the blocking gate on the independent sector. Emits **17 findings** to `data/reference/findings.csv`. The ids are not contiguous: F-01 to F-12, F-18, F-19, F-21, F-22, F-23. The gaps are findings that live only in `WORKLOG.md`, because ids emitted by code take precedence over ids typed into prose. |
| `03_data_processing.ipynb` | **Transformation.** Merges 96 files into one canonical table on an explicit column contract, reconciles the April 2021 schema break, resolves the ICB escalation key, builds the federation panel. |
| `04_eda.ipynb` | **Exploration.** Reads `data/canonical/` and writes nothing back. Holds the three analyses this document quotes that are not part of the build: the 18-week series, the independent-substitution lag test, and the identity worked example. |

### Outputs

| File | Contents |
|---|---|
| `rtt_canonical.parquet` / `.csv` | **322,531 rows x 15 columns.** One row per provider x specialty x month. 653 providers, 19 specialties, 96 months. All providers retained; sector is a flag, never a filter. |
| `rtt_panel.parquet` | **229,824 rows x 20 columns.** The rectangular 126 x 19 x 96 federation cube. It carries the 15 canonical columns plus five modelling flags: `service_exists`, `reported_demand`, `reported_full`, `n_parts`, `usable`. **[measured] 179,520 rows are `usable`**, meaning the service exists and demand was reported. |
| `provider_dim.csv` | **653 rows x 11 columns**, one per provider: `provider_code`, `provider_name`, `sector`, `icb`, `icb_ods`, `icb_reported_last`, `fl_client`, `allocatable`, `first_month`, `last_month`, `own_icb_share`. |
| `column_contract.csv` | The 15 kept columns, each naming the component that consumes it. |
| `csv_manifest.csv` | 96 sha256 fingerprints, the integrity baseline. |
| `findings.csv` | **17 findings**, generated by code, not typed by hand. Ids are non-contiguous by design. |

### The column contract: 121 raw columns to 15

Decided **in code**, not in prose, by three tests applied in order:

1. **Is it populated?** A blank, constant or rounding-error column decides nothing.
2. **Is it a label or an axis?** Group by provider x treatment function x part type and count distinct
   values. Exactly one per group means the column is *functionally determined* by keys already
   carried: it is a **label**, and dropping it loses nothing a join could not restore. More than one
   means a genuine **axis**, and collapsing it discards information.
3. **Does the problem statement consume it?** Every kept column names its consumer.

**[measured]** on the 121-column schema: **16 descriptive/measure columns and 105 band columns**, and
the 16 break down as:

| Kind | Count | Of which kept |
|---|---|---|
| **axis** | **4**, all commissioner columns | 0 |
| **label** | 9 | 3 (`Provider Org Code`, `RTT Part Type`, `Treatment Function Code`) |
| **measure** | 3 | 1 (`Total All`) |

The two dropped measures fail test 1: `Total` is populated in only **28.5%** of rows and is
identically zero for `Part_2`, `Part_2A` and `Part_3`; `Patients with unknown clock start date` is
populated in **18.7%** and is already inside `Total All` **[measured]**.

*(Test 2 applies only to descriptive columns. A measure varies inside a key holding several
commissioner rows by definition, so classifying measures as axes is a category error. This project
made exactly that error and published it as a finding before catching it.)*

**The commissioner axis is a real loss, taken deliberately.** **[measured]** up to **110 distinct
commissioner codes** appear inside a single provider x specialty x part group (on the contract cell's
basis, which includes the `C_999` rows; the inspection dossier, which excludes them, gives **104**).
Summing over that is not the removal of redundancy.

It is justified by a separate measurement. **[measured, `provider_dim.csv`]** across the **173 public
providers that have an own-ICB share at all**, the mean is **82.7%** and the median **89.9%**. On the
inspection notebook's basis, which counts differently, F-22 reports **84.3% of all new referrals
commissioned within the provider's own ICB, median 91.9%**. Both are in the outputs; say which you
are quoting.

So the trust-to-ICB escalation tier is sound for the typical trust, and **not** universal.
**[measured] 12 of 173 public providers sit below 50%**, and the list is exactly what the design
predicts, national and specialist centres drawing referrals from many ICBs:

| Trust | own-ICB share |
|---|---|
| Central and North West London | 0.0% |
| South West Yorkshire Partnership | 0.2% |
| Moorfields Eye Hospital | 13.9% |
| Central London Community Healthcare | 15.2% |
| Great Ormond Street | 16.1% |
| Royal National Orthopaedic | 18.1% |
| The Royal Marsden | 20.7% |
| The Walton Centre | 33.3% |
| Hounslow and Richmond Community | 34.7% |
| Royal Papworth | 40.3% |
| Queen Victoria | 44.5% |
| Surrey and Sussex Healthcare | 45.1% |

`own_icb_share` is retained per provider in `provider_dim.csv` so a reader can see how literally to
take any given trust's escalation. **Moorfields matters most here**: it is the flagship ophthalmology
trust, ophthalmology is the specialty with the fastest independent substitution, and it is among the
least ICB-aligned trusts in the country. Any C_130 regional claim is confounded twice over.

### The 15 kept columns

| Column | Consumed by |
|---|---|
| `month`, `provider_code`, `dept` | the key: one series per client x department |
| `demand` | **the forecast target**, `Part_3` new RTT periods |
| `completed_admitted`, `completed_nonadmitted` | the capacity ask, split as NHS splits it |
| `completed` | throughput term of the backlog identity |
| `waiting` | backlog stock |
| `waiting_gt18` | the 18-week standard the agent projects against |
| `waiting_gt52` | breach severity: separates "behind" from "in crisis" |
| `waiting_dta` | the bed-linked admission queue |
| `sector` | independents as purchasable substitution capacity |
| `icb` | the escalation key |
| `fl_client` | selects the 126 federation clients |
| `allocatable` | who can *receive* capacity (public only) |

### Standing asserts

The notebooks halt rather than warn. **[measured] 15 `assert` statements in `03_data_processing.ipynb`
and 2 in `02_inspect_dataset.ipynb`.** What they guard:

1. **Coverage identity.** 18 named + `X_OTHER` = the published `C_999` total, for every provider, part
   type and month. **[measured] 199,410 groups compared, 0 mismatches.**
2. **Boundary continuity at 2021-04**, at a 3x local-variation threshold, for both reconstructions.
3. **Key uniqueness**, 0 duplicate provider/dept/month rows.
4. **Hierarchy completeness**, 0 federation clients without an ICB, and none in the panel either.
5. **ICB stability**, no provider changes ICB mid-window, and no non-ICB code leaks into the key.
   Both are needed: the first alone passes if a provider is *consistently* given something that is
   not an ICB, which is the failure that actually occurred here once.
6. **Contract agreement**, the built table is exactly the 15 contracted columns.
7. **Integer measures**, no NaN and nothing fractional before the cast to `int64`.
8. **Merge safety**, the reporting join does not change the row count.
9. **Round trip**, both parquet and CSV read back with the same shape, `month` still a datetime, and
   `demand` summing to the same total.
10. In `02_inspect_dataset.ipynb`: the `C_999` aggregate identity, and no two months sharing a sha256.

---

# 5. The five traps

Each of these silently produces a well-formed, plausible, wrong answer. Every one was found the hard
way, and several were found only after being published internally as a result.

### Trap 1: `C_999` is not a specialty

The `Treatment Function Code` column contains a code that is the **exact sum of all the others**,
published as extra rows in the same table. **[measured]** verified exact across **199,410 provider x
part-type groups, 0 mismatches**.

Fail to exclude it and the England waiting list for March 2026 reads **14,091,020 instead of
7,045,510**, exactly **2.00x**.

It is not useless. It is an independently published control total, so it is retained as a permanent
assert: if NHS ever adds a treatment function outside our roster, our sum falls short and the notebook
stops. That converts a silent coverage loss into a hard failure.

### Trap 2: the schema changed three times, not once

- **April 2020.** The `Provider Parent Org Code` column changed meaning. Until then it held one of
  **14 NHS England Region/Local Offices (Direct Commissioning Offices)**; from April 2020 it holds one
  of **42 sustainability and transformation partnerships (STPs)**, which later became the 42 ICBs
  **[NHS: SPN July 2020]**. The X24 commissioner-code phase-out also began here, not in 2021, and was
  deliberately extended because providers were diverted to the COVID response.
  **[measured]** agreement between this column and the ODS parent, by year: **2018 and 2019, 14
  distinct values and 0.0%; 2020, 56 values and 56.2%; 2021 onward, 42 values and 72.8% to 74.2%**.
  The 0.0% is not poor agreement, it is a different entity type entirely, and 2020 carries both
  vocabularies at once, which is why it shows 56 values rather than 14 or 42.
- **April 2021.** 69 columns become 121 **[measured]**. The single `Gt 52 Weeks` column is replaced by
  weekly bands to 104+; the single "Other" specialty splits into five; and **NHS renamed 18 of 24
  treatment functions while leaving the codes unchanged** **[measured]**. Group by name, or by code
  *and* name, and every specialty silently splits into a 36-month row and a 60-month row. Neither
  looks wrong. Both are. **Join on codes, never names.**
- **February 2024.** Consultant-led community services left RTT entirely **[NHS: §7.2]**. NHS
  quantifies it as "a decrease of approximately **43,000 pathways** within the community paediatric
  specialty" **[NHS: SPN §4]**, landing inside the Other buckets.

The bands **below** 52 weeks are identical in both eras **[measured]**, which is why the 18-week metric
is era-stable and only the >52 tail needs an explicit branch. The reconciliation direction is forced:
you can turn fine into coarse by adding up, never the reverse.

### Trap 3: the backlog identity leaks, in one direction, every month

The obvious arithmetic is `backlog(t+1) = backlog(t) + demand − completions`.

**[measured]** it over-predicts the backlog in **95 of 95 months**. Not noise: a systematic,
one-directional leak of roughly 15% of demand.

**NHS publishes this quantity and has a name for it: "unreported removals".** Their definition,
verbatim: "Unreported removals = waiting list at start of period + clock starts during period –
completed pathways during period – waiting list at end of period" **[NHS: Derived unreported
removals]**. That is algebraically our residual with the sign reversed.

Ours against theirs, on **their** denominator, share of total removals:

| Era | **[measured]** ours | **[NHS]** published |
|---|---|---|
| pre-pandemic | **17.50%** | 17% |
| 2021 onward | **14.94%** | 14% |

The notebook prints all three denominators **[measured]**:

| Basis | mean-of-ratios | ratio-of-means |
|---|---|---|
| of total removals (NHS's basis) | 15.64% | 15.61% |
| of demand (this project's historic basis) | **15.40%** | **15.27%** |
| of the waiting list | 4.25% | 3.98% |

Mean unreported removals: **183,635 per month** over **95 months** **[measured]**. The era split above
uses **22 pre-pandemic months and 63 months from 2021**.

**What the leak actually is, and this changes the phase-4 design.** From NHS's record-level linkage,
of unreported removals with a recorded reason in 2025: **49% were patients who started treatment** but
were recorded too late to count, 23% a decision not to treat, 11% a did-not-attend at first
appointment **[NHS]**. Providers may only submit removals occurring within the reporting month, so
historic removals are "lost to reporting" entirely.

**So this is not one attrition rate. About half of it is throughput that happened.** A decision layer
modelling it as a single loss term will understate real capacity.

*Worked example of the danger.* **[measured]** at panel trust `RTD` in Trauma & Orthopaedics, over
the 8 months August 2025 to March 2026, demand exceeded throughput in **every** month, by 6,074 in
total, a mean of 759 per month. Applying the identity to the July 2025 opening backlog of **7,922**
projects a March 2026 backlog of **13,996**. The actual figure is **7,437**.

The identity over-predicts by **88%** over eight months, and the error compounds with the horizon. An
agent built on it would escalate this department to the national tier on a crisis that is not
occurring, while the real waiting list was flat to falling throughout.

### Trap 4: zero-filled cells are not zeros

The federation cube is rectangular by construction, so absent combinations are filled with zero.
**[measured] 62,313 of 229,824 cells, 27.11%**, are filled this way.

That fill is overwhelmingly **structural absence, not missingness**: **524 of 2,394 trust x specialty
series, 21.9%, have zero demand in all 96 months**. Most trusts simply do not provide neurosurgery or
cardiothoracic surgery. The remaining **1,870 active series have a median of 96 of 96 months active**
**[measured]**.

**Why this is dangerous rather than untidy.** Most forecast error metrics score a perfect zero
prediction against a zero actual as zero error. Leaving 524 constant-zero series in the evaluation set
**drags headline accuracy toward zero and makes the model look better than it is**. This is the single
most likely way the project produces a result that is wrong in its own favour, which is the most
dangerous kind. The fix is a mask carried through the windowing **and** through the metric's series
set, not a comment.

### Trap 5: "present in all 96 months" has two meanings

A provider can appear in a month with `Part_2` rows but no `Part_3` rows: present, but contributing no
demand. The two readings give different answers, and **this project has already published a wrong
number from exactly that ambiguity**.

The panel uses the demand-row definition, filed new-referral rows in all 96 months. On that definition
**[measured]** the panel is 126 public trusts.

Related, and measured this session: providers do stop submitting, and NHS names them. **[measured]**
across all 653 providers there are **42,542 provider-month returns, of which 6,908 are partial, 504
filed something but no `Part_3`, and 393 are gaps inside a provider's own reporting span**. NHS-named
cases verify against our files exactly: Barnsley (RFF) and Royal Free (RAL) filed nothing for July
2020; Bradford (RAE) filed only `Part_2` and `Part_2A` that month; Frimley (RDU) and Manchester
University (R0A) filed nothing in October and November 2022; Sheffield (RHQ) nothing in March 2026.

**In the panel itself the count of such rows is 0** **[measured]**, because the demand-row panel rule
already excludes any trust that ever missed filing referrals. The guard is kept because it becomes
load-bearing the moment the panel is widened.

---

# 6. Findings

### The removal rate validates against NHS

Our per-trust measurement reproduces NHS's published national rate to within half a percentage point
on both eras (trap 3). **This is the only external validation any number in this project has.** It
confirms `demand`, `completed` and `waiting` are constructed correctly, and that the panel is
representative enough to reproduce a national figure.

It also means **the leak is not a novel discovery**. It is a known, named, published NHS data
property. The project's contribution is measuring it **per trust x specialty**, which NHS does not
publish.

### The independent sector does not respond quickly

**Hypothesis tested:** public backlog rises, so work is bought from independent providers.

**[measured]** correlating the monthly change in independent share of demand against the change in
public backlog, across the 18 named specialties:

| Lag | Mean correlation |
|---|---|
| 0 months | +0.078 |
| 3 months | −0.015 |
| 6 months | −0.018 |
| 12 months | +0.008 |

Specialties with a positive correlation: **13 of 18 at lag 0, 5 at lag 3, 7 at lag 6, 10 at lag 12**
**[measured]**. Only lag 0 is meaningfully away from half, and it disappears immediately afterwards.

**No monthly substitution response.** The same-month figure is what joint determination produces:
commissioners buy independent capacity *because* waits are long, so both series respond to the same
pressure in the same month without either causing the other.

**What is real is the slow shift.** **[measured]** the independent share of ophthalmology moved from
**6.20% to 19.65%**, a change of **13.45 percentage points**, the largest of any specialty. Six of 24
specialties trend at more than 0.5pp per year **in absolute terms**, and that phrasing matters: two
of the six (`X03` and `X06`) are trending **downward**, so "6 specialties are shifting to the
independent sector" would be wrong. The next largest risers are Neurosurgery (+4.49pp), Dermatology
(+4.30pp) and General Surgery (+3.79pp); Gastroenterology moves the other way at -3.09pp.

**Inference, stated as such:** substitution operates on a multi-year contracting timescale. Consistent
with NHS placing the decision with ICBs and encouraging "long-term contractual relationships"
**[NHS: partnership agreement]**, but the causal direction is **not identified** by this test.

**A confounder fatal to the naive version of the question.** NHS directs independent capacity towards
"the most challenged specialties and geographies" **[NHS]**. So independent share rises *because* waits
are worst there. Share and backlog are **jointly determined**, and "share rose, trust demand fell,
therefore substitution" is observationally indistinguishable from "demand was high, so capacity was
bought".

**Limits.** National, not per ICB, because independent providers have **no ICB parent in ODS**, so
`icb` is 100% null for them. Local substitution could be real and invisible here. Month-on-month
differencing also rules out only a *fast* response, not a slow one.

### COVID collapsed demand harder than throughput

**[NHS]** March 2020 clock starts fell to 58,400 per working day from 85,100 a year earlier, **down
31%**; completed admitted fell 34%; non-admitted fell 14%. The waiting list **fell by 189,000** between
February and March 2020, because "while COVID-19 resulted in a reduction in completed pathways, there
was an even greater decrease in clock starts" **[NHS: Annual Report §1.2]**.

**So in the forecast target COVID is a V-shaped collapse and recovery, not a spike.** The spike is in
the long-wait tail: 52-week waiters went from 3,097 in March 2020 to **83,203 by July 2020**, a
27-fold rise in four months **[NHS]**.

**The clock rules did not change during COVID** **[NHS: C0009, 24 March 2020]**. Shielding and
self-isolating patients were treated as "temporarily unfit" and "the RTT clock should continue to
tick"; provider cancellations and suspended services likewise left clocks running. **The dynamics are
therefore real accumulation, not a redefinition**, which is what makes the COVID window usable as an
evaluation scenario.

**The collection was never suspended.** All 96 months exist.

---

# 7. Decisions taken, and the evidence for each

### Federation clients are the 126 public trusts

Independent providers report the same columns and genuine demand (**[measured]** 11,541,248 referrals,
**0 zero-months**), so this is not obvious. They fail on structure, and the reasons are documented
rather than argued:

| Requirement | Independents | Basis |
|---|---|---|
| Same reporting obligation | **No.** Mandatory for NHS trusts under the NHS Standard Contract; independents are "encouraged" | **[NHS: Annual Report §6.3]** |
| Submit their own data | **Not always.** "When Independent Sector providers do not have the technical capability to submit data, NHS commissioners can submit on their behalf" | **[NHS: §6.3]** |
| Covered by NHS missing-data estimates | **No.** Acute NHS providers only | **[NHS: §6.3]** |
| Have an ICB parent for escalation | **No.** `icb` is 100% null for them | ODS `RE5` |
| Can receive an allocation | **No.** An ICB can buy from them, not direct NHS staff and capital into one | design |
| Report the same construct | **No.** Only NHS-*commissioned* care appears; private-pay work is invisible | **[NHS: §10.1.1.1]** |

Note what does **not** justify the decision: **[measured] 126 independents also span all 96 months**,
exactly as many as the 126 public trusts. An earlier version of this project claimed the
balanced-panel rule performed the sector filtering by itself. **It does not.** An explicit sector
filter does.

**Adding them would also damage the framing.** Cross-silo federated learning assumes few, large,
reliable institutional clients. Adding 457 small, irregularly-reporting providers moves the setting
toward cross-device heterogeneity, a different research problem with different baselines, entered by
accident rather than by design.

**The inclusion question remains a pre-registered ablation**, not a closed argument: score on the
fixed 126-trust series in both arms so the metric population does not change, and pin aggregation
weighting to n-samples.

### Independents stay in the canonical table

They are the "buy" half of the allocate-or-buy decision. Filtering at build time would bake in a
choice that should stay reversible and visible. `sector` is a flag, never a filter.

### Keep all 96 months

COVID is roughly **19 to 22% of every 96-point series**, and per-client scaling statistics computed
over a window containing the shock are distorted for all ~1,870 series. That concern is legitimate,
and it was raised by the previous supervisor.

But it is a **training-set** problem with a **training-set** answer. The forecaster is trained; the
agentic layer is not, being a state machine over forecasts and thresholds. COVID can be excluded from
forecaster training while retained as the agent's evaluation scenario. Every genuine remedy, split
placement, a regime indicator, sample weighting, scaling on a declared clean sub-window, requires the
data to be present. Deleting it removes the ability to *demonstrate* the concern was handled, which is
the question a reviewer will ask.

Cutting also buys less than it appears: the February 2024 break and the October-to-December 2022
non-submissions sit inside every candidate post-COVID window.

### 19 series, 15 columns, ICB from ODS

- **19 series** so the tiers reconcile to 100% of demand rather than 74.4%.
- **15 columns**, each with a named consumer, decided by measurement.
- **`icb` from the ODS `RE5` relationship**, not from the file's parent column, which is a DCO, then
  an STP, then an ICB. This makes the hierarchy **time-invariant by construction**: every month is
  attributed to the trust's present-day ICB. Correct for simulating today's escalation; **wrong for
  any historical ICB-level claim**, which must say so.

---

# 8. Roadmap

**Complete.** Acquisition, validation, cleaning, the column contract, the integrity baseline.

**Next, in order. Do not skip step 2.**

1. **Exploratory analysis.** Nobody has done this. Seasonality per specialty; whether the seasonal
   shape survives COVID or breaks permanently; which specialties recovered to trend and which never
   did; client heterogeneity using **p90/p10 rather than max/min**, since max/min over a two-month
   provider and a 22-referrals-a-month minnow gave a meaningless 1,435x on an earlier pass.
2. **Baselines, before any model.** Persistence first. Establish the number every later result must
   beat, and implement the `usable` mask at the same time so no baseline is scored on constant-zero
   series.
3. **The federated forecaster.** Windowing; a **temporal** split, never random, or the model sees the
   future of a series it is tested on and produces excellent meaningless results; a declared decision
   on where COVID goes; per-client scaling; FedAvg; an explicit and reported weighting choice;
   per-client fine-tuning. Against all three baselines.
4. **The agentic layer.** State vector, gap classification, escalation, board decision, release.
   **Must carry an explicit removal term**, split rather than modelled as a single loss rate.

### Open questions

Genuinely open. No target numbers, because nobody has computed one.

1. **The February 2024 break is measured but not isolated.** **[measured]** the step is −29,179 in
   `X_OTHER` at 1.24x local variation, and January to March 2024 falls 52,849 against NHS's stated
   ~43,000. Separating the real removal from ordinary seasonal movement needs a counterfactual nobody
   has built. Note the step is *smaller relative to local noise* than the 2021-04 steps we assert
   against, so the continuity assert would not have caught it.
2. **No ICB mapping for independent providers**, so the local substitution test cannot be run at all.
   A dataset limit, not a task.
3. **The residual ~26% post-2021 disagreement** between the file's parent column and ODS has never
   been chased on a sample of disagreeing trusts.
4. **KH03.** 61 workbooks, validated, consumed by nothing. Give them a role or drop them. Note the
   resolution mismatch: quarterly and per trust, against monthly and per trust x specialty.
5. **Is independent-sector growth general or concentrated?** Ophthalmology is fastest. Is that drift
   across the board, or one specialty carrying it?
6. **Comment density** in `02_inspect_dataset.ipynb` stands at roughly 28% against the project standard.

---

# 9. How to run it

Everything runs from `src/`, because the notebooks use paths relative to it.

**Environment.** This laptop: Python 3.12.10 with `pandas`, `pyarrow`, `requests`, `beautifulsoup4`,
`matplotlib`, `jupyter`, kernel registered as `python3`. The original work used a Linux box with a
virtualenv at `fed_learning/` and an A100 (MIG-partitioned). **That is where training belongs**, and
`CLAUDE.md` documents its constraints, including that MIG instances cannot do peer-to-peer or
multi-GPU collectives, so simulated federated clients run sequentially rather than across GPUs.

**Run a notebook headless**, which is how all three were last executed:

```
cd src
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3 03_data_processing.ipynb
```

Takes 5 to 20 minutes each. Output goes to `logs/`. A failed cell aborts the run and writes nothing,
so an unchanged notebook after a run means it failed.

**Order matters:** `fetch`, then `inspect`, then `data_processing`. The middle one builds
`provider_census.csv`, which the third reads.

**Two things that will catch you out.**

1. While a notebook runs headless, **the file on disk still shows the old outputs**; it is rewritten
   only at the end. If it is open in an editor at that moment, **do not save**, or you will overwrite
   the results with the stale copy. That has already destroyed a run's evidence once here.
2. `01_fetch_dataset.ipynb` is safe to re-run. It skips completed downloads and writes each file to a
   temporary name renamed only on completion, so a finished filename always means a finished file.
   This is the one place a safety net is permitted in this project, and for a data reason rather than
   a coding one.

---

# 10. Where to look

| File | Contains |
|---|---|
| `PROGRESS.md` | this briefing |
| `RTT_SOURCE_DOSSIER.md` | **the reference.** What NHS says about the collection, 13 sections, every claim cited to their documents |
| `README.md` | the problem statement and the canonical schema |
| `WORKLOG.md` | the lab notebook, 25 entries, including every mistake and every retraction |
| `CLAUDE.md` | working conventions. Read before writing anything |
| `GUIDE.md` / `.pdf` | see the warning below |
| `data/reference/findings.csv` | 17 findings, generated by code. Non-contiguous ids |

**A warning about `GUIDE.md`.** It was written to teach the previous owner by making him derive things
himself: it sets traps without disclosing them, covers target numbers, and gates tasks behind written
notes. As a *reference* it will cost you time. Its genuinely useful part is **Appendix E**, the exact
band-to-day mapping and the per-column dictionary.

---

## How to read a number in this project

Three rules, each learned by getting it wrong.

1. **Say which denominator.** 15.40% and 15.27% are the same leak, mean-of-ratios and ratio-of-means.
   17% and 15% are the same leak on removals and on demand. An unlabelled percentage is not a number.
2. **A test passed by a wide margin has not been passed.** A boundary check once reported 6.60x against
   a 10x threshold and was accepted; the statistic itself was wrong and the true value was 1.26x.
   Equally, a check that fails *everything* is as suspect as one that passes everything, and that has
   also happened here.
3. **Every provider count comes from `provider_census.csv`, on its stated definition.** A count
   computed ad hoc from another table is a different question wearing the same words.

**Ask about anything here.** Nothing in this document matters more than you being able to defend it.
