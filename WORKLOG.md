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

### 1.12 Working conventions adopted

Recorded in `CLAUDE.md` and enforced where enforcement is possible:

- Analysis code is written in Jupyter notebooks under `src/`, kept simple and research-grade, without production-style exception handling or defensive scaffolding.
- Code is commented on a per-line basis; the reasoning behind non-obvious constructions is stated explicitly.
- Long-running jobs are executed detached under `tmux` or `nohup`, never in a foreground shell, as the machine is accessed over SSH.
- Claims are verified against the source before being relied upon, and the distinction between what was measured and what was inferred is maintained throughout.
