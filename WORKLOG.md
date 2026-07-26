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

### 4.3 Defect in our own boundary test — F-13

Assert 2 reported the `>52` reconstruction at **6.60× typical** monthly change and still passed, because the threshold had been set loosely at 10×. Passing a test by a wide threshold is not evidence; the number was investigated rather than accepted.

**The 6.60× was an artefact of the test statistic, not of the data.** The comparison used a *global* median absolute monthly change. The `>52` series is near zero for the whole pre-covid period, so that global median (6,622) is dominated by quiet months and inflates the ratio for any step occurring during a volatile one.

Measured against **local** volatility — the twelve months either side of the break, median 24,583 — the ratio is **1.26×**. The surrounding months settle it: Mar 2021 +26,825, **Apr 2021 −30,988**, May 2021 −37,359. April's movement is *smaller* than May's. This is the ordinary post-peak decline of the covid long-wait backlog, not a step introduced by the reconciliation.

**Correction applied:** `boundary_ratio()` now measures against local variation with the step itself excluded from the window, and the threshold is tightened from 10× to 3×. Both reconciliations pass on the stricter test (`X_OTHER` 0.97×, `>52` 1.26×).

*Generalisation:* a boundary-continuity test must compare against variation local to the boundary. A global dispersion statistic makes a quiet-era series look discontinuous at any turbulent join, and a loose threshold then hides the fact that the statistic is wrong.

### 4.4 Structural zeros in the panel cube — F-14

Filling the 126 × 19 × 96 cube required creating **62,313 cells (27.11%)** absent from the source. Investigated rather than accepted as missing data:

- **2,394** trust × department pairs exist in the cube.
- **524 of them (21.9%) have zero demand in all 96 months** — these trusts simply do not provide that specialty. Most trusts have no neurosurgery, no cardiothoracic surgery.
- The remaining **1,870 active pairs have a median of 96/96 months active**.

So the 27% fill is overwhelmingly **structural absence, not sporadic missingness**: a service that does not exist, rather than a service that failed to report.

*Consequence for phase 3:* the real client-series count is **~1,870 trust × department series, not 2,394**. Training on all-zero series would waste capacity and distort any pooled loss. The 524 structurally-absent pairs must be excluded by a "was this service ever provided" rule, and that rule belongs in the modelling notebook, not in the canonical table — the table keeps them so the exclusion stays visible and reversible.

### 4.5 The backlog accounting identity leaks — F-15, material for phase 4

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

---

# Entry 5 — 2026-07-24
## Process deviation: comment standard not upheld. Corrected.

### 5.1 The deviation

`CLAUDE.md` requires per-line commentary. It was upheld in `fetch_dataset.ipynb` and then allowed to lapse as the notebooks grew. Measured, counting docstrings as documentation:

| Notebook | Before | After |
|---|---|---|
| `fetch_dataset.ipynb` | 81% | 81% (unchanged, was already to standard) |
| `data_processing.ipynb` | 20% | **49%** |
| `inspect_dataset.ipynb` | 18% | **33%** |

Raised by the project owner, not self-detected — which is itself the finding. The rule was being applied to whichever file was small enough to make it easy.

### 5.2 What the residual gap actually is

Rather than claim the remaining shortfall is acceptable, the undocumented lines in `inspect_dataset.ipynb` were categorised (376 lines):

| Category | Lines |
|---|---|
| Inside a `print(...)` call | 140 |
| `print` / f-string continuation lines | 66 |
| List/dict literal continuation | 17 |
| `def` / `for` / `if` / `with` headers (mostly followed by a docstring) | 22 |
| **Genuine code lines lacking a comment** | **131** |

So roughly 206 of the 376 are output-formatting lines that cannot carry a meaningful per-line comment. Excluding them, documented coverage of *logic* is 183/353 ≈ 52%. The notebook is print-heavy by design — it is a report — which distorts the raw metric, but **131 genuine code lines are still uncommented and that part of the gap is real.**

### 5.3 Substantive simplification, not just comments

`data_processing.ipynb` was also simplified while being re-commented. The build pass previously computed `gt18` and `gt52` band sums for **all five** RTT part types and then discarded eight of the ten resulting columns. Band columns are now read and summed **only for `Part_2`**, the waiting list — the only part whose long-wait detail is used. Less IO, fewer columns, same output.

### 5.4 Re-run results after the rewrite

`data_processing.ipynb`, 0 cell errors:

- **Assert 1** — 199,410 groups compared, **0 mismatched**. 18 named + `X_OTHER` = `C_999` everywhere.
- **Assert 2**, now on the corrected local-variation statistic and the tightened 3× threshold: `X_OTHER` **1.51×**, `>52` **1.68×**. Both pass honestly rather than by a loose threshold. (The earlier 6.60× figure was the flawed global statistic, F-13 in Entry 4.)
- Panel cube 229,824 rows; 62,313 cells (27.11%) zero-filled, of which **524 of 2,394 series (21.9%) are structurally absent** — a service the trust has never provided. 1,870 genuinely active series, median 96/96 months.
- Backlog identity residual: **−183,635/month, −4.25% of the list, −15.40% of demand, negative in 95 of 95 months.**

### 5.5 Correction to a number reported in Entry 4

Entry 4 §4.5 gave the identity residual as −15.3% of demand. The re-run gives **−15.40%**. The difference is the changed `>52`/`gt18` computation path, not a data change. The Entry 4 figure should be read as superseded.

### 5.6 Standing rule reinforced

`CLAUDE.md` now also carries: **do not take the owner's stated opinions, decisions or framings at face value.** Treat them as hypotheses; find the measurement that would falsify them and run it before building. Applied immediately to D-02 — the `X01` → `X02..X06` merge assumption was tested at the boundary before the canonical build depended on it, and passed at 1.51× local variation.

---

# Entry 6 — 2026-07-24
## All three notebooks executing clean. Phase 1 and 2 complete.

### 6.1 Pipeline status

| Notebook | Executed | Errors | Produces |
|---|---|---|---|
| `src/fetch_dataset.ipynb` | yes | 0 | 96 monthly extracts, ODS reference, 61 KH03 workbooks |
| `src/inspect_dataset.ipynb` | yes | 0 | 12 findings (F-01…F-12), provider census, monthly/department/specialty summaries |
| `src/data_processing.ipynb` | yes | 0 | `rtt_canonical.parquet`, `rtt_panel.parquet`, `national_monthly.csv` |

Note on sequencing: `inspect_dataset.ipynb` was rewritten for comment density and then had **zero stored outputs until re-executed** — a rewritten-but-unrun notebook looks finished and is not. Caught only because the owner asked for run status. Standing habit: after any rewrite, verify stored outputs exist before treating the artefact as done.

### 6.2 F-id collision, corrected

`inspect_dataset.ipynb` generates F-01 … F-12, and F-12 there is the X-bucket coverage finding. Entry 4 had independently used F-12, F-13 and F-14 for worklog-only findings. Since the notebook-generated ids are produced by code and written to `data/reference/findings.csv`, they are authoritative; the worklog ids were renumbered:

- boundary-test defect: F-12 → **F-13**
- structural zeros: F-13 → **F-14**
- backlog identity leak: F-14 → **F-15**

*Generalisation:* ids emitted by code win over ids typed into prose. Future worklog-only findings start at F-16.

### 6.3 The twelve generated findings

| id | Substance |
|---|---|
| F-01 | Integrity PASS. 96/96 months sound, extraction sizes exact, no Period mismatch, no truncation, 61/61 KH03 valid, no duplicate codes. |
| F-02 | Schema break Apr 2021, 69→121 columns; the 52 bands below 52w identical in both eras, so >18w is era-stable. |
| F-03 | `Part_3` has no week bands by design; demand is `Total All` alone. |
| F-04 | `C_999` exact aggregate, 199,410 groups, 0 mismatches; 7,045,510 vs 14,091,020 = **2.00×**. |
| F-05 | 653 provider codes; public 196 (194 RO197 + 2 RO107); independent 457; balanced panel **126**. |
| F-06 | Roster: **18 named specialties, all 96 months, 0 dropped**; 6 X-buckets, themselves split at Apr 2021. |
| F-07 | Independents report genuine demand: 11,541,248 referrals, **0 zero-months**; share 6.20% → 7.70%. |
| F-08 | Independent share trends in **6 of 24** specialties; fastest **C_130 +2.20pp/yr (6.2% → 19.6%)**. |
| F-09 | **64%** of public providers span all 96 months vs **28%** of independents. |
| F-10 | Mar 2026 published basis **7,045,510**, of which 441,656 (6.27%) independent. Press-notice check still OPEN. |
| F-11 | NHS renamed **18 of 24** treatment functions at Apr 2021 — join on code, never name. |
| F-12 | X-buckets carry **25.6%** of demand; an 18-specialty roster covers only 74.4%, so `C_999` is not the trust total of a roster-restricted panel. |

F-01 now reports "archives CRC-clean (0 tested)" because the archives were deleted after verification; the CRC evidence is the run recorded in §2.10, and checks A1/A2 self-skip by design.

### 6.4 Canonical outputs, verified

- `rtt_canonical.parquet` — 322,531 rows, 653 providers × 19 departments × 96 months, flags not filters.
- `rtt_panel.parquet` — 229,824 rows, the rectangular 126 × 19 × 96 federation cube.
- Asserts: coverage identity 0 mismatches; boundary continuity `X_OTHER` 1.51×, `>52` 1.68× against a 3× threshold; code-only joins; key uniqueness 0 duplicates.

### 6.5 Open items carried into phase 3

1. Exclude the **524 structurally-absent** trust × department series (F-14); the real client set is **~1,870** series.
2. Add a removal term to the backlog dynamics (F-15): residual **−15.40% of demand, negative in 95 of 95 months**.
3. Confirm F-10 against the published NHS England press notice (D-06), before the report.
4. Carry F-08 forward: sector mix non-stationary, sharpest in ophthalmology; the D-05 caveat sentence accompanies every C_130 result.
5. Geography question from §1.11 still open.
6. Comment standard: **131 genuine code lines in `inspect_dataset.ipynb` remain uncommented** (Entry 5 §5.2), and the new CLAUDE.md rule — explain each unfamiliar library/function on first use — has not yet been applied retrospectively to the three notebooks.

---

# Entry 7 — 2026-07-24
## Bug hunt on the canonical outputs

Deliberate search for defects other than the comment-standard gap. Five checks run against `rtt_canonical.parquet` and `rtt_panel.parquet`.

### 7.1 Clean

| Check | Result |
|---|---|
| Nulls in `sector`, `dept`, `provider_code`, `icb_reported` | **0** in every column |
| Negative counts in any measure | **0** |
| `waiting_gt18 > waiting` | **0 rows** — the band subset never exceeds its total |
| `waiting_gt52 > waiting_gt18` | **0 rows** — bands nest correctly |
| Panel vs canonical monthly demand | **max abs difference 0.00** — the cube is a faithful subset |

The two reconciliations and the pivot introduce no arithmetic error detectable by these invariants.

### 7.2 `icb_ods` is 36.8% null — expected, documented so it is not mistaken for missing data

`icb_ods` comes from `trust_icb.csv`, which was built from ODS role RO197 only. Independent-sector providers have no ICB parent and therefore no value. The null rate matches the independent share of rows. `icb_reported` — the parent as stated in the RTT file itself — is **0% null** and is the column to use for hierarchy work.

### 7.3 F-16 — 47 rows where `Part_2A` exceeds `Part_2`, and it is NHS's data, not ours

`Part_2A` (incomplete pathways *with* a decision to admit) is by definition a subset of `Part_2` (all incomplete pathways), so `waiting_dta > waiting` should be impossible. It occurs in **47 of 322,531 rows (0.0146%)**.

**Verified against the raw source before blaming the pipeline.** For provider `AAH`, treatment function `C_330`, August 2018, the unmodified NHS file contains `Part_2A` rows summing to 47 against a `Part_2` of 7. The anomaly is published upstream; our aggregation reproduces it faithfully.

Characteristics:
- **46 of 47 rows are independent-sector providers**, one public — consistent with F-09, which found independent reporting materially weaker.
- Magnitudes are trivial: median excess 3, maximum 254, **total excess 1,141 pathways against 578,432,603 total waiting** (0.0002%).
- Scattered across 2018–2026 with no concentration in any single period.

*Assessment:* upstream data-quality noise in small independent returns, not a modelling concern at this magnitude. **No correction applied** — silently clamping published values would be worse than carrying them. Recorded so that a downstream `dta_share = waiting_dta / waiting` calculation, which would exceed 1 in these 47 cells, is anticipated rather than discovered.

### 7.4 Contrarian re-test of F-15 — the backlog leak is real, not a panel artefact

F-15 reported the accounting identity leaking ~15% of demand every month. An obvious alternative explanation was never tested: the residual is measured on the **126-trust panel**, so a patient transferring from a panel trust to a non-panel provider leaves the panel's list without a panel completion — which would manufacture exactly this negative residual without any real removals.

Tested by recomputing on **all 653 providers**, where transfers between providers cancel out:

| Basis | Mean residual | As % of demand |
|---|---|---|
| Panel, 126 trusts | −183,635 | **−15.28%** |
| All providers, 653 | −233,155 | **−14.40%** |

The residual does **not** shrink. The leak is system-wide, so it is genuine attrition — removals, transfers out of RTT, validation, deaths, declines — and not an artefact of the panel boundary. **F-15 stands, and is now stronger for having survived the alternative explanation.**

### 7.5 Precision correction

Entry 5 gave the residual as −15.40% of demand; this entry gives −15.28% for the same panel. The difference is aggregation method: −15.40% is the *mean of the monthly ratios*, −15.28% is the *ratio of the means*. Both are correct for what they measure. Future reporting should state which, and the ratio-of-means figure is the one to quote for an annual-scale statement.

### 7.6 Weakness noted, not yet fixed — F-17

`inspect_dataset.ipynb` computes an integrity `PASS` flag that includes `not bad_zip`. With the archives deleted, `zips` is empty, so that clause is **vacuously true** and F-01 now reports `PASS=True` alongside "archives CRC-clean (0 tested)". The flag can no longer detect archive corruption but still reads as a full pass.

Not a wrong result — the CRC evidence is the run in §2.10 — but the wording overstates what the current run verified. The flag should distinguish *checked and clean* from *not checked*.

---

# Entry 8 — 2026-07-24
## Notebook audit against CLAUDE.md, and the column contract

Two questions asked: do the three `src/` notebooks obey CLAUDE.md and do what was requested; and can `data_processing.ipynb` be taken further by dropping columns that earn nothing and merging the RTT files into one table. Both answered by measurement, and one genuine defect found in the process.

## 8.1 Audit — rule adherence

| Rule | fetch_dataset | inspect_dataset | data_processing |
|---|---|---|---|
| Notebook, not script | yes | yes | yes |
| No `try`/`except`/retry/logging | **0 occurrences** | **0** | **0** |
| Fail-loud asserts instead | n/a | 1 | 3 → **6** |
| Per-line comments | 88 code lines, 19 uncommented (**78%**) | 526 lines, 379 uncommented (**28%**) | 209 lines, 122 uncommented (**42%**) |
| Executed with stored outputs | 6/7 cells | 30/30 | 12/12 |

No production-style error handling anywhere — the ban holds. The comment standard does not: `inspect_dataset.ipynb` is still the weak notebook at 28% trailing-comment coverage, unchanged from Entry 5. (The raw count overstates the gap — continuation lines inside multi-line expressions cannot carry a trailing comment — but the direction is right and the gap is real.)

## 8.2 Audit — did each notebook do what was asked

- **fetch_dataset** — yes. Three datasets, correct folders, resumable downloads, ODS reference built from the live API rather than the 403-ing static file.
- **inspect_dataset** — yes for validation, inventory, `C_999`, the provider census, the roster, the independent-sector gate. **Two defects found in section G** (below). Section I (KH03) is four lines: the workbooks are counted and nothing else. KH03 has never been joined to anything and no README component consumes it — it is currently dead weight, and should either be given a role or dropped from the acquisition.
- **data_processing** — yes for the era reconciliations, the coverage identity, the panel and the backlog residual. Extended this entry.

## 8.3 F-18 — the "per region" averages in section G are fragmented, and the entity is not stable

Section G groups public-provider demand by `["Provider Parent Org Code", "Provider Parent Name"]` and reports **111 regions**. England has 7 NHS regions and 42 ICBs. Measured on `provider_month_demand.csv`, public providers only:

| | |
|---|---|
| groups by code **and** name | **111** |
| distinct parent **codes** | **56** |
| parent codes carrying more than one name | **51 of 56** |
| median months spanned per code+name group | **27 of 96** |

This is **exactly the F-11 trap on a different axis**. F-11 established that NHS renames entities while keeping codes stable, and that every join must therefore be on code. The fix was applied to treatment functions and never carried across to the provider parent. Consequence: each real organisation appears two or more times, and `avg_per_month = total_demand / months` is computed over a ~27-month fragment rather than the window, so every figure in the section-G region table is wrong.

Grouping by code alone would fix the fragmentation but **not** the deeper problem — see F-20.

## 8.4 F-19 — the department averages predate the X_OTHER merge

The same section reports "avg new referrals per department per month: 83,880" over 24 treatment function codes, with `X01` (36 months) and `X02`–`X06` (60 months) appearing as six separate departments alongside the 18 real specialties. The canonical universe is **19 series**, not 24, and the six X codes are two eras of one thing. The averages section was written before D-02 and never revisited. The named-specialty rows are unaffected; the X rows and the mean across departments are not comparable to anything downstream.

## 8.5 F-20 — `Provider Parent Org Code` is not an ICB, and cannot be the escalation key

The README's decision layer escalates trust → ICB → national, so it needs a stable ICB per trust. The obvious candidate is the parent code stated in the RTT file. It fails. Agreement against `icb_ods` (the ODS `RE5` "is commissioned by" parent), public providers only:

| Year | rows | distinct reported parents | agreement with ODS |
|---|---|---|---|
| 2018 | 19,205 | 14 | **0.0%** |
| 2019 | 25,971 | 14 | **0.0%** |
| 2020 | 25,981 | 56 | 56.2% |
| 2021 | 25,815 | 42 | 74.2% |
| 2022 | 25,610 | 42 | 73.8% |
| 2023–2026 | ~81,400 | 42 | 72.8–74.1% |

The 2018–19 rows are not a bad ICB — they are **NHS regions**, a different level of the hierarchy, which is why agreement is exactly zero and there are only 14 of them. 2020 is the transition year (56 values). From 2021 the file names 42 ICBs and still disagrees with ODS in ~26% of rows.

*Decision:* the canonical table carries a single resolved `icb`, taken from ODS and backfilled from the reported parent only where ODS has no answer — one public provider, `TAD` (Bradford District Care NHS FT, the RO107 care trust), whose reported parent Q72 is a real ICB code. Asserted: **0 panel trusts without an ICB**. `icb_reported` and `icb_ods` leave the fact table and survive as provenance columns in `provider_dim.csv`.

Note this makes the hierarchy **time-invariant by construction**: every month is attributed to the trust's present-day ICB. That is the right choice for an escalation simulation — the board that would receive a request today is today's board — but it is a modelling decision, not a property of the data, and any historical ICB-level statement must say so.

## 8.6 The column contract — 121 raw columns to 14

The request was "drop unnecessary columns, decided by whether the column contributes to the README's goals". Each drop is justified by a measurement now printed in the notebook, not by assertion.

**Contrarian note on the framing:** "merge all the CSVs into one" was already done — `rtt_canonical.parquet` has been the merge of all 96 files since Entry 5. The work that remained was the contract, not the merge. A CSV copy is now written alongside for tools that cannot read parquet.

### Dropped, and why

| Dropped | Measurement |
|---|---|
| `Total` | Summed by part type, it is **identically zero** for `Part_2`, `Part_2A` and `Part_3` in both eras. Populated only for the two completed part types, where it equals `Total All` minus the unknown-clock-start count. `Total All` is the only headline column populated for all five part types — the choice made in Entry 5 is now proved rather than assumed. |
| `Patients with unknown clock start date` | 0.0061% of `Total All` pre-2021, 0.0066% post, and already included in it. |
| `Commissioner Org/Parent Code` + names | A second hierarchy (who pays), orthogonal to provider → ICB → national. The raw file is at provider × commissioner grain: **~145,000 rows/month collapse to ~16,000** provider × dept × part groups, a 8.8–9.6× multiplier. Assert 1 (full-coverage identity vs `C_999`) passes *after* the collapse, so nothing about provider totals is lost. |
| `Provider Parent Name`, `Commissioner *Name`, `RTT Part Description`, `Treatment Function Name` | Labels for codes already carried, and F-11/F-18 show the labels are unstable while the codes are not. Carrying them is an active hazard. |
| bands 0–18 weeks | Within-standard waits. The agent's state is the breach count. |
| bands on `Part_1A/1B/2A/3` | `Part_3` has **0 of 29,155 rows** with any band populated (F-03 reconfirmed). For the completed parts the bands are realised wait — a plausible future feature, in no README state variable, dropped deliberately and recoverable from raw. |
| `provider_name` | One value per code occupying 30 MB of a 170 MB in-memory table. Moved to `provider_dim.csv`. |
| `icb_reported`, `icb_ods` | Superseded by `icb` (F-20); kept as provenance in `provider_dim.csv`. |
| `in_roster` | Exactly `dept != X_OTHER`, verified. Two ways to state one fact is two ways to disagree. |

`completed` is **kept** despite being exactly `admitted + nonadmitted`: it is a measure the README names directly. The rule adopted is *drop derivable flags, keep derived measures*.

### Kept: 14 columns

`month`, `provider_code`, `dept`, `sector`, `icb`, `panel_member`, `demand`, `completed_admitted`, `completed_nonadmitted`, `completed`, `waiting`, `waiting_gt18`, `waiting_gt52`, `waiting_dta`.

Every one maps to a named consumer in the README — forecast target, throughput split, backlog stock, the 18-week standard, breach severity, the bed-linked admission queue, the substitution-capacity split, the escalation key, the client selector.

## 8.7 New standing asserts

Two added, taking the notebook from 4 to 6:

5. **Hierarchy completeness** — 0 panel trusts without an ICB, or escalation has nowhere to go.
6. **Round trip** — the written parquet is read back and must return the same shape with `month` still a datetime, because a written file that cannot be read is not an output.

## 8.8 README

Rewritten for structure rather than content: the project prose was six unbroken paragraphs. Now sectioned — problem, the two engines as a division-of-labour table, the RTT-concept → project-role mapping, the three baselines, bounded scope, repository, data layout, the canonical schema table, measured facts, environment. Notebook and worklog references are links. No claim was added that is not measured somewhere in `src/`.

## 8.9 Open

- **F-18 and F-19 are not yet fixed** — the defect is in `inspect_dataset.ipynb` section G, which was not in scope this turn. The region table there should not be quoted until it groups on code alone and, better, on the resolved `icb`.
- **F-17** (vacuous integrity `PASS` flag) still open from Entry 7.
- **KH03 has no consumer.** Decide whether the bed data enters the model or leaves the repository.
- The `inspect_dataset.ipynb` comment gap (§8.1) is unchanged.

---

# Entry 9 — 2026-07-25
## Column dossier, the escalation assumption tested, and three corrections including two of mine

## 9.1 The dossier — a standing rule for column fate

`inspect_dataset.ipynb` gains **section J**, which characterises every column and decides nothing; the keep/drop decision stays in `data_processing.ipynb`. Three tests in order:

1. **Is it populated?** blank, constant or rounding-error columns decide nothing.
2. **Is it a label or an axis?** A column taking exactly one value per `provider × treatment function × part type` is *functionally determined* by keys already carried — a label, and F-11 proved labels are unstable while codes are not. More than one value means a genuine dimension, and collapsing it is a loss of information requiring justification.
3. **Does the goal consume it?** measured against the README's named state vector.

Test 2 is the sharp one: it converts "is this redundant?" from a judgement into a query. Adopted as a convention.

## 9.2 F-21 — the commissioner columns are the only real second axis

Of the 16 descriptive columns, every one is a key or a label **except the four commissioner columns**. So the earlier justification for dropping them — "a second hierarchy, orthogonal to ours" — was a hand-wave: it is a real dimension being summed over, not redundancy being removed.

*Defect in the finding as first emitted:* the test was run over all 16 non-band columns, so `Total`, `Total All` and `Patients with unknown clock start date` were also reported as "axes". They are measures, not descriptive columns — of course they vary within a key that has several commissioner rows. The finding overstates: **4** columns are the real answer, not 7. To be corrected in the cell.

## 9.3 F-22 — the trust → ICB escalation tier is sound, with a nameable exception

This was never a column question. The README escalates trust → ICB, which is only sound if an ICB commissions the work its trusts deliver. Measured for the first time:

| | |
|---|---|
| all new referrals commissioned within the provider's own ICB | **84.3%** |
| median per public provider | **91.9%** |
| public providers below 50% | **11 of 150** |

The low tail is not noise and not a data defect — it is **national specialist centres**, exactly as predicted before the number was seen:

| Trust | own-ICB share |
|---|---|
| Clatterbridge Cancer Centre | 0.0% |
| Central and North West London | 0.0% |
| Moorfields Eye Hospital | **13.1%** |
| The Royal Marsden | 14.3% |
| Great Ormond Street | 15.1% |
| Royal National Orthopaedic | 18.5% |
| Alder Hey Children's | 23.0% |
| Royal Brompton & Harefield | 26.0% |

*Decision:* option (a) plus the retained measurement. The commissioner axis is collapsed, escalation is modelled trust → parent ICB as a **stated approximation, weakest for specialist centres**, and `own_icb_share` is retained per provider in `provider_dim.csv` so a reader can see how literally to take any given trust's escalation. This matters for the ophthalmology story specifically: Moorfields is a flagship for the C_130 finding and is one of the least ICB-aligned trusts in the country.

## 9.4 F-23 — `Total All` is the only universal headline column, proved on the full column set

`Total` is identically zero for `Part_2`, `Part_2A` and `Part_3`; for the completed parts it is `Total All` minus the unknown-clock-start count, which is **0.0066%** of all activity and already inside `Total All`. Bands sum to `Total All` exactly for `Part_2`/`Part_2A`, to 0.999× for the completed parts (unknown-start patients are unbanded), and to **zero for `Part_3`** — F-03 reconfirmed across every column rather than by inspection of one part type.

## 9.5 F-09 was wrong — correction

> ~~F-09: "the balanced-panel rule performs most of the sector filtering by itself, as predicted."~~

It does not. On the census basis (months carrying a `Part_3` row), **126 independent providers span all 96 months — exactly as many as the 126 public trusts.** The rule removes 331 of 457 independents and leaves 126; the panel is public because an **explicit sector filter** does that work, not the balance rule.

The substance matters: the owner's criterion — "if independents report the same data, include them" — is satisfied by 126 providers, so the question is live rather than settled by the data. What the data also says is that they are not like trusts: ~1/20th the scale, a median of 11 of 19 departments, 86.5% vs 98.5% of cells carrying non-zero demand, and 46 of 47 `Part_2A > Part_2` anomalies (F-16) are theirs.

## 9.6 My own error — the "4 missing full-history trusts" was an artefact of my definition

Reported last turn: *"4 public providers with full 96-month history (RAE, RBQ, RH5, RW5) are not in the panel — the panel rule uses a different condition."*

Wrong, and the fault was mine. I counted months as **any row in the canonical table**; the census counts months carrying a **demand row**. RAE appears in 96 months but has `Part_3` rows in only 74 of them. On the census's own basis, `public & months_present == 96` reproduces `panel_member` **exactly, 126 = 126**. The panel rule is consistent and needed no diagnosis.

The correction is not cosmetic — it also revises §9.5 from 169 independents to **126**, because that count was made on the same wrong basis. The lesson is the one the census exists to enforce: *every provider count comes from `provider_census.csv`, on its stated definition; a count computed ad hoc from another table is a different question wearing the same words.*

## 9.7 D-07 — `panel_member` split into two flags

`panel_member` was doing two jobs: "trains the forecaster" and "can receive an allocation". They separate on the axis the README already draws — capacity is **allocated to** NHS trusts and **purchased from** independents.

- **`fl_client`** — federated training client. Currently the 126 trusts.
- **`allocatable`** — can receive NHS capacity. `sector == public`. Independents are `False` by construction: an ICB can commission from a private provider, it cannot direct NHS staff and capital into one.

Neither implies the other, which is what makes "126 vs 126+126 independents" a runnable phase-3 ablation rather than a design argument.

*Ablation pre-registration, recorded now so the result cannot be read post-hoc:* scored on the **fixed 126-trust series in both arms** (adding clients changes the metric population as well as the training set); aggregation weighting **pinned to n-samples**, so the test is inclusion under the deployed scheme rather than a weighting artefact; and the hypothesis registered **against the previous refutation** — the earlier pre-registered "FL rescues the small data-poor client" was refuted, with gains in mid-size clients and the thinnest better off local. These providers are thinner still, so prior evidence predicts little gain and little contribution. Either outcome is a result; framing them in advance as the method's best test cases would repeat exactly the error that pre-registration exists to prevent. If they enter, `sector` becomes a **model input**, not just a table column, because independent `Part_3` is partly commissioned flow rather than organic demand and F-08 already showed the mix is non-stationary.

## 9.8 The backfill leak, fixed properly

Found by re-reading my own output rather than by a test: `icb` came back with **47 distinct values** for a country with 42 ICBs. Cause: the fallback was applied **per row**, so a provider ODS could not place took its own reported parent each month — a region code before 2020, an ICB after. Eleven region codes (`Q71`, `Q72`, `Q74`–`Q79`, `Q85`, `Q86`, `QRV`) entered the escalation key, and `TAD` was Q72-the-region in 2018–19 and QWO-the-ICB from 2021.

This is the **third instance of one failure class in two weeks** — an organisation-level attribute resolved per row from the monthly files: names (F-11), parent organisations (F-18), now the backfill. Rule adopted, and written into the notebook: *attributes of an organisation resolve once into `provider_dim` and are joined from there; nothing entity-level is ever derived per-row from the monthly files.*

Fix: the fallback is the provider's most recent post-2021 reported parent, **accepted only if that code is a known ICB**, giving one fixed value per provider. Two asserts, because either alone is insufficient:

- **6a** — `icb` has exactly one value per provider across all months.
- **6b** — no resolved value lies outside the ODS ICB set. 6a alone would pass if a provider were *consistently* backfilled with a region code, which is the leak that actually occurred.

## 9.9 Contract frozen at 15 columns

`waiting_gt52` **retained**, and the README amended rather than the contract. Three consumers, none of which were stated: the agent's classifier cannot separate "behind" (breaching 18 weeks) from "in crisis" (a year-plus tail) on `waiting_gt18` alone, since two services with identical breach counts can have very different tails, and the two states demand different asks; the `>52` series is one of the two reconstructions **Assert 2 guards**, so it is load-bearing in the verification layer regardless; and 52 weeks is the NHS's own elective-recovery target line, so severity measured there maps onto a real policy standard rather than an invented threshold. The contract's rule — a column earns its place only if the README's system consumes it — was being violated by a column that deserves its place, so the README gains the line.

`fl_client` and `allocatable` replace `panel_member`, taking the table to **15 columns**. `own_icb_share` is retained in `provider_dim.csv`.

## 9.10 Still open

- **F-01 has mutated** — the stored finding reads "archives CRC-clean **(0 tested)**" because the notebook was re-run after deletion. The original verification happened; the artefact no longer evidences it. Fix: pin the original CRC log and write a **sha256 manifest of the extracted CSVs**, which decision 5 required before deletion and which was never produced.
- **Cell 27 overclaim** — "largest/smallest ratio 1,435×" is max/min over 196 public providers including a 2-month provider and a 22-referrals/month minnow, the same tenure-confounded overclaim the EDA revision purged. Must be a p90/p10 spread before it reaches any report.
- **F-21 text** overstates (§9.2) — 4 axis columns, not 7.
- **F-14 needs an evaluation guard, not a note.** 524 all-zero series in the forecast path would *fraudulently improve* macro-sMAPE, since sMAPE(0,0) → 0 drags the mean down, as well as wasting training. Phase 3 must implement an `offered` mask in the windowing **and** in the metric's series set.
- **The ~26% post-2021 ICB disagreement** between file and ODS is asserted as real drift and never chased on a sample of disagreeing trusts.
- `inspect_dataset.ipynb` comments unchanged at 28% against the 78% `fetch_dataset.ipynb` demonstrates.

---

# Entry 10 — 2026-07-25
## Working mode changed: the owner writes everything from `inspect_dataset` onward

## 10.1 The decision, and the reason

The owner stated that a **completed earlier version of this project was rejected by their supervisor**, and that the correction is to derive the work themselves rather than review work already done. Recorded as **D-08**.

From now on:

- `src/fetch_dataset.ipynb` (acquisition) stands as built. Everything downstream is the owner's to write from scratch.
- Claude explains concepts, sets tasks with **target numbers** so the owner can self-check, and reviews code the owner has written. Claude does **not** write analysis code, scaffold notebooks, or supply solutions — including as "a starting point", an illustrative snippet, or pseudocode that transcribes 1:1.
- The only override is explicit and must be logged here as a decision, so the supervisor can see exactly which parts were not hand-written. Frustration or a rephrased request is not an override.

Written into `CLAUDE.md` as its first substantive section, above the researcher rules, so it is read before anything else each turn. The rationale is written in too: **code the owner did not write is a defect in the deliverable even when it is correct.**

`CLAUDE.md` also now carries the *forcing* clauses, which are the operative part: ask what they think before explaining; make them predict before they measure; ask "why" after every result; do not let a passing assert go unexamined; insist on worklog notes every session.

## 10.2 The previous build is archived, not deleted

`inspect_dataset.ipynb` and `data_processing.ipynb` moved to **`src/_solutions/`**. They are a reference of last resort — a number can be checked against them when everything else has failed. They are not to be read to answer a question the owner is currently working on, and not to be extended. `src/` now contains only `fetch_dataset.ipynb`.

This is deliberately not a deletion: the findings F-01…F-23 were expensive to obtain and several are non-obvious traps. Losing them would mean rediscovering them by accident rather than by design.

## 10.3 `GUIDE.md` / `GUIDE.pdf` — the teaching document

Nine parts plus an appendix, ~25 KB, rendered to PDF (162 KB, A4).

Structure: what is on disk → what one row means (the five part types, stocks vs flows) → the April 2021 schema break and its three consequences → who is in the data (sectors, the balanced panel) → building the canonical table → the hierarchy problem → the panel and the zero-fill evaluation trap → the accounting identity → open questions → the pandas idioms this dataset actually demands.

Design decisions worth recording:

- **Targets, not code.** Every task states the number to hit — 96 files, 653 providers, 199,410 identity groups with 0 mismatches, 322,531 canonical rows, 18 of 24 renamed, 526/524 structural series, and so on. The owner writes the query; the number tells them whether they were right without showing them how.
- **Traps are set, not disclosed.** `C_999` is introduced as "one of these codes is not a specialty" with the 7,045,510 vs 14,091,020 pair given as the tell. The April 2021 step is set as "plot file size and see the jump" before it is explained.
- **Both definitions of "present" are made an exercise**, because the project has already shipped a wrong number from exactly that ambiguity (Entry 9.6). The task explicitly asks for it computed both ways.
- **The p90/p10 vs max/min task** exists to make the 1,435× overclaim (still open, Entry 9.10) something the owner discovers rather than inherits.
- **Part 9 lists the genuinely open questions** with no target number, so it is clear which parts of the project are unanswered rather than merely unwritten: the 26% ICB disagreement, KH03's lack of a consumer, seasonality, COVID recovery by specialty, independent-share concentration, and the independents-as-clients ablation.

## 10.4 The canonical build was finished and verified before the handover

The `icb` backfill leak from Entry 9.8 is fixed and the notebook re-ran clean, so the archived state is a correct one rather than a broken one:

| | |
|---|---|
| errors | **0** |
| canonical | 322,531 rows × **15** columns, 653 providers, 19 depts, 96 months |
| `icb` | **36 distinct, all valid** — no region codes; asserts 6a and 6b both pass |
| federation clients / allocatable | 126 / 196 |
| own-ICB share (public) | mean 82.7%, **median 89.9%**, 12 of 173 below 50% |
| outputs | `rtt_canonical.csv` **28.1 MB** (literal single CSV, as asked), parquet, panel, `provider_dim.csv` |

Two honest consequences of the stricter backfill rule: only **2** public providers are now backfilled rather than 16, because the rule refuses any code that is not a known ICB — so **14 public providers have no ICB at all**. None is a federation client, so nothing is blocked, but it is a real gap and not a rounding detail. The stale `rtt_canonical.csv.gz` was removed now that a literal CSV is written.

One bug was introduced and caught during this pass: a blanket rename of `panel_member` → `fl_client` also hit `census.panel_member`, which is a column name in `provider_census.csv` and not ours to rename. Caught by the run failing immediately with `AttributeError`. Cheap because it was loud — the argument for asserts and against silent fallbacks, again.

## 10.5 Where this leaves the open items

Items still open from Entry 9.10 are now **the owner's work, not Claude's**, and most are folded into `GUIDE.md` as tasks: the sha256 manifest and F-01 honesty, the 1,435× overclaim, the `offered` mask, the 26% ICB disagreement, KH03. They stay listed here so nothing is lost in the handover.

The F-21 text defect (4 axis columns, not 7) is now moot in the sense that the notebook containing it is archived — but the *lesson* is in the guide, as the label-or-axis test, which is the part worth keeping.

## 10.6 `NOTES.md` — the owner's learning log, enforced

Added to `CLAUDE.md` at the owner's instruction. `NOTES.md` is separate from this file: `WORKLOG.md` records what the project found, `NOTES.md` records what the **owner** now understands. It is the artefact that answers the supervisor's objection directly.

Every completed task gets an entry with four required parts: **what I expected** (written before running it), **what I got**, **the gap and why** (mental model, query, or assumption about the data), and **what I now know that I did not**.

Claude enforces it as a gate rather than a reminder: ask for the prediction before the task starts, and **refuse to move to the next task while the previous one has no entry**. Claude must not write, draft, or template the notes — an entry Claude produced is worth nothing, since the entire value of the artefact is that the owner produced it. Thin entries get pushed back on; questions already covered by an existing note get answered by pointing at the note rather than re-explaining.

## 10.7 `GUIDE.pdf` expanded to cover the whole project

The first version covered only the dataset and the table build. Rewritten to cover everything: **12 parts plus four appendices**, 40 KB markdown, 208 KB PDF.

Added over the first version:

- **Part 0 — what the project is.** The forecaster, the three baselines it must beat (persistence, isolated per-client, pooled central), the agentic decision layer, and what is deliberately out of scope. The guide previously assumed this context; now it states it, so the owner builds a table that fits the job.
- **Part 1 — acquisition and the reference tables.** What `fetch_dataset.ipynb` actually did, why the `.part`-then-rename pattern is the one permitted safety net, a dictionary of all eight files in `data/reference/`, how the ODS ORD API works (`PrimaryRoleId`, `Rels`, `RE5`), and KH03 stated as an **open question rather than a settled exclusion**, including the resolution mismatch that makes the join non-trivial.
- **Part 3 — the full 24 treatment functions** with names and demand shares, measured from `tf_month_demand.csv`. Two observations drawn out: the X buckets are ~25% of demand, and specialties differ >50-fold in size, so any cross-specialty average is a weighting choice.
- **Part 10 — what comes after the table.** Windowing, the temporal-split requirement, where COVID goes, per-client scaling, FedAvg, the weighting decision, per-client fine-tuning — and the **pre-registration warning** that "FL rescues the small client" was already refuted once on this project and must not be quietly re-adopted.
- **Task 8.3** — a new task making the zero-fill metric trap numerical rather than described: score a metric with and without 500 constant-zero series and watch it move for a reason unrelated to model quality.
- **Task 6.4** — the label-or-axis test as an exercise, including the category error made on this project (running it over the measure columns and reporting them as axes).
- **Task 7.4** — the entity-attribute rule as an exercise, with the requirement to write **both** asserts and explain why either alone is insufficient.
- **Task 9.3** — mean-of-ratios vs ratio-of-means, from the Entry 7.5 correction.
- **Appendix A — glossary** of 22 NHS and FL terms.
- **Appendix C — every target in one table**, so self-checking does not require re-reading.
- **Appendix D — sources**, with `WORKLOG.md` named as the most useful one.

Open question 7 added: **no sha256 manifest of the extracted CSVs was ever written**, so there is no standing integrity baseline now the archives are gone. Flagged as cheap to fix and to be done before anything is published from these files.

The pedagogy is unchanged: no analysis code anywhere, traps set rather than disclosed, and every task carries the number to hit. `findings.csv` is explicitly labelled in the reference dictionary as the answer key, not to be read until the exercises are done.

## Laptop realigned to the handover state

**2026-07-25, laptop session.** The owner asked for the laptop's `FedOPD/` directory to be
emptied entirely — code, `data/` (60 monthly CSVs + archives), `.venv`, `.git` — with no backup,
then re-cloned from the latest remote state only. Done: directory wiped, then shallow clone
(`--depth 5`) of `origin/master` at `e6354e5`. Nothing was committed or pushed from the laptop
during this; the parallel laptop line from 2026-07-23 (decision-first `src/`, `a100/`, dashboard)
remains in remote history beneath the handover commits, superseded by the restructure.

Consequences on this machine:

- **No `data/`** — re-acquisition is via `src/fetch_dataset.ipynb`, run by the owner.
- **No Python environment** — the old `.venv` (torch cu128 on the RTX 4060, flwr) was deleted
  with everything else and the new tree carries no `requirements.txt`; environment setup is
  needed before any notebook runs locally.
- This laptop Claude session has read `CLAUDE.md` and operates under D-08 from here on:
  concepts, target numbers, and review only — no analysis code, no scaffolds.

---

# Entry 11 — 2026-07-25
## Source-documentation pass: what NHS England actually publishes, read from the primary docs

Owner asked, before starting EDA, to understand the CSVs from the NHS source itself — how the
files are constructed and what each column means — rather than reverse-engineering meaning from
the data. No code written; this is a documentation/teaching pass. Authoritative sources retrieved
and read directly (two NHS PDFs downloaded and text-extracted with `pypdf`, since WebFetch's
parser cannot decode FlateDecode-compressed NHS PDFs):

- **Recording and reporting RTT guidance v5.2 (PRN01045, Oct 2025)** — the definitions.
- **RTT statistics work area page** and the **2025-26 monthly data page** — file inventory.
- **March 2026 statistical press notice (published 14 May 2026)** — methodology / estimation.
- **NHS Data Dictionary, Treatment Function Code** — the specialty codes.

### 11.1 Confirmed from primary source (matches existing project facts)

- **The CSV is an aggregate return, not patient-level.** Providers submit via SDCS a spreadsheet
  form broken down by commissioner; the collection is "in three sections" = the part types. Grain
  is provider × commissioner × treatment function × part type × week-band. Confirms the README/GUIDE
  grain and the commissioner axis being the one genuine second dimension (F-21).
- **Exact part-type definitions (guidance p.41), verbatim:** Part 1a completed–admitted (clock
  stopped with inpatient/day-case admission); Part 1b completed–non-admitted (clock stopped for
  other reasons); Part 2 incomplete ("a 'snapshot' on the last day of the reporting period");
  Part 2a incomplete with a decision to admit (subset of Part 2, clinical decision to admit to a
  bed made); Part 3 new RTT periods (clock-start date within the month, "will include those where
  the clock also stopped within the reporting month"). Confirms GUIDE Part 2.
- **April 2021 change, from NHS's own list (guidance p.42 / press-notice Notes for editors §4):**
  (1) X24 commissioner code phased out for granular NHSE commissioning codes; (2) weekly bands
  52-53…104+ added to Parts 1A/1B/2/2A; (3) treatment-function changes — name updates **and** the
  'Other' category split into five groups. This is F-02 + F-11 + the X-bucket split, now sourced.
- **Independents are genuine.** Guidance p.40: IS providers commissioned by a sub-ICB/NHSE "should
  engage in the RTT data collection… in the same way as NHS provider organisations." Confirms F-07.

### 11.2 New facts the project docs do NOT currently capture

1. **A THIRD structural break inside the window: community services removed from RTT, Feb 2024.**
   Press-notice Notes for editors: from Feb 2024 community-service pathways are no longer reported
   in RTT (moved to the Community Health Services waiting-list collection). Measured impact ~43,000
   pathways dropped — mostly **Community Paediatric / Paediatric Neurodisability**, which sit inside
   **"Other – Paediatric Services" and "Other – Other Services"**, i.e. our `X_OTHER` post-2021
   buckets (X02–X06). ~36k left the Feb 2024 figures, ~7k the Mar 2024 figures; ~4,400 fewer 52-wk,
   2,500 fewer 65-wk, 1,400 fewer 78-wk waits. **Consequence:** `X_OTHER` has a genuine
   discontinuity at Feb–Mar 2024 that the project has treated as a smooth 96-month series with only
   the Apr-2021 recode. The D-02 boundary-continuity assert guards **2021-04 only**; it does not
   look at 2024-02. This is concentrated in the X buckets, not the 18 named specialties, so the
   forecast target for the named roster is largely unaffected — but any `X_OTHER` series and any
   paediatric "Other" analysis crosses a ~43k downward step in early 2024. **Open: check X_OTHER at
   2024-02/03 against local variation the same way the Apr-2021 break was checked.**

2. **The published headline includes estimates for non-reporting trusts; the CSV does not.** March
   2026: **Sheffield Teaching Hospitals (RHQ) submitted no RTT data.** The press-notice "7.1 million"
   waiting and the precise long-wait counts (94,406 >52wk, etc.) **include an estimate** for missing
   acute trusts, carried in the *RTT Overview Timeseries* file, "based on the latest data submitted
   by non-reporting" trusts. The **Full CSV is the raw submitted aggregate with no estimate.** So the
   GUIDE/F-10 target **7,045,510** is the raw-CSV Part_2 sum and is the right number to reproduce
   from our data — but it is **not** identical to the press-notice headline, which is higher because
   of the Sheffield estimate. F-10's "press-notice confirmation OPEN" should be closed with this
   understanding: raw CSV ≠ published headline **by construction**, not by our error. Also flags that
   **March 2026 (our last month) is missing a large trust** — a real data-quality caveat for the end
   of the window.

3. **Treatment-function reporting exceptions (roll-ups).** Codes 108 (Spinal Surgery), 111
   (Orthopaedic), 115 (Trauma Surgery) are reported **inside 110 Trauma & Orthopaedics**; 144/145
   (Maxillofacial / Oral & Maxillofacial) inside **140 Oral Surgery**. So those codes do not appear
   as separate series by design — relevant to understanding why the roster is what it is.

4. **Pathways ≠ patients.** Press notice: 7.1M pathways vs ~6.0M unique patients (WLMDS-based);
   "some patients are on more than one pathway." The forecast target `demand` counts pathway
   clock-starts, not people. Worth stating in any patient-level interpretation.

5. **Waiting measured in completed weeks; bands are "Gt X To Y Weeks" = more than X and up to Y.**
   Read from the column names + the ">18 weeks" standard; NHS states "waiting times in weeks" but I
   did not find an explicit inclusive/exclusive sentence — treat the boundary convention as inferred
   from the column labels, not quoted. March 2026 sanity figures for the incomplete list: median
   11.3 wk, 92nd percentile 38.3 wk — derivable from the banded data as a cross-check.

### 11.3 Sources (for Appendix D / future reference)

- RTT statistics work area: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/
- Rules & guidance index: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-guidance/
- Recording & reporting guidance v5.2 (definitions, part types p.41, Apr-2021 changes p.42):
  https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/10/Recording-and-reporting-RTT-waiting-times-guidance-v5.2-Feb25.pdf
- March 2026 statistical press notice (estimation, community-services removal, Sheffield missing):
  https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/05/Mar26-RTT-statistical-press-notice-PDF-545K-Dc1i9U.pdf
- NHS Data Dictionary — Treatment Function Code:
  https://archive.datadictionary.nhs.uk/DD%20Release%20August%202024/attributes/treatment_function_code.html
- DCB0095 (the data standard behind the Apr-2021 collection change) — named in the press notice, not yet retrieved.

Open follow-ups from this pass: (a) X_OTHER break at Feb 2024 needs the same local-variation check
as Apr 2021; (b) fold the sourced definitions + the two new facts into GUIDE.md — **done, see 11.4**;
(c) DCB0095 and DCB0028 named by the docs but their own text not yet pulled.

### 11.4 GUIDE.md/GUIDE.pdf rebuilt with source citations (owner request)

Owner asked to rebuild the guide grounded in the fetched sources, citing NHS source rather than
memory, "all details, what each column is." Done. The guide is Claude-authored teaching material
(Entry 10.3), so rebuilding it is not a D-08 violation — no analysis code, pedagogy preserved
(tasks, targets, traps not disclosed).

Changes:
- **Two-tier fact discipline made explicit:** every claim about *what the data is* now carries a
  bracketed citation to the NHS doc + section/page (`[G §10.1.7, p.46]`), and every project number
  (653, 322,531, the leak) is labelled "measured" — not NHS-published. This mirrors the
  observation-vs-inference rule.
- **New "sources this guide is grounded in" table** with citation keys [G]/[SPN]/[DD]/[DD-T]/[SWA]/
  [DCB0095]/[DCB0028] and URLs.
- **Part 2** part-type table now quotes the guidance verbatim (p.41); column dictionary cited.
- **Part 3** rebuilt from the collection form's own 18 treatment functions with NHS names
  (`[G §10.1.4, p.43-44]`), the roll-up exceptions (108/111/115→110; 144/145→140; 170=172+173),
  and what falls into the five Other buckets.
- **Part 4** grounds the Apr-2021 break in NHS's own 3-item change list, adds the **exact band-to-day
  mapping** (18 weeks = 126 days is *within* standard), and adds the **Feb-2024 community-services
  break** as a second, grounded discontinuity in X_OTHER.
- **Part 5** adds pathways≠periods≠patients (7.1M vs 6.0M) and the **estimate-for-missing-trusts**
  nuance (Sheffield/RHQ; raw CSV 7,045,510 ≠ published 7.1M by construction).
- **Part 6/9** tie the coverage identity and the accounting-identity leak to NHS's own Annex-B
  validation checks and the rule-4/rule-5 clock-stop definitions.
- **Appendix A** glossary reworked to quote the guidance §13 terminology; **Appendix E** added — the
  band-to-day table and a per-column grounded dictionary; **Appendix D** is now a cited bibliography.
- New open items added to Part 11: the Feb-2024 X_OTHER step and the estimate-gap quantification.

### 11.5 CLAUDE.md gains the owner's learning method and communication style

Owner supplied a "how I work with Claude" brief; added to `CLAUDE.md` as two sections after the
`_solutions` paragraph: **"How the owner learns, and how to pitch to them"** (goal is recall not
tutorial-fluency; give shape/vocab/tradeoffs not code; find the gap don't fill it; adversarial
honesty, no validation; respect the owner's gates — brief-before-code, skeleton-first, smallest
end-to-end slice, trivia-stuck vs concept-stuck handled differently, the 20-minute rule, the error
log) and **"Communication style the owner wants"** (British/Indian spelling, no em-dashes, no emoji,
high signal-to-word, research-level not personal framing, short-and-crisp with depth underneath, do
not dump a wall of text in one reply — a long standalone doc like GUIDE.pdf is fine, a long reply is
not). Complements the existing "who writes the code" rule rather than duplicating it.

---

### 11.6 GUIDE rebuilt for the owner's audience framing + note-forcing

Owner: highly technical undergrad, first real research; wants detail kept and note-taking forced.
Edits to `GUIDE.md`: added a "Who this is written for" paragraph (no dumbing-down; detail is where
the result lives; notes are the deliverable the rejected version lacked), and promoted note-taking
from a closing reminder to a **standing "note gate"** near the top (a task is finished when the
four-part note is written, not when the number matches; do not batch notes). Also applied the new
style rule: **stripped all 182 em-dashes** to spaced hyphens. Caught and fixed a self-inflicted bug
- the em-dash pass included a `re.sub(r'  +',' ')` space-collapse that flattened the `data/` ASCII
tree in the one fenced code block; restored the tree and set `white-space: pre` in the print CSS.
Re-rendered: **GUIDE.pdf 16 pages / 864 KB**, verified 0 em-dashes and the new sections present.

Render path (no pandoc/latex/weasyprint on this laptop): `python -m markdown` (installed this turn)
→ styled HTML with an NHS-blue print stylesheet → **headless Chrome `--print-to-pdf`**. Gotcha
logged: Git-Bash `$(pwd)` yields `/c/...`, which Chrome rejects as a file URL — must pass
`file:///C:/...`; and Chrome could not overwrite an open `GUIDE.pdf`, so render to scratchpad then
`cp`. Result: **GUIDE.md 71 KB, GUIDE.pdf 15 pages / 857 KB**, verified to contain the key strings
(7,045,510; Gt 17 To 18; 43,000; Sheffield; 199,410; Appendix E). Intermediate `GUIDE.html` deleted.

### 11.7 GUIDE gains an active-learning gate ("do not blind-read")

Owner asked the PDF to push active engagement, not passive reading. Added a **"Do not blind-read this"**
callout directly after the note gate: cover the target before predicting; try to find each trap in
the data before reading its explanation; keep a kernel running beside the guide (stop if two pages
pass with no query); rebuild each part's core idea from memory before moving on; being stuck is the
mechanism. Re-rendered: **GUIDE.pdf 16 pages / 872 KB**, 0 em-dashes, section verified present.

### 11.8 Recurring active-learning reminders seeded through the GUIDE PDF

Owner wanted the predict/try/note/don't-blind-read discipline reinforced continually, not just once
up front. Chrome's print-to-pdf cannot do a CSS running footer (Blink ignores `@page` margin-box
content), so instead a small script inserts a rotating one-line reminder (`<div class="remind">`)
before every `# Part`, `# Appendix` and `### Task` heading - **45 in total, ~2.5 per page over 17
pages**. Ten messages cycle deterministically (predict before revealing; kernel open; write the note;
try the trap first; sit in the stuck; believe the data but check the question; rebuild from memory;
stop if only reading; a task ends at the note; ten rows before any hypothesis). Styled as a small
italic amber rule, distinct from the yellow target blockquotes. **Idempotent**: the script strips any
existing `class="remind"` lines before re-inserting, so rebuilds do not stack them. GUIDE.pdf now
17 pages / ~1.0 MB, 0 em-dashes.

### 11.9 Reminders rewritten from generic to context-specific and blunt

Owner: reminders must be tied to the concept on that page, and "be brutal". Replaced the 10 rotating
generic lines with **45 bespoke reminders, one authored per anchor** (each Part, Appendix and Task),
keyed to the exact heading text via a dict in a scratchpad script (heredoc quoting failed, so the
script was written to file and run). Each names that section's specific failure mode in blunt terms
(e.g. C_999 "hands you exactly double and lets you publish it"; Part 8 "wrong in your favour ... the
kind you will never think to question"; Task 9.2 "doing PR for your result, not research on it").
Restyled from soft amber to a red left-border callout to read as an alarm, distinct from the yellow
target blockquotes. Still idempotent (strips `class="remind"` before reinserting). GUIDE.pdf now
**18 pages / ~913 KB, 45 reminders, 0 em-dashes**; all anchors matched (0 missed).

### 11.10 Reminders rewritten again - bite on consequence, not hollow scolding

Owner flagged the Task 1.1 reminder as "lame": it scolded over trivial arithmetic (predicting 96 =
8x12) while ignoring the actual trap (missing months / original-plus-revised duplicates), and the
"if you cannot X you have not understood Y" construction recurred across several. Rewrote all 45 so
each names the concrete failure mode or consequence instead (Task 1.1 now points at gaps/duplicates;
9.2 "advertising your result, not testing it"; Appendix C "a loaded gun aimed at your own learning").
Same idempotent script, values only. GUIDE.pdf still 18 pages, 45 reminders, 0 em-dashes.

### 11.11 CLAUDE.md working-mode change: coding restriction removed

Owner decision: remove the rule barring Claude from writing analysis code, and remove the note-taking
gates and learning-method scaffolding along with it. Kept: the "simple notebook code" quality rules
(per-line comments, no production safety nets), the "Work like a researcher" critical rules, the
communication style, and a slim "who the owner is / wants detail" note. Replaced the whole "Who writes
the code" section with a short **"Working mode - Claude can help write the code"**: Claude may hand over
working code, held to the research-grade quality bar (no BS, no production-looking scaffolding); explain
as you go so numbers stay defensible, but this is guidance not a gate. `NOTES.md` and the per-task note
gates are retired; `WORKLOG.md` stays as the project record. This supersedes the D-08-era "owner writes
everything from inspect_dataset onward" mode.
