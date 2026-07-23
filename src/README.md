# src/ — the decision-first pipeline

The pipeline rewritten from the point of view of `docs/PROBLEM.md`: the goal is not demand
prediction for its own sake — it is that **a branch hospital that needs more staff can access
it**, through an auditable request → allocation → approval → verification loop, with the
demand forecaster learned federatedly (no raw data leaves a branch) as the instrument.

| # | notebook | PROBLEM.md goal it serves |
|---|---|---|
| 00 | `00_network_and_data` | the group: branches (trusts), boards (ICBs), departments (specialties) + the operational panel |
| 01 | `01_pressure` | detect pressure: who needs staff, where, how much (GREEN/AMBER/RED, backlog, WTE lens) |
| 02 | `02_federated_forecaster` | learn jointly without sharing data; the ladder is the instrument's honesty certificate |
| 03 | `03_staffing_requests` | branch coordinator agents convert forecasts into staffing requests (+N WTE / slots per month) |
| 04 | `04_board_allocation` | boards rank requests under budget → fund / partial / defer + strategic decisions (enhance, expand, segregate) |
| 05 | `05_verification` | the thesis test: did units in true need raise requests, and did they get access? precision, recall, access rate — plus forecast-driven vs backlog-driven allocation |
| 06 | `06_selection_audit` | appendix — provenance: the 35-branch network re-derived from raw + NHS ODS registry (AUDIT PASSED) |

`src/` is fully self-contained: it needs only `../config/nhs_network.json` and the raw monthly
CSVs under `../data/` — nothing else. The A100 mirror of this pipeline (96-month data, powered
multi-seed sweep) lives in `../a100/`.

Stated planning assumption used throughout: **1 clinical WTE ≈ 200 outpatient appointments
per month** (`SLOTS_PER_WTE = 200`, adjustable in one place; a coarse NHS job-planning
ballpark — the loop's logic is invariant to the exact number).

Run in order (each notebook is self-contained given the previous one's artifacts):

```bash
cd src
jupyter nbconvert --to notebook --execute --inplace 00_network_and_data.ipynb
# ... then 01..05 in order
```
