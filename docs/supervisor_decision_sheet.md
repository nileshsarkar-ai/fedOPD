# Supervisor decision sheet — the four calls that unblock notebooks 15 and 17

Written 2026-07-30. Notebook 15 (frozen agent rules) and notebook 17 (one-shot sealed FY 2025-26
evaluation) are deliberately unwritten: 15 must restate *ratified* constants, and 17 must run frozen
rules exactly once. Nothing below is a recommendation to tune anything against a metric — every option
is a design/policy choice, and whatever is decided gets restated in 15 with the decision date. Every
number on this page traces to a stored output re-read today: `src/10_agent_logic.ipynb` stored prints,
`output/evals/eval_c110_agent_stress_h6.csv`, `data/processed/fl_scaleup_by_specialty.csv`,
`data/processed/fl_neural_summary.csv`.

## Decision 1 — ratify or revise the agent constants

All declared 2026-07-30 in `src/10_agent_logic.ipynb`, marked `pending supervisor ratification` in the
source; none was ever adjusted after seeing a result.

| constant | value | stated rationale (in 10) |
|---|---|---|
| pressure weights (>18w share, >52w share, occupancy) | 0.2 / 0.6 / 0.2 | the >52w share is the component that exploded post-Covid (0.05% → 4.11%, 81×); occupancy adds strain context despite near-zero forecast importance (07) |
| v1 pressure thresholds `P_HIGH` / `P_MID` | 0.70 / 0.40 | weighted within-month percentile: "top third of peers" |
| v1 band thresholds `G_RISK` / `G_STABLE` | 1.20 / 1.05 | band-upper vs current list |
| v1 spare-capacity threshold `OCC_SLACK` | 0.80 | G&A occupancy below 80% counts as slack |
| v2 within-ICB thresholds `OUT_THR` / `IN_THR` | 0.80 / 0.30 | ICB-internal pressure/occupancy percentile ranks |

Evidence on how they behave (2,337 provider-months, Apr 2023 – Sep 2024, 132 providers, C_110, h=6):

- **v1**: STATUS_QUO 2,003, EXPAND_CAPACITY 334 (30 distinct providers ever trigger it),
  REDISTRIBUTE_IN **0** — the receiving condition (pressure in [0.40, 0.70), occupancy < 0.80, band
  capping growth at +5%) never co-occurs in the real data. 10 also documents an absolute-band artefact:
  `upper ≥ 1.20 × current` reduces to `band ≥ 0.20 × current`, which fires more easily for small lists.
- **v2**: STATUS_QUO 1,775, REDISTRIBUTE_OUT 457, REDISTRIBUTE_IN 105. The three-window stress test
  (disjoint 6-month windows partitioning all 2,337 rows, asserted in 13) shows a stable shape: OUT
  median pressure 0.764 / 0.717 / 0.673 vs IN 0.179 / 0.181 / 0.198 across the windows, and OUT
  precedes the largest median realized 6-month changes (17.5 / 44.5 / 181.0 patients).

**Question: ratify the constants as-is, or revise (weights, thresholds, or the band construction)?**

## Decision 2 — receiving-side redesign

Only **13.6% of the 457** REDISTRIBUTE_OUT provider-months have at least one in-ICB REDISTRIBUTE_IN
slot in the same month (asserted in 13) — under the current in-ICB rule, most senders have nowhere to
send. Options, not mutually exclusive:

1. allow **cross-ICB** redistribution (neighbouring or any ICB);
2. include **independent-sector** providers as receivers (they are in the panel but outside the cohort);
3. a **minimum-group rule** (an ICB below k providers merges with a neighbour for matching);
4. keep in-ICB and treat unmatched OUT months as **ESCALATE** — an explicit "no local receiver" signal
   rather than a silent no-op.

**Question: which receiving-side rule should 15 freeze?**

## Decision 3 — multi-seed check of the neural C_110 result

Notebook 16 (one architecture, one seed, no tuning) produced the project's first sub-persistence C_110
scores: neural pooled 150.6 and neural FedAvg 152.4 vs persistence 154.1 on 1,401 identical rows. It is
one seed among 184 computed model-regime-specialty scores, so isolated sub-persistence results are
expected by chance. The declared check: rerun 16's training under K additional seeds (e.g. 5), change
nothing else, report every run. cuDNN nondeterminism is already disclosed in 16.

**Question: run the multi-seed check, or leave the result flagged single-seed?**

## Decision 4 — is a model layer justified outside C_110?

- Linear (14): a delta model beats persistence at 12 of 24 specialties, largest margin 6.5 MAE
  (C_120: 165.1 vs 171.6, n=1,265); persistence wins the rest (X01 has zero validation rows).
- Neural (16): neural FedAvg beats persistence at 11 of 23 scored specialties (full regime).
- Everywhere, deltas stay ≥ 92.5% noise (best delta-R² anywhere +0.075).

**Question: adopt a per-specialty model layer where it wins, keep persistence everywhere for
simplicity, or defer to the write-up as a finding without an operational recommendation?**

## What happens after these decisions

1. **Notebook 15** is written: the ratified constants restated with the ratification date, the agent
   re-run on validation only, outputs stored. No constant changes after this point.
2. **Notebook 17** is written and run exactly once on the sealed FY 2025-26 year, on explicit
   instruction, and its numbers are reported as-is — good or bad.

---

## Decisions (2026-07-30) — made by the project owner

The user directed that these calls be made now by the project owner; the supervisor reviews the final
draft. This section records who decided and when — nothing below is external sign-off. Frozen in
`src/15_agent_rules_frozen.ipynb`, which proves the constants reproduce notebook 10's stored decisions
bit for bit (asserted on all 2,337 rows).

1. **Constants: ratified as declared.** No value changed. The externally proposed ratification text
   was adopted only after correcting its labels — it called the component weights "low/medium/high
   pressure weights" and the five thresholds "action multipliers"; the values were right, the
   semantics were not.
2. **Receiving side: in-ICB only, minimum group 4 by arithmetic.** A rank ≤ 0.30 requires an ICB of
   ceil(1/0.30) = 4+ providers, so the minimum group is already enforced by the ratified threshold
   (asserted in 15: every stored receiver sits in a ≥4-provider ICB). The proposed "≥ 30 validation
   rows" group rule was **rejected as impossible**: the largest provider group in the simulation has
   18 rows (asserted), so it would have driven REDISTRIBUTE_IN to 0 — the opposite of its stated
   goal. Independent sector: excluded already by cohort construction. Newly measured in 15: **246 of
   457 OUT months (53.8%) sit in sub-4-provider ICBs** where no local receiver is ever possible —
   an inherent property of the frozen in-ICB rule, reported, not patched.
3. **Multi-seed check: run and CONFIRMED** (`src/19_neural_c110_multiseed.ipynb`; seeds 42/123/999
   and the verdict rule declared before running). Full regime, both models below persistence under
   all three seeds: neural pooled 151.5 ± 0.9 MAE (150.6 / 152.2 / 151.9), neural FedAvg 152.4 ± 0.0
   (152.4 / 152.3 / 152.4) vs persistence 154.1, n=1,401. Post regime reported as-is: FedAvg 3 of 3,
   pooled 2 of 3 (seed 123 lands exactly on 154.1).
4. **Model layer outside C_110: exploratory only.** Persistence stays the operational forecast layer
   everywhere; per-specialty gains (≤ 6.5 MAE) are findings, not deployment claims.

Correction made while ratifying: this sheet previously said 150 providers; the stored decisions cover
**132 providers** (recounted from `agent_decisions_h6_c110.csv` and now pinned by assert in 13).

**Execution record (2026-07-30):** 15 froze the rules; 19 confirmed the C_110 neural result on
validation (3 seeds); **17 ran the sealed year exactly once** — at C_110, persistence 151.5 edged
neural pooled 151.6 (n=1,407), so the neural edge did not replicate prospectively, while in aggregate
neural pooled beat persistence at 15 of 23 specialties. Full record: `sealed_year_eval.csv` and the
summary md's sealed-year section. Notebook 17 is never re-run.

**Audit addendum (2026-08-01):** the independent integrity audit confirmed the freeze is bit-for-bit
sound and found no tampering, but surfaced two findings the frozen rules inherit. (1) The `fl_client`
cohort rule in notebook 03 reads the sealed year (selection look-ahead); the agent chain is untouched
(`fl_allocatable` is identical under the prospective rule — zero providers differ), but the forecast
anchors carry a sensitivity, quantified in notebook 21 / `cohort_sensitivity.csv`. (2) 103 of the 457
REDISTRIBUTE_OUT flags (22.5%) are mechanical: a lone provider in its ICB-month ranks 1.0 by
definition and clears the 0.80 sender bar regardless of state (median pressure 0.533 vs 0.765 for the
354 peer-based flags; asserted in 13). Per the freeze policy the frozen redistribution rules are NOT
overwritten; any future rule version (e.g. requiring at least 2 in-ICB peers, or an explicit
NO_PEERS_ESCALATE class) is a new dated decision for this sheet. The papers now present the pressure
separation as by-construction, the outcome separation as the finding, and the design sequence
(redistribution rules written after the capacity rules' outcome check, same 2,337 rows) as in-sample.
