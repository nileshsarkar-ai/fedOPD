# Understanding the NHS RTT Dataset

### A working guide for fedOPD — read it, then write the code yourself

---

## How to use this

This document explains **what the data is** and **what the project is trying to do with it**. It contains no analysis code. That is yours to write, and writing it is the point.

Every section ends with **tasks**. Each states what to find and, where a definite answer exists, **the number you should get**. That number is the whole mechanism: you write the code, run it, compare. If you match, you understood it. If you don't, the gap between your number and the target tells you exactly what you missed — and working that out yourself is worth more than being handed the line that would have worked.

Do not look in `src/_solutions/`. Those archived notebooks exist so a number can be checked when everything else has failed. Reading them costs you the exercise.

**The loop to work in:**

1. **Look at the thing.** Print ten rows. Print the column names. Print the distinct values of any column that has few of them. Before any hypothesis.
2. **Say what you expect**, in a markdown cell, *before* you measure. "There should be about 200 trusts." The written-down expectation is what makes being wrong informative.
3. **Measure it.**
4. **When it disagrees with you, believe the data** — but first check you measured the thing you meant to. Most disagreements are a bug in the question, not a surprise in the world.
5. **Write the note.** What you expected, what you got, what the gap was, what you now know. `NOTES.md`. Every task. No exceptions — a result you cannot explain is not a result you have.

---

# Part 0 — What the project is

You are building two things that connect.

### The forecaster

Every hospital needs a demand forecast per department to plan capacity. A single central model is both impossible and inadequate: hospitals will not pool raw activity data, and they differ enormously in size and casemix — yet their demand moves together, so there *is* shared structure worth learning jointly.

**Cross-silo federated learning** is the answer to exactly that. Each hospital is a client that trains a shared neural forecaster by exchanging model updates, never raw data, then fine-tunes locally so the global model does not flatten local differences.

It is measured honestly against three baselines, and you should be suspicious of any result that skips one:

1. **Persistence** — next month equals this month. A hard naive baseline, not a strawman. Monthly hospital demand is highly autocorrelated and persistence is surprisingly hard to beat.
2. **Isolated per-hospital training** — does federating actually beat each site going it alone?
3. **Pooled central training** — the privacy-violating ceiling. Federation should approach it, not exceed it.

### The agentic decision layer

A forecast plans nothing. The second half converts forecasts into action. For each trust × department the system holds an operational state — forecast demand in, trailing throughput out, backlog stock, the bed-linked admission queue, the >18-week breach count — glued by an accounting identity. It compares forecast demand against capacity, projects the backlog against the 18-week standard, classifies any shortfall as **transient, sustained, or regime change**, and on a sustained gap raises a structured capacity request up the real NHS hierarchy: **trust → ICB → national**.

The ICB tier is human-in-the-loop. The board sees the evidence and approves, refuses, or defers — and its view is two-sided, because the data is: internal trust capacity, plus the independent sector's volume in that ICB as *purchasable* substitution capacity. That is the allocate-or-buy decision made concrete. De-escalation is symmetric: gaps that stay closed release their allocation.

### What is deliberately out of scope

- **The currency is operational, not financial.** Treatments, queues, waiting-time standards. There is no money in this data, so there are no cost claims.
- **Capacity is requested in treatments per month**, split admitted vs non-admitted — never in literal beds. The data does not contain beds per specialty.
- **COVID is inside the window on purpose.** It is the built-in stress test: the forecaster must survive it, and the agent is *evaluated* on it — detect the collapse, escalate through the recovery, normalise afterwards.

---

# Part 1 — How the data got here, and what is on disk

```
data/
  rtt_csv/     96 CSV files, ~8.2 GB, one per month, April 2018 → March 2026
  reference/   provider lookups built from the NHS ODS API
  kh03/        61 quarterly bed-availability workbooks
```

### What `fetch_dataset.ipynb` did

Acquisition is the one part already written. Read it — it is short, and it is the model for the commenting standard the rest of your code should meet.

1. **Scraped eight NHS England financial-year pages** (`rtt-data-2018-19` through `rtt-data-2025-26`), collecting the link to each month's *Full CSV* extract. Where NHS published a **revised** version of a month, the revised one wins.
2. **Downloaded each archive to a `.part` file and renamed it on completion.** This is the one place a safety net is allowed in this project, and for a data reason rather than a coding one: a rename is atomic, so a half-downloaded file can never be mistaken for a complete one and reruns resume cleanly.
3. **Extracted the CSVs**, then verified them against the archives before the archives were deleted.
4. **Built the provider reference from the NHS ODS ORD API.** The RTT file gives you a provider *code* and nothing about what kind of organisation it is. ODS gives each code a primary role and its relationships. This is the only way to know which providers are NHS trusts.
5. **Fetched the KH03 bed workbooks.**

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
| `findings.csv` | The `F-…` findings from the previous build. **Do not read this until you have done the exercises** — it is the answer key. |

### The ODS API, since you will need it again

`https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{code}` returns an organisation record. The two things that matter:

- **`PrimaryRoleId`** — what kind of organisation it is. `RO197` NHS Trust, `RO107` Care Trust, `RO261` ICB, plus various independent-sector roles.
- **`Rels`** — its relationships. The one you want is **`RE5`, "is commissioned by"**, whose target is the commissioning parent. An active `RE5` pointing at an `RO261` gives you the trust's ICB.

Note that ODS describes the organisation **as it is now**. It has no history. That limitation drives a real decision in Part 7.

### KH03 — downloaded, validated, and used by nothing

61 quarterly Excel workbooks of overnight bed availability and occupancy per trust. They were fetched because the admitted pathway is bed-constrained, so beds are the obvious capacity denominator for `Part_2A`.

They have never been joined to anything. **This is a live open question, not a settled exclusion** — see Part 11. Note in advance that KH03 is *quarterly and per trust*, while RTT is *monthly and per trust × specialty*, so any join costs you resolution on both axes. Whether that trade is worth making is for you to decide with a measurement, not a preference.

### Task 1.1
How many files are there, and does each month from April 2018 to March 2026 appear exactly once? The filenames are inconsistent — some carry a date prefix, some say `-revised`, capitalisation of the month name varies. Parse the month out of the filename; do not trust sort order.

> **Target: 96 files, 96 distinct months, no gaps, no duplicates.**

### Task 1.2
Plot file size against month.

> You should see a **step up around April 2021**. That step is the most important structural fact in this dataset. Do not read ahead — see it first, then form a guess about what changed.

---

# Part 2 — What one row means

### The RTT clock

A patient is referred, usually by a GP, to a hospital service. That starts an **RTT clock**. It stops when treatment begins, or when it is decided no treatment is needed. The NHS constitutional standard is that **92% of patients wait no more than 18 weeks** from clock start to clock stop.

That is the whole operational story. Clocks start, clocks run, clocks stop. Every number in this file is a count of clocks in some state.

### The grain of a row

> *For this **provider**, commissioned by this **commissioner**, in this **treatment function**, in this **part type** — here are the counts.*

| Column | What it is |
|---|---|
| `Provider Org Code` | **Who delivered the care.** An NHS trust or an independent provider. In fedOPD, a **federated client**. |
| `Provider Parent Org Code` | The organisation the provider sits under. **Changes meaning over time** — Part 7. |
| `Commissioner Org Code` | **Who paid.** A different axis entirely from who delivered. |
| `Treatment Function Code` | **The specialty.** In fedOPD, a **department**. |
| `RTT Part Type` | **Which question this row answers.** Five values. |

### The five part types — the most important table in this document

The same file holds five genuinely different measurements, distinguished only by this column. Confusing them is the easiest way to produce a confidently wrong number.

| Part type | Meaning | In fedOPD | Stock or flow |
|---|---|---|---|
| `Part_1A` | Pathways **completed** this month, patient **admitted** | throughput (admitted) | flow |
| `Part_1B` | Pathways **completed** this month, **not admitted** | throughput (non-admitted) | flow |
| `Part_2` | Pathways still **incomplete** at month end | **the waiting list / backlog** | **stock** |
| `Part_2A` | Of those incomplete, those with a **decision to admit** | the bed-linked queue | **stock, subset of `Part_2`** |
| `Part_3` | **New** RTT periods started this month | **demand — the forecast target** | flow |

`Part_2` is a stock: how many are waiting *right now*. `Part_1A`, `Part_1B` and `Part_3` are flows: how many arrived or left *during* the month. Adding a stock to a flow is meaningless, and nothing in the file stops you.

`Part_2A` is a **subset** of `Part_2`, not an addition to it.

### The measure columns

- `Total All` — the headline count for the row.
- `Total` — also present. Do not assume it means the same thing (Task 2.3).
- `Patients with unknown clock start date` — a small residual.
- A long run of `Gt 04 To 05 Weeks SUM 1`-style columns — a **waiting-time histogram**. `Gt 04 To 05` means *more than 4 and up to 5 weeks*. These are what make the 18-week standard measurable: not just how many are waiting, but how long.

### Task 2.1
Read one month. Rows? Distinct providers, commissioners, treatment functions? Confirm exactly five part types.

### Task 2.2
For each part type separately, does `Total All` equal the sum of the week-band columns?

> **One part type sums to exactly zero.** Work out *why* from the meaning of that part type — it is not a data error. Two others give 0.999× rather than 1; work out what the missing 0.1% is.

### Task 2.3
Sum `Total` and `Total All` by part type.

> **`Total` is identically zero for three of the five.** Which three — and which column does that make safe to build on?

### Task 2.4
Look at the distinct `Treatment Function Code` values. One is not a specialty.

> Find it. Then: summing `Total All` for `Part_2` across the March 2026 file, do you get the England waiting list or exactly twice it? The published figure is **7,045,510**. If you get **14,091,020**, you have found the trap — now state precisely what it is, and why it is *exactly* double rather than merely too big.

---

# Part 3 — The 24 treatment functions

18 named specialties run the full 96 months. Six `X` codes are residual buckets, and they split at the April 2021 break (Part 4).

| Code | Specialty | % of all demand |
|---|---|---|
| `C_130` | Ophthalmology | 9.85 |
| `C_110` | Trauma and Orthopaedics | 9.80 |
| `C_502` | Gynaecology | 6.98 |
| `C_100` | General Surgery | 6.42 |
| `C_330` | Dermatology | 6.29 |
| `C_120` | Ear, Nose and Throat | 6.14 |
| `C_301` | Gastroenterology | 5.29 |
| `C_101` | Urology | 5.04 |
| `C_320` | Cardiology | 4.70 |
| `C_140` | Oral Surgery | 2.99 |
| `C_340` | Respiratory Medicine | 2.72 |
| `C_400` | Neurology | 2.40 |
| `C_410` | Rheumatology | 1.93 |
| `C_160` | Plastic Surgery | 1.35 |
| `C_300` | General Internal Medicine | 0.99 |
| `C_150` | Neurosurgery | 0.67 |
| `C_430` | Elderly Medicine | 0.64 |
| `C_170` | Cardiothoracic Surgery | 0.18 |
| `X01` | Other *(pre-2021 only)* | 8.41 |
| `X02`–`X06` | Other, themed *(post-2021 only)* | 17.19 combined |

Two things to notice, both of which matter later.

**The `X` buckets are not small.** Together they are about a quarter of all demand. Any analysis restricted to the 18 named specialties covers roughly 74% of activity — which is fine as long as you say so, and fatal if you claim it is the total.

**The specialties differ by more than fifty-fold in size.** Cardiothoracic surgery is 0.18% of demand; ophthalmology is 9.85%. A model or a metric that averages across specialties without thinking about weighting is making a choice, whether or not it knows it.

---

# Part 4 — April 2021: the schema break

Files before it have **69 columns**; from it, **121**. Two independent changes happened at once, both with the same shape: coarse became fine.

### Change 1 — the long-wait tail

Before: everything over 52 weeks in one column, `Gt 52 Weeks SUM 1`. From April 2021: weekly bands 52→53, 53→54, … 104, plus `Gt 104 Weeks`.

Bands **below** 52 weeks are identical in both eras.

Reason it through: you can always turn fine into coarse by adding up, never coarse into fine. So any metric spanning the window must reconcile to the **coarser** form. This is why the 18-week metric is safe across all 96 months and the 52-week metric needs an explicit era branch.

### Change 2 — the "Other" specialties

One residual code `X01` before; five themed buckets `X02`–`X06` after. Same shape, same rule: merge back to one series.

### Change 3 — the renaming, which is the trap

At the same break NHS England **renamed 18 of the 24 treatment functions**. "General Surgery" became "General Surgery Service". **The codes did not change.**

So grouping by name — or worse, by code *and* name together — silently splits every specialty into a 36-month row and a 60-month row. Neither looks wrong. Both are.

**The rule: join on codes, never names.** And it generalises. The same thing happens to provider parent organisations: on this dataset, 51 of 56 parent codes carry more than one name across the window. Names are labels; labels drift.

### Task 4.1
Confirm the 69/121 counts, find the exact month, and print the columns unique to each era.

### Task 4.2
Write a function that, given a file's column names and a week threshold, returns the band columns at or above it — **selected by name, unchanged in both eras**. Selecting by position will break silently.

> `>18`: 35 columns pre-2021, 87 post. `>52`: 1 pre, 53 post.

### Task 4.3
How many treatment function codes appear in both eras, and how many changed name?

> **Target: 18 of 24 renamed.**

### Task 4.4
Build a national monthly `Part_3` series for one merged "Other" (X01 before, X02–X06 summed after) and plot it across the break.

> A correct reconstruction shows **no visible step at April 2021**. Judge any step against the *typical month-to-month change in the surrounding months* — not against variation over the whole eight years, which is dominated by COVID and would hide a real break behind a bigger one. Getting this yardstick wrong once produced a "6.6× discontinuity" on this project that turned out to be 1.7×.

---

# Part 5 — Who is in this data

653 distinct provider codes across the 96 months, and they are not all what you would assume.

- **NHS trusts** — the ~196 public organisations. The federated clients.
- **Independent-sector providers** — ~457 codes: private hospitals and clinics doing NHS-funded work. Real elective delivery, not noise.

You cannot tell which is which from the RTT file. The code prefix is a hint, not a rule. ODS is authoritative.

### Why independents matter, and why they are still not clients

Two facts that pull in opposite directions:

1. They deliver genuine demand — over **11 million** new referrals across the window, and their share is *growing*: in ophthalmology from about 6% to about 20%. A model ignoring them models a shrinking fraction of reality.
2. But the NHS cannot **allocate** capacity to them. An ICB can *buy* from a private provider; it cannot direct NHS staff and capital into one.

Hence two separate flags in the project rather than one: who trains the model, and who can receive an allocation. Conflating them hid this distinction for weeks.

There is a second, subtler reason to keep the sector visible: independent `Part_3` is partly **commissioned** volume — flows steered by NHS purchasing decisions, which is the very mechanism the agent simulates. It is not purely organic demand, and the mix is not stationary.

### The balanced panel

Providers open, close, merge and are renamed. For a forecasting experiment you want clients with complete history, so the project defines a **balanced panel**: present in all 96 months.

Be careful what "present" means. A provider can appear in a month with `Part_2` rows but no `Part_3` rows — present, but contributing no demand. Different definitions, different answers. Pick one, write it down, use it everywhere.

### Task 5.1
Count distinct provider codes across all 96 months.

> **Target: 653.** Not one month's count — a provider that reported for two years then closed is still in this dataset's history.

### Task 5.2
Split those 653 by sector using the ODS lookup.

> **Target: 196 public (194 NHS trusts + 2 care trusts), 457 independent.**

### Task 5.3
How many providers are present in all 96 months? Compute it **both** ways — months with any row, and months with a demand row — and compare.

> On the demand-row definition: **126 public and 126 independent.** The any-row definition gives different numbers. This is the point, not a trick: two reasonable readings of one English phrase give two answers, and quoting one while computing the other publishes a wrong number. That has already happened once on this project.

### Task 5.4
Biggest trust vs smallest, by average monthly referrals. Compute max/min, then p90/p10.

> **They differ by more than a hundredfold.** Decide which belongs in a paper and be able to say why the other misleads. Then ask what a 2-month provider is doing in a comparison of trust sizes at all.

---

# Part 6 — From 96 files to one table

The goal: one tidy table, one row per **provider × department × month**, measures as columns. Everything downstream reads it.

The raw file is *long* — five part types as five sets of rows. You want *wide on part type*: five columns, one row per key. That is a pivot.

### The two collapses to be deliberate about

Going from ~143,000 raw rows a month to ~16,000 means summing over things.

- **Commissioner.** The raw file splits each provider's activity by who paid. This is the **only genuine second dimension** in the return — everything else is a key or a label determined by a key. Collapsing it is a real loss of information, not a tidy-up. Whether you can afford it depends on a measurable question, in Part 7.
- **The X buckets.** X01–X06 merge into one `X_OTHER`, for the era reason in Part 4.

### The label-or-axis test — a general tool, worth learning properly

For any column, ask: **does it take exactly one value within a `provider × treatment function × part type` group?**

- If yes, it is *functionally determined* by keys you already carry. It is a **label**. Dropping it loses nothing a join cannot restore — and since labels drift (Part 4), carrying it is an active hazard rather than harmless redundancy.
- If no, it is a genuine **axis**, and collapsing it discards information that needs justifying.

This converts "is this column redundant?" from a judgement call into a query. Use it on every column before deciding its fate. The three tests, in order: **is it populated → is it a label or an axis → does the goal consume it.**

### The check that proves you lost nothing

Remember the aggregate code from Task 2.4. It gives you a free, exact test: for every provider, part type and month, **your 18 named specialties plus your merged `X_OTHER` must equal the published aggregate.** Not approximately — exactly.

Write it as an assertion that stops the notebook, not a printed number you might scroll past.

### Task 6.1
Build the table: one row per provider × department × month; columns for demand, both completion types, waiting, >18w, >52w, decision-to-admit.

> **Target: 322,531 rows, 653 providers, 19 departments, 96 months, zero duplicate keys.**

### Task 6.2
Assert the coverage identity.

> **Target: 199,410 groups compared, 0 mismatches.** Mismatches mean you either kept the aggregate rows in your data or dropped a treatment function code.

### Task 6.3
Check your own output: no negatives; `waiting_gt52 ≤ waiting_gt18 ≤ waiting`; `waiting_dta ≤ waiting`.

> The first three hold everywhere. **The fourth fails in 47 rows.** Before concluding you have a bug, go back to the raw file and check whether it fails *there*. Deciding what to do about a defect published upstream is a different question from fixing your own — and the answer is usually to record it, not to silently clamp published numbers.

### Task 6.4
Apply the label-or-axis test to all 16 non-band columns.

> **Only the commissioner columns come out as axes.** If you get more than that, check whether you accidentally ran the test on the *measure* columns too — they will of course vary within a key, and reporting them as axes is a category error. This mistake was made on this project.

---

# Part 7 — The hierarchy, and why it is harder than it looks

The project escalates **trust → ICB → national**. An **ICB** (Integrated Care Board) is the regional NHS commissioning body; there are 42 in England.

The obvious way to get a trust's ICB is `Provider Parent Org Code`. **It does not work, and how it fails is instructive.**

England's commissioning structure was reorganised inside the window. Before 2020 the recorded parent is an **NHS region** — there are only 14, and they are a different level of the hierarchy entirely. ICBs became statutory bodies in July 2022. One column, two kinds of thing, depending on the month.

The alternative is the ODS `RE5` relationship: one fixed value per trust.

State the trade-off before you adopt it. The ODS answer is **time-invariant**, so it attributes 2018 activity to a body that did not exist in 2018. For simulating *today's* escalation that is right — the board receiving a request is today's board. For a historical claim about ICB-level demand it is wrong. Know which you are making.

### Task 7.1
Per year: how often does `Provider Parent Org Code` agree with the ODS parent, and how many distinct parent codes appear?

> **14 distinct values and 0% agreement in 2018–19; 42 values and ~74% agreement from 2021.** Explain to yourself why 2018–19 is *exactly* zero rather than merely low.

### Task 7.2 — open
The residual ~26% disagreement after 2021 is unexplained. Sample the disagreeing trusts and work out why. **Nobody on this project has done this.**

### Task 7.3
Using the commissioner columns before collapsing them: what share of a trust's new referrals are commissioned by an organisation under the trust's own parent?

> **Target: ~84% overall, median ~90% per public provider, about a dozen below 50%.** Then look at *which* trusts are in the low tail. You can explain the pattern from their names alone. This is the most satisfying single query in the dataset — and it is not a column question at all, it is the first real test of whether the escalation design is sound.

### Task 7.4
The entity-attribute rule, learned the hard way three separate times on this project: **an attribute of an organisation resolves once into a per-provider table and is joined from there. Nothing entity-level is ever derived per row from the monthly files.**

Check your own table against it. If a provider's ICB, sector, or name can differ between two of its rows, you have the bug. Write the assert: **one value per provider, and every value a valid ICB code.** Note carefully why you need *both* — the first alone passes if a provider is *consistently* assigned something that is not an ICB at all, which is exactly the failure that occurred here.

---

# Part 8 — The panel, and a trap that will inflate your results

Federated learning wants a rectangular block: every client × department × month. Real data is ragged, so gaps get filled with zeros.

**Not all zeros mean the same thing.**

- A trust that *provides* neurosurgery and had no referrals one month — a real zero. Informative.
- A trust that has *never* provided neurosurgery — not a zero. **That series does not exist.**

Filling the second kind creates hundreds of constant-zero series. Two things then go wrong. You waste training on them. And — much worse — most forecast error metrics score a perfect zero prediction against a zero actual as *zero error*, so those series **drag your headline accuracy toward zero and make your model look better than it is.**

This is not a hypothetical. It is the single most likely way this project produces a result that is wrong in your favour, which is the most dangerous kind.

The fix is not a comment. It is a mask carried through the windowing **and** through the metric's series set.

### Task 8.1
Build the rectangular panel: 126 clients × 19 departments × 96 months.

> **Target: 229,824 rows, about 27% filled zeros.**

### Task 8.2
How many filled cells belong to a series that **never** has demand in any month?

> **Target: 524 of 2,394 trust × department series are structurally absent, leaving about 1,870 real series.** 1,870 is the true size of your modelling problem.

### Task 8.3
Convince yourself of the metric trap numerically. Take any error metric you plan to use, score a set of real series, then score the same set with 500 constant-zero series added. Report both.

> There is no target — the point is that you see the number move for a reason that has nothing to do with model quality.

---

# Part 9 — The accounting identity, and a real research finding

The decision layer assumes:

> backlog next month ≈ backlog now + new demand − completions

Patients arrive, patients are treated, the queue is what is left. Every column you need is in your table. Test it.

### Task 9.1
Compute the predicted waiting list from the previous month's waiting list plus demand minus completions, and compare to actual.

> **The identity over-predicts in every single month — 95 of 95.** A residual with a consistent sign is not noise; it is a missing term. What leaves a waiting list without being a completion? There are several answers and all are real.

### Task 9.2
Now try to destroy your own finding. The obvious alternative: you measured on 126 trusts, so a patient transferring to a non-panel provider leaves your list with no matching completion — manufacturing exactly this result out of nothing.

> Re-run on **all 653 providers**, where transfers between providers cancel. If the residual survives, it is real. **It does.** This is the difference between a result and a claim, and it is the single most important habit in this document.

### Task 9.3
Report the residual as a percentage two ways: the mean of the monthly ratios, and the ratio of the means.

> They differ (about −15.4% vs −15.3% here). Both are correct for what they measure. State which you are quoting — an unlabelled percentage is not a number.

---

# Part 10 — What comes after the table

You are not being asked to build this yet. Read it so the table you build is the one these phases need.

### The forecasting setup

Each **client** is a trust; each client holds 19 department series of 96 months. That is short — 96 points, of which one is a pandemic. Expect this to constrain model choice far more than compute does.

Decisions you will have to make and defend:

- **Windowing.** How many months of history predict how many ahead? Longer input means fewer training windows from 96 months.
- **The split.** It must be **temporal**, never random. A random split lets the model see the future of a series it is being tested on, and will silently produce excellent, meaningless results.
- **Where COVID goes.** If March 2020 is in train and not test, you are claiming robustness you have not demonstrated. If it is only in test, you are testing extrapolation to an unprecedented shock. Neither is wrong; choosing without noticing is.
- **Scaling.** Trusts differ 100-fold in size. Per-client scaling makes clients comparable but changes what the loss optimises.

### The federated part

The standard algorithm is **FedAvg**: each client trains locally for a few epochs, sends weights (not data) to a server, the server averages them weighted by client sample count, and sends the global model back. Repeat.

Two things to think about early:

- **Weighting.** Under n-samples weighting, small clients barely move the global model. Under equal weighting they dominate. This choice will drive your results more than most architecture choices, so pin it deliberately and report it.
- **Per-client fine-tuning.** After the global model converges, each client fine-tunes locally. This is what stops the shared model flattening local differences — and it is also where the comparison against *isolated* training gets interesting, since fine-tuning is a mixture of both.

**A pre-registration you should honour:** the intuitive hypothesis is "federation rescues the small data-poor client". On an earlier run of this project that hypothesis was pre-registered and **refuted** — the gains sat in mid-size clients, and the thinnest clients did *better* trained alone, collapsing onto the naive baseline. Do not quietly re-adopt the intuitive version. Write your hypothesis down before you run, and let it be refuted again if that is what happens.

### The agentic part

Per trust × department, per month, the state is: forecast demand, trailing throughput, backlog, the bed-linked queue, the >18-week count. From those, a capacity gap in treatments per month, classified transient / sustained / regime change, escalated on sustained gaps.

The classification is where `waiting_gt52` earns its place: two services with identical 18-week breach counts can have very different tails, and "behind" and "in crisis" demand different asks. 52 weeks is also the NHS's own elective-recovery target line, so severity measured there maps onto a real policy standard rather than an invented threshold.

---

# Part 11 — The open questions

Genuinely open. No target numbers, because nobody has computed one.

1. **The 26% ICB disagreement** (Task 7.2).
2. **KH03.** 61 workbooks downloaded, validated, read by nothing. Either find them a role — the admitted pathway is bed-constrained — or argue they should be dropped. Note the resolution mismatch: quarterly and per trust, against monthly and per trust × specialty.
3. **Seasonality.** Referrals should have a strong annual cycle. Measure it per specialty. Does the seasonal shape survive COVID or break permanently?
4. **COVID as a natural experiment.** March 2020 is a step change in every series. Which specialties recovered to trend and which never did? This is probably where the interesting story is.
5. **Is the independent-sector growth general or concentrated?** Ophthalmology is fastest. Is that a drift across the board or one specialty carrying it?
6. **Are the 126 full-history independent providers worth including as federated clients?** Same columns, about one twentieth the scale, 11 of 19 departments, measurably weaker reporting. Prior evidence says thin clients gain little — but that was a different set of thin clients. If you run it: score on the **fixed 126-trust series in both arms** so the metric population does not change, and pin the weighting, or you will be measuring the weighting rather than the clients.
7. **Integrity baseline.** The archives were CRC-verified before deletion, but no sha256 manifest of the extracted CSVs was ever written, so there is no standing baseline to detect later corruption or accidental modification. Cheap to fix, and it should be fixed before anything is published from these files.

---

# Appendix A — Glossary

| Term | Meaning |
|---|---|
| **RTT** | Referral to Treatment. The waiting-time measurement regime this data comes from. |
| **RTT clock** | Starts at referral, stops at treatment or a decision not to treat. |
| **18-week standard** | The constitutional target: 92% of incomplete pathways within 18 weeks. |
| **Trust** | An NHS provider organisation — usually one or more hospitals. |
| **Foundation Trust (FT)** | A trust with greater financial autonomy. Same thing for our purposes. |
| **Care Trust** | Combined health and social care provider. ODS role `RO107`. |
| **Treatment function** | A specialty as recorded in RTT. Our "department". |
| **Provider** | Who delivered the care. |
| **Commissioner** | Who paid for the care. A different organisation. |
| **ICB** | Integrated Care Board. Regional commissioning body, statutory from July 2022. 42 in England. |
| **CCG / STP / ICS** | The predecessors ICBs replaced. Why the parent column changes meaning mid-window. |
| **DTA** | Decision To Admit. `Part_2A` is the subset of the waiting list with one. |
| **ODS** | Organisation Data Service. The NHS organisation registry. |
| **ORD** | The ODS REST API. |
| **`RE5`** | The ODS relationship "is commissioned by" — trust → ICB. |
| **KH03** | The quarterly bed-availability return. |
| **Elective recovery** | The post-COVID programme to clear the backlog; source of the 52-week target line. |
| **Cross-silo FL** | Federated learning with few, large, reliable clients — institutions, not phones. |
| **FedAvg** | The baseline federated algorithm: local training, weighted averaging of weights. |
| **Persistence baseline** | Next month = this month. The naive forecast to beat. |
| **sMAPE** | Symmetric mean absolute percentage error. Note its behaviour at zero — Part 8. |
| **Balanced panel** | Providers present in every month of the window. |

---

# Appendix B — The pandas you will actually need

Not a tutorial. These are the specific things this dataset demands, with the reason you would reach for each.

**`pd.read_csv(path, usecols=…)`** — reading 121 columns × 96 files when you need 8 is the difference between seconds and minutes. `usecols` takes a list, or a *function* of the column name returning True/False — which is what you want when columns differ by era.

**`low_memory=False`** — pandas reads in chunks and guesses each column's type per chunk, which can give one column two types. This forces a whole-column read before deciding. Use it whenever a column might be mixed.

**`df.groupby(keys)[col].sum()`** — the workhorse. Understand what it *returns*: a Series indexed by the group keys, not a DataFrame. `.reset_index()` flattens it back.

**`.nunique()`** — count of distinct values. On a groupby it answers "how many different X per Y", which *is* the label-or-axis test: exactly one distinct value per key means the column carries nothing the key does not.

**`.ngroups`** — how many groups a groupby would make, without materialising them. Useful for sizing a collapse before you do it.

**`df.pivot_table(index=…, columns=…, values=…, fill_value=0)`** — turns distinct values of one column into new columns. How five part-type *rows* become five *columns*. Think hard about `fill_value`: absent and zero are not the same thing, and this is where you decide which one you mean.

**`df.merge(other, on=…, how="left")`** — joins. `how="left"` keeps every left row, filling unmatched with NaN. **Always check the row count before and after.** A merge that *increases* the count means your join key was not unique — a bug you will not otherwise notice.

**`pd.MultiIndex.from_product([a, b, c])`** — every combination of the given lists. With `.reindex()`, this is how a ragged table becomes rectangular: build the full index, reindex onto it, and missing cells appear as NaN rows for you to fill deliberately.

**`.shift(1)`** — moves a series down one row, so row *t* can see row *t−1*. How the accounting identity is written. **Sort by month first**, or you will silently compare unrelated months.

**`.dt.to_period("Y")`** — collapses timestamps to a year key without string formatting. Handy for the year-by-year tables in Part 7.

**`assert condition, "message"`** — stops execution when something you believe stops being true. Use these liberally. A printed number can be scrolled past; an assert cannot. Every structural fact you rely on should be an assert, not a comment. Then ask of each one: *what would have made this fail?* If you cannot say, you do not yet know what it tests.

**`df.to_parquet` / `pd.read_parquet`** — a columnar format that preserves dtypes. CSV turns your dates back into strings; parquet does not. Write both if you want portability, read the parquet.

---

# Appendix C — Every target in one place

Check yourself against these as you go.

| Task | Target |
|---|---|
| 1.1 | 96 files, 96 months, no gaps or duplicates |
| 2.3 | `Total` is zero for 3 of 5 part types |
| 2.4 | 7,045,510 correct vs 14,091,020 with the trap |
| 4.1 | 69 columns → 121, at April 2021 |
| 4.2 | `>18`: 35 pre / 87 post. `>52`: 1 pre / 53 post |
| 4.3 | 18 of 24 renamed |
| 4.4 | No visible step at April 2021 |
| 5.1 | 653 provider codes |
| 5.2 | 196 public (194 + 2), 457 independent |
| 5.3 | 126 public and 126 independent on the demand-row definition |
| 5.4 | max/min and p90/p10 differ by >100× |
| 6.1 | 322,531 rows, 653 providers, 19 depts, 96 months, 0 duplicate keys |
| 6.2 | 199,410 groups, 0 mismatches |
| 6.3 | 47 rows where `waiting_dta > waiting`, present in the raw source |
| 6.4 | Only the commissioner columns are axes |
| 7.1 | 14 parents / 0% agreement in 2018–19; 42 / ~74% from 2021 |
| 7.3 | ~84% overall, median ~90%, ~12 trusts below 50% |
| 8.1 | 229,824 panel rows, ~27% filled zeros |
| 8.2 | 524 structural series, ~1,870 real |
| 9.1 | Identity over-predicts in 95 of 95 months |
| 9.2 | Residual survives on all 653 providers |

---

# Appendix D — Sources

- **RTT waiting times statistics**, NHS England — the eight financial-year pages the extracts came from.
- **ODS ORD API** — `https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{code}`
- **RTT rules suite**, NHS England — the definitive statement of what starts and stops a clock. Worth reading if a part type ever confuses you.
- **KH03 bed availability and occupancy**, NHS England.
- **`WORKLOG.md`** in this repository — every decision on this project, including the mistakes, with the reasoning. The most useful source in this list.

---

## One last thing

The most valuable output of this exercise is not the table. It is your list of things you tried that were wrong, and why — because those are the failure modes that reappear silently in the modelling, where there is no published aggregate to check against.

Write `NOTES.md` as you go: what you expected, what you got, what the gap was, what you now know. Especially when the mistake is yours. That file is what makes the work defensible.
