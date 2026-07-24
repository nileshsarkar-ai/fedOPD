# Understanding the NHS RTT Dataset

### A working guide for fedOPD — read it, then write the code yourself

---

## How to use this

This document explains **what the data is**. It does not contain the code that analyses it — that is yours to write, and the point of the exercise.

Every section ends with **tasks**. Each task states what to find and, where a definite answer exists, **the number you should get**. That number is the whole mechanism: you write the code, run it, and compare. If you match, you understood. If you don't, the gap between your number and the target tells you exactly what you missed — and finding that out yourself is worth more than being handed the working line.

Do not look in `src/_solutions/`. Those notebooks exist so a number can be checked when everything else has failed. Reading them costs you the exercise.

**The loop to work in:**

1. **Look at the thing.** Print the first ten rows. Print the column names. Print the distinct values of a column with few of them. Before any hypothesis.
2. **Say what you expect.** Out loud, or in a markdown cell. "There should be about 200 trusts." Writing the expectation down before you measure is what makes being wrong informative.
3. **Measure it.**
4. **When it disagrees with you, believe the data** — but check that you measured the thing you meant to. Most disagreements are a bug in the question, not a surprise in the world.

---

# Part 1 — What is on disk

```
data/
  rtt_csv/     96 CSV files, ~8.2 GB total, one per month, April 2018 → March 2026
  reference/   provider lookups built from the NHS ODS API
  kh03/        61 quarterly bed-availability workbooks (not yet used by anything)
```

Each file in `rtt_csv/` is one month of England's **Referral to Treatment** return. Every NHS trust, and every independent provider doing NHS-funded work, reports how many patients are waiting, how long they have been waiting, and how many started or finished a treatment pathway that month.

**Start here:** open one file. Not with pandas — with your eyes, or `head`. Look at the header row. Look at the first few data rows. You cannot reason about a table you have not seen.

### Task 1.1
How many files are there, and does each month between April 2018 and March 2026 appear exactly once? The filenames are not consistently formatted — some carry a date prefix, some say `-revised`, the month name capitalisation varies. You will need to parse the month out of the filename rather than trusting sort order.

> **Target: 96 files, 96 distinct months, no gaps, no duplicates.**

### Task 1.2
How large is each file, and does the size jump anywhere? Plot file size against month.

> You should see a **step up around April 2021**. That step is the single most important structural fact about this dataset, and Part 3 is about it. Do not read ahead — see it first.

---

# Part 2 — What one row means

### The RTT clock

A patient is referred (usually by a GP) to a hospital service. That starts an **RTT clock**. The clock stops when treatment begins, or when it is decided no treatment is needed. The NHS constitutional standard is that **92% of patients should wait no more than 18 weeks** from clock start to clock stop.

That is the entire operational story: clocks start, clocks run, clocks stop. Everything in this file is a count of clocks in some state.

### The grain of a row

A row is roughly:

> *For this **provider**, commissioned by this **commissioner**, in this **treatment function**, in this **part type** — here are the counts.*

Four things identify a row. Learn what each is:

| Column | What it is |
|---|---|
| `Provider Org Code` | **Who delivered the care.** An NHS trust (`R…`, `T…`) or an independent provider. This is the hospital. In fedOPD, this is a **federated client**. |
| `Provider Parent Org Code` | The organisation the provider sits under. **Beware — this changes meaning over time.** Part 6. |
| `Commissioner Org Code` | **Who paid.** A different axis entirely from who delivered. |
| `Treatment Function Code` | **The specialty** — `C_110` Trauma and Orthopaedics, `C_130` Ophthalmology, and so on. In fedOPD, this is a **department**. |
| `RTT Part Type` | **Which question this row answers.** Five values. See below. |

### The five part types — the most important thing in this document

The same table holds five genuinely different measurements, distinguished only by this column. Confusing them is the single easiest way to produce a wrong number.

| Part type | Meaning | In fedOPD |
|---|---|---|
| `Part_1A` | Pathways **completed** this month, patient **admitted** | throughput (admitted) |
| `Part_1B` | Pathways **completed** this month, patient **not admitted** | throughput (non-admitted) |
| `Part_2` | Pathways still **incomplete** at month end | **the waiting list / backlog** |
| `Part_2A` | Of those incomplete, the ones with a **decision to admit** already made | the bed-linked queue |
| `Part_3` | **New** RTT periods started this month | **demand — the forecast target** |

Read that table again. `Part_2` is a **stock** (how many are waiting right now). `Part_1A`, `Part_1B` and `Part_3` are **flows** (how many arrived or left during the month). Mixing a stock and a flow in the same sum is meaningless, and nothing in the file stops you doing it.

`Part_2A` is a **subset** of `Part_2`, not an addition to it.

### The measure columns

- `Total All` — the headline count for the row.
- `Total` — also present, but do not assume it means the same thing. Task 2.3.
- `Patients with unknown clock start date` — a small residual.
- A long run of columns named like `Gt 04 To 05 Weeks SUM 1` — a **histogram of waiting times**. `Gt 04 To 05` means *more than 4 and up to 5 weeks*. These say not just how many are waiting but **how long they have been waiting**, which is what makes the 18-week standard measurable.

### Task 2.1
Read one month. How many rows? How many distinct providers, commissioners, treatment functions? Print the five part types and confirm there are exactly five.

### Task 2.2
Does `Total All` for `Part_2` equal the sum of all the week-band columns for `Part_2`? Check the same for each of the five part types separately.

> **You will find one part type where the bands sum to exactly zero.** Work out *why* before reading on — the answer is in the meaning of that part type, not in a data error. Two others sum to 0.999× rather than exactly 1; work out what the missing 0.1% is.

### Task 2.3
Sum `Total` and `Total All` by part type.

> **`Total` is identically zero for three of the five part types.** Which three, and does that make `Total All` or `Total` the column you should build on?

### Task 2.4
Look at the distinct values of `Treatment Function Code`. One of them is not a specialty.

> Find it. Then answer this: **if you sum `Total All` for `Part_2` across all rows in the March 2026 file, do you get the England waiting list, or exactly twice it?** The published figure is **7,045,510**. If your first attempt gives **14,091,020**, you have just found the trap — and you should now be able to say precisely what it is.

---

# Part 3 — April 2021: the schema break

In April 2021 NHS England changed the return. Files before it have **69 columns**; files from it onward have **121**.

Two independent changes happened at once, and both have the same shape: something coarse became something fine.

### Change 1 — the long-wait tail

Before April 2021, everything over 52 weeks was a single column: `Gt 52 Weeks SUM 1`. From April 2021, that one column is replaced by weekly bands running 52→53, 53→54, … up to 104, plus a final `Gt 104 Weeks`.

The bands **below** 52 weeks are identical in both eras.

The consequence you must reason through: you can always turn fine into coarse by adding up, but you can never turn coarse into fine. So any metric you build across the whole window must reconcile to the **coarser** form.

This is why the 18-week metric is safe across the full window and the 52-week metric needs an explicit era branch.

### Change 2 — the "Other" specialties

Before April 2021 there was one residual code, `X01 Other`. From April 2021 it is replaced by five themed buckets, `X02`–`X06`.

Same shape, same rule: they must merge back into one series to be comparable across the break.

### Change 3 — the renaming, which is the trap

At the same break, NHS England **renamed 18 of the 24 treatment functions**. "General Surgery" became "General Surgery Service". The **codes did not change**.

So if you ever group by name — or worse, by code *and* name together — every specialty silently splits into two rows: one with 36 months of history and one with 60. Neither is wrong-looking. Both are wrong.

**The rule this produces, which applies to every organisational axis in this dataset, not just specialties: join on codes, never on names.** Names are labels; labels drift.

### Task 3.1
Confirm the column counts (69 / 121) and find the exact month the change happens. Print the column names that exist in one era and not the other.

### Task 3.2
Write a function that, given a file's column names and a threshold in weeks, returns the band columns at or above that threshold — **selected by name, working unchanged in both eras**. Selecting by position will break, and it will break silently.

> For `>18` it should return 35 columns pre-2021 and 87 post. For `>52`, 1 column pre and 53 post.

### Task 3.3
How many treatment function codes appear in both eras, and how many of those changed name?

> **Target: 18 of 24 renamed.**

### Task 3.4
Build the national monthly `Part_3` total for one merged "Other" series (X01 before, X02–X06 summed after) and plot it across the break.

> If your reconstruction is right, the line will show **no visible step at April 2021**. If you see a cliff, your merge is wrong. Judge the step against the *typical month-to-month change in the months either side* — not against the variation over the whole eight years, which is dominated by COVID and would hide a real break.

---

# Part 4 — Who is in this data

653 distinct provider codes appear across the 96 months. They are not all hospitals in the sense you would assume.

- **NHS trusts** — the ~196 public organisations. These are the federated clients.
- **Independent-sector providers** — around 457 codes: private hospitals and clinics doing NHS-funded work. They are a real and growing part of NHS elective delivery, not noise to be filtered out.

You cannot tell which is which from the RTT file alone. The provider code prefix is a hint, not a rule. The authoritative source is the NHS **ODS** (Organisation Data Service) API, which gives each code a *primary role*: `RO197` NHS Trust, `RO107` Care Trust, and various independent-sector roles. `data/reference/` already holds this lookup — `fetch_dataset.ipynb` built it.

### Why independents matter to this project

Two reasons, and they pull in different directions:

1. They deliver genuine demand — over 11 million new referrals across the window, and their share is *growing*. In ophthalmology it went from about 6% to about 20%. A model that ignores them is modelling a shrinking fraction of reality.
2. But the NHS cannot **allocate** capacity to them. An ICB can *buy* from a private provider; it cannot direct NHS staff and capital into one. So they are relevant as purchasable substitution capacity, not as recipients of an allocation.

This is why the project keeps them in the table with a `sector` flag rather than filtering them out, and why "who trains the model" and "who can receive capacity" are two separate questions.

### The balanced panel

Not every provider reports in every month. Providers open, close, merge, and are renamed. For a forecasting experiment you want clients with a complete history, so the project defines a **balanced panel**: providers present in all 96 months.

Be careful what "present" means. A provider can appear in a month with `Part_2` rows but no `Part_3` rows — present, but contributing no demand. Those are different definitions and they give different answers. Pick one, write it down, and use it everywhere.

### Task 4.1
Count distinct provider codes across all 96 months.

> **Target: 653.** Not the count in one month — a provider that reported for two years and closed still exists in this dataset's history.

### Task 4.2
Using the ODS lookup in `data/reference/`, split those 653 by sector.

> **Target: 196 public (194 NHS trusts + 2 care trusts), 457 independent.**

### Task 4.3
How many providers are present in all 96 months? Compute it **both** ways — months with any row, and months with a demand row — and compare.

> On the demand-row definition: **126 public and 126 independent.** On the any-row definition you get different numbers. This is not a trick; it is the point. Two reasonable definitions of one English phrase give two different answers, and if you quote one while computing the other you will publish a wrong number. (This has already happened once on this project.)

### Task 4.4
How large is the biggest trust compared to the smallest, by average monthly referrals?

> Compute max/min, then compute the 90th percentile over the 10th percentile. **The two answers differ by more than a hundredfold.** Decide which one you would put in a paper, and be able to say why the other is misleading.

---

# Part 5 — From 96 files to one table

The goal is a single tidy table, one row per **provider × department × month**, with the measures as columns. That table is what everything downstream reads.

### What "tidy" means here

The raw file is *long*: the five part types are five sets of rows. The table you want is *wide on part type*: five columns, one row per key. Getting there is a pivot.

### The two collapses you must decide about

Going from 143,000 raw rows a month to about 16,000 means summing over things. Be deliberate about which:

- **Commissioner.** The raw file splits each provider's activity by who paid for it. Collapsing this is a real loss of information — it is the only genuine second dimension in the return, everything else is a label. Whether you can afford to lose it depends on a question you can measure: *does a trust's own ICB commission the work that trust delivers?* If yes, the project's trust → ICB escalation makes sense and the axis can go.
- **The X buckets.** X01–X06 merge into one `X_OTHER` series, for the era reason in Part 3.

### The check that proves you did not lose anything

Remember the aggregate code from Task 2.4. It gives you a free, exact test: for every provider, part type and month, **your 18 named specialties plus your merged X_OTHER must equal the published aggregate**. Not approximately — exactly.

Write that as an assertion that stops the notebook, not as a printed number you might not read. If it ever fails, something upstream silently changed.

### Task 5.1
Build the table. One row per provider × department × month; columns for demand, both completion types, waiting, the >18w and >52w counts, and the decision-to-admit count.

> **Target: 322,531 rows, 653 providers, 19 departments, 96 months, zero duplicate keys.**

### Task 5.2
Assert the coverage identity from above.

> **Target: 199,410 groups compared, 0 mismatches.** If you get mismatches, you have either kept the aggregate rows in your data, or dropped a treatment function code somewhere.

### Task 5.3
Check the internal consistency of your own output: no negative counts; `waiting_gt52 ≤ waiting_gt18 ≤ waiting`; `waiting_dta ≤ waiting`.

> The first three hold everywhere. **The fourth fails in 47 rows.** Before concluding you have a bug, go back to the raw file and check whether it fails there too. Deciding what to do about a defect *published upstream* is a different question from fixing your own — and the answer is usually to record it, not to silently clamp the numbers.

---

# Part 6 — The hierarchy, and why it is harder than it looks

The project escalates capacity requests **trust → ICB → national**. An ICB (Integrated Care Board) is the regional NHS commissioning body; there are 42 in England.

The obvious way to get a trust's ICB is `Provider Parent Org Code` in the file. **It does not work, and the way it fails is instructive.**

England's commissioning structure was reorganised inside our window. Before 2020 the parent recorded here is an **NHS region** — there are only 14 of them, and they are a completely different level of the hierarchy. ICBs became statutory bodies in July 2022. So this one column silently means two different kinds of thing depending on the month.

The alternative is the ODS API, which gives each trust its current commissioning parent via a relationship called `RE5` ("is commissioned by"). That is one fixed value per trust.

The trade-off is real and you should be able to state it: the ODS answer is **time-invariant**, so it attributes 2018 activity to a body that did not exist in 2018. For simulating *today's* escalation that is correct — the board that would receive a request is today's board. For a historical claim about ICB-level demand it is not. Know which you are making.

### Task 6.1
For each year, compute how often `Provider Parent Org Code` agrees with the ODS parent, and how many distinct parent codes appear.

> **You should find 14 distinct values and 0% agreement in 2018–19, and 42 values with about 74% agreement from 2021.** Zero agreement is not a bug — explain to yourself why it is exactly zero rather than merely low.

### Task 6.2
The residual ~26% disagreement after 2021 is unexplained. Take a sample of disagreeing trusts and work out why. **This is an open question on the project — nobody has done it.**

### Task 6.3
Using the commissioner columns before you collapse them: what share of a trust's new referrals are commissioned by an organisation under the trust's own parent?

> **Target: about 84% overall, median about 92% per public provider, with roughly a dozen below 50%.** Then look at *which* trusts are in that low tail and see whether you can explain the pattern from their names alone. You can. This is the most satisfying single query in the dataset.

---

# Part 7 — The panel, and a trap in evaluation

For federated learning you want a rectangular block: every client × every department × every month. Real data is ragged, so you fill the gaps with zeros.

**But not all zeros mean the same thing**, and this distinction will decide whether your eventual results are honest:

- A trust that *provides* neurosurgery and had no referrals in one month — a real zero. Informative.
- A trust that has *never* provided neurosurgery — not a zero. That series does not exist.

Filling the second kind with zeros creates hundreds of series that are constant zero forever. Two things then go wrong. You waste training on them. And, worse, most forecast error metrics score a perfect zero prediction against a zero actual as *zero error*, so those series **drag your headline accuracy down toward zero and make your model look better than it is.**

The fix is not a comment in the notebook. It is a mask carried through the windowing **and** through the metric's series set.

### Task 7.1
Build the rectangular panel for the 126 public clients × 19 departments × 96 months.

> **Target: 229,824 rows, of which about 27% are filled zeros.**

### Task 7.2
Of those filled cells, how many belong to a series that **never** has any demand in any month?

> **Target: 524 of 2,394 trust × department series are structurally absent, leaving about 1,870 real series.** That 1,870 is the true size of your modelling problem, not 2,394.

---

# Part 8 — The accounting identity, and a real research finding

The project's decision layer assumes:

> backlog next month ≈ backlog now + new demand − completions

Patients arrive, patients are treated, the queue is what is left. Test it. Every column you need is in your table.

### Task 8.1
Compute the predicted waiting list each month from the previous month's waiting list plus demand minus completions, and compare to the actual.

> **The identity over-predicts in every single month — 95 of 95.** A residual with a consistent sign is not noise; it is a missing term. What leaves a waiting list without being a completion? There are several answers and they are all real.

### Task 8.2
Before you believe that, try to destroy it. The obvious alternative explanation: you measured it on 126 trusts, so a patient transferring to a non-panel provider leaves your list with no matching completion — which would manufacture exactly this result out of nothing.

> Re-run it on **all 653 providers**, where transfers between providers cancel out. If the residual survives, the leak is real. **It does.** This is what checking your own finding looks like, and it is the difference between a result and a claim.

---

# Part 9 — The questions nobody has answered yet

These are genuinely open. There is no target number because nobody has computed one.

1. **The 26% ICB disagreement** (Task 6.2).
2. **KH03.** 61 quarterly bed-availability workbooks are downloaded and validated, and *nothing reads them*. Either find them a role — the admitted pathway is bed-constrained, so there is an obvious candidate — or say they should be dropped.
3. **Seasonality.** Referrals should have a strong annual cycle. Measure it, per specialty. Does the seasonal shape survive COVID, or does the pandemic break it permanently?
4. **COVID as a natural experiment.** March 2020 is a step change in every series. Which specialties recovered to trend, and which never did? This is where the interesting story probably is.
5. **Does the independent share grow evenly, or is it concentrated?** Ophthalmology is known to be growing fastest. Is that a general drift or one specialty?
6. **Are the 126 independent providers with full history worth including as federated clients?** They report the same columns at about one twentieth the scale. Prior evidence on this project says thin clients gain little from federation — but that was a different set of thin clients.

---

# Appendix — pandas you will need, and what it actually does

Not a tutorial. These are the specific things this dataset demands, with the reason you would reach for each.

**`pd.read_csv(path, usecols=…)`** — reading 121 columns × 96 files when you need 8 of them is the difference between seconds and minutes. `usecols` accepts a list, or a *function* taking a column name and returning True/False, which is what you want when the columns differ by era.

**`low_memory=False`** — pandas reads a file in chunks and guesses each column's type per chunk, which can give one column two different types. This forces it to read the whole column before deciding. Use it whenever a column might be mixed.

**`df.groupby(keys)[col].sum()`** — the workhorse. Understand what it *returns*: a Series indexed by the group keys, not a DataFrame. `.reset_index()` turns it back into a flat table.

**`.nunique()`** — count of distinct values. On a groupby it answers "how many different X per Y", which is the whole label-or-axis test: if a column has exactly one distinct value per key, it is determined by that key and carries no information the key does not.

**`df.pivot_table(index=…, columns=…, values=…, fill_value=0)`** — turns distinct values of one column into new columns. This is how five part-type *rows* become five *columns*. `fill_value` decides what an absent combination means; think about whether it means zero or unknown, because they are not the same.

**`df.merge(other, on=…, how="left")`** — joins. `how="left"` keeps every row of the left table and fills unmatched rows with NaN. Always check the row count before and after: a merge that *increases* it means your join key was not unique, which is a bug you will not otherwise notice.

**`pd.MultiIndex.from_product([a, b, c])`** — every combination of the given lists. Combined with `.reindex()`, this is how you make a ragged table rectangular: build the full index, reindex onto it, and the missing cells appear as NaN rows for you to fill deliberately.

**`.shift(1)`** — moves a series down one position, so row *t* can see row *t−1*. This is how the accounting identity in Part 8 is written. Make sure your series is sorted by month first, or you will silently compare unrelated months.

**`assert condition, "message"`** — stops execution when something you believe stops being true. Use these liberally. A printed number can be scrolled past; an assert cannot. Every structural fact you rely on should be an assert, not a comment.

**`df.to_parquet` / `pd.read_parquet`** — a columnar file format that preserves dtypes. A CSV turns your dates back into strings; parquet does not. Write both if you want portability, but read the parquet.

---

## One last thing

The most valuable output of this exercise is not the table. It is the list of things you tried that were wrong, and why — because those are the failure modes that will otherwise reappear silently in the modelling, where there is no published aggregate to check against.

Keep `WORKLOG.md` as you go. Write down what you expected, what you got, and what the gap turned out to be. Especially when the mistake is yours.
