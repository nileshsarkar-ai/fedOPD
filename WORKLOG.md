# fedOPD — Project Worklog

**Project:** Federated forecasting of outpatient demand and flow across NHS England providers
**Repository:** `fedOPD` (private)
**Document purpose:** Chronological record of objectives, methods, decisions, results and open issues. Maintained so that any result in the project can be traced back to its source data, the processing applied to it, and the reasoning behind each methodological choice.

**Conventions for this document**
- Newest entries at the end. Each entry is dated and self-contained.
- Every quantitative claim states how it was measured.
- Negative results, defects and dead ends are recorded in full. A worklog that records only successes cannot be used to audit a result.
- Observation, assumption and inference are stated separately.

---

# Entry 1 — 2026-07-24
## Phase 1: Data acquisition

### 1.1 Objective

Acquire and validate the three datasets required for the project:

1. NHS England Referral to Treatment (RTT) monthly "Full CSV" extracts, April 2018 – March 2026, providing both the demand table (Part 3) required at phase 2 and the flow tables (Parts 1A/1B, 2, 2A and the >18-week bands) required at phase 4.
2. A provider → Integrated Care Board (ICB) and geography reference, required for the hierarchy tiers at phases 10–12.
3. KH03 overnight bed availability and occupancy, optional, required only for the bed-context extension at phase 11.

### 1.2 Data sources and provenance

| # | Dataset | Source | Access method |
|---|---|---|---|
| 1 | RTT monthly Full CSV extracts | NHS England, *RTT Waiting Times* statistical work area, one page per financial year 2018-19 to 2025-26 | HTML scrape of the eight financial-year index pages, followed by direct download of the linked ZIP archives |
| 2 | Provider → ICB reference | NHS Organisation Data Service, ORD API (`directory.spineservices.nhs.uk/ORD/2-0-0`) | REST API |
| 3 | KH03 overnight beds | NHS England, *Bed Availability and Occupancy* (overnight series) | HTML scrape and direct download |

The ORD API was selected in preference to the static `etr.zip` organisation file, which returns HTTP 403 from some networks.

Only the Full CSV archives were retrieved. The Incomplete, Admitted, NonAdmitted and New-Periods XLS files published alongside them, in both Commissioner and Provider variants, are pre-aggregated views of the same underlying table and were deliberately excluded.

### 1.3 Source validation performed prior to implementation

The acquisition code was not written against assumed URL patterns. The eight financial-year index pages were retrieved and parsed first, and the following were established empirically:

- All eight pages return HTTP 200 and each exposes **exactly twelve** Full CSV archives, giving **96 months, April 2018 – March 2026, with no gaps and no duplicates**.
- Where NHS England has reissued a month, both the original and the revised archive are linked from the same page. The selection rule adopted is *revised supersedes original*, keyed on the three-letter month plus two-digit year token in the filename. This rule was confirmed to reproduce the known-correct URLs for March 2019, March 2022 and March 2026.

**Finding — published file sizes are unreliable.** The archive `Full-CSV-data-file-Mar22-revised-ZIP-111805K.zip` is named as though it were approximately 110 MB. A range request returned `Content-Range: bytes 0-0/4504261`, i.e. the file served is 4.5 MB. Inspection of the leading bytes returned `PK\x03\x04`, confirming a structurally valid ZIP archive rather than a truncated or error response.

*Inference:* the size token in these filenames reflects an earlier revision of the file and is not maintained. *Decision:* filename size tokens are not used for validation anywhere in the pipeline. Integrity is established by CRC verification of archive contents instead (§1.8).

Further filename irregularities observed across the eight years: an empty size token (`Full-CSV-data-file-Sep18-revised-ZIP-K.zip`) and apparently random alphanumeric suffixes on recent months (`-SrRW6y`, `-1Xmjkk`, `-9j03fJT`). These affect filename parsing only, not file content.

### 1.4 Defect identified and corrected prior to first run

The provider → ICB lookup was initially implemented to select organisation relationships whose target carried ODS primary role **RO318**. Direct inspection of live API responses showed this to be incorrect: an NHS Trust is linked to its ICB by an **active RE5 ("is commissioned by") relationship whose target organisation carries primary role RO261**. Verified against a known case — North London NHS Foundation Trust resolves to `Z9B2Z`, NHS West and North London Integrated Care Board.

*Significance:* under the original filter every `icb_code` value would have been returned empty. The failure mode is silent — the process completes without error and produces a well-formed CSV of the expected row count in which one column is uniformly blank. This class of defect is not detectable from exit status and would have propagated into the phase 10–12 hierarchy. The filter was corrected before any production run.

### 1.5 Results

| Dataset | Outcome | Location |
|---|---|---|
| RTT archives | 96 of 96 retrieved, 329 MB | `data/rtt_zips/` |
| RTT extracts | 96 CSV files, 7.7 GB | `data/rtt_csv/` |
| Provider → ICB reference | 544 organisations; 214 with an ICB code; 247 with status Active | `data/reference/trust_icb.csv` |
| KH03 overnight beds | 61 quarterly workbooks, 11 MB, earliest Q1 2011-12, latest Q4 2025-26 | `data/kh03/` |

**Interpretation of the 214/544 ICB coverage.** This is the expected result, not a shortfall. The ORD query returns all organisations that have ever held primary role RO197, including dissolved and merged trusts, of which only 247 are currently Active; an organisation that no longer exists has no current commissioner and therefore no active RE5 relationship. Historic organisations were retained deliberately because they appear as providers in the earlier RTT months and are required for those periods to join correctly.

**Structural spot-check.** One month (October 2019) contains 204,137 lines. The header carries the fields required downstream, including `Period`, `Provider Parent Org Code`, `Provider Org Code`, `RTT Part Type`, `RTT Part Description` and `Treatment Function Code`. This is consistent with a table at provider × commissioner × treatment-function × RTT-part granularity.

### 1.6 Compute environment

| Component | Specification |
|---|---|
| Virtual environment | `fed_learning/` at repository root, Python 3.10.12 |
| Deep learning | PyTorch 2.13.0+cu130, torchvision 0.28.0 |
| Federated learning | Flower (`flwr`) 1.30.0 |
| Analysis | pandas 2.3.3, scikit-learn 1.7.2, scipy, statsmodels, pyarrow, matplotlib, seaborn |
| Notebook | JupyterLab; kernel registered as `fed_learning (CUDA)` |
| GPU | NVIDIA A100 80GB PCIe, driver 580.159.03, CUDA 13.0 |

**GPU access is mediated by MIG.** Multi-Instance GPU mode is enabled on this card. The GPU is reachable only through its MIG device, currently a single `7g.80gb` instance spanning the whole card (`MIG-c196af98-196a-5e8c-af32-0eff63a870e1`). Because that instance covers the entire card, PyTorch presents it as one ordinary device.

Availability was confirmed by execution rather than by capability query: `torch.cuda.is_available()` returns True, the device reports as `NVIDIA A100 80GB PCIe MIG 7g.80gb` with 84.7 GB of 85.1 GB free, and a 4096 × 4096 matrix multiplication was executed on the device successfully.

*Implication for the federated design:* MIG instances do not support peer-to-peer transfers or multi-GPU collective operations between them. Simulated federated clients must therefore run sequentially, or as separate processes sharing the single instance, and cannot be distributed across GPUs. Device selection should use the MIG UUID via `CUDA_VISIBLE_DEVICES` rather than an integer index, since integer indices are not stable if the instance layout is reconfigured. Per-process utilisation is not reported by `nvidia-smi` under MIG, so the usual method of checking whether the shared machine is busy is unavailable.

### 1.7 Storage management

The home filesystem was at 92% capacity (86 GB free) prior to the extraction of the RTT data. Three model directories were removed from `fable_KD/models/` at the project owner's explicit instruction, after confirming by inspection that each contained only downloaded weights, configuration files and HuggingFace lock files, and no project code:

| Directory | Reclaimed |
|---|---|
| `gemma-4-31B-it-qat-w4a16-ct` | 22 GB |
| `Qwen-AgentWorld-35B-A3B-AWQ` | 22 GB |
| `Qwen3.6-27B-AWQ` | 21 GB |

Filesystem after removal: **150 GB free, 85% used**. No other directory was modified.

*Noted for future reference, no action taken:* `~/.cache/huggingface/hub` retains separate cached copies of `gemma-4-31B-it-qat-w4a16-ct` and `Qwen-AgentWorld-35B-A3B`. Separately, `colm/ERDOS/forge-training/outputs/forge-7b-qlora/` holds six checkpoint copies of a 4.7 GB adapter (~28 GB total); if only the final checkpoint is required, this is the largest remaining recoverable allocation.

### 1.8 Verification protocol — defined, execution pending

File counts alone establish nothing about content integrity. The following checks were specified so that each is capable of failing on a real defect, and implemented in `verify.py`:

| # | Check | Defect it detects |
|---|---|---|
| 1 | CRC test of every member of all 96 archives, plus ZIP magic-byte check | Silent corruption in transit; HTML error pages saved under a `.zip` name |
| 2 | Size of each extracted CSV against its archive manifest entry | Incomplete or interrupted extraction |
| 3 | `Period` value inside each CSV against the month parsed from its filename | Mislabelled files at source; month-token parsing errors |
| 4 | Field count of the final row against the header | Truncated download not caught by other means |
| 5 | Distinct month coverage against the exact April 2018 – March 2026 set | Missing or duplicated reporting periods |
| 6 | Magic bytes of all 61 KH03 workbooks (ZIP for `.xlsx`, OLE2 for `.xls`) | Error pages served in place of spreadsheets |
| 7 | Provider codes from a recent RTT month joined against `trust_icb.csv`, match rate reported | Systematic join failure between the two datasets |

**Stated in advance:** check 7 is expected to return a match rate below 100%, because provider codes appearing in historic months include organisations that have since merged or dissolved. The measured rate will be reported as observed, and a low rate will be investigated rather than accepted.

### 1.8a Verification results — executed 2026-07-24

All seven checks were executed after the notebook re-run completed.

| # | Check | Result |
|---|---|---|
| 1 | CRC of every member of all 96 archives | **96 of 96 pass, 0 corrupt** |
| 2 | Extracted size vs archive manifest | **96 of 96 exact, 0 mismatched** |
| 3 | Internal `Period` vs filename month | **0 mismatches** across all 96 |
| 4 | Final-row field count vs header | **0 truncated or ragged** |
| 5 | Month coverage | **96 distinct months, 0 missing, 0 unexpected** |
| 6 | KH03 workbook magic bytes | **61 of 61 valid**, 0 HTML error pages |
| 7 | Provider-code join rate | 149 of 517 distinct providers matched (29%) — see §1.8c |

The acquired data is therefore intact: nothing was corrupted, truncated, mislabelled or missed. Two substantive findings emerged from the checks, both of which affect later phases.

### 1.8b Finding: the RTT schema changes in April 2021

Check 3 recorded two distinct column counts across the 96 months — **69 columns for the 36 months from April 2018 to March 2021, and 121 columns for the 60 months from April 2021 to March 2026**. The changeover is clean, with no mixed or intermediate variants.

The difference is confined to the long-wait bands. Up to March 2021 there is a single aggregate column, `Gt 52 Weeks SUM 1`. From April 2021 that column is removed and replaced by weekly bands — `Gt 52 To 53 Weeks SUM 1`, `Gt 53 To 54 Weeks SUM 1`, and so on up to 104 weeks. All other fields are unchanged.

*Consequence.* Any series spanning the change must reconcile the two representations. A consistent long-wait measure over the full eight years requires summing the weekly bands from April 2021 onward back into a single >52-week figure; the pre-2021 period cannot be disaggregated to match the later detail, so the coarser representation governs. This directly constrains the phase-4 flow extraction, which uses the >18-week bands. Code that reads a fixed column list, or that concatenates months without reconciling this, will fail or silently misalign at the April 2021 boundary.

### 1.8c Finding: the provider reference covers only 29% of providers, but 91.5% of activity

Check 7 returned a match rate of 149 of 517 distinct providers in the January 2026 extract. The unmatched codes were investigated directly against the ORD API and are **independent-sector providers**, not missing NHS trusts — for example `A0C5S` SpaMedica Gloucester and `A1D1B` SpaMedica Wembley (ODS primary role RO176), and `AAH` Tetbury Hospital Trust Ltd (RO172). The reference table was built from primary role RO197 (NHS Trust) alone, so independent providers delivering NHS-funded elective work are correctly absent from it.

The provider count is therefore the wrong denominator. Measured by volume, using the `Total` column of the January 2026 extract:

| Provider group | Distinct providers | Share of total pathways |
|---|---|---|
| NHS trusts (present in reference) | 149 | **91.5%** |
| Independent sector (absent) | 368 | **8.5%** |

*Interpretation.* Independent providers are numerous but individually small — 368 organisations account for 8.5% of activity, an average of well under a tenth the volume of a typical trust. Restricting the federated cohort to NHS trusts retains 91.5% of pathways and yields clients with a plausible institutional structure (each with an ICB parent and a geography, which the independent sites lack).

*Decision required, not yet taken:* whether the federated clients are NHS trusts only, or whether independent providers are included as a separate client class. This is a modelling choice with a real trade-off — excluding them loses 8.5% of activity and any capacity substitution effect between sectors, while including them introduces hundreds of very small, structurally different clients into the federation. Recorded here as an open question for §1.11.

### 1.8d Correction to a previously reported figure

Entry §1.5 originally reported 221 organisations carrying an ICB code. **The correct figure is 214.** The original number came from `awk -F,` applied to the reference CSV, which splits naively on commas; 13 trust names contain commas inside quoted fields, shifting the column positions and producing seven false positives. Re-measured with a proper CSV parser the value is 214, and the table in §1.5 has been corrected.

The discrepancy was initially suspected to indicate non-determinism in the ORD API — that a rebuild might return different relationships between runs, which would make the reference unreproducible. This was tested directly: all 33 Active trusts currently lacking an ICB code were re-queried, and none returned an ICB on retry. The reference build is reproducible; the discrepancy was a measurement error on this project's side, not instability at the source.

*Generalisation:* delimiter-splitting tools must not be used to measure quoted CSV data, even for a quick count. The failure is silent and produces a plausible-looking number.

### 1.9 Issues encountered during execution

Both issues below were caused by tooling, not by the data. Both are recorded because each produced a misleading appearance of correct operation.

**Issue 1 — process wait loop that never terminated.** A shell loop intended to wait for a package installation to finish used `pgrep -f "…pip install torch"`. The pattern matched the command line of the waiting shell itself, so the condition was permanently true, the loop never exited, and the dependent installation never ran. Nothing reported an error; the job simply appeared to be in progress indefinitely.
*Resolution:* the process was terminated and the installation run directly.
*Generalisation:* `pgrep -f` must not be given a pattern that appears in the command line of the process performing the search.

**Issue 2 — loss of recorded notebook outputs.** Editing the cells of `fetch_dataset.ipynb` to add per-line commentary discarded the stored execution outputs, removing the record of the completed run. The data on disk was unaffected; only the notebook's own evidence of execution was lost.
*Resolution:* the notebook is being re-executed to restore the outputs. This is inexpensive because completed downloads are skipped on re-run by design; the cost is dominated by the approximately 544 sequential ORD API calls.
*Status at time of writing:* in progress in `tmux` session `fetch`.

### 1.10 Deliverables

| Path | Contents | Executed |
|---|---|---|
| `src/fetch_dataset.ipynb` | Acquisition of all three datasets: manifest construction, download, extraction, ORD reference build, KH03 retrieval | Yes; re-running to restore outputs |
| `src/inspect_dataset.ipynb` | File inventory, size-variation analysis against a rolling median, filename-template analysis, header/schema comparison across all 96 months, row counts, and deletion of the redundant archives | **No — not yet executed** |
| `.claude/hooks/inject_context.py` | Tooling: loads project conventions and this worklog at each session turn | n/a |

Downloads are idempotent: each file is written under a temporary `.part` name and renamed only on completion, so a completed filename always denotes a complete file and an interrupted run resumes rather than restarting.

### 1.11 Open items

1. **Decide the federated client definition** — NHS trusts only (91.5% of activity, 149 structurally comparable clients), or NHS trusts plus independent providers as a second client class (100% of activity, but 368 additional very small clients lacking ICB parent and geography). See §1.8c. This decision shapes the federation topology and should be settled before phase 2 extraction.
2. **Handle the April 2021 schema change** in the phase-2 and phase-4 extraction code. The long-wait bands must be reconciled to a common representation; see §1.8b. This is the highest-risk item for silent misalignment.
3. **Execute `src/inspect_dataset.ipynb`** to produce the full inventory, size and row-count series. Note that the schema question it was written to answer has since been answered by the verification run (§1.8b); the notebook remains useful for the per-month row counts and the size/outlier series.
4. **Archive deletion** (section 6 of the inspection notebook) is now unblocked: verification has passed, so the 329 MB of ZIP archives is confirmed redundant against the extracted CSVs. Left as a deliberate manual step.
5. **Confirm whether the geographic region** required for the phase-11 scenario panel should be derived from the trust postcode now captured in the reference table, or obtained separately. The RTT extracts already carry `Provider Parent Org Code`, which duplicates the ICB assignment; the reference table's contribution is the true geography.

### 1.12 Working conventions adopted (continued below in Entry 2)

Recorded in `CLAUDE.md` and enforced where enforcement is possible:

- Analysis code is written in Jupyter notebooks under `src/`, kept simple and research-grade, without production-style exception handling or defensive scaffolding.
- Code is commented on a per-line basis; the reasoning behind non-obvious constructions is stated explicitly.
- Long-running jobs are executed detached under `tmux` or `nohup`, never in a foreground shell, as the machine is accessed over SSH.
- Claims are verified against the source before being relied upon, and the distinction between what was measured and what was inferred is maintained throughout.

---

# Entry 2 — 2026-07-24
## Phase 1b: Validation, inspection, and the canonical-spec revision

### 2.1 Scope discipline — one responsibility per notebook

Agreed and now enforced by naming: each notebook does what its filename says and nothing else.

| Notebook | Responsibility |
|---|---|
| `src/fetch_dataset.ipynb` | Acquisition only |
| `src/inspect_dataset.ipynb` | Validation and inspection only — transforms nothing |
| `src/data_processing.ipynb` | Transformation, including the April 2021 band reconciliation and panel construction |
| `src/eda/EDA.ipynb` | Exploration of the processed table |

The `>52`-week reconciliation logic was drafted into the inspection notebook and then **removed**: detecting and documenting the schema break is inspection, but implementing the handling rule is transformation. It now belongs to `data_processing.ipynb`. Recorded because the boundary is easy to blur and the drafting error is instructive.

`README.md` was updated with the notebook responsibilities, the data layout, and the measured facts that constrain the build.

### 2.2 Handling rule for the April 2021 band change (specification for `data_processing.ipynb`)

Established here, implemented there.

- **Post-2021:** sum the weekly bands from `Gt 52 To 53` through `Gt 103 To 104`, plus the `Gt 104 Weeks` tail, into a single >52 figure.
- **Pre-2021:** take the single `Gt 52 Weeks` column.
- **Never the reverse.** The early era cannot be disaggregated into weekly bands, so the coarser representation governs the joined series.
- Select columns **by name with an explicit era branch**, never by position.
- **Boundary assert required:** the reconciled >52 series must be continuous across 2021-03 → 2021-04, so that no step is introduced by the reconstruction itself.

**The mitigating fact.** The agentic layer's headline metric is the >18-week count, and the 18→52 bands are identical in both eras. Measured: 53 band columns exist pre-2021 and 105 post-2021, of which the 52 bands below 52 weeks are common to both. So only the >52 tail requires reconciliation; everything the decision layer keys on is era-stable.

### 2.3 Canonical spec revision (D-01): independents stay in the data

**Superseded:** the extraction no longer filters to `R##` trust codes.

The canonical table now holds **every provider**, trust and independent alike, with one added column `sector`, derived from ODS primary role (queried with retired organisations included) rather than from code shape. Sector filtering becomes a **downstream, one-line panel decision** rather than a data decision baked into the parquet.

Federation clients remain **trusts only**, enforced by the balanced-panel rule rather than by a filter — and the data largely enforces it by itself, since few independents have full-window history. The independents' role is downstream: aggregate per-specialty, per-ICB context that the board sees as substitution capacity.

**Sector decision, taken explicitly rather than left implicit:**

- `sector = public` covers ODS primary roles **RO197 (NHS Trust) and RO107 (Care Trust)**. The design criterion is **allocability** — a public body with an ICB parent that capacity can be allocated to — not the role label. The two Care Trusts satisfy it.
- The single **RO157 (non-NHS organisation) is grouped with the independents.**
- RO172 and RO176 are independent sector.

### 2.4 Trust census table

Built as `data/reference/provider_census.csv`: one row per provider code **ever** seen in RTT, carrying name, ODS primary role and role name, active/retired status, first month, last month, months present, ICB parent, sector, and panel membership.

Purpose: every provider count used anywhere in the project must be **derivable from this one table** rather than asserted in prose. The counts that previously floated around the project — reference ≈ 247 active, RTT-active 149, panel ~125, union 194 — are now all recomputed from it and printed side by side.

### 2.5 Corrections to standing numbers, before they fossilised

1. **The provider universe is 653 codes across the window, not 517.** 517 was one month's reporters (January 2026). The census and every canonical build must run on the 653.
2. **Roster arithmetic re-derived, not inherited.** The latest month has 24 treatment-function codes = 23 real departments + `C_999`, and the 23 comprise **18 named specialties + 5 X-family "Other" buckets**. An earlier build's "18 stable" conflated some X-family codes era-dependently. The notebook now derives the roster fresh from first/last-appearance — candidate set = named specialties spanning all 96 months — and prints every excluded code with its reason and month range. The resulting count is whatever the data says; it is not carried over from any previous build.
3. **214, not 221**, organisations carry an ICB code — see §1.8d. Cause was a naive `awk -F,` split across quoted fields containing commas.

### 2.6 C_999 — hardened from a sample to a standing assert

§1.8 proved the aggregate identity on one month. It is now asserted across **all 96 months × 5 part types × every provider**, with a hard `assert` that halts the notebook on any mismatch, so future schema drift cannot silently break the exclusion.

The headline number is worth stating plainly because it is the difference between a dropped row and a doubled national statistic: summing `Part_2` without excluding `C_999` gives an England waiting list of **14,375,354** against the correct **7,187,677** — exactly **2.00×**.

### 2.7 `Part_3` has no waiting-time bands — expected, not a defect

New referrals have waited ~0 weeks by definition, so waiting-time bands are meaningless for that part type. Demand is the `Total All` column alone; the bands only ever feed the backlog and agentic side. Recorded explicitly so that nobody later "fixes" it.

### 2.8 Blocking gate: verify the independent sector against ground truth

**Status: implemented in `inspect_dataset.ipynb`, execution in progress.** No phase-2 build proceeds until this is complete and reviewed.

The gate establishes with numbers and plots whether independent rows are genuine demand or a reporting artefact:

- **(a)** Do independents report real `Part_3` new-referral volumes with plausible monthly dynamics, or only completed/incomplete pathways? Measured as the population rate of each part type per provider-month by sector, plus independent demand totals, zero-months, and the correlation of month-on-month change against the public sector.
- **(b)** Independent **share of pathways over time, per specialty**, with a fitted slope in percentage points per year; any specialty drifting more than 0.5pp/year is flagged as trending rather than stable. Ophthalmology is expected to trend, given the growth of private cataract provision — stated in advance so a confirmation cannot be read as post-hoc.
- **(c)** Reporting behaviour by sector: entry/exit churn by year, months present, gaps inside a provider's own reporting window, ODS-retirement rate, and systematic differences in how the five part types are populated.
- **(d)** National totals **with and without** independents, so it is known exactly which published figure the table reproduces. Four variants are computed. Confirmation against the NHS England press notice for the month is logged as OPEN — not claimed.

All results are logged as findings with F-ids, negative results included, and written to `data/reference/findings.csv`.

**Contingency, decided in advance:** if independent reporting proves partial, erratic, or structurally different in a way that contaminates the table, the `sector` column allows it to be quarantined in one line. That decision will be made on the evidence produced here, not on assumption.

### 2.9 Open items

1. **Complete and review the independents gate** (§2.8). Blocking for phase 2.
2. Confirm the (d) reconciliation against the published NHS England figure for the month.
3. Build `src/data_processing.ipynb` to the specification in §2.2 and §2.3.
4. Carry forward the geography question from §1.11.

### 2.10 Execution results — `inspect_dataset.ipynb`, 2026-07-24

Executed end to end, 0 cell errors. Findings written to `data/reference/findings.csv`.

| F-id | Result |
|---|---|
| F-01 | Integrity **PASS**. 96/96 months sound; 96/96 archives CRC-clean; extraction sizes exact; no Period/filename mismatch; no truncation; 61/61 KH03 workbooks valid; no duplicate provider codes. |
| F-02 | Schema break Apr 2021: 69 cols × 36 months → 121 cols × 60 months. 53 band columns before, 105 after; the 52 bands below 52w identical in both eras. |
| F-03 | `Part_3` has no populated week bands, by design. Demand = `Total All` alone. |
| F-04 | `C_999` exact aggregate over **199,410 provider × part-type groups, 0 mismatches**. Waiting list 7,045,510 correct vs 14,091,020 naive = **2.00×**. |
| F-05 | Universe **653 codes**; public 196 (RO197 194 + RO107 2); independent 457; **balanced panel 126 trusts**. |
| F-06 | Roster: **18 named specialties, all spanning 96 months, 0 dropped**; 6 X-buckets excluded by definition. |
| F-07 | Independents report genuine demand: 11,541,248 referrals, **0 zero-months**; national share 6.20% → 7.70%. |
| F-08 | Independent share **trends in 6 of 24 specialties**. Fastest **C_130 Ophthalmology +2.20pp/yr (6.2% → 19.6%)** — the trend predicted in advance. |
| F-09 | **64% of public providers span all 96 months vs 28% of independents.** |
| F-10 | Mar 2026 published-basis total **7,045,510**, of which 441,656 (6.27%) independent. Press-notice confirmation still OPEN. |
| F-11 | **NHS renamed 18 of 24 treatment functions at Apr 2021.** Codes stable, names not. |

Archives deleted after verification; filesystem now 120 GB free (88% used).

*Provenance note:* the CRC and extraction-size checks (F-01) were executed in the 22:45 run, **before** the archives were deleted. A later rerun with corrected roster logic reports "0 archives tested" for those two checks, by design — they self-skip once the archives are gone. The verification evidence is the earlier run.

### 2.11 Defect in this notebook, found and corrected

The first execution emitted F-06 as *"0 named specialties span all 96 months, out of 36 named codes"* — internally inconsistent with the 24 codes observed directly in a single month, which is what prompted the check.

**Cause.** The roster was grouped by treatment-function **code *and* name**. NHS renamed 18 of the 24 functions at the same April 2021 break (`General Surgery` → `General Surgery Service`), so each specialty split into a 36-month row and a 60-month row and none reached 96.

**Correction.** Group by code only, taking the most recent name for display. Corrected result: **18 named specialties, all spanning the full window, none dropped.**

**Generalisation, now F-11:** treatment-function *codes* are stable across the window; *names* are not. All joins and groupings must key on `Treatment Function Code`. Grouping by code+name fails silently — it produces a well-formed table in which every specialty has partial history.

This also surfaced that the X-family splits at the same break: one combined `X01 Other` for the 36 pre-2021 months, five themed buckets (`X02`–`X06`) for the 60 after. The union across the window is therefore 6 X-buckets, not the 5 visible in any single month.

### 2.12 Is `C_999` useful for our problem? — assessment

Question raised deliberately as a contrarian check against the README problem statement. Conclusion: **useless as data, valuable as a control, and asking it exposed a coverage gap.**

**Not data.** The identity is exact over 199,410 groups with 0 mismatches, so C_999 is reconstructible from the rows beneath it and carries no information they lack. Were it ever to *exceed* the sum of parts it would be capturing unitemised specialties and would become real data; it never does. In the modelling table it would enter as a "department" perfectly collinear with the sum of the real ones — leakage — while doubling every total. **Excluded from the canonical table.**

**Valuable as a control, for one specific reason.** C_999 is an independently published control total per provider per month. If NHS England adds a treatment function not in our roster, our sum falls short of C_999 and the standing assert fires. That converts a silent coverage loss — the failure mode that yields plausible numbers and wrong conclusions — into a hard stop. Retained permanently as an assert.

**The coverage gap this exposed.** C_999 = 18 named specialties + 6 X-buckets. Measured over all 96 months of `Part_3`:

| | New referrals | Share |
|---|---|---|
| 18 named specialties (the roster) | 115,664,910 | **74.41%** |
| 6 X "Other" buckets | 39,784,766 | **25.59%** |
| = C_999 | 155,449,676 | 100% |

The X share is stable at 25.6% ± 1.2 and drifts up from 24.1% to 26.5% across the window.

Two consequences:

1. **C_999 is not the trust total of our panel.** It is 100% of demand; the roster is 74.4%. Using C_999 as the trust tier of the trust → ICB → national escalation while forecasting a roster-restricted panel would leave the tiers incoherent by roughly a quarter. **Rule: derive trust aggregates by summing the roster, never by reading C_999.**
2. **The README's "each treatment function a department" holds for 74.4% of demand.** The X-buckets cannot simply be promoted to departments: their own era break means that across the full window they are usable only as a single merged "Other" category, not at the five-way post-2021 granularity.

*Open decision:* whether the panel is the 18 named specialties (74.4% coverage, clean semantics) or 18 + one merged "Other" (100% coverage, one coarse residual client per trust). To be decided explicitly with this number attached, not left as an unnoticed gap.

### 2.13 Open items (supersedes §2.9)

1. **Panel scope decision:** 18 named specialties, or 18 + merged "Other"? See §2.12. Blocking for the canonical build.
2. Confirm F-10 against the published NHS England press notice for March 2026.
3. Build `src/data_processing.ipynb` to the specification in §2.2 (band reconciliation, with the boundary assert) and §2.3 (all providers retained, `sector` column, balanced-panel client rule).
4. The independents gate (§2.8) is **complete and passed** — independents report genuine demand with no zero-months. Carry F-08 forward as a live constraint: the sector mix is non-stationary, most sharply in ophthalmology, so the model must carry the sector split rather than assume fixed composition.
5. Carry forward the geography question from §1.11.

---

# Entry 3 — 2026-07-24
## Decisions taken after the inspection run. Phase 2 unblocked.

### 3.1 D-02 — the 25.6% gets a design answer: `X_OTHER` as a 19th series

**Decision.** Carry a merged Other series alongside the 18 named specialties: `X_OTHER = X01` pre-2021, `= sum(X02..X06)` post-2021. One continuous 96-month series per trust, with a **boundary-continuity assert at 2021-04**, exactly as for the wait-band break. The X-family recode is the same shape as that break — coarse before, finer after — so the same reconciliation applies.

**Consequences, which is why this beats disclosure.**
- The panel becomes **19 series per trust** (18 named + Other) and the hierarchy reconciles **exactly**.
- It upgrades the `C_999` assert from roster-drift detection to a **full-coverage identity**: 18 named + `X_OTHER` = `C_999`, per provider, per part type, per month.
- **The agentic split follows naturally:** department-level capacity requests are raised only for the 18 real specialties — you cannot staff "Other" — but **trust-tier capacity arithmetic includes Other**, because that demand consumes real capacity and an escalation sum that ignores a quarter of the workload is wrong.

**Alternative recorded and rejected:** scope to the 18 named specialties and state 74.4% coverage. Rejected because the trust tier stays incoherent by ~25% and the figure becomes the obvious reviewer question. The merged series costs one row per trust and removes the question.

### 3.2 D-03 — the roster is 18; the old 17 is dead

With code-only grouping, **all 18 named specialties span all 96 months**, so the default roster is the full 18 with **no coverage filter**.

The former ≥50%-presence threshold — which dropped Neurosurgery at 36% — is **demoted from default to sensitivity run**. The design criterion is "a real, allocable clinical service", which Neurosurgery plainly is, and the previous build's own sensitivity showed including it costs nothing.

**Standing finding (F-11), promoted from the bug that caused it:** treatment-function **codes are stable, names are not** — 18 of 24 were renamed at 2021-04. Join and group on `Treatment Function Code` only, never on name. The failure is silent: it yields a well-formed table in which every specialty has partial history.

### 3.3 D-04 — sector definition and the panel of 126, made explicit

`sector = public` **= RO197 (NHS Trust) + RO107 (Care Trust)**. Criterion is **allocability**: a public body with an ICB parent that capacity can be allocated to. RO157 is grouped with the independents.

The balanced-panel rule (public **and** present in all 96 months) yields **126**, decomposed from the census as:

| Role | In panel |
|---|---|
| RO197 NHS Trust | 125 |
| RO107 Care Trust | **1** — `TAD` Bradford District Care NHS Foundation Trust (96/96 months) |

The second Care Trust, `TAJ` Black Country Partnership NHS Foundation Trust, is excluded by the panel rule on 24/96 months — not by a sector judgement. So 126 is a **filter result derived from `provider_census.csv`**, not a new magic number: 125 → 126 is precisely the admission of one Care Trust, which is the RO107 decision showing up in the data.

### 3.4 D-05 — the ophthalmology interpretive caveat

Wherever `C_130` appears in a report, one sentence must accompany it:

> Ophthalmology is both the largest department by volume and the fastest-substituting one, with the independent-sector share rising from 6.2% to 19.6% across the window. Trust-level ophthalmology demand trends are therefore **partly sector shift, not population change** — which is exactly why the ICB-level independent context series exists.

Stated once, the non-stationarity caveat is handled rather than lurking in the results.

### 3.5 D-06 — item (d) scheduled before the report, not before phase 2

Internal consistency is proven, so the build proceeds. The open reconciliation has a concrete target: the NHS England statistical press notice for a chosen month publishes the national incomplete-pathways figure, and the check is **which of the two bases reproduces it** — all-provider **7,045,510** or trusts-only. Expectation, stated in advance: the published headline is the all-provider figure. Whichever way it lands, the report then states "our table reproduces the published X on basis Y" with no hedging.

### 3.6 Status

Phase 2 is **unblocked**. The standing asserts now guard every trap found so far:

1. **`C_999` coverage identity** — 18 named + `X_OTHER` = `C_999`, every provider, part type and month.
2. **Boundary continuity at 2021-04** — for both the >52 wait-band reconciliation and the `X_OTHER` recode.
3. **Code-only joins** — treatment functions keyed on code, never name.

Next artefact: `src/data_processing.ipynb`, built to §2.2, §2.3, §3.1 and §3.2.

---

# Entry 4 — 2026-07-24
## Phase 2: canonical table built. Three findings, one a defect in our own test.

`src/data_processing.ipynb` built to §2.2, §2.3, §3.1 and §3.2. Executed end to end, 0 cell errors.

### 4.1 Outputs

| File | Contents |
|---|---|
| `data/canonical/rtt_canonical.parquet` | 322,531 rows — 653 providers × 19 departments × 96 months, **all providers retained**, `sector` / `panel_member` / `in_roster` as flags, never filters. 3.7 MB |
| `data/canonical/rtt_panel.parquet` | The rectangular federation cube: **126 trusts × 19 departments × 96 months = 229,824 rows**. 2.2 MB |
| `data/canonical/national_monthly.csv` | National monthly series including the accounting-identity check |

Measures per cell: `demand` (Part_3), `completed_admitted`, `completed_nonadmitted`, `completed`, `waiting`, `waiting_gt18`, `waiting_gt52`, `waiting_dta`.

Sector split of the canonical table: public 196 providers / 207,504 rows / 143,908,428 referrals; independent 457 providers / 115,027 rows / 11,541,248 referrals (**7.4%** of demand).

### 4.2 Assert 1 — full-coverage identity: PASSED

18 named + `X_OTHER` = `C_999` across **199,410 provider × part-type groups, 0 mismatches**. D-02 delivered what it promised: the 19 series account for *all* reported activity, so the hierarchy reconciles exactly rather than approximately. The assert is now a coverage guarantee, not merely drift detection.

### 4.3 Defect in our own boundary test — F-12

Assert 2 reported the `>52` reconstruction at **6.60× typical** monthly change and still passed, because the threshold had been set loosely at 10×. Passing a test by a wide threshold is not evidence; the number was investigated rather than accepted.

**The 6.60× was an artefact of the test statistic, not of the data.** The comparison used a *global* median absolute monthly change. The `>52` series is near zero for the whole pre-covid period, so that global median (6,622) is dominated by quiet months and inflates the ratio for any step occurring during a volatile one.

Measured against **local** volatility — the twelve months either side of the break, median 24,583 — the ratio is **1.26×**. The surrounding months settle it: Mar 2021 +26,825, **Apr 2021 −30,988**, May 2021 −37,359. April's movement is *smaller* than May's. This is the ordinary post-peak decline of the covid long-wait backlog, not a step introduced by the reconciliation.

**Correction applied:** `boundary_ratio()` now measures against local variation with the step itself excluded from the window, and the threshold is tightened from 10× to 3×. Both reconciliations pass on the stricter test (`X_OTHER` 0.97×, `>52` 1.26×).

*Generalisation:* a boundary-continuity test must compare against variation local to the boundary. A global dispersion statistic makes a quiet-era series look discontinuous at any turbulent join, and a loose threshold then hides the fact that the statistic is wrong.

### 4.4 Structural zeros in the panel cube — F-13

Filling the 126 × 19 × 96 cube required creating **62,313 cells (27.11%)** absent from the source. Investigated rather than accepted as missing data:

- **2,394** trust × department pairs exist in the cube.
- **524 of them (21.9%) have zero demand in all 96 months** — these trusts simply do not provide that specialty. Most trusts have no neurosurgery, no cardiothoracic surgery.
- The remaining **1,870 active pairs have a median of 96/96 months active**.

So the 27% fill is overwhelmingly **structural absence, not sporadic missingness**: a service that does not exist, rather than a service that failed to report.

*Consequence for phase 3:* the real client-series count is **~1,870 trust × department series, not 2,394**. Training on all-zero series would waste capacity and distort any pooled loss. The 524 structurally-absent pairs must be excluded by a "was this service ever provided" rule, and that rule belongs in the modelling notebook, not in the canonical table — the table keeps them so the exclusion stays visible and reversible.

### 4.5 The backlog accounting identity leaks — F-14, material for phase 4

The README states `backlog ≈ previous backlog + demand − completions`. Measured over all 96 months on the panel:

| | |
|---|---|
| Mean residual (actual − predicted) | **−183,635 per month** |
| As % of the waiting list | **−4.2%** (range −7.9% to −2.4%) |
| As % of monthly demand | **−15.3%** |
| Sign | **negative in 95 of 95 months** |

This is not noise. It is a systematic, one-directional leak: the identity **over-predicts the backlog every single month**. Roughly **15% of new referrals leave the waiting list without a recorded completion** — removals, transfers, validation exercises, patients who die or decline treatment.

*Consequence:* a per-service agent projecting the backlog forward on the stated identity will over-project it consistently and escalate more aggressively than the data warrants, and the error compounds over a multi-month projection horizon. **Phase 4 must carry an explicit removal term**, estimable from this residual, rather than treating the identity as exact. The README wording "≈" is doing heavy lifting and should be quantified there.

### 4.6 Open items

1. **Phase 3 modelling:** exclude the 524 structurally-absent trust × department pairs; the client set is ~1,870 series.
2. **Phase 4:** add a removal term to the backlog dynamics; the residual measured here is the estimator.
3. Confirm F-10 against the published NHS England press notice (D-06, before the report).
4. Carry F-08 forward: the sector mix is non-stationary, sharpest in ophthalmology.
5. Carry forward the geography question from §1.11.
