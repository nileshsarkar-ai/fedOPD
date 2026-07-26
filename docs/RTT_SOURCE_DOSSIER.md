# The NHS RTT dataset, read from source

**A complete record of the 2026-07-26 primary-source reading pass.**

This document is what NHS England says about the Referral to Treatment collection, read directly
from their own documents rather than recalled or inferred from the data. It exists because the
project needed to be able to defend every claim about what the data *is*, separately from what the
project *measured*.

Two kinds of statement appear here and they are marked differently throughout:

- **Sourced** claims carry a bracketed citation key and, for PDFs, a page number. These are what NHS
  publishes. If a claim about the data has no citation, it is not sourced.
- **Measured** claims are this project's own numbers, reproduced from the CSVs. They are labelled
  "measured". They are not NHS-published figures.

Where the two disagree, that is a finding and it is stated as one, not smoothed over.

---

## Contents

1. [The sources](#1-the-sources)
2. [What the collection actually is](#2-what-the-collection-actually-is)
3. [The five part types](#3-the-five-part-types)
4. [The treatment functions](#4-the-treatment-functions)
5. [The waiting-time bands, exactly](#5-the-waiting-time-bands-exactly)
6. [Three structural breaks, not one](#6-three-structural-breaks-not-one)
7. [COVID: what actually happened to this data](#7-covid-what-actually-happened-to-this-data)
8. [Unreported removals: NHS's own name for our F-15](#8-unreported-removals-nhss-own-name-for-our-f-15)
9. [Non-submission, and the estimates that fill it](#9-non-submission-and-the-estimates-that-fill-it)
10. [The two sectors are not symmetric](#10-the-two-sectors-are-not-symmetric)
11. [What this means for the federation](#11-what-this-means-for-the-federation)
12. [Corrections to the project's own records](#12-corrections-to-the-projects-own-records)
13. [What remains open](#13-what-remains-open)

---

## 1. The sources

Every document below was downloaded and read directly. The NHS PDFs are FlateDecode-compressed and
cannot be parsed by ordinary web-fetching tools, so they were pulled and decoded locally with
`pypdf`; the one Word document was unzipped and its XML stripped. Page numbers are the printed page.

| Key | Document | What it grounds |
|---|---|---|
| **[G]** | *Recording and reporting referral to treatment (RTT) waiting times for consultant-led elective care*, v5.2, PRN01045, NHS England (Feb 2025, formatting rev. Oct 2025), 79pp | The definitive statement of the collection: part types, clock rules, treatment functions, bands, submission mechanics, commissioner assignment, non-reporting policy |
| **[UR]** | *Derived unreported removals*, NHS England, 14 April 2026 | The accounting-identity residual, NHS's own formula, magnitude and causes |
| **[AR-1920]** | *RTT Annual Report 2019/20*, NHS England (published Nov 2020), 37pp | COVID's measured effect on 2019/20, the missing-data estimation method, the sector reporting obligations |
| **[SPN-Jul20]** | *Statistical Press Notice, RTT waiting times, July 2020* (published 10 Sep 2020), 13pp | The COVID trajectory month by month, named non-submitting trusts, the April 2020 commissioner and parent-org changes |
| **[C0009]** | *Referral to treatment measurement and COVID-19*, v1, 24 March 2020, 4pp | Whether the clock rules changed during the pandemic |
| **[SPN]** | *Statistical Press Notice, RTT waiting times, March 2026* (published 14 May 2026) | Current published figures, the estimate for non-reporting trusts, the Feb-2024 community-services change |
| **[PA]** | *Elective recovery: a partnership agreement between the NHS and the independent sector*, NHS England | How independent capacity is commissioned and directed |
| **[REA]** | *Recovery of Elective Activity* statistics page, NHS England | Independent-sector activity reporting, and its own definitional break |
| **[SWA]** | *Referral to Treatment (RTT) Waiting Times* work area, plus all eight financial-year data pages 2018-19 to 2025-26 | File inventory, revisions timetable, named non-submitters |
| **[DD]** | *NHS Data Dictionary, Treatment Function Code* | What a treatment function is |

Two standards are named by the documents above but their own text has not been pulled: **DCB0095**
(the collection standard behind the monthly return) and **DCB0028** (the treatment-function
specification). Where this document relies on them it relies on [G]'s summaries and says so.

---

## 2. What the collection actually is

### It is an aggregate return, not patient records

This is the single most important structural fact and it governs everything downstream. NHS states
it plainly: *"The national data collection looks at RTT waiting times in weeks, split by treatment
function. Returns are submitted by providers, split by commissioner"* **[G §10.1.1.2, p.40]**, and
*"The data collection is provider and commissioner based"* **[G §10.1.1.1, p.40]**.

Providers download a spreadsheet form from NHS England's **Strategic Data Collection Service
(SDCS)** portal, enter their data broken down by commissioner, and upload it. There is *"functionality
in the form which semi-automates this and allows for CSV import of the data"* **[G §10.1.2, p.42]**.

So one row is never a patient. It is a **count of RTT clocks in one state**, for one provider ×
commissioner × treatment function × part type, spread across the weekly-band columns.

### Who has to submit

*"Any organisation that provides NHS services that fall within the scope of RTT should complete a
provider return to the SDCS portal and submit via WLMDS. This includes acute trusts, specialist
trusts, mental health trusts and any other provider of consultant-led services for NHS patients in
England including Independent Sector providers or providers of interface services"* **[G §10.1.1.1,
pp.39-40]**.

Providers are expected to use an NHS Trust, Independent Sector Healthcare Provider, Independent
Sector Healthcare Provider Site or NHS Care Trust ODS code **[G §10.1.1.1, p.40]**. That is the
documentary basis for using ODS to classify providers, which the RTT file itself cannot do.

Note there are **three** parallel RTT collections, and this project uses only the first:

1. The **monthly aggregate return via SDCS**, which is the Full CSV this project consumes.
2. The **Commissioning Data Sets via SUS**, which are record-level patient interactions from which
   SUS reconstructs pathways **[G §10.1, p.39]**.
3. The **weekly Waiting List Minimum Data Set (WLMDS)**, also record-level **[G §10.1, p.39]**.

The WLMDS matters later, because NHS uses it to characterise unreported removals (§8), which the
aggregate return cannot do.

### The timetable, and what "revised" means

The provider deadline is **13 working days** after the final day of the reference period; the
commissioner assurance deadline is **18 working days** **[G §10.1.3, p.43]**. Between those two,
commissioners have five days to review daily files delivered through SEFT and query errors with
providers.

*"Data revisions are normally published every six months (generally in January and July), alongside
the latest release of new monthly data"* **[G §10.1.6, p.46]**. This is why a month appears twice on
a financial-year page, as original and revised, and why the acquisition rule *revised supersedes
original* is correct.

A consequence the project has not yet handled: **revisions continue to arrive after acquisition**.
The 2025-26 page currently shows December 2025 and March 2026 as revised on 9 July 2026. Without a
sha256 manifest of the extracted CSVs, there is no way to distinguish a legitimate upstream revision
from corruption on our side. That manifest was specified and never written.

### What is published each month

Alongside the Full CSV, NHS publishes eight Excel views: a Commissioner and a Provider version each
of Incomplete, Admitted, Non-Admitted and New Periods **[SWA]**. The commissioner files *"include
aggregations of waiting times by sub-ICB, ICB, region and England as a whole"* **[SPN p.2]**. These
are pre-aggregated slices of the same underlying table, which is why the project uses the Full CSV
alone.

---

## 3. The five part types

The collection template is *"in three sections"* **[G §10.1.1.2, p.40]**, which surface in the CSV
as five part types. Quoted verbatim from **[G §10.1.1.2, p.41]**:

| Part type | NHS definition (quoted) | Project role | Stock or flow |
|---|---|---|---|
| `Part_1A` | "cases where patients completed their RTT pathway during the month with an inpatient or day case admission" | throughput, admitted | flow |
| `Part_1B` | "cases where patients completed their RTT pathway during the month for reasons other than an inpatient or day case admission" | throughput, non-admitted | flow |
| `Part_2` | "cases where patients are still waiting to start treatment at the end of the reporting month. This is a 'snapshot' on the last day of the reporting period" | the backlog | **stock** |
| `Part_2A` | "cases where patients are still waiting to start treatment at the end of the reporting month where a clinical decision to admit to a hospital bed for treatment has been made" | the bed-linked queue | **stock**, subset of `Part_2` |
| `Part_3` | "Number of new RTT periods during the month" | **demand, the forecast target** | flow |

Three properties these definitions fix, each of which is easy to get wrong:

- **`Part_2A` is a subset of `Part_2`, not an addition.** NHS states the arithmetic directly: *"The
  difference between the values submitted for this data item and for total incomplete pathways
  equates to the number of incomplete pathways without a decision to admit"* **[SPN §4, p.13]**. So
  `waiting_dta ≤ waiting` must hold. *Measured: it fails in 47 of 322,531 rows, and it fails in the
  raw NHS file too, so those are published upstream defects, not ours.*
- **`Part_3` is gross, not net.** *"RTT pathways where the clock start date is within the reporting
  month. This will include those where the clock also stopped within the reporting month"* **[SPN §4,
  p.13]**. A pathway opened and closed in the same month still counts as demand. This matters for the
  accounting identity: demand is not "additions that survived to month-end".
- **Stocks and flows must not be added.** `Part_2` and `Part_2A` are snapshots; `Part_1A`, `Part_1B`
  and `Part_3` are counts of events during the month. Nothing in the file prevents you summing them.

### Why the clock stops, and why it matters

A clock stops for treatment **or** for several non-treatment reasons. NHS's general principle: once
started a clock *"continues to tick until: the patient starts first definitive treatment, or a
clinical decision is made that stops the clock or the patient declines treatment"* **[G §2.1, p.8]**.

- **Rule 4, clock stop for treatment.** *"A clock stops when first definitive treatment starts"*
  **[G §4.3, p.17]**, where first definitive treatment is *"an intervention intended to manage a
  patient's disease, condition or injury and avoid further intervention"* **[G §4.3.1, p.17]**.
- **Rule 5, clock stop for non-treatment.** A communicated clinical decision not to treat, the start
  of **active monitoring** (*"a period of monitoring in secondary care without clinical
  intervention"*, **[G §13, p.56]**), a qualifying DNA, or the patient declining **[G §4.4, p.20]**.

`Part_1A` and `Part_1B` count clocks that stopped, but the completions reported are those the
provider recorded *in that month*. Pathways leaving the list by other routes, or recorded late, are
not captured. That is the documented origin of the accounting-identity leak, treated in full in §8.

---

## 4. The treatment functions

The return does **not** collect every specialty separately. NHS lists exactly what a provider must
report **[G §10.1.4, pp.43-44]**: 18 named services, then five "Other" buckets. The rationale is
given: *"The 18 treatment functions listed out separately on the spreadsheet form were chosen as they
were high volume areas with a large volume of RTT pathways"* **[G §10.1.4, p.44]**.

| Code | NHS name **[G §10.1.4]** | Share of all demand (measured) |
|---|---|---|
| 130 | Ophthalmology Service | 9.85% |
| 110 | Trauma & Orthopaedics Service | 9.80% |
| 502 | Gynaecology Service | 6.98% |
| 100 | General Surgery Service | 6.42% |
| 330 | Dermatology Service | 6.29% |
| 120 | Ear, Nose & Throat Service | 6.14% |
| 301 | Gastroenterology Service | 5.29% |
| 101 | Urology Service | 5.04% |
| 320 | Cardiology Service | 4.70% |
| 140 | Oral Surgery Service | 2.99% |
| 340 | Respiratory Medicine Service | 2.72% |
| 400 | Neurology Service | 2.40% |
| 410 | Rheumatology Service | 1.93% |
| 160 | Plastic Surgery Service | 1.35% |
| 300 | General Internal Medicine Service | 0.99% |
| 150 | Neurosurgery Service | 0.67% |
| 430 | Elderly Medicine Service | 0.64% |
| 170 | Cardiothoracic Surgery Service | 0.18% |
| X01 | Other, single bucket, pre-2021 form only | 8.41% |
| X02 to X06 | Other, five themed buckets, post-2021 form | 17.19% combined |

The five post-2021 buckets, verbatim **[G §10.1.4, p.44]**: `X02` Other Medical Services (*"All other
TREATMENT FUNCTIONS in the Medical Services group not reported individually"*), `X03` Other Mental
Health Services, `X04` Other Paediatric Services, `X05` Other Surgical Services, `X06` Other Other
Services.

### The roll-up exceptions, which explain why codes are missing

NHS folds specific codes into a named one **[G §10.1.4, p.45]**:

- **Spinal Surgery (108), Orthopaedic (111) and Trauma Surgery (115) are reported inside Trauma and
  Orthopaedics (110).**
- **Maxillofacial Surgery (144) and Oral and Maxillofacial Surgery (145) are reported inside Oral
  Surgery (140).**
- **Cardiothoracic Surgery** may be reported as 170, *"or an aggregation of 172 (Cardiac) and 173
  (Thoracic)"*.
- Sub-specialties such as 306, 307, 308 and 309 *"are all within the Medical Services group and
  should therefore be included in the 'Other - Medical Services' line"* **[G §10.1.4, p.45]**.

So high-profile specialties absent from the named 18, such as Clinical Oncology (800),
Endocrinology (302), Clinical Haematology (303), Radiology (810) and Audiology (840), are **not
missing**. They are inside the Other buckets. That is why the Other buckets carry roughly a quarter
of all demand.

Two consequences for the project:

1. **The named specialties are already aggregates.** A "department" in this project is a reporting
   category, not a clinical unit. A capacity request for Trauma and Orthopaedics implicitly covers
   spinal and trauma surgery.
2. **NHS's own pre-2021 structure was "19 treatment functions (including 'Other')"** **[AR-1920 §7]**.
   The project's 19-series design, 18 named plus one merged `X_OTHER`, is not an invention. It
   reproduces NHS's own reporting structure exactly.

### A rule that must be obeyed everywhere

A completed pathway is reported against the treatment function of the activity that **stopped the
clock**, and *"the treatment function against which an incomplete (open) RTT pathway is reported can
change while the RTT pathway progresses"* **[G §10.1.4, p.45]**.

So a pathway can migrate between departments while waiting. Department-level demand and
department-level backlog are therefore not perfectly reconcilable at the individual-pathway level,
which is a second, smaller reason the accounting identity does not close per department.

---

## 5. The waiting-time bands, exactly

Do not guess the boundary convention. NHS states it in days **[G §10.1.7, p.46]**:

- Bands are *"0-1 weeks, >1-2 weeks, >2-3 weeks, then for all weekly time bands through to >103-104
  weeks, >104 weeks."*
- *"0 to 1 weeks includes patients waiting/having waited 0, 1, 2, 3, 4, 5, 6 and 7 days"* - **eight**
  day-values in the first band, not seven.
- *"17 to 18 weeks includes patients waiting/having waited 120, 121, 122, 123, 124, 125 and 126
  days."*
- **"A patient who has waited exactly 18 weeks (126 days) is included in the 17-18 weeks time
  band."**
- *"51 to 52 weeks includes patients waiting/having waited 358, 359, 360, 361, 362, 363 and 364
  days"*; *"104+ weeks includes patients waiting/having waited 729 days and more."*
- A clock that starts and stops the same day has an RTT time of zero days and is reported *"in the
  0-1 week time band"* **[G §10.1.7, p.46]**.

**The consequence for the code, and it is an off-by-one waiting to happen:** exactly 18 weeks is
*within* standard, not a breach. The >18-week breach count is the sum of bands **strictly after** the
17-18 band, that is 127 days and over, starting at `Gt 18 To 19 Weeks`. Getting this wrong silently
mis-defines the agentic layer's headline metric for all 96 months.

### What the standard actually is

The 18-week standard is a legal right, not a target. Providers and commissioners must meet patients'
*"legal right to start consultant-led non-emergency treatment within a maximum of 18 weeks from
referral"* **[G §1.1, p.5]**. The operational standard is that **92%** of incomplete pathways are
within 18 weeks, and since 2015 this incomplete-pathway measure is *"the sole measure of patients'
constitutional right to start treatment within 18 weeks"* **[G §1.1, p.5]**. The admitted (90%) and
non-admitted (95%) standards were abolished in October 2015 **[AR-1920 §3.2]**.

That is why 18 weeks is the right line for the agent to project against, and why 52 weeks is a
meaningful severity threshold rather than an invented one: NHS introduced *"a zero tolerance of any
referral to treatment waits of more than 52 weeks in 2013/14"* **[AR-1920 §3.2]**.

---

## 6. Three structural breaks, not one

The project had documented one break, at April 2021. There are three, and the first is a year
earlier than the project believed.

### Break 1: April 2020, the commissioner and parent-organisation reorganisation

**This was not previously in the project record and it corrects a stated fact.** From
**[SPN-Jul20 p.3]**, verbatim:

> "From April 2020, 14 NHS England (Region, Local Offices), also known as Direct Commissioning
> Offices (DCO), were replaced by 42 sustainability and transformation partnerships (STPs) as the
> Higher-Level Health Authority in NHS Organisation Reference Data. As a result, the
> Provider/Commissioner Parent Org Code/Parent Name columns in the Full CSV data file now show the
> relevant STP code/name."

And on the commissioner axis, **[SPN-Jul20 p.2]**:

> "The overarching commissioning code X24, which was used for all NHS England Commissioned activity
> until March 2020, is being phased out from the monthly RTT data return with effect from the **April
> 2020** data return onwards. Providers that are able to submit data under the relevant commissioner
> code ... were asked to do so from the April 2020 data return onwards. The X24 code will continue to
> be available until further notice for those providers that are not able to make the change at this
> time **because of the need to divert resources to support the response to COVID-19**."

The press notice lists all 23 replacement NHS England commissioning-hub and region codes.

*This explains, from source, a pattern the project had only measured.* The project measured the
`Provider Parent Org Code` column as carrying **14** distinct values in 2018-19 with **0%** agreement
against the ODS parent, **56** in 2020, and **42** from 2021 with roughly 74% agreement. That
progression is now fully explained: 14 DCOs, replaced from April 2020 by 42 STPs, with 56 being both
vocabularies coexisting during the changeover year.

Two corrections follow:

- The entity chain is **DCO to STP to ICB**, not "region to ICB". The 42 that appeared in April 2020
  were **STPs, not ICBs**; ICBs became statutory in July 2022. A 2020 or 2021 parent code is an STP
  code that later carried over.
- The X24 phase-out is a **phased change spanning April 2020 to April 2021**, not a step at April
  2021. Guidance **[G §10.1.1.3, p.42]** describes it as complete at April 2021, which is where the
  project's records place the whole change.

Because the project drops the commissioner columns, nothing in the canonical table is wrong. But any
use of the commissioner axis crosses a vocabulary change beginning a year earlier than documented,
and that includes the own-ICB-share measurement used to justify the escalation design.

### Break 2: April 2021, the collection template

NHS lists three simultaneous changes **[G §10.1.1.3, p.42]**, restated in **[SPN §4, p.13]**:

1. *"Phased out the use of X24 code entirely and moved to the more granular NHS England commissioning
   codes."*
2. *"Additional weekly time bands from 52-53 weeks to 104+ added to Parts 1A, 1B, 2 and 2A of the
   collection."*
3. *"Changes to the treatment function categories"*, being (a) name updates, and (b) the single
   "Other" category separated into five groups.

*Measured consequences:* 69 columns before, 121 after, changing cleanly at April 2021 with no
intermediate variants. 53 band columns before, 105 after. **The bands below 52 weeks are identical in
both eras**, which is why the >18-week metric is era-stable and only the >52 tail needs reconciling.

The reconciliation direction is forced and not a choice: you can turn fine into coarse by adding up,
never coarse into fine. So a series spanning the break must reconcile to the **pre-2021** form.

**The renaming trap.** The codes did not change; 18 of 24 names did (*measured*). Grouping by name,
or by code and name together, silently splits every specialty into a 36-month row and a 60-month row.
Neither looks wrong and both are. **Join on codes, never names.**

### Break 3: February 2024, community services leave RTT

From **February 2024** consultant-led community services were removed from RTT. NHS: where a
community service is consultant-led, *"these pathways should be recorded in relevant Community
datasets and should be excluded from the RTT data submissions ... Community Paediatrics and Community
Medicine ... should not be reported within RTT data submissions"* **[G §7.2, p.32]**.

The measured impact, from NHS **[SPN §4, p.15]**: *"a decrease of approximately **43,000 pathways**
within the community paediatric specialty"*, of which *"about 36,000 ... were excluded from the
February 2024 figures and most of the remaining 7,000 ... from the March 2024 figures"*, including
*"approximately 4,400 fewer 52-week waits, 2,500 fewer 65-week waits and 1,400 fewer 78-week waits."*
These pathways *"are recorded under 'Other - Paediatric Services' and 'Other - Other services'"*,
which is to say inside `X04` and `X06`, both of which merge into `X_OTHER`.

**So `X_OTHER` has a genuine downward step in February and March 2024 that is neither a data error
nor COVID.** The 18 named specialties are essentially unaffected. The project's boundary-continuity
assert guards April 2021 only and does not look at February 2024. This has never been checked.

---

## 7. COVID: what actually happened to this data

### The collection was never suspended

All twelve months of 2019-20 and all twelve of 2020-21 are published, confirmed by inspecting the
financial-year pages directly. **There is no gap in the RTT series.** The COVID effect is in the
values and in per-provider submission completeness, not in coverage.

### The clock rules did not change

This is important, and it was verified from the COVID-specific guidance **[C0009]**, issued 24 March
2020, rather than assumed:

- Patients self-isolating are covered by the guidance on patients *"temporarily unfit"* for
  treatment, so *"the RTT clock should continue to tick"* **[C0009 p.1]**.
- Shielding groups asked to stay at home for 12 weeks: *"it will be appropriate in most circumstances
  to consider them 'temporarily unfit' for treatment and the RTT clock will therefore continue to
  tick. This will ensure that they remain on an active RTT waiting list and their waiting times are
  visible"* **[C0009 p.1]**.
- Patients declining dates through fear: *"The usual rules on patient choice will apply and the clock
  should continue to tick"* **[C0009 p.2]**.
- Provider-cancelled appointments: *"If a provider cancels an appointment at any point in the RTT
  pathway, this has no effect on the RTT waiting time. The RTT clock should continue to tick"*
  **[C0009 p.3]**.
- Suspended services: the usual provider-cancellation rules apply and *"the RTT waiting time clock
  should continue to tick"* **[C0009 p.3]**.
- Active-monitoring clock stops were expected to *"apply to only a few patients"* **[C0009 p.2]**.
- *"Delay related to COVID-19 is not a reason to add a patient to a planned list"* **[C0009 p.4]**.

**Therefore the COVID waiting-list dynamics in this dataset are real accumulation, not a change of
measurement convention.** That is what makes the COVID window a genuine stress test of the system
rather than an artefact of redefinition, and it is the documentary basis for the project's claim
that COVID is a usable evaluation scenario.

### What the numbers did

NHS's own published figures, which include their estimates for missing trusts:

| Quantity | Value | Source |
|---|---|---|
| Clock starts, Mar 2020 vs Mar 2019 | 58,400 per working day vs 85,100, **down 31%** | [AR-1920 §1.5] |
| Completed admitted, Mar 2020 vs Mar 2019 | 9,900 per wd vs 15,000, **down 34%** | [AR-1920 §1.3] |
| Completed non-admitted, Mar 2020 vs Mar 2019 | 46,300 per wd vs 53,600, **down 14%** | [AR-1920 §1.4] |
| Waiting list, Feb to Mar 2020 | **fell by 189,000** | [AR-1920 §1.2] |
| Completed pathways, 12 months to Jul 2020 | **down 17.3%** year on year | [SPN-Jul20 p.4] |
| Waiting list, end Jul 2020 vs Jul 2019 | **down 8.9%** | [SPN-Jul20 p.4] |

### The fact that changes how the shock should be modelled

**The waiting list fell through the first COVID months.** NHS explains why: *"The fall in the list
occurred as, while COVID-19 resulted in a reduction in completed pathways, there was an even greater
decrease in clock starts"* **[AR-1920 §1.2]**.

Demand collapsed harder than throughput. So in the **forecast target**, which is `Part_3`
clock-starts, COVID is a **V-shaped collapse and recovery, not a spike**. The spike people picture is
in the long-wait tail, and it is real but it is a different variable.

### The 18-week standard and the long-wait tail through the collapse

From **[SPN-Jul20 Table 2]**, the incomplete-pathway measures:

| Month | % within 18 weeks | Median wait (weeks) | 92nd percentile (weeks) |
|---|---|---|---|
| Feb 2020 | 83.2% | 7.5 | 24.7 |
| Mar 2020 | 79.7% | 8.9 | 26.5 |
| Apr 2020 | 71.3% | 12.2 | 30.6 |
| May 2020 | 62.2% | 15.3 | 34.3 |
| Jun 2020 | 52.0% | 17.6 | 37.4 |
| **Jul 2020** | **46.8%** | **19.6** | **40.0** |

The agentic layer's headline metric moves roughly **36 percentage points in five months**. That sets
the scale any "regime change" classifier has to detect and is a useful calibration target.

**52-week waiters**: 3,097 at the end of March 2020, up nearly 1,500 from February for two reasons
NHS states explicitly, being *"activity being down generally as a result of COVID-19, and hence more
waiters moving from 48-52 weeks in February to 52+ week waiters in March"* and *"patients that had
already waited more than 52 weeks at the end of February not being treated during March"*
**[AR-1920 §3]**. By July 2020 the figure was **83,203**, a 27-fold rise in four months.

This is the clearest justification in the whole record for keeping `waiting_gt52` in the column
contract. Two services with identical 18-week breach counts can have entirely different tails, and
during COVID the tail is where the story is.

### The implication for the forecaster, stated carefully

The concern that a model trained across COVID is biased is legitimate, and the mechanism can be named
precisely rather than gestured at:

- COVID occupies roughly **19 to 22% of every 96-point series**.
- **Per-client scaling is the concrete failure route.** The design standardises each client series
  because trusts differ roughly 100-fold in size. A mean and standard deviation computed over a
  window containing the shock is distorted for all roughly 1,870 series, and not uniformly across
  specialties. This corrupts model inputs before any architecture decision.
- A model trained across the shock learns a transition dynamic that does not recur.

What does **not** follow is that the pre-COVID data should not be acquired. The forecaster is
trained; the agentic layer is not, being a state machine over forecasts, actuals and thresholds. The
COVID months can be excluded from *forecaster training* while retained as the agent's *evaluation
scenario*. Every genuine remedy - split placement, a regime indicator, sample weighting, scaling
computed on a declared clean sub-window - is a within-window modelling choice that requires the data
to be present. Acquiring everything and declaring the training window explicitly is strictly stronger
than pre-deleting, because only the former can produce the with-and-without ablation that
demonstrates the concern was handled.

---

## 8. Unreported removals: NHS's own name for our F-15

This project independently discovered that the accounting identity leaks, recorded it as F-15, and
defended it against the obvious alternative explanation. **NHS England publishes a document about
exactly this**, and it was not previously in the project record.

### The formula is identical

**[UR]** defines it verbatim:

> "The term unreported removal describes any flow on or off the waiting list not captured in the
> submitted clock starts (new RTT periods) and completed pathways numbers. It is calculated as the
> balancing item ... **Unreported removals = waiting list at start of period + clock starts during
> period – completed pathways during period – waiting list at end of period.**"

That is algebraically the project's residual with the sign reversed. The project computes
`actual − predicted`, so its residual is negative where NHS's is positive.

### The magnitude, and a denominator warning

*"Unreported removals have occurred throughout the history of the statistics, averaging **17% of
total removals prior to the pandemic and 14% since 2021**"* **[UR]**, and *"they averaged 281
thousand per month"* pre-pandemic.

**These are not directly comparable to the project's −15.28%.** NHS's denominator is *total
removals*; the project's is *demand*. The two must be recomputed on a common basis before either is
quoted against the other. This is exactly the mean-of-ratios versus ratio-of-means discipline the
project already adopted, applied to a different axis.

### NHS confirms the project's contrarian re-test, independently

The project worried that its residual was manufactured by the panel boundary: a patient transferring
from a panel trust to a non-panel provider leaves the panel's list without a panel completion. It
re-ran on all 653 providers and the residual survived.

NHS reaches the same conclusion from first principles **[UR]**:

> "the patient's pathway will be added to the waiting list in the receiving provider without an
> associated clock start and removed from the originating provider's waiting list without an
> associated completed pathway ... However, **the combined effect of such transfers on unreported
> removals at England level should be neutral.**"

### The causes, which are richer than the project assumed

The project attributed the leak to rule-5 non-treatment stops, deaths and transfers. NHS enumerates
more, and one of them is structural rather than clinical **[UR]**:

- **Late recording is the big one.** *"providers are required to submit only removals that happened
  within the reporting month. If they identify removals that happened in previous months, they won't
  be counted in the latest month's figure, but will be taken into account in their latest waiting
  list number. So, those 'historic' removals are 'lost' to reporting."* This is reinforced by
  **[G §10.1.5, p.45]**: pathways found to have completed in a previous month *"should not be added
  to the monthly reporting of completed RTT pathways for the current reporting period."*
- **Clock nullifications**, where a patient does not attend the first appointment after the referral
  that started the clock, or the provider cannot accept the referral because it is not clinically
  appropriate.
- **Duplicate pathways** identified and removed by routine validation.
- **Submission gaps.** *"A lack of triangulation ... also occurs when a provider does not submit data
  for a period of time due to data quality issues."*

NHS is careful that *"unreported removals are not the same thing as cases removed from the list
through validation work"*, although validation may increase them.

### What unreported removals actually are, from record-level linkage

NHS characterises them using the WLMDS, which the aggregate return cannot do **[UR]**. In 2025, for
the subset with a recorded reason (113,000 records):

| Reason | Unreported removals | Reported completed pathways |
|---|---|---|
| Patient started treatment | **49%** | 50% |
| Decision not to treat | 23% | 29% |
| DNA at first appointment | **11%** | 1% |

And by linkage to activity data: *"at least 73% of unreported removals involved some outpatient or
admitted activity, compared with at least 87% of reported completed pathways"*, with around 32%
involving activity *after* the clock stop against 36% for reported completions.

NHS's conclusion: unreported removals are *"very similar in nature to reported completed pathways"*.

### What this changes for the project

1. **F-15 is confirmed at source and is not an artefact.** It is a known, named, quantified NHS data
   property.
2. **It is therefore not a novel discovery**, and should not be presented as one. The project's
   actual contribution is measuring it **per trust × specialty**, which NHS does not publish.
3. **The phase-4 removal term may become obtainable rather than estimable.** NHS states an intention
   to include *"figures for unreported removals"* within the published official statistics **[UR]**.
   Whether that series already exists in the RTT Overview Timeseries file has not been checked.
4. **Roughly half of the leak is treatment that happened.** Since 49% of unreported removals are
   patients who started treatment, a decision layer that treats the residual purely as attrition will
   understate true throughput. The removal term should be split, not modelled as a single loss rate.

---

## 9. Non-submission, and the estimates that fill it

### Providers can and do stop submitting

NHS has a formal policy **[G §10.3, p.50]**. Suspension requires a board-level decision: *"The
decision to suspend the submission of data needs to be a decision taken and owned by the board of a
provider"*, and *"The NHS trust will be highlighted in any national publications as not being able to
submit data."*

They are named, and they recur throughout the window, not only during COVID:

| Month | Non-submitting providers | Source |
|---|---|---|
| Jul 2020 | **Barnsley (RFF)** and **Royal Free London (RAL)** submitted nothing; **Bradford (RAE)** submitted no completed-admitted, completed-non-admitted or new-RTT-periods data; North West Anglia (RGN) returned to reporting | [SPN-Jul20 p.1] |
| Oct and Nov 2022 | **Frimley Health (RDU)** and **Manchester University (R0A)** | [SWA 2022-23] |
| Dec 2022 | **Manchester University (R0A)** | [SWA 2022-23] |
| Mar 2026 | **Sheffield Teaching Hospitals (RHQ)** | [SPN p.1] |

Three consequences, and the middle one is a defect in the current build:

1. **The RAE case explains a puzzle the project had recorded but not diagnosed.** The project found
   that RAE appears in 96 months but has demand rows in only 74, and treated it as a definitional
   curiosity about what "present" means. It is not. It is a named partial submission during COVID.
2. **A zero in the panel may be a non-submission rather than real activity.** After excluding the 524
   structurally-absent series, the remaining zeros are currently assumed real. That assumption is now
   known to be false for at least the named trust-months above, and it has never been quantified. The
   panel needs a permanent per-trust-per-month "was this provider reporting" flag. It is not a
   COVID-specific patch.
3. **A post-COVID window does not escape this.** October to December 2022 and March 2026 sit inside
   every candidate post-COVID cut, and Manchester University is one of the largest trusts in England.

### How NHS fills the gaps, and why our totals differ from theirs

The method, from **[AR-1920 §6.3]**:

- Estimates use **the last month submitted before the gap**.
- For **incomplete pathways**, the prior month's total is carried forward to every missing month.
- For **completed pathways**, the prior month's **per-working-day** rate is carried forward and
  multiplied by each missing month's working days.
- *"Estimates are only applied for total admitted, non-admitted and incomplete pathways and are
  included for **acute NHS providers**."*

Four things follow:

1. **The Full CSV contains no estimates.** It is the raw submitted aggregate. The published headline
   contains estimates. So the project's measured March 2026 `Part_2` total of **7,045,510** and the
   press-notice headline of **7.1 million** differ **by construction, not by our error**. This closes
   the long-open F-10 question.
2. **The estimates are not broken down by treatment function**, so there is no specialty-level
   published figure available to reconcile against.
3. **Independent-sector gaps are never estimated.** Only acute NHS providers are covered.
4. **The estimation method is itself a persistence forecast.** Carry the last observation forward.
   That is worth noting given persistence is one of the project's three required baselines: NHS
   itself uses persistence when it has to impute.

---

## 10. The two sectors are not symmetric

The RTT return covers independent-sector providers as well as NHS trusts, and they report the same
columns. That similarity is superficial. The obligations differ, and the differences are documented.

### The reporting obligation is not the same

Both statements appear in the same paragraph **[AR-1920 §6.3]**:

> "The NHS Standard Contract requires providers to report monthly RTT data; data submission is
> **mandatory for all NHS trusts** that provide services that fall within the scope of consultant-led
> RTT waiting times measurement. Independent Sector providers are **encouraged to engage** in the RTT
> data collection process ... **When Independent Sector providers do not have the technical
> capability to submit data, NHS commissioners can submit on their behalf.**"

The guidance uses the softer verb for independents too: they *"should engage in the RTT data
collection process"* **[G §10.1.1.1, p.40]**, against the contractual requirement that binds trusts.

Three asymmetries, each sourced:

1. **Mandatory against encouraged.** Two different data-generating processes wearing one schema.
2. **The submitting entity may not be the provider.** For some independent codes the organisation
   that holds the data is not the organisation that filed it, which undercuts the premise of
   federated learning for those rows specifically.
3. **Missing-data estimation covers acute NHS providers only** **[AR-1920 §6.3]**. The two sectors
   are treated differently in NHS's own corrections.

### Independent RTT rows are purchasing decisions, not private demand

Independents submit RTT only *"where NHS care is funded and directly commissioned by a SUB-ICB or NHS
England"* **[G §10.1.1.1, p.40]**. Privately funded activity at the same hospital is entirely absent.
So the independent series is a lower bound on independent activity and is not a measure of the
private market.

More importantly, the volume is **directed**. The NHS and independent-sector partnership agreement
places commissioning with ICBs and states that *"improving access to treatment in the most challenged
specialties and geographies is a priority for commissioners"*, with independent providers committing
*"to providing support in the most challenged specialties when enabled to do so"* **[PA]**.

**This is a first-order confounder.** Independent share rises *where and because* waits are worst.
Independent share and trust backlog are jointly determined. Any finding of the form "independent
share rose and trust demand fell, so independents absorbed demand" is observationally
indistinguishable from "trust demand was high, so commissioners bought independent capacity."

### What the project measured about independents

| Finding | Value |
|---|---|
| Independents report genuine demand | 11,541,248 referrals, **0 zero-months** |
| National independent share of demand | 6.20% to 7.70% across the window |
| Specialties with a trending share | 6 of 24; fastest **C_130 Ophthalmology +2.20pp/yr, 6.2% to 19.6%** |
| Share of total demand | 7.4%, from 457 providers |
| Full-window coverage | **64%** of public providers span all 96 months, against **28%** of independents |
| Data-quality anomalies | **46 of 47** `Part_2A > Part_2` violations are independent rows |
| Scale and coverage | roughly 1/20th the scale, median **11 of 19** departments, 86.5% against 98.5% non-zero cells |

**What this supports:** independents are real, growing, and concentrated in one specialty.

**What it does not support:** that independents are responsible for demand change. A national share
moving 6.20% to 7.70% over eight years cannot account for a waiting list that roughly doubled. In
**ophthalmology specifically** the shift is large enough to matter, and that is the one place the
claim is plausible.

**The decisive test has never been run** and requires the data: within a trust × specialty, does
trust demand fall in the months *after* independent share in that trust's ICB rises. The confounder
must be pre-registered before the model is fitted, because a positive contemporaneous association is
expected and proves nothing. If the lag structure does not separate them, the honest finding is that
RTT alone cannot answer the question.

### A separate independent-sector break, outside RTT

**[REA]**: the Independent Sector Weekly Activity Return has **ceased**, and from October 2024
independent-sector activity is reported through SUS Outpatients and Admitted Patient Care instead.
NHS states plainly that *"due to definitional differences the SUS data are not comparable to the IS
WAR data."* This does not affect the RTT monthly return, but it means any attempt to corroborate the
independent story against NHS's own independent-activity series crosses a definitional break at
October 2024.

Also from **[PA]**: *"In 2024 the independent sector treated over 1 million NHS patients."* Useful as
an external order-of-magnitude check, on a different basis (patients treated, not pathway
clock-starts), and it should not be equated with the project's measured volumes.

---

## 11. What this means for the federation

### The clients are the 126 NHS trusts

The project statement asks two different things of a client, and they come apart. A client must (a)
help train the shared forecaster without surrendering data, and (b) sit in the trust to ICB to
national escalation as a body that can *receive* an allocation.

| Requirement | Independents | Basis |
|---|---|---|
| Report the same columns | **Yes** | Same SDCS return **[G §10.1.1.2]** |
| Report genuine demand | **Yes** | Measured, 0 zero-months |
| Submit under the same obligation | **No** | **[AR-1920 §6.3]** |
| Submit their own data | **Not always** | **[AR-1920 §6.3]** |
| Covered by NHS missing-data estimation | **No** | **[AR-1920 §6.3]** |
| Have an ICB parent for escalation | **No** | ODS `RE5`; the `icb_ods` null rate matches the independent share exactly |
| Can receive an NHS capacity allocation | **No** | An ICB can buy from them, not direct staff and capital into them |
| Comparable scale and coverage | **No** | Measured, roughly 1/20th scale, 11 of 19 departments |
| Report the same demand construct | **No** | Only NHS-commissioned care **[G §10.1.1.1]** |

Independents pass the schema test and fail every structural test. The federation clients are the 126
public trusts with complete history.

### How RTT satisfies the project statement in both directions at once

This is the part worth stating clearly, because it turns an exclusion into a design.

The independents are not discarded. They are **the other half of the board's decision**. The
allocate-or-buy framing requires a measure of purchasable substitution capacity per ICB per
specialty, and RTT supplies exactly that, because independent providers report the same
treatment-function-level volumes under the same collection at the same monthly grain.

So one dataset serves both engines:

- **The forecaster** gets 126 institutional silos with complete 96-month history, differing widely in
  size and casemix while their demand co-moves. That is textbook cross-silo federated learning.
- **The decision layer** gets the escalation hierarchy from ODS, the 18-week standard as a real legal
  line, the backlog and its long-wait tail as state, and the independent volumes as the revealed,
  purchasable substitution capacity the human tier weighs against internal allocation.

Adding independents as clients would actively damage the first. Cross-silo federated learning assumes
few, large, reliable institutional clients. Adding 457 small, irregularly-reporting providers, or
even the 126 with full history, moves the setting toward cross-device heterogeneity. That is a
different research problem with different baselines, and it would be entered by accident rather than
by design.

The two flags the project already carries encode this correctly: `fl_client` for who trains the
model, `allocatable` for who can receive capacity. Neither implies the other, which is what makes the
inclusion question a runnable ablation rather than a design argument.

### The ablation stays available, and stays pre-registered

If independents are ever admitted as clients, the pre-registration already recorded stands: score on
the **fixed 126-trust series in both arms**, so the metric population does not change with the
training set; pin aggregation weighting to n-samples, so the test is inclusion under the deployed
scheme rather than a weighting artefact; and register the hypothesis against the project's earlier
refutation, where "federation rescues the small data-poor client" was tested and refuted, with gains
in mid-size clients and the thinnest clients better off trained alone.

The documentation now supplies a *reason* to expect little gain, which strengthens the
pre-registration rather than replacing it. If the ablation is run, `sector` must become a model
input, because independent `Part_3` is commissioned flow rather than organic demand and the mix is
measurably non-stationary.

---

## 12. Corrections to the project's own records

Stated explicitly so they are not lost, and because a record that only accumulates confirmations is
not being checked.

| # | What the project held | What the source says |
|---|---|---|
| 1 | The parent-organisation column changes at April 2021 | It changes at **April 2020**: 14 DCOs replaced by 42 STPs in ODS **[SPN-Jul20 p.3]** |
| 2 | The X24 commissioner phase-out is an April 2021 step | It is **phased from April 2020 to April 2021**, deliberately extended because providers were diverted to the COVID response **[SPN-Jul20 p.2]** |
| 3 | The pre-2020 parent values are "NHS regions" | They are **NHS England Region/Local Offices, i.e. Direct Commissioning Offices**; and their 2020 replacements were **STPs, not ICBs** |
| 4 | The accounting-identity leak is a project finding | It is NHS's **published "unreported removals"**, with an identical formula and a quantified magnitude **[UR]** |
| 5 | The leak is attrition | Roughly **49% of it is patients who started treatment** but were recorded late **[UR]** |
| 6 | RAE's 74-of-96 demand months is a definitional curiosity | It is a **named partial non-submission** during COVID **[SPN-Jul20 p.1]** |
| 7 | Non-submission is a COVID-era concern | It recurs throughout: **RDU and R0A in Oct to Dec 2022**, RHQ in Mar 2026 |
| 8 | F-10's press-notice reconciliation is open | **Closed.** The Full CSV carries no estimates; the headline does. They differ by construction **[AR-1920 §6.3]** |

And one confirmation worth recording because it validates a design choice that looked arbitrary:
**NHS's own pre-2021 reporting structure is "19 treatment functions (including 'Other')"**
**[AR-1920 §7]**. The project's 18-named-plus-`X_OTHER` design reproduces it exactly.

---

## 13. What remains open

Ordered by how badly each could damage a result.

1. **The non-submission zeros.** Named trust-months exist and have never been quantified. Until they
   are, some panel zeros are silently wrong, and they are concentrated exactly where the agentic
   layer is meant to be evaluated. Needs a permanent reporting flag, not a patch.
2. **The February 2024 step in `X_OTHER`.** A real 43,000-pathway discontinuity that no assert
   checks. Measure it against local variation the way April 2021 was measured.
3. **The evaluation guard for structurally-absent series.** 524 all-zero series in the forecast path
   would *improve* macro-sMAPE for reasons unrelated to model quality. Needs a mask in the windowing
   **and** in the metric's series set.
4. **The removal term, now split.** Half the leak is late-recorded treatment, not attrition. Check
   whether NHS already publishes the unreported-removals series in the RTT Overview Timeseries file
   before estimating it.
5. **The residual on a common denominator.** Recompute the project's −15.28% as a share of total
   removals so it can be set against NHS's 17% and 14%.
6. **The substitution test.** Does trust demand fall after independent share rises, with the
   confounder pre-registered. This is the only way to answer the independents question honestly.
7. **The training-window ablation.** Full window against post-COVID only, both tested on a post-COVID
   horizon, with the expectation written down first.
8. **The sha256 manifest.** The archives are gone and revisions keep arriving upstream. Without a
   baseline there is no way to tell a revision from a corruption.
9. **The residual ICB disagreement.** Roughly 26% of post-2021 rows disagree between the file and
   ODS, and it has never been chased on a sample of disagreeing trusts.
10. **KH03.** 61 workbooks, validated, read by nothing. Give them a role or drop them. Note the
    resolution mismatch: quarterly and per trust, against monthly and per trust × specialty.
11. **DCB0095 and DCB0028.** Named by the guidance, text never pulled.

---

*Compiled 2026-07-26 from primary NHS England sources. Every sourced claim carries its citation.
Project numbers are labelled "measured" and are reproducible from the CSVs. The reasoning behind
every decision, including the mistakes, is in [`WORKLOG.md`](WORKLOG.md), Entries 12 to 14.*
