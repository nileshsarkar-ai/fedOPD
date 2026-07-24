# Understanding the NHS RTT Dataset

### A source-grounded working guide for fedOPD - read it, then write the code yourself

---

## How to use this

This document explains **what the data is** and **what the project is trying to do with it**. It contains no analysis code. That is yours to write, and writing it is the point.

**Who this is written for.** A technically strong undergraduate doing their first piece of real research. That has two consequences for how this guide is pitched. First, it does not dumb anything down: the detail is deliberate, because in research the detail is where the result lives, and a claim you cannot source or reproduce is not yours. Second, it forces notes. First research is judged not on whether the code ran but on whether you can defend every number in it months later, in front of someone who will push. The notes are that defence. They are not optional, and they are not admin. They are the deliverable that the previous version of this project lacked.

Every section ends with **tasks**. Each states what to find and, where a definite answer exists, **the number you should get**. That number is the whole mechanism: you write the code, run it, compare. If you match, you understood it. If you don't, the gap between your number and the target tells you exactly what you missed - and working that out yourself is worth more than being handed the line that would have worked.

Do not look in `src/_solutions/`. Those archived notebooks exist so a number can be checked when everything else has failed. Reading them costs you the exercise.

### Two kinds of fact live in this guide, and they are marked differently

This matters, because the whole project runs on keeping observation separate from assumption.

1. **What the data *is*** - definitions of columns, part types, bands, schema changes. These are **not** from memory. Every one carries a bracketed citation to the NHS England document it came from, e.g. **[G §10.1.7, p.46]**. If a claim about the data has no citation, treat it as unverified. The citation keys are in the next section.
2. **What *this project* measured** - 653 providers, 322,531 rows, the accounting-identity leak. These are **your targets**, reproduced from the CSVs. They are labelled "measured" or "target". They are not NHS-published figures, and you should be able to re-derive every one.

Where an NHS-published headline and your CSV-derived number **disagree**, that is a finding, not an error - see Part 5 and Part 11 on the estimate for non-reporting trusts.

### The loop to work in

1. **Look at the thing.** Print ten rows. Print the column names. Print the distinct values of any column that has few of them. Before any hypothesis.
2. **Say what you expect**, in a markdown cell, *before* you measure. "There should be about 200 trusts." The written-down expectation is what makes being wrong informative.
3. **Measure it.**
4. **When it disagrees with you, believe the data** - but first check you measured the thing you meant to. Most disagreements are a bug in the question, not a surprise in the world.
5. **Write the note.** What you expected, what you got, what the gap was, what you now know. `NOTES.md`. Every task. No exceptions. A result you cannot explain is not a result you have.

### The note gate, stated once and applied everywhere

Every task below ends in a target number. **A task is not finished when the number matches. It is finished when the note is written.** The note has four parts, and all four are required:

1. **Expected** - the number or shape you committed to *before* running it.
2. **Got** - the actual output.
3. **Gap, and why** - if they differ, what was actually wrong: your mental model, your query, or your assumption about the data. "Off by a bit" is not a diagnosis.
4. **Now know** - one or two sentences on what you understand now that you did not. If this is blank, you have not finished the task, you have only run it.

Do not batch these. Write the note before moving to the next task, while the surprise is still fresh, because the value is in the gap between prediction and result and that gap is gone once you have moved on. Where a task hides a trap, the note is where you prove to yourself you understood the trap and did not just step around it.

### Do not blind-read this

Reading this guide cover to cover and nodding along will teach you almost nothing. The words are cheap; the doing is where the learning is. Treat the whole document as a set of prompts to act on, not prose to absorb.

- **Cover the target before you read it.** Every task ends in a number. The instant you see it before predicting, the task is spent - you can no longer be surprised, and surprise is the mechanism. Predict first, in writing, then reveal.
- **Try before you look.** When a section sets a trap ("one of these codes is not a specialty"), stop and go find it in the data yourself before reading the paragraph that explains it. Finding it costs you twenty minutes; reading it costs you the lesson.
- **Open a notebook, not just this file.** If you have read more than two pages without running a single query, stop and go measure something. This guide is meant to be read with a kernel running beside it.
- **Rebuild from memory.** After a part, close this document and re-derive its main idea - the identity, the schema break, the zero-fill trap - from scratch. If you cannot, you read it; you did not learn it. That is the signal to go back, not to push on.
- **Being stuck is the work, not a failure of it.** The struggle before you look something up is exactly where the capability forms. Do not shortcut it by reading ahead.

If you find yourself just reading, you have stopped learning. Put the guide down and go break something in a notebook.

---

## The sources this guide is grounded in

Everything factual below is cited to one of these. All were retrieved and read directly from NHS England / NHS Digital for this guide - not recalled. Page numbers are the printed page of the PDF.

| Key | Document | What it grounds | Location |
|---|---|---|---|
| **[G]** | *Recording and reporting referral to treatment (RTT) waiting times for consultant-led elective care*, v5.2, publication ref **PRN01045**, NHS England (formatting rev. 14 Oct 2025; substantive content Feb 2025) | The definitive statement of what each part type, column and band means, the collection mechanics, the clock rules, the treatment-function list, and the schema changes | [PDF](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/10/Recording-and-reporting-RTT-waiting-times-guidance-v5.2-Feb25.pdf) |
| **[SPN]** | *Statistical Press Notice - NHS referral to treatment (RTT) waiting times data, March 2026* (published 14 May 2026), NHS England | The published national figures, the estimation method for non-reporting trusts, the "Notes for editors" restatement of the collection and its April-2021 and Feb-2024 changes | [PDF](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Mar26-RTT-statistical-press-notice-PDF-545K-Dc1i9U.pdf) |
| **[DD]** | *NHS Data Dictionary - Attribute: TREATMENT FUNCTION CODE* (Aug 2024 release) | What a treatment function code is, and how it differs from a main specialty code | [HTML](https://archive.datadictionary.nhs.uk/DD%20Release%20August%202024/attributes/treatment_function_code.html) |
| **[DD-T]** | *NHS Data Dictionary - Main Specialty and Treatment Function Codes Table* | The full code list, including every sub-specialty that folds into an "Other" bucket | [HTML](https://archive.datadictionary.nhs.uk/DD%20Release%20August%202024/supporting_information/main_specialty_and_treatment_function_codes_table.html) |
| **[SWA]** | *Referral to Treatment (RTT) Waiting Times* statistics work area, NHS England | The monthly file inventory (what is published each month) and the revisions timetable | [page](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/) |
| **[DCB0095]** | *DCB0095: Consultant-led referral to treatment (RTT) waiting times* (NHS Digital data standard) | The formal data-collection standard behind the monthly return and the April-2021 change | named in [SPN §4]; standard on NHS Digital |
| **[DCB0028]** | *DCB0028: Treatment Function and Main Specialty Standard* | The authoritative treatment-function code specification and its grouping rules | named in [G §10.1.4] |

The one thing **not** yet retrieved from source: **DCB0095** and **DCB0028** were named by the documents above but their own text has not been pulled - where this guide relies on them it relies on [G]'s and [SPN]'s summaries of them, and says so.

---

<div class="remind">Two engines, one job each. In a single sentence: what does the forecaster hand over, and what does the agent do with it? Fuzzy here means a table that fits neither.</div>

# Part 0 - What the project is

You are building two things that connect.

### The forecaster

Every hospital needs a demand forecast per department to plan capacity. A single central model is both impossible and inadequate: hospitals will not pool raw activity data, and they differ enormously in size and casemix - yet their demand moves together, so there *is* shared structure worth learning jointly.

**Cross-silo federated learning** is the answer to exactly that. Each hospital is a client that trains a shared neural forecaster by exchanging model updates, never raw data, then fine-tunes locally so the global model does not flatten local differences.

It is measured honestly against three baselines, and you should be suspicious of any result that skips one:

1. **Persistence** - next month equals this month. A hard naive baseline, not a strawman. Monthly hospital demand is highly autocorrelated and persistence is surprisingly hard to beat.
2. **Isolated per-hospital training** - does federating actually beat each site going it alone?
3. **Pooled central training** - the privacy-violating ceiling. Federation should approach it, not exceed it.

### The agentic decision layer

A forecast plans nothing. The second half converts forecasts into action. For each trust × department the system holds an operational state - forecast demand in, trailing throughput out, backlog stock, the bed-linked admission queue, the >18-week breach count - glued by an accounting identity. It compares forecast demand against capacity, projects the backlog against the 18-week standard, classifies any shortfall as **transient, sustained, or regime change**, and on a sustained gap raises a structured capacity request up the real NHS hierarchy: **trust → ICB → national**.

The ICB tier is human-in-the-loop. The board sees the evidence and approves, refuses, or defers - and its view is two-sided, because the data is: internal trust capacity, plus the independent sector's volume in that ICB as *purchasable* substitution capacity. That is the allocate-or-buy decision made concrete. De-escalation is symmetric: gaps that stay closed release their allocation.

The **18-week standard** the agent projects against is a real legal one: NHS providers and commissioners must meet patients' "legal right to start consultant-led non-emergency treatment within a maximum of 18 weeks from referral" **[G §1.1, p.5]**. The specific operational standard is that **92%** of incomplete pathways are within 18 weeks - since 2015 this incomplete-pathway measure is "the sole measure of patients' constitutional right to start treatment within 18 weeks" **[G §1.1, p.5]**.

### What is deliberately out of scope

- **The currency is operational, not financial.** Treatments, queues, waiting-time standards. There is no money in this data, so there are no cost claims.
- **Capacity is requested in treatments per month**, split admitted vs non-admitted - never in literal beds. The data does not contain beds per specialty.
- **COVID is inside the window on purpose.** It is the built-in stress test: the forecaster must survive it, and the agent is *evaluated* on it - detect the collapse, escalate through the recovery, normalise afterwards.

---

<div class="remind">You are about to build eight years of conclusions on 96 files you have not opened. Open one. Look before you trust.</div>

# Part 1 - How the data got here, and what is on disk

```
data/
  rtt_csv/     96 CSV files, ~8.2 GB, one per month, April 2018 to March 2026
  reference/   provider lookups built from the NHS ODS API
  kh03/        61 quarterly bed-availability workbooks
```

### What the data actually is, before what the notebook did

The monthly Full CSV is an **aggregate return, not patient records**. NHS England describes the collection plainly: *"The national data collection looks at RTT waiting times in weeks, split by treatment function. Returns are submitted by providers, split by commissioner"* **[G §10.1.1.2, p.40]**, and *"The data collection is provider and commissioner based"* **[G §10.1.1.1, p.40]**. Providers fill in a spreadsheet form in NHS England's **Strategic Data Collection Service (SDCS)** portal and upload it; there is functionality that "allows for CSV import of the data" **[G §10.1.2, p.42]**. So one row is never a patient - it is a **count of RTT clocks** in one state, for one provider × commissioner × treatment function × part type, spread across the weekly-band columns.

Two consequences worth carrying from the start:

- Because the return is provider-by-commissioner, the raw file has **multiple rows per provider × treatment function × part type** - one per commissioner. That commissioner split is the only genuine second dimension in the file (Part 6).
- Independent-sector providers are **in scope of the same collection**: where NHS care is commissioned from them, they "should engage in the RTT data collection process … in the same way as NHS provider organisations" **[G §10.1.1.1, p.40]**. So independent rows are real submitted data, not an artefact (Part 5).

### What `fetch_dataset.ipynb` did

Acquisition is the one part already written. Read it - it is short, and it is the model for the commenting standard the rest of your code should meet.

1. **Scraped eight NHS England financial-year pages** (`rtt-data-2018-19` through `rtt-data-2025-26`), collecting the link to each month's *Full CSV* extract. Where NHS published a **revised** version of a month, the revised one wins.
2. **Downloaded each archive to a `.part` file and renamed it on completion.** This is the one place a safety net is allowed in this project, and for a data reason rather than a coding one: a rename is atomic, so a half-downloaded file can never be mistaken for a complete one and reruns resume cleanly.
3. **Extracted the CSVs**, then verified them against the archives before the archives were deleted.
4. **Built the provider reference from the NHS ODS ORD API.** The RTT file gives you a provider *code* and nothing about what kind of organisation it is. ODS gives each code a primary role and its relationships. This is the only way to know which providers are NHS trusts.
5. **Fetched the KH03 bed workbooks.**

### What NHS England publishes each month, and how it is revised

For each month NHS England publishes, alongside the **Full CSV data file** (a ZIP), eight Excel views - a **Commissioner** and a **Provider** version each of *Incomplete*, *Admitted*, *Non-Admitted* and *New Periods* **[SWA]**. The commissioner files "include aggregations of waiting times by sub-ICB, ICB, region and England as a whole" **[SPN p.2]**. The project uses the Full CSV because it is the un-aggregated provider × commissioner × treatment-function × part-type table; the Excel views are pre-aggregated slices of it.

**Revisions.** "Data revisions are normally published every six months (generally in January and July), alongside the latest release of new monthly data" **[G §10.1.6, p.46]**. This is why a month can appear twice on a financial-year page (original + revised) - and why the acquisition rule *revised supersedes original* is correct.

**Submission timetable, for context on how fresh a month is.** The provider deadline is "13 working days after the final day of the reference period, and the commissioner assurance deadline is 18 working days after the end of the reference period" **[G §10.1.3, p.43]**.

### The reference tables, one by one

| File | What it holds |
|---|---|
| `provider_census.csv` | **The authoritative provider table.** One row per provider code ever seen: name, first/last month, months present, ODS primary role and role name, active/retired status, sector, ICB parent, panel membership. Every provider count in this project should come from here. |
| `provider_types.csv` | Raw ODS role lookup per code. |
| `trust_icb.csv` | Trust → ICB, resolved through the ODS `RE5` relationship, plus postcode. |
| `provider_month_demand.csv` | Demand per provider per month, with the stated parent. |
| `tf_month_demand.csv` | Demand per treatment function per month. |
| `specialty_sector_month.csv` | Public vs independent demand per specialty per month, and the independent share. |
| `monthly_summary.csv` | One row per month: rows, providers, parents, commissioners, treatment functions, demand, waiting. |
| `findings.csv` | The `F-…` findings from the previous build. **Do not read this until you have done the exercises** - it is the answer key. |

### The ODS API, since you will need it again

`https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{code}` returns an organisation record. The two things that matter:

- **`PrimaryRoleId`** - what kind of organisation it is. `RO197` NHS Trust, `RO107` Care Trust, `RO261` ICB, plus various independent-sector roles.
- **`Rels`** - its relationships. The one you want is **`RE5`, "is commissioned by"**, whose target is the commissioning parent. An active `RE5` pointing at an `RO261` gives you the trust's ICB.

That independent providers should hold an ODS code at all is required by the collection: NHS expects RTT submitters to use "an NHS Trust, Independent Sector Healthcare Provider, Independent Sector Healthcare Provider Site or NHS Care Trust ODS … code" **[G §10.1.1.1, p.40]**. Note that ODS describes the organisation **as it is now** - it has no history. That limitation drives a real decision in Part 7.

### KH03 - downloaded, validated, and used by nothing

61 quarterly Excel workbooks of overnight bed availability and occupancy per trust. They were fetched because the admitted pathway is bed-constrained, so beds are the obvious capacity denominator for `Part_2A`.

They have never been joined to anything. **This is a live open question, not a settled exclusion** - see Part 11. Note in advance that KH03 is *quarterly and per trust*, while RTT is *monthly and per trust × specialty*, so any join costs you resolution on both axes. Whether that trade is worth making is for you to decide with a measurement, not a preference.

<div class="remind">96 is the easy part. The trap is a month that is missing, or one that shows up twice as original-plus-revised. Predict where a gap or a double could hide before you trust your count.</div>

### Task 1.1
How many files are there, and does each month from April 2018 to March 2026 appear exactly once? The filenames are inconsistent - some carry a date prefix, some say `-revised`, capitalisation of the month name varies. Parse the month out of the filename; do not trust sort order.

> **Target: 96 files, 96 distinct months, no gaps, no duplicates.** (Measured on this project.)

<div class="remind">Plot it and look before you read Part 4. Seeing the April 2021 cliff yourself, and not yet knowing why, is worth more than being told. Do not spend that for free.</div>

### Task 1.2
Plot file size against month.

> You should see a **step up around April 2021**. That step is the most important structural fact in this dataset. Do not read ahead - see it first, then form a guess about what changed.

---

<div class="remind">Get the grain wrong here and every groupby downstream is quietly counting the wrong thing. Say out loud what one row is before you move on.</div>

# Part 2 - What one row means

### The RTT clock - grounded in the rules

A patient is referred to a hospital service; that starts an **RTT clock**. NHS's own general principle: once a clock has started "it continues to tick until: the patient starts first definitive treatment, or a clinical decision is made that stops the clock or the patient declines treatment" **[G §2.1, p.8]**.

- **Clock start (rule 1).** "A waiting time clock starts when any care professional or service permitted by an English NHS commissioner to make such referrals, refers to a consultant-led service" **[G §2.2 / §3.2, p.8, 11]**. For referrals not via the NHS e-Referral Service, "the clock starts on the date that the referral is received by the provider organisation" **[G §3.2.1, p.12]**.
- **Clock stop for treatment (rule 4).** "A clock stops when first definitive treatment starts" **[G §4.3, p.17]**, where first definitive treatment is "an intervention intended to manage a patient's disease, condition or injury and avoid further intervention" **[G §4.3.1, p.17]**.
- **Clock stop for 'non-treatment' (rule 5).** A clock also stops on a communicated clinical decision not to treat, on a decision to start **active monitoring** ("a period of monitoring in secondary care without clinical intervention" - the clock stops **[G §13, p.56]**), on a DNA that meets the conditions, or when the patient declines treatment **[G §4.4, p.20]**.

That distinction - clocks stop for treatment **and** for several non-treatment reasons - is exactly why the accounting identity in Part 9 leaks. Not everything that leaves the waiting list is a completion.

### The grain of a row

> *For this **provider**, commissioned by this **commissioner**, in this **treatment function**, in this **part type** - here are the counts.*

| Column | What it is | Source |
|---|---|---|
| `Provider Org Code` | **Who delivered the care.** An NHS trust or an independent provider. In fedOPD, a **federated client**. | [G §10.1.1.1] |
| `Provider Parent Org Code` | The organisation the provider sits under. **Changes meaning over time** - Part 7. | - |
| `Commissioner Org Code` | **Who paid.** A different axis entirely from who delivered. Assigned by NHSE-code / `NONC` / SUB-ICB rules **[G §10.1.8, p.47]**. | [G §10.1.8] |
| `Treatment Function Code` | **The specialty.** In fedOPD, a **department**. "A unique identifier for a TREATMENT FUNCTION … a division of clinical work based on main specialty" **[DD]**. | [DD], [G §10.1.4] |
| `RTT Part Type` | **Which question this row answers.** Five values. | [G §10.1.1.2] |

### The five part types - verbatim from the collection template

The single most important table in this document. NHS defines the collection template as being "in three sections" **[G §10.1.1.2, p.40]**, which surface in the CSV as these five part types. Quoted from **[G §10.1.1.2, p.41]**:

| Part type | NHS definition (quoted) | In fedOPD | Stock/flow |
|---|---|---|---|
| `Part_1A` | "cases where patients completed their RTT pathway during the month with an inpatient or day case admission" | throughput (admitted) | flow |
| `Part_1B` | "cases where patients completed their RTT pathway during the month for reasons other than an inpatient or day case admission" | throughput (non-admitted) | flow |
| `Part_2` | "cases where patients are still waiting to start treatment at the end of the reporting month. This is a 'snapshot' on the last day of the reporting period" | **the waiting list / backlog** | **stock** |
| `Part_2A` | "cases where patients are still waiting to start treatment at the end of the reporting month where a clinical decision to admit to a hospital bed for treatment has been made" | the bed-linked queue | **stock, subset of `Part_2`** |
| `Part_3` | "Number of new RTT periods during the month" | **demand - the forecast target** | flow |

Two things the definitions nail down that you will otherwise get wrong:

- **`Part_2A` is a subset of `Part_2`, not an addition.** NHS states it directly: "The difference between the values submitted for this data item and for total incomplete pathways equates to the number of incomplete pathways *without* a decision to admit" **[SPN §4, p.13]**. So `waiting_dta ≤ waiting` must hold - Task 6.3.
- **`Part_3` counts clock-starts, and is gross not net.** "RTT pathways where the clock start date is within the reporting month. This will include those where the clock also stopped within the reporting month" **[SPN §4, p.13]**. So a pathway opened and closed in the same month still counts as demand.

`Part_2` is a stock (how many are waiting *right now*); `Part_1A`, `Part_1B`, `Part_3` are flows (how many arrived or left *during* the month). Adding a stock to a flow is meaningless, and nothing in the file stops you.

### The measure columns

- `Total All` - the headline count for the row.
- `Total` - also present. Do not assume it means the same thing (Task 2.3).
- `Patients with unknown clock start date` - "in the unlikely event that the provider may not be able to accurately identify the RTT clock start date, patients can be reported on the RTT return in the 'unknown clock start' column" **[G §10.1.5, p.45]**. A small residual, and one of NHS's own data-quality checks flags a "large proportion of patients with an unknown clock start" **[G Annex B, p.64]**.
- A long run of `Gt 04 To 05 Weeks SUM 1`-style columns - a **waiting-time histogram**, defined precisely in Part 4 and Appendix E.

<div class="remind">Five part types, and you will lean on the difference for the whole project. Predict how many rows each has. If one of them behaves oddly, chase it now, not later.</div>

### Task 2.1
Read one month. Rows? Distinct providers, commissioners, treatment functions? Confirm exactly five part types.

<div class="remind">One part type's bands sum to exactly zero, and it is not a bug. Reason out which from meaning alone. Reach for the code first and you have skipped the actual question.</div>

### Task 2.2
For each part type separately, does `Total All` equal the sum of the week-band columns?

> **One part type sums to exactly zero.** Work out *why* from the meaning of that part type - it is not a data error. (Grounding: read the `Part_3` definition above and ask what a brand-new clock has "waited".) Two others give 0.999× rather than 1; work out what the missing 0.1% is (the `unknown clock start` residual is the tell - **[G §10.1.5]**).

<div class="remind">Predict which three are zero before you sum. The interesting part is not that they are zero, it is why the other two are not.</div>

### Task 2.3
Sum `Total` and `Total All` by part type.

> **`Total` is identically zero for three of the five.** Which three - and which column does that make safe to build on?

<div class="remind">This is the trap that hands you exactly double the England waiting list and lets you ship it looking clean. Find the fake code yourself. Reading the answer only teaches you how to be fooled quietly.</div>

### Task 2.4
Look at the distinct `Treatment Function Code` values. One is not a specialty.

> Find it. NHS's own monthly validation includes a check on "**incorrect totals - where the total is a sum over all treatment functions**" **[G Annex B, p.64]** - so a total-over-all-treatment-functions row is a thing NHS itself computes. Then: summing `Total All` for `Part_2` across the March 2026 file, do you get the England waiting list or exactly twice it? Your CSV-derived target is **7,045,510**. If you get **14,091,020**, you have found the trap - now state precisely what it is, and why it is *exactly* double rather than merely too big.
>
> Note for later (Part 5): **7,045,510 is the raw-CSV sum and is not the same as the published "7.1 million" headline** - the headline includes an estimate for a trust that did not submit. That is not your error; it is by construction **[SPN p.1]**.

---

<div class="remind">Eighteen named specialties, and a quarter of all demand hiding inside 'Other'. Build on the eighteen, call it the whole, and you are off by 25% with nothing flashing red.</div>

# Part 3 - The treatment functions, from the collection form

The RTT return does **not** collect every specialty separately. NHS lists exactly the treatment functions a provider must report on the spreadsheet form, verbatim **[G §10.1.4, p.43–44]** - 18 named services, then five "Other" buckets. "The 18 treatment functions listed out separately on the spreadsheet form were chosen as they were high volume areas with a large volume of RTT pathways" **[G §10.1.4, p.44]**.

| Code (form) | NHS name **[G §10.1.4]** | Specialty | % of all demand (measured) |
|---|---|---|---|
| `130` | Ophthalmology Service | Ophthalmology | 9.85 |
| `110` | Trauma & Orthopaedics Service | Trauma and Orthopaedics | 9.80 |
| `502` | Gynaecology Service | Gynaecology | 6.98 |
| `100` | General Surgery Service | General Surgery | 6.42 |
| `330` | Dermatology Service | Dermatology | 6.29 |
| `120` | Ear, Nose & Throat Service | ENT | 6.14 |
| `301` | Gastroenterology Service | Gastroenterology | 5.29 |
| `101` | Urology Service | Urology | 5.04 |
| `320` | Cardiology Service | Cardiology | 4.70 |
| `140` | Oral Surgery Service | Oral Surgery | 2.99 |
| `340` | Respiratory Medicine Service | Respiratory Medicine | 2.72 |
| `400` | Neurology Service | Neurology | 2.40 |
| `410` | Rheumatology Service | Rheumatology | 1.93 |
| `160` | Plastic Surgery Service | Plastic Surgery | 1.35 |
| `300` | General Internal Medicine Service | General Internal Medicine | 0.99 |
| `150` | Neurosurgery Service | Neurosurgery | 0.67 |
| `430` | Elderly Medicine Service | Elderly Medicine | 0.64 |
| `170` | Cardiothoracic Surgery Service | Cardiothoracic Surgery | 0.18 |
| `X01` | Other *(single bucket, pre-2021 form only)* | Other | 8.41 |
| `X02`–`X06` | Other, five themed buckets *(post-2021 form)* | Other | 17.19 combined |

(Percentages are **measured** from `tf_month_demand.csv`, not from NHS. The 18 codes and their names are from **[G §10.1.4]**.)

### The "Other" buckets, and what falls into them

The five post-2021 buckets are, verbatim **[G §10.1.4, p.44]**:

- `X02` **Other – Medical Services** - "All other TREATMENT FUNCTIONS in the Medical Services group not reported individually"
- `X03` **Other – Mental Health Services**
- `X04` **Other – Paediatric Services**
- `X05` **Other – Surgical Services**
- `X06` **Other – Other Services**

So high-profile specialties that are *not* in the named 18 - e.g. **800 Clinical Oncology, 302 Endocrinology, 303 Clinical Haematology, 810 Radiology, 840 Audiology, 715 Old Age Psychiatry** and dozens more in the full code list **[DD-T]** - are not missing; they are **inside these Other lines**. That is why the Other buckets are ~25% of demand: they carry every specialty outside the top 18.

### The roll-up exceptions - codes you will *not* see separately, by rule

NHS folds several specific codes into a named one **[G §10.1.4, p.45]**:

- **Spinal Surgery (108), Orthopaedic (111), Trauma Surgery (115) → reported inside Trauma & Orthopaedics (110).**
- **Maxillofacial Surgery (144), Oral & Maxillofacial Surgery (145) → reported inside Oral Surgery (140).**
- **Cardiothoracic (170)** may be reported as 170, "or an aggregation of 172 (Cardiac) and 173 (Thoracic)."
- Sub-specialties like 306/307/308/309 "are all within the Medical Services group and should therefore be included in the 'Other – Medical Services' line" **[G §10.1.4, p.45]**.

This is why those codes do not appear as their own series - by design, not omission. It also tells you the named specialties are already **aggregates** at their reported level.

Two things to carry forward, both of which matter later:

- **The `X` buckets are not small - ~25% of all demand (measured).** Any analysis restricted to the 18 named specialties covers roughly 74% of activity - fine as long as you say so, fatal if you claim it is the total. That is why the project carries a 19th merged `X_OTHER` series.
- **The specialties differ by more than fifty-fold in size (measured).** Cardiothoracic is 0.18% of demand; ophthalmology 9.85%. Any cross-specialty average is a weighting choice.

---

<div class="remind">This one break silently misaligns everything that crosses it. Before you touch a band, be able to say why you can turn fine into coarse but never the reverse.</div>

# Part 4 - April 2021: the schema break, from NHS's own change list

Files before it have **69 columns**; from it, **121** (measured). The changes were made deliberately, and NHS lists them. From **[G §10.1.1.3, p.42]** and restated in **[SPN §4, p.13]**, three changes landed at once for April 2021 data:

1. **"Phased out the use of X24 code entirely and moved to the more granular NHS England commissioning codes."** The commissioner axis got finer - previously everything NHSE-commissioned sat under one code `X24`.
2. **"Additional weekly time bands from 52-53 weeks to 104+ added to Parts 1A, 1B, 2 and 2A of the collection."** The long-wait tail went from one column to weekly bands.
3. **"Changes to the treatment function categories"**: (a) treatment-function **name** updates, and (b) the single **"Other" category split into five** (X02–X06).

### Change 1 (for us): the long-wait tail

Before: everything over 52 weeks in one column, `Gt 52 Weeks SUM 1`. From April 2021: weekly bands 52→53, 53→54, … 104, plus `Gt 104 Weeks` **[G §10.1.1.3, p.42]**.

Bands **below** 52 weeks are identical in both eras (measured). Reason it through: you can always turn fine into coarse by adding up, never coarse into fine. So any metric spanning the window must reconcile to the **coarser** form. This is why the 18-week metric is safe across all 96 months and the 52-week metric needs an explicit era branch.

### Change 2 (for us): the "Other" specialties

One residual code `X01` before; five themed buckets `X02`–`X06` after (**[G §10.1.4, p.44]**; the pre-2021 single "Other" is the un-split predecessor). Same shape, same rule: merge back to one series.

### Change 3, the trap: the renaming

At the same break NHS renamed treatment functions - the form names carry "Service" and other wording that the pre-2021 files did not. **The codes did not change** (compare the code column of **[G §10.1.4]** against an old file). The project measured **18 of 24 codes renamed**.

So grouping by name - or worse, by code *and* name together - silently splits every specialty into a 36-month row and a 60-month row. Neither looks wrong. Both are. **The rule: join on codes, never names.** It generalises: the same drift hits provider parent organisations (Part 7).

### The exact band definition - this is what "> 18 weeks" *means*

Do not guess the boundary convention; NHS states it in days **[G §10.1.7, p.46]**:

- Bands are "0-1 weeks, >1-2 weeks, >2-3 weeks, then for all weekly time bands through to >103-104 weeks, >104 weeks."
- "**0 to 1 weeks includes patients waiting/having waited 0, 1, 2, 3, 4, 5, 6 and 7 days**" - eight days in the first band.
- "**17 to 18 weeks includes … 120, 121, 122, 123, 124, 125 and 126 days.**"
- "**A patient who has waited exactly 18 weeks (126 days) is included in the 17-18 weeks time band.**"
- "**51 to 52 weeks includes … 358 … 364 days**"; "**104+ weeks includes … 729 days and more.**"
- A clock that starts and stops the same day (0 days) is a completed pathway reported "in the 0-1 week time band" **[G §10.1.7, p.46]**.

**Consequence for the code you write:** the column `Gt 17 To 18 Weeks` holds waits of 120–126 days, and **exactly 18 weeks is *within* standard, not a breach**. So the ">18-week breach count" is the sum of bands **strictly after** the 17–18 band (127+ days), i.e. `Gt 18 To 19 Weeks` onward. Off-by-one here silently mis-defines the agent's headline metric. Full mapping in Appendix E.

### The SECOND structural break the project must handle: community services, Feb 2024

This is grounded and load-bearing, and older project notes treat the X-series as smooth across the window. It is not.

From **February 2024**, consultant-led community services were **removed from RTT**. NHS: where a community service is consultant-led, "these pathways should be recorded in relevant Community datasets and should be excluded from the RTT data submissions … Community Paediatrics and Community Medicine … should not be reported within RTT data submissions" **[G §7.2, p.32]**.

Measured impact, from NHS **[SPN §4, p.15]**: "a decrease of approximately **43,000 pathways** within the community paediatric specialty," of which "about 36,000 … were excluded from the February 2024 figures and most of the remaining 7,000 … from the March 2024 figures," including "approximately **4,400 fewer 52-week waits**, 2,500 fewer 65-week waits and 1,400 fewer 78-week waits." These pathways "are recorded under 'Other – Paediatric Services' and 'Other – Other services'" - i.e. **inside `X04`/`X06`, which merge into your `X_OTHER`**.

So `X_OTHER` (and any paediatric "Other" analysis) has a **genuine downward step in Feb–Mar 2024** that is not a data error and not COVID. The 18 named specialties are essentially unaffected; the drop is in the Other buckets. The project's boundary-continuity assert guards **2021-04 only** - it does not look at 2024-02. That is now an open task (Part 11).

<div class="remind">Predict both column counts and the exact month. The whole schema story hangs on this one figure, so pin it yourself rather than taking it on trust.</div>

### Task 4.1
Confirm the 69/121 counts, find the exact month, and print the columns unique to each era.

> **Target: 69 columns → 121, at April 2021** (measured), matching NHS's listed changes **[G §10.1.1.3]**.

<div class="remind">Pick bands by column position and it breaks silently, always in your favour. Predict the pre and post counts, then prove your selector on both eras before you believe it.</div>

### Task 4.2
Write a function that, given a file's column names and a week threshold, returns the band columns at or above it - **selected by name, unchanged in both eras**. Selecting by position will break silently.

> `>18`: 35 columns pre-2021, 87 post. `>52`: 1 pre, 53 post (measured). Cross-check against the NHS band list in **[G §10.1.7]** and Appendix E - and remember exactly-18-weeks is *within* standard.

<div class="remind">Group by name instead of code and every specialty quietly splits into two half-histories that both look fine. Guess how many were renamed first. This has already bitten the project once.</div>

### Task 4.3
How many treatment function codes appear in both eras, and how many changed name?

> **Target: 18 of 24 renamed** (measured), consistent with NHS's "update to treatment function names" **[G §10.1.1.3]**.

<div class="remind">A bad yardstick already inflated a 1.7x wobble into a phantom 6.6x break here. Predict where a step belongs and where it does not, measure against nearby months, then go look hard at Feb 2024.</div>

### Task 4.4
Build a national monthly `Part_3` series for one merged "Other" (X01 before, X02–X06 summed after) and plot it across the break.

> A correct reconstruction shows **no visible step at April 2021**. Judge any step against the *typical month-to-month change in the surrounding months* - not against variation over the whole eight years, which is dominated by COVID and would hide a real break behind a bigger one. Getting this yardstick wrong once produced a "6.6× discontinuity" on this project that turned out to be 1.7×. **Then look at Feb 2024** - the ~43,000-pathway community-services removal **[SPN §4]** is a real step in `X_OTHER` and should be visible against local variation.

---

<div class="remind">196 and 457, and the number you eventually quote is probably neither. Predict the split, and know exactly which denominator any later claim is standing on.</div>

# Part 5 - Who is in this data

653 distinct provider codes across the 96 months (measured), and they are not all what you would assume.

- **NHS trusts** - the ~196 public organisations. The federated clients.
- **Independent-sector providers** - ~457 codes: private hospitals and clinics doing NHS-funded work. Real elective delivery, not noise - and in scope of the same collection: "Independent Sector (IS) providers should engage in the RTT data collection process … in the same way as NHS provider organisations" **[G §10.1.1.1, p.40]**.

You cannot tell which is which from the RTT file. The code prefix is a hint, not a rule. ODS is authoritative (Part 1).

### Pathways, periods, patients - three different things

Get this straight before you interpret any total. NHS: "NHS England often uses the term 'RTT pathway' in published reports … this is the same as an 'RTT period'" **[G §13, p.60]**, and "a person may therefore have multiple RTT periods … along one patient pathway" **[G §13, p.60]**. The March 2026 press notice makes the scale concrete: **7.1 million pathways ≈ 6.0 million unique patients** **[SPN p.1]**. Your `demand` counts **pathway clock-starts**, not people. No per-patient claim is supportable from this data alone.

### Why independents matter, and why they are still not clients

Two facts that pull in opposite directions:

1. They deliver genuine demand - over **11 million** new referrals across the window (measured), and their share is *growing*: in ophthalmology from about 6% to about 20%. A model ignoring them models a shrinking fraction of reality.
2. But the NHS cannot **allocate** capacity to them. An ICB can *buy* from a private provider; it cannot direct NHS staff and capital into one.

Hence two separate flags in the project rather than one: who trains the model, and who can receive an allocation. Conflating them hid this distinction for weeks. A second, subtler reason to keep the sector visible: independent `Part_3` is partly **commissioned** volume - flows steered by NHS purchasing decisions, the very mechanism the agent simulates - not purely organic demand, and the mix is not stationary.

### The balanced panel

Providers open, close, merge and are renamed. For a forecasting experiment you want clients with complete history, so the project defines a **balanced panel**: present in all 96 months.

Be careful what "present" means. A provider can appear in a month with `Part_2` rows but no `Part_3` rows - present, but contributing no demand. Different definitions, different answers. Pick one, write it down, use it everywhere.

### The published headline is not the CSV total - the estimation nuance, grounded

When a trust does not submit, the CSV simply lacks its rows, but the **published national figure adds an estimate for it**. For March 2026: "**Sheffield Teaching Hospitals NHS Foundation Trust (RHQ) did not submit any RTT data for March 2026**" **[SPN p.1]**; the headline figures "include estimates for missing acute trusts … contained in the RTT Overview Timeseries file … Estimates are based on the latest data submitted by non-reporting acute trusts" **[SPN p.1]**. Non-reporting is a serious, board-level decision and "the NHS trust will be highlighted in any national publications as not being able to submit data" **[G §10.3, p.50]**.

So:
- Your CSV-derived `Part_2` total for March 2026 (**7,045,510**, measured) is the **raw submitted** figure - correct to reproduce, but it excludes the Sheffield estimate.
- The press-notice headline "**7.1 million**" **[SPN p.1]** includes that estimate, so the two will not match - by construction, not by your error.
- **March 2026, your last month, is missing a large trust.** Treat the end of the window with that caveat.

<div class="remind">Predict it before you count. Quote one month's provider list as the grand total and you have walked straight into the mistake this task was built to catch.</div>

### Task 5.1
Count distinct provider codes across all 96 months.

> **Target: 653** (measured). Not one month's count - a provider that reported for two years then closed is still in this dataset's history.

<div class="remind">Predict public versus independent before the join. Then the real question: without ODS, could you have told them apart at all? Sit with why the answer is no.</div>

### Task 5.2
Split those 653 by sector using the ODS lookup.

> **Target: 196 public (194 NHS trusts + 2 care trusts), 457 independent** (measured).

<div class="remind">'Present' has two honest meanings that give two different answers, and this project once shipped the wrong one. Compute both before you let yourself see either target.</div>

### Task 5.3
How many providers are present in all 96 months? Compute it **both** ways - months with any row, and months with a demand row - and compare.

> On the demand-row definition: **126 public and 126 independent** (measured). The any-row definition gives different numbers. This is the point, not a trick: two reasonable readings of one English phrase give two answers, and quoting one while computing the other publishes a wrong number. That has already happened once on this project.

<div class="remind">Max over min will lie to you through a two-month minnow. Compute both spreads, then pick the one you would defend to a reviewer and be ready to say why the other misleads.</div>

### Task 5.4
Biggest trust vs smallest, by average monthly referrals. Compute max/min, then p90/p10.

> **They differ by more than a hundredfold** (measured). Decide which belongs in a paper and be able to say why the other misleads. Then ask what a 2-month provider is doing in a comparison of trust sizes at all.

---

<div class="remind">The pivot is where rows silently vanish or double. Name the two collapses you are about to make, and what each one costs, before you write a line.</div>

# Part 6 - From 96 files to one table

The goal: one tidy table, one row per **provider × department × month**, measures as columns. Everything downstream reads it.

The raw file is *long* - five part types as five sets of rows, and (because the return is provider × commissioner **[G §10.1.1.1]**) several commissioner rows per key. You want *wide on part type* and *summed over commissioner*. That is a pivot plus a collapse.

### The two collapses to be deliberate about

Going from ~143,000 raw rows a month to ~16,000 means summing over things.

- **Commissioner.** The raw file splits each provider's activity by who paid - the **only genuine second dimension** in the return (everything else is a key or a label determined by a key). Collapsing it is a real loss of information, not a tidy-up. Whether you can afford it depends on a measurable question, in Part 7.
- **The X buckets.** X01–X06 merge into one `X_OTHER`, for the era reason in Part 4.

### The label-or-axis test - a general tool, worth learning properly

For any column, ask: **does it take exactly one value within a `provider × treatment function × part type` group?**

- If yes, it is *functionally determined* by keys you already carry. It is a **label**. Dropping it loses nothing a join cannot restore - and since labels drift (Part 4), carrying it is an active hazard rather than harmless redundancy.
- If no, it is a genuine **axis**, and collapsing it discards information that needs justifying.

This converts "is this column redundant?" from a judgement call into a query. Use it on every column before deciding its fate. The three tests, in order: **is it populated → is it a label or an axis → does the goal consume it.**

### The check that proves you lost nothing - and NHS runs it too

Remember the aggregate code from Task 2.4. It gives you a free, exact test: for every provider, part type and month, **your 18 named specialties plus your merged `X_OTHER` must equal the published aggregate.** Not approximately - exactly. This is not a project invention: NHS's own monthly validation checks "incorrect totals - where the total is a sum over all treatment functions" **[G Annex B, p.64]**. You are re-running NHS's own identity as your integrity gate.

Write it as an assertion that stops the notebook, not a printed number you might scroll past.

### The other invariants NHS itself checks - reuse them as your asserts

NHS's monthly validation **[G Annex B, p.64]** is a ready-made assert list. Among the checks:

- "No negative or decimal numbers have been submitted." → your no-negatives assert.
- "The number of incomplete pathways with a decision to admit is a subset of the total number of incomplete pathways." → `waiting_dta ≤ waiting` (and the 47-row upstream violation in Task 6.3 is a case where NHS's *own* check did not hold).
- "The sum of incomplete pathways in first four time-bands (0-4 weeks) is lower than the number of new RTT periods." → a sanity relation between the stock's short tail and the demand flow.

<div class="remind">Predict all five numbers first. A shape you did not predict is a broken table you will not notice, because nothing throws.</div>

### Task 6.1
Build the table: one row per provider × department × month; columns for demand, both completion types, waiting, >18w, >52w, decision-to-admit.

> **Target: 322,531 rows, 653 providers, 19 departments, 96 months, zero duplicate keys** (measured).

<div class="remind">This assert is the only thing between you and a silently wrong table. If it passes first try, do not move on: ask what input would have broken it. If you cannot say, you do not know what it checks.</div>

### Task 6.2
Assert the coverage identity.

> **Target: 199,410 groups compared, 0 mismatches** (measured). Mismatches mean you either kept the aggregate rows in your data or dropped a treatment function code.

<div class="remind">Three invariants hold, one fails in 47 rows. Predict which, then open the raw file before you touch anything. The fix for a published error is to record it, not to quietly clamp it and pretend.</div>

### Task 6.3
Check your own output: no negatives; `waiting_gt52 ≤ waiting_gt18 ≤ waiting`; `waiting_dta ≤ waiting`.

> The first three hold everywhere. **The fourth fails in 47 rows** (measured). Before concluding you have a bug, go back to the raw file and check whether it fails *there* - it does. NHS defines `Part_2A` as a strict subset **[SPN §4, p.13]** and even lists it as a validation check **[G Annex B]**, so these 47 are upstream submissions that violate NHS's own rule. Recording a published defect is a different question from fixing your own - and the answer is usually to record it, not silently clamp published numbers.

<div class="remind">Run this on the measure columns by accident and you will 'find' axes that are not real. That exact slip happened here. Predict the answer first: commissioner, and nothing else.</div>

### Task 6.4
Apply the label-or-axis test to all 16 non-band columns.

> **Only the commissioner columns come out as axes** (measured). If you get more than that, check whether you accidentally ran the test on the *measure* columns too - they will of course vary within a key, and reporting them as axes is a category error. This mistake was made on this project.

---

<div class="remind">The obvious ICB column is wrong in a way that looks completely right, and stays wrong for two whole years of data without ever throwing. Distrust it before you read why.</div>

# Part 7 - The hierarchy, and why it is harder than it looks

The project escalates **trust → ICB → national**. An **ICB** (Integrated Care Board) is the regional NHS commissioning body; there are 42 in England, statutory from July 2022 (Appendix A).

The obvious way to get a trust's ICB is `Provider Parent Org Code`. **It does not work, and how it fails is instructive.**

England's commissioning structure was reorganised inside the window. Before 2020 the recorded parent is an **NHS region** - there are only 14, a different level of the hierarchy entirely. One column, two kinds of thing, depending on the month. This is visible in the collection too: the April-2021 switch from the single `X24` commissioner code to "more granular NHS England commissioning codes" **[G §10.1.1.3, p.42]** is the same reorganisation showing up on the commissioner axis.

The alternative is the ODS `RE5` relationship: one fixed value per trust. NHS's commissioner-assignment rule itself is layered - NHSE code where NHSE commissions, `NONC` for non-English commissioners, otherwise a SUB-ICB code "of GP practice if known; then … of residence if no GP; then 'host' SUB-ICB" **[G §10.1.8, p.47]** - which is why the "who paid" axis and the "who is the trust's ICB" question are not the same thing.

State the trade-off before you adopt ODS: the ODS answer is **time-invariant**, so it attributes 2018 activity to a body that did not exist in 2018. For simulating *today's* escalation that is right - the board receiving a request is today's board. For a historical claim about ICB-level demand it is wrong. Know which you are making.

<div class="remind">Predict why 2018 to 2019 is exactly zero, not merely low, before you run it. 'Poor agreement' is the wrong answer, and why it is wrong is the whole lesson.</div>

### Task 7.1
Per year: how often does `Provider Parent Org Code` agree with the ODS parent, and how many distinct parent codes appear?

> **14 distinct values and 0% agreement in 2018–19; 42 values and ~74% agreement from 2021** (measured). Explain to yourself why 2018–19 is *exactly* zero rather than merely low (hint: regions are a different entity type, not wrong ICBs).

<div class="remind">No one on this project has done this, so there is no target to hide behind. Put a cause in writing, then actually go test it on a handful of the disagreeing trusts.</div>

### Task 7.2 - open
The residual ~26% disagreement after 2021 is unexplained. Sample the disagreeing trusts and work out why. **Nobody on this project has done this.**

<div class="remind">Predict which trusts fall into the low tail from their names alone, before you look. If the pattern does not jump out at you, that gap is the thing to fix.</div>

### Task 7.3
Using the commissioner columns before collapsing them: what share of a trust's new referrals are commissioned by an organisation under the trust's own parent?

> **Target: ~84% overall, median ~90% per public provider, about a dozen below 50%** (measured). Then look at *which* trusts are in the low tail - you can explain the pattern from their names alone (national specialist centres). This is the first real test of whether the escalation design is sound, and it is not a column question at all.

<div class="remind">This same failure has bitten the project three separate times. If a provider's ICB can differ between two of its rows, you have it too. Write both asserts, and say why either one alone still lets the leak through.</div>

### Task 7.4
The entity-attribute rule, learned the hard way three separate times on this project: **an attribute of an organisation resolves once into a per-provider table and is joined from there. Nothing entity-level is ever derived per row from the monthly files.**

Check your own table against it. If a provider's ICB, sector, or name can differ between two of its rows, you have the bug. Write the assert: **one value per provider, and every value a valid ICB code.** Note carefully why you need *both* - the first alone passes if a provider is *consistently* assigned something that is not an ICB at all, which is exactly the failure that occurred here.

---

<div class="remind">This is the most likely way you produce a result that is wrong in your favour, the exact kind you will never think to double-check. Read this part as if it were written about you.</div>

# Part 8 - The panel, and a trap that will inflate your results

Federated learning wants a rectangular block: every client × department × month. Real data is ragged, so gaps get filled with zeros.

**Not all zeros mean the same thing.**

- A trust that *provides* neurosurgery and had no referrals one month - a real zero. Informative.
- A trust that has *never* provided neurosurgery - not a zero. **That series does not exist.**

Filling the second kind creates hundreds of constant-zero series. Two things then go wrong. You waste training on them. And - much worse - most forecast error metrics score a perfect zero prediction against a zero actual as *zero error*, so those series **drag your headline accuracy toward zero and make your model look better than it is.**

This is not a hypothetical. It is the single most likely way this project produces a result that is wrong in your favour, which is the most dangerous kind. The fix is not a comment. It is a mask carried through the windowing **and** through the metric's series set.

<div class="remind">Predict the fill rate before you build the cube. If a quarter of it turns out to be invented zeros and that surprises you, you had not yet reckoned with what 'rectangular' costs.</div>

### Task 8.1
Build the rectangular panel: 126 clients × 19 departments × 96 months.

> **Target: 229,824 rows, about 27% filled zeros** (measured).

<div class="remind">Predict how many series never exist at all. Leave those in and your headline accuracy improves for a reason that is a lie. The real problem is 1,870 series, not 2,394.</div>

### Task 8.2
How many filled cells belong to a series that **never** has demand in any month?

> **Target: 524 of 2,394 trust × department series are structurally absent, leaving about 1,870 real series** (measured). 1,870 is the true size of your modelling problem.

<div class="remind">No target here on purpose. Add constant-zero series, watch the metric 'improve' while the model does nothing, and let that unsettle you. If it does not, you have not felt the trap yet.</div>

### Task 8.3
Convince yourself of the metric trap numerically. Take any error metric you plan to use, score a set of real series, then score the same set with 500 constant-zero series added. Report both.

> There is no target - the point is that you see the number move for a reason that has nothing to do with model quality.

---

<div class="remind">The identity leaks about 15%, and every downstream phase trusts it anyway. Treat it as exact and your agent over-escalates for eight straight years. This finding is one to earn, not to read.</div>

# Part 9 - The accounting identity, and a real research finding

The decision layer assumes:

> backlog next month ≈ backlog now + new demand − completions

Patients arrive, patients are treated, the queue is what is left. Every column you need is in your table. Test it.

**Why it should leak, grounded in the clock rules.** A clock stops for treatment (rule 4) **or** for several non-treatment reasons (rule 5): a communicated decision not to treat, entry to **active monitoring** (a clock stop *without* treatment - **[G §13, p.56]**), a qualifying DNA, or the patient declining **[G §4.4, p.20]**. Completions (`Part_1A`/`1B`) count only the clocks that stopped *for treatment*. So pathways that leave the waiting list via a rule-5 non-treatment stop - plus deaths, and transfers out - are removals the identity does not see. The identity therefore *should* over-predict the backlog, and by roughly the size of the rule-5 outflow.

<div class="remind">A one-sided residual is never noise, it is a missing term. Predict the sign first, then name what leaves a waiting list without being a completion. The clock rules already handed you the answer.</div>

### Task 9.1
Compute the predicted waiting list from the previous month's waiting list plus demand minus completions, and compare to actual.

> **The identity over-predicts in every single month - 95 of 95** (measured). A residual with a consistent sign is not noise; it is a missing term. What leaves a waiting list without being a completion? The clock rules above name several, and all are real.

<div class="remind">Now try to kill your own finding. If you are not actively hunting the artefact that would explain it away, you are advertising your result, not testing it. Re-run on all 653.</div>

### Task 9.2
Now try to destroy your own finding. The obvious alternative: you measured on 126 trusts, so a patient transferring to a non-panel provider leaves your list with no matching completion - manufacturing exactly this result out of nothing.

> Re-run on **all 653 providers**, where transfers between providers cancel. If the residual survives, it is real. **It does** (measured). This is the difference between a result and a claim, and it is the single most important habit in this document.

<div class="remind">An unlabelled percentage is not a number. Predict whether the two definitions even differ, then say which one you would print and why. If you cannot pick, you have not pinned down your own claim.</div>

### Task 9.3
Report the residual as a percentage two ways: the mean of the monthly ratios, and the ratio of the means.

> They differ (about −15.4% vs −15.3% here, measured). Both are correct for what they measure. State which you are quoting - an unlabelled percentage is not a number.

---

<div class="remind">You are not building this yet, but the table you make now either fits these phases or wastes them. Read it as a spec to satisfy, not a trailer to skim.</div>

# Part 10 - What comes after the table

You are not being asked to build this yet. Read it so the table you build is the one these phases need.

### The forecasting setup

Each **client** is a trust; each client holds 19 department series of 96 months. That is short - 96 points, of which one stretch is a pandemic. Expect this to constrain model choice far more than compute does.

Decisions you will have to make and defend:

- **Windowing.** How many months of history predict how many ahead? Longer input means fewer training windows from 96 months.
- **The split.** It must be **temporal**, never random. A random split lets the model see the future of a series it is being tested on, and will silently produce excellent, meaningless results.
- **Where COVID goes.** If March 2020 is in train and not test, you are claiming robustness you have not demonstrated. If it is only in test, you are testing extrapolation to an unprecedented shock. Neither is wrong; choosing without noticing is.
- **Scaling.** Trusts differ 100-fold in size. Per-client scaling makes clients comparable but changes what the loss optimises.

### The federated part

The standard algorithm is **FedAvg**: each client trains locally for a few epochs, sends weights (not data) to a server, the server averages them weighted by client sample count, and sends the global model back. Repeat.

- **Weighting.** Under n-samples weighting, small clients barely move the global model. Under equal weighting they dominate. This choice will drive your results more than most architecture choices, so pin it deliberately and report it.
- **Per-client fine-tuning.** After the global model converges, each client fine-tunes locally. This is what stops the shared model flattening local differences - and it is where the comparison against *isolated* training gets interesting, since fine-tuning is a mixture of both.

**A pre-registration you should honour:** the intuitive hypothesis is "federation rescues the small data-poor client". On an earlier run of this project that hypothesis was pre-registered and **refuted** - the gains sat in mid-size clients, and the thinnest clients did *better* trained alone. Do not quietly re-adopt the intuitive version. Write your hypothesis down before you run, and let it be refuted again if that is what happens.

### The agentic part

Per trust × department, per month, the state is: forecast demand, trailing throughput, backlog, the bed-linked queue, the >18-week count. From those, a capacity gap in treatments per month, classified transient / sustained / regime change, escalated on sustained gaps.

The classification is where `waiting_gt52` earns its place: two services with identical 18-week breach counts can have very different tails, and "behind" and "in crisis" demand different asks. 52 weeks is also a real elective-recovery target line, so severity measured there maps onto a policy standard rather than an invented threshold.

---

<div class="remind">No targets here, because nobody has the answers yet. This is the one place you can add something new instead of reproducing a known number. Pick one, and write your prediction before you touch it.</div>

# Part 11 - The open questions

Genuinely open. No target numbers, because nobody has computed one.

1. **The 26% ICB disagreement** (Task 7.2).
2. **The Feb 2024 community-services break in `X_OTHER`.** The ~43,000-pathway removal **[SPN §4, p.15]** is a real discontinuity inside the Other buckets that the project's continuity assert (which guards only April 2021) does not check. **Task: measure the `X_OTHER` step at 2024-02/03 against local variation, the same way April 2021 was checked, and decide whether the series needs a second reconciliation or an explicit break flag.**
3. **The estimate-for-missing-trusts gap.** Your CSV totals exclude non-reporting trusts; the published headline includes an estimate **[SPN p.1]**. For any month with a non-submitter (March 2026 = Sheffield/RHQ), quantify the gap between your raw total and the published figure, and decide whether the panel needs a "was this trust reporting this month" flag.
4. **KH03.** 61 workbooks downloaded, validated, read by nothing. Either find them a role - the admitted pathway is bed-constrained - or argue they should be dropped. Note the resolution mismatch: quarterly and per trust, against monthly and per trust × specialty.
5. **Seasonality.** Referrals should have a strong annual cycle. Measure it per specialty. Does the seasonal shape survive COVID or break permanently?
6. **COVID as a natural experiment.** Which specialties recovered to trend and which never did? This is probably where the interesting story is.
7. **Is the independent-sector growth general or concentrated?** Ophthalmology is fastest. Is that a drift across the board or one specialty carrying it?
8. **Are the 126 full-history independent providers worth including as federated clients?** Same columns, ~1/20th the scale, measurably weaker reporting. If you run it: score on the **fixed 126-trust series in both arms** so the metric population does not change, and pin the weighting.
9. **Integrity baseline.** The archives were CRC-verified before deletion, but no sha256 manifest of the extracted CSVs was ever written. Cheap to fix, and it should be fixed before anything is published from these files.

---

<div class="remind">A crutch, not a hiding place. If you cannot recall what DTA or an incomplete pathway means without flipping here mid-task, that is the gap to close, not paper over.</div>

# Appendix A - Glossary (NHS terminology, quoted)

Definitions marked **[G §13]** are quoted or closely paraphrased from the guidance's own terminology section, pp.56–62. Others are as noted.

| Term | Meaning |
|---|---|
| **RTT** | Referral to Treatment. The waiting-time measurement regime this data comes from. |
| **RTT period / RTT pathway** | "The time between a person's referral to a consultant-led service, which initiates a clock start, and the point at which the clock stops" **[G §13, p.60]**. NHS uses "pathway" and "period" interchangeably; a person may have several along one *patient pathway* **[G §13, p.60]**. |
| **RTT clock** | Starts at referral **[G §3.2, rule 1]**; stops at first definitive treatment or a decision that stops the clock **[G §2.1, p.8]**. |
| **First definitive treatment** | "An intervention intended to manage a patient's disease, condition or injury and avoid further intervention" **[G §13, p.58]**. |
| **18-week standard** | Legal right to start consultant-led non-emergency treatment within 18 weeks; operational standard is 92% of incomplete pathways within 18 weeks **[G §1.1, p.5]**. |
| **Active monitoring** | A clock may be *stopped* to start "a period of monitoring in secondary care without clinical intervention"; a new clock starts on a later decision to treat **[G §13, p.56]**. A key reason the accounting identity leaks. |
| **Admitted pathway** | "A pathway that ends in a clock stop for admission (day case or inpatient)" **[G §13, p.56]**. |
| **Non-admitted pathway** | "A pathway that results in a clock stop for treatment that does not require an admission or for 'non-treatment'" **[G §13, p.59]**. |
| **Decision to admit (DTA)** | "Where a clinical decision is taken to admit the patient for either day case or inpatient treatment" **[G §13, p.58]**. `Part_2A` is the subset of the waiting list with one. |
| **Incomplete pathway** | A pathway still open at month-end; the `Part_2` snapshot **[G §10.1.1.2, p.41]**. |
| **Unknown clock start** | Column for patients whose clock-start date the provider cannot identify **[G §10.1.5, p.45]**. |
| **Treatment function** | "A division of clinical work based on main specialty" **[DD]**. Our "department". |
| **Provider** | Who delivered the care **[G §10.1.1.1]**. |
| **Commissioner** | Who paid for the care - a different organisation, assigned by NHSE/`NONC`/SUB-ICB rules **[G §10.1.8, p.47]**. |
| **ICB** | Integrated Care Board. Regional commissioning body, statutory from July 2022; 42 in England. Predecessor bodies (CCG/STP/ICS) are why the parent column changes meaning mid-window. |
| **ODS / ORD** | Organisation Data Service and its REST API - the NHS organisation registry. |
| **`RE5`** | The ODS relationship "is commissioned by" - trust → ICB. |
| **SDCS** | Strategic Data Collection Service - the portal providers submit the aggregate return through **[G §10.1, p.39]**. |
| **DNA / WNB** | Did Not Attend / Was Not Brought - patient misses an appointment "without prior notice" **[G §13, p.57, 62]**. |
| **KH03** | The quarterly bed-availability return. |
| **Cross-silo FL** | Federated learning with few, large, reliable clients - institutions, not phones. |
| **FedAvg** | The baseline federated algorithm: local training, weighted averaging of weights. |
| **Persistence baseline** | Next month = this month. The naive forecast to beat. |
| **sMAPE** | Symmetric mean absolute percentage error. Note its behaviour at zero - Part 8. |
| **Balanced panel** | Providers present in every month of the window. |

---

<div class="remind">Coming back here a fifth time for the same idiom means you are copying it, not learning it. Once it works, shut the tab and retype it from memory, or it never becomes yours.</div>

# Appendix B - The pandas you will actually need

Not a tutorial. These are the specific things this dataset demands, with the reason you would reach for each.

**`pd.read_csv(path, usecols=…)`** - reading 121 columns × 96 files when you need 8 is the difference between seconds and minutes. `usecols` takes a list, or a *function* of the column name returning True/False - which is what you want when columns differ by era.

**`low_memory=False`** - pandas reads in chunks and guesses each column's type per chunk, which can give one column two types. This forces a whole-column read before deciding. Use it whenever a column might be mixed.

**`df.groupby(keys)[col].sum()`** - the workhorse. Understand what it *returns*: a Series indexed by the group keys, not a DataFrame. `.reset_index()` flattens it back.

**`.nunique()`** - count of distinct values. On a groupby it answers "how many different X per Y", which *is* the label-or-axis test: exactly one distinct value per key means the column carries nothing the key does not.

**`.ngroups`** - how many groups a groupby would make, without materialising them. Useful for sizing a collapse before you do it.

**`df.pivot_table(index=…, columns=…, values=…, fill_value=0)`** - turns distinct values of one column into new columns. How five part-type *rows* become five *columns*. Think hard about `fill_value`: absent and zero are not the same thing, and this is where you decide which one you mean.

**`df.merge(other, on=…, how="left")`** - joins. `how="left"` keeps every left row, filling unmatched with NaN. **Always check the row count before and after.** A merge that *increases* the count means your join key was not unique - a bug you will not otherwise notice.

**`pd.MultiIndex.from_product([a, b, c])`** - every combination of the given lists. With `.reindex()`, this is how a ragged table becomes rectangular: build the full index, reindex onto it, and missing cells appear as NaN rows for you to fill deliberately.

**`.shift(1)`** - moves a series down one row, so row *t* can see row *t−1*. How the accounting identity is written. **Sort by month first**, or you will silently compare unrelated months.

**`.dt.to_period("Y")`** - collapses timestamps to a year key without string formatting. Handy for the year-by-year tables in Part 7.

**`assert condition, "message"`** - stops execution when something you believe stops being true. Use these liberally. A printed number can be scrolled past; an assert cannot. Every structural fact you rely on should be an assert, not a comment. Then ask of each one: *what would have made this fail?*

**`df.to_parquet` / `pd.read_parquet`** - a columnar format that preserves dtypes. CSV turns your dates back into strings; parquet does not. Write both if you want portability, read the parquet.

---

<div class="remind">Every target on one page, which makes this a loaded gun aimed at your own learning. Read a number before you have predicted it and that task is spent. Cover it until you commit.</div>

# Appendix C - Every target in one place

NHS-sourced facts are cited; everything else is **measured on this project** and is a number for you to reproduce.

| Task | Target |
|---|---|
| 1.1 | 96 files, 96 months, no gaps or duplicates |
| 2.2 | one part type's bands sum to 0 (`Part_3`, by definition **[G §10.1.1.2]**) |
| 2.3 | `Total` is zero for 3 of 5 part types |
| 2.4 | 7,045,510 correct vs 14,091,020 with the trap (raw CSV; headline "7.1m" includes an estimate **[SPN p.1]**) |
| 4.1 | 69 columns → 121, at April 2021 (NHS change list **[G §10.1.1.3]**) |
| 4.2 | `>18`: 35 pre / 87 post. `>52`: 1 pre / 53 post. Exactly-18-weeks is within standard **[G §10.1.7]** |
| 4.3 | 18 of 24 renamed |
| 4.4 | No visible step at April 2021; a real ~43k step at Feb 2024 in X_OTHER **[SPN §4]** |
| 5.1 | 653 provider codes |
| 5.2 | 196 public (194 + 2), 457 independent |
| 5.3 | 126 public and 126 independent on the demand-row definition |
| 5.4 | max/min and p90/p10 differ by >100× |
| 6.1 | 322,531 rows, 653 providers, 19 depts, 96 months, 0 duplicate keys |
| 6.2 | 199,410 groups, 0 mismatches (= NHS's own "sum over all treatment functions" check **[G Annex B]**) |
| 6.3 | 47 rows where `waiting_dta > waiting`, present in the raw source **[G Annex B; SPN §4]** |
| 6.4 | Only the commissioner columns are axes |
| 7.1 | 14 parents / 0% agreement in 2018–19; 42 / ~74% from 2021 |
| 7.3 | ~84% overall, median ~90%, ~12 trusts below 50% |
| 8.1 | 229,824 panel rows, ~27% filled zeros |
| 8.2 | 524 structural series, ~1,870 real |
| 9.1 | Identity over-predicts in 95 of 95 months |
| 9.2 | Residual survives on all 653 providers |

---

<div class="remind">If a claim in your writeup cannot be traced to something on this page, you cannot defend it, so it does not belong there. Cite it or cut it.</div>

# Appendix D - Sources

Every one retrieved and read directly for this guide.

- **[G]** *Recording and reporting referral to treatment (RTT) waiting times for consultant-led elective care*, v5.2 (PRN01045), NHS England - the definitions of every part type (§10.1.1.2, p.41), the collection mechanics (§10, pp.39–50), the band-to-day mapping (§10.1.7, p.46), the treatment-function list (§10.1.4, pp.43–45), the clock rules (§§2–4), community-services exclusion (§7, p.32), and the terminology glossary (§13). https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/10/Recording-and-reporting-RTT-waiting-times-guidance-v5.2-Feb25.pdf
- **[SPN]** *Statistical Press Notice - RTT waiting times, March 2026*, NHS England - the published national figures, the estimation method for non-reporting trusts (p.1), and the "Notes for editors" restatement of the April-2021 and Feb-2024 changes (§4, pp.12–16). https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Mar26-RTT-statistical-press-notice-PDF-545K-Dc1i9U.pdf
- **[SWA]** *Referral to Treatment (RTT) Waiting Times* statistics work area - the monthly file inventory and revisions. https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/
- **[G-guidance-index]** *Consultant-led RTT Waiting Times Rules and Guidance* - the rules suite (Oct 2022) and the FAQs that accompany [G]. https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-guidance/
- **[DD]** *NHS Data Dictionary - Attribute: TREATMENT FUNCTION CODE*. https://archive.datadictionary.nhs.uk/DD%20Release%20August%202024/attributes/treatment_function_code.html
- **[DD-T]** *NHS Data Dictionary - Main Specialty and Treatment Function Codes Table* - the full code list, incl. every sub-specialty that folds into an "Other" bucket. https://archive.datadictionary.nhs.uk/DD%20Release%20August%202024/supporting_information/main_specialty_and_treatment_function_codes_table.html
- **[DCB0095]** *DCB0095: Consultant-led referral to treatment (RTT) waiting times* - the data-collection standard behind the return and the April-2021 change (named in [SPN §4]; text not yet pulled). https://digital.nhs.uk/data-and-information/information-standards/information-standards-and-data-collections-including-extractions/publications-and-notifications/standards-and-collections
- **[DCB0028]** *DCB0028: Treatment Function and Main Specialty Standard* - the authoritative treatment-function specification (named in [G §10.1.4]; text not yet pulled).
- **ODS ORD API** - `https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{code}`
- **`WORKLOG.md`** in this repository - every decision on this project, including the mistakes, with the reasoning. The most useful *internal* source; NHS documents above are the external ground truth.

---

<div class="remind">One week off here and your headline breach metric is quietly wrong for all 96 months. Do not eyeball the boundary: 126 days is exactly 18 weeks, and it sits within standard, not over it.</div>

# Appendix E - The exact band-to-day mapping, and the column dictionary

Both grounded, so you never have to guess a boundary or a column's meaning.

### E.1 Waiting-time bands, in days [G §10.1.7, p.46]

Each column `Gt N To (N+1) Weeks` holds a count of clocks whose wait falls in that band. NHS allocates by **days**:

| Band column | Days included | Notes |
|---|---|---|
| `0 To 1 Weeks` (first band) | 0–7 days | **eight** day-values, not seven |
| `Gt 1 To 2 Weeks` | 8–14 days | seven day-values |
| … | … | one week each |
| `Gt 17 To 18 Weeks` | 120–126 days | **exactly 18 weeks (126 days) sits here → within standard** |
| `Gt 18 To 19 Weeks` | 127–133 days | first band that is a **>18-week breach** |
| … | … | |
| `Gt 51 To 52 Weeks` | 358–364 days | exactly 52 weeks (364 days) sits here |
| `Gt 52 To 53 Weeks` … | 365+ | post-2021 only; pre-2021 all of this is one `Gt 52 Weeks` column |
| `Gt 104 Weeks` | 729 days and more | the tail |

**Derived metrics, defined exactly:**
- `waiting_gt18` (>18-week breaches) = sum of bands **from `Gt 18 To 19 Weeks` upward** (127+ days). Do **not** include `Gt 17 To 18`.
- `waiting_gt52` = sum from `Gt 52 To 53 Weeks` upward post-2021; the single `Gt 52 Weeks` column pre-2021. Reconcile to the coarse (pre-2021) form.
- A same-day pathway (0 days) is a completion in the `0 To 1 Weeks` band **[G §10.1.7]**.

### E.2 The 15-column canonical dictionary, each grounded

The build reduces 121 raw columns to 15. What each kept column is, and the NHS basis for it:

| Column | Derived from | NHS grounding |
|---|---|---|
| `month`, `provider_code`, `dept` | the key | grain of the return **[G §10.1.1.1]** |
| `demand` | `Part_3` `Total All` | "Number of new RTT periods during the month" **[G §10.1.1.2, p.41]**; gross clock-starts **[SPN §4, p.13]** |
| `completed_admitted` | `Part_1A` `Total All` | completed with inpatient/day-case admission **[G §10.1.1.2, p.41]** |
| `completed_nonadmitted` | `Part_1B` `Total All` | completed for other reasons **[G §10.1.1.2, p.41]** |
| `completed` | 1A + 1B | throughput term of the identity; leaks because rule-5 non-treatment stops are not completions **[G §4.4]** |
| `waiting` | `Part_2` `Total All` | incomplete snapshot at month-end **[G §10.1.1.2, p.41]** |
| `waiting_gt18` | `Part_2` bands ≥ 127 days | the 18-week breach count **[G §10.1.7, p.46]** |
| `waiting_gt52` | `Part_2` bands ≥ 365 days | breach severity; era-reconciled **[G §10.1.1.3, p.42]** |
| `waiting_dta` | `Part_2A` `Total All` | incomplete with a decision to admit; subset of `waiting` **[SPN §4, p.13]** |
| `sector` | ODS primary role | public = RO197/RO107; IS providers submit the same return **[G §10.1.1.1, p.40]** |
| `icb` | ODS `RE5`, backfilled | commissioning parent; time-invariant by choice (Part 7) |
| `fl_client`, `allocatable` | census flags | trust-only training vs public-only allocation (Part 5) |

Columns **dropped** and why: `Total` (identically zero for `Part_2/2A/3` - measured); `Patients with unknown clock start date` (~0.006% residual, already in `Total All` - **[G §10.1.5]**); commissioner columns (a real second axis, summed over deliberately - **[G §10.1.1.1, p.40]**); all name/label columns (drift, join on codes - **[G §10.1.1.3]**); the 0–18-week bands (within-standard); bands on `Part_1A/1B/2A/3` (recoverable, not a state variable).

---

## One last thing

The most valuable output of this exercise is not the table. It is your list of things you tried that were wrong, and why - because those are the failure modes that reappear silently in the modelling, where there is no published aggregate to check against.

Write `NOTES.md` as you go: what you expected, what you got, what the gap was, what you now know. Especially when the mistake is yours. That file is what makes the work defensible.
