# `src/` baseline — complete specification and results

Everything the 5-year (60-month) run used and produced. Extracted verbatim from the executed
notebooks `src/00`–`src/06` on 2026-07-23. **This is the reference the A100 scale-up is measured
against** — any A100 number is only meaningful next to its row here.

Run environment: laptop RTX 4060, `device: cuda`, torch 2.11+cu128, **single seed (0)**.

---

## 1. Dataset sizes at every stage

| stage | artifact | size |
|---|---|---|
| raw | 60 monthly RTT CSVs, `2021-04` … `2026-03` | ~5.1 GB, ~121 cols/file |
| raw grain | provider × commissioner × RTT part × specialty | — |
| panel | `data/processed/rtt_long.csv` | **210,328 rows × 11 cols** |
| panel scope | 35 branches · 23 departments · 60 months · 5 parts (`Part_1A/1B/2/2A/3`) | — |
| ops panel | `data/processed/ops_panel.csv` | **694 units × 60 months = 41,640 rows** |
| features | `data/processed/features.csv` | **33,312 rows** = 694 series × 48 months |
| — train | months ≤ `2024-09` (30 target months) | **20,820 rows** (~595/client) |
| — val | `2024-10` … `2025-03` (6 months) | **4,164 rows** (~119/client) |
| — test | `2025-04` … `2026-03` (12 months) | **8,328 rows** (~238/client) |

Note: the 48 (not 60) feature months come from the `lag12` warm-up eating the first 12 months.

**The group:** 35 branches · 7 regions · **29 boards (ICBs)** · ~675,458 referrals/month.
Departments per branch: 16–23. Panel units = 694 of 760 possible (trust, specialty) pairs —
kept if `demand > 0` in **all 60 months**.

**Selection audit** (`src/06`, run live against raw + NHS ODS registry):
172 NHS trusts ever seen → **139 eligible** (demand in all 60 months) → top-5 per region by mean
monthly referrals → 35. Eligible pool per region: East of England 15 · London 21 · Midlands 27 ·
North East & Yorkshire 21 · North West 21 · South East 20 · South West 14. Distinct anchor ICBs
seen: 42. **AUDIT PASSED** — 0 config trusts unreproduced, 0 audit trusts missing from config.

---

## 2. Forecaster — every hyperparameter

### Architecture (`Net`) — **1,597 trainable parameters**

| component | value | params |
|---|---|---|
| `nn.Embedding(23, 4)` | 23 departments, `emb=4` | 92 |
| `nn.Linear(12, 32)` | 8 features + 4 embedding, `hidden=32` | 416 |
| `nn.ReLU()` | — | 0 |
| `nn.Linear(32, 32)` | — | 1,056 |
| `nn.ReLU()` | — | 0 |
| `nn.Linear(32, 1)` | — | 33 |
| **output head** | `ŷ = x[:,0] + MLP(…)` — **residual on lag1** | — |

The residual head is why the model *starts at the naive baseline* instead of having to
re-learn persistence from scratch (this was the v1→v2 fix).

### Optimization

| knob | value |
|---|---|
| loss | `nn.functional.l1_loss` (L1, in z-space — matched to the MAE metric) |
| optimizer | `Adam` |
| learning rate | `1e-3` (fixed; **no schedule**) |
| batch size | `256`, `shuffle=True` |
| weight decay | **none** |
| dropout | **none** |
| gradient clipping | **none** |
| seed | `torch.manual_seed(0)` — **single seed** |

### Epoch / round budgets per rung

| rung | budget | selection | compute |
|---|---|---|---|
| naive (`lag1`) | — | — | 0 |
| seasonal-naive (`lag12`) | — | — | 0 |
| **local-only** (×35) | **40 epochs** | best epoch on that trust's val | 1,400 client-epochs |
| **FedAvg** | **100 rounds × 2 local epochs** | best round on global val (**best = 47/100**) | 7,000 client-epochs |
| **FedAvg + fine-tune** (×35) | **40 epochs**, `init = fed.state_dict()` | best epoch on that trust's val | 1,400 client-epochs |
| **centralized** | **40 epochs**, all 20,820 rows | best epoch on pooled val | 40 full-data epochs |

FedAvg client weighting: `w_t = len(client_rows[t]) / len(train)` — i.e. by **row count**
(series per trust), not referral volume.

Fine-tune uses the **identical protocol** to local-only — same 40-epoch budget, same
val-selected early stopping, same seed. **Only the initialization differs** (federated weights
vs random). This was the v3 fairness fix; before it, fine-tune got a blunt fixed 5 epochs with
no selection, which unfairly favoured local-only.

### Features (8) + embedding

`lag1`, `lag2`, `lag3`, `lag12` (log1p demand) · `backlog` at t−1 · `throughput` at t−1 ·
`month_sin`, `month_cos` · + specialty embedding (23 → 4).

All strictly known before the target month. Every value is a **per-series z-score of
`log1p(demand)`**, with mean/std computed from **train months only** — asserted in code:

```python
assert np.allclose(s["lag1"].values[1:], s["y"].values[:-1])          # lag alignment
assert np.allclose(chk["mean"], 0, atol=1e-6) and \
       np.allclose(chk["std"], 1, atol=1e-3)                           # train-only stats
```

Backlog and throughput carry their own per-series train-only stats (`mu_b/sd_b`, `mu_t/sd_t`),
all std clipped at `1e-6`.

### Protocol

- **Splits are dates, not counts** — train ≤ `2024-09`, val ≤ `2025-03`, test ≤ `2026-03`.
  This is what makes the 60-month and 96-month runs directly comparable.
- **Selection on val only.** Test evaluated once per rung.
- **Metric:** MAE in **referral units** — predictions are `expm1(ŷ·sd + mu)` before scoring, so
  normalization cannot flatter the score. Reported two ways:
  `per-branch` = mean over the 35 per-branch MAEs (the headline) · `pooled` = mean over all rows.

---

## 3. Forecaster results — the ladder (test, 12 held-out months, seed 0)

| rung | per-branch MAE | pooled MAE | vs naive |
|---|---|---|---|
| **local-only** | **106.9** | 107.3 | −4.3 |
| FedAvg + fine-tune | 108.1 | 108.6 | −3.1 |
| FedAvg | 110.9 | 111.4 | −0.3 |
| naive (last month) | 111.2 | 111.7 | — |
| centralized ("upper bound") | 114.2 | 114.7 | +3.0 |
| seasonal-naive (t−12) | 144.9 | 145.7 | +33.7 |

**Verdict as recorded:** learned models beat naive (the v2/v3 fixes worked), but **the
federation does NOT beat local-only** — local wins by 1.2 MAE over fed+fine-tune under an
identical protocol. Centralized ranking *below* local corroborates the mechanism: one global
correction function underfits 35 heterogeneous clients, while per-series normalization + the
residual head already absorb the shared structure (scale, persistence).

Convergence curve: val MAE 122 → 105, plateau from ~round 40, best round 47 of 100.

**Caveat on record:** the label "centralized (upper bound)" is a misnomer — at 114.2 it is not
an upper bound at this data scale.

Persisted: `models_src.pt` (1 global + 35 fine-tuned + 35 local) · `results_src.json`.

---

## 4. Decision plane — every knob

All are **stated assumptions**, not fitted quantities.

| knob | value | notebook |
|---|---|---|
| `SLOTS_PER_WTE` | **200** appointments/month per clinical WTE | 01, 03, 04, 05 |
| RED | `share18 > 0.08` **AND** `netflow3 > 0` | 01 |
| GREEN | `share18 ≤ 0.08` | 01 |
| AMBER | misses standard but `netflow3 ≤ 0` | 01 |
| `share18` | (18–52w + >52w) / banded total, from `Part_2` | 01 |
| `netflow3` | 3-month rolling mean demand − 3-month rolling mean throughput | 01 |
| request trigger | RED in **≥2 of last 3** months **AND** 12-mo forecast mean > `thr6` | 03 |
| `thr6` | 6-month mean throughput (capacity reference) | 03, 04, 05 |
| gap | `forecast_12m.mean() − thr6` (slots/month) | 03 |
| priority | `gap × (1 + share52)` | 03 |
| board budget | **2%** of the ICB's trusts' monthly throughput | 04 |
| fill order | greedy, priority-descending, per-ICB purse | 04 |
| ENHANCE | RED in **≥9 of last 12** months | 04 |
| EXPAND | deferred gap > **25%** of branch monthly throughput | 04 |
| forecast horizon | 12 months, **recursive rollout** | 03, 05 |
| rollout context | `backlog`/`throughput` **frozen** at as-of for all 12 steps | 03, 05 |
| backtest date | `AS_OF = 2025-03` | 05 |

Rollout mechanics: predictions are fed back as `lag1/2/3` (compounding), but `lag12` is read
from `hist`, which is **not** appended — so all 12 horizons use true history for the seasonal
lag. The model used is the branch's own **fine-tuned federated** model (`saved["fed_ft"][trust]`).

---

## 5. Decision plane — results

### Pressure, as-of 2026-03 (`src/01`)

- **482 RED · 170 AMBER · 42 GREEN** of 694 units. RED dominates every region.
- 458 of the 482 RED units have a positive 6-month gap.
- **Group staffing shortfall: 103,390 slots/month = 517 WTE.**
- Largest single-unit shortfalls (WTE): RTE·X02 7.8 · RX1·X02 6.6 · RC9·C_320 6.0 ·
  RAL·X05 5.8 · RAL·X02 5.8 · RTE·C_320 5.7 · RX1·C_301 5.4 · R0D·C_301 5.3 · RAJ·C_320 5.3.

### Requests, as-of 2026-03 (`src/03`)

- **423 requests · 95,371 slots/month · 477 WTE asked.**
- Top asks: Other-Medicals @ RAJ +12.3 WTE · T&O @ RAJ +10.2 · Other-Medicals @ RTE +7.8 ·
  Ophthalmology @ RAJ +6.8 · Cardiology @ RAJ +6.6 · ENT @ RAJ +6.3.

### Allocation, as-of 2026-03 (`src/04`)

- **29 FUNDED · 27 PARTIAL · 367 DEFERRED.**
- **Granted 11,875 of 95,371 slots/month = 59 of 477 WTE** — the 2% budget covers ~12%.
  Scarcity, not the loop, is the binding constraint.
- Decision mix: **321 ENHANCE · 56 ALLOCATE · 46 monitor**.
- EXPAND candidates (deferred WTE): RAJ 60 · RC9 24 · RX1 24 · RDE 20 · RTE 20 · RXN 12.
- Region ask vs granted (WTE): East of England 139/8 · London 71/11 · Midlands 69/9 ·
  North East & Yorkshire 57/8 · North West 58/7 · South West 64/7 · South East 19/9.
- Top branches by ask (WTE): RAJ 72.1 · RX1 28.4 · RTE 28.0 · RC9 27.4 · RAL 26.0 · RDE 25.8.

### Verification — backtest as-of 2025-03, judged on 12 months of actuals (`src/05`)

Ground truth = `mean demand over the 12 months after AS_OF − thr6 at AS_OF`, computed for
**every** unit, not just requesters.

| metric | value | meaning |
|---|---|---|
| true-need units | **519 of 694** | units where future demand exceeded capacity |
| requests raised | **451** | |
| **detection recall** | **82%** | needy units that raised a request |
| **request precision** | **95%** | requests that were truly needed |
| **access rate** | **10%** | needy requesters that received funding |
| **need coverage** | **8.1%** | of 646 WTE total true need, under the 2% budget |
| silent needs | 92 units = **37 WTE** | misses are small units |

Largest silent needs (WTE): RR8·C_320 2.1 · RRK·C_130 1.7 · RHM·C_330 1.7 · RM3·C_502 1.6.

**Policy test — the paper's argument in one table** (identical budgets, only ranking differs):

| policy | granted | useful | useful share | need coverage |
|---|---|---|---|---|
| **forecast-driven priority** | 11,712 | 10,424.75 | **0.89** | **0.081** |
| biggest current backlog | 11,712 | 9,724.17 | 0.83 | 0.075 |

12-month-mean demand MAE on requested units: **federated 117 vs naive 106**.

> **KEY FINDING:** the federated forecast improves the *decision* (89% vs 83% of granted staff
> landing on true future need) **even though its 12-month rollout MAE is worse than naive**.
> Decision value ≠ forecast MAE.

Precision caveat on record: the sustained-RED rule itself selects persistent pressure, so 95%
partly reflects the persistence of NHS backlogs.

---

## 6. What was never tuned

**No hyperparameter in this baseline was ever searched.** There is no grid, no sweep, no
selection over configurations. `lr=1e-3`, `hidden=32`, `emb=4`, `batch=256`, `local_epochs=2`,
`rounds=100`, `epochs=40` were each chosen once and never varied.

This is what makes the baseline honest — and it is also its main limitation: **the ladder
compares six rungs at a single arbitrary hyperparameter point**, on **one seed**. The
`local-only 106.9 vs fed+ft 108.1` gap is 1.2 MAE; whether it is a finding or an artifact of
that point is exactly what the A100 run has to settle.

Known open items carried into the A100 run:

1. **No hyperparameter search** — all rungs at one point (above).
2. **Single seed** — no error bars; a 1.2-MAE gap is not resolvable at this resolution.
3. **Val is thin and heavily reused** — 6 months / 4,164 rows carries best-of-100-rounds for
   FedAvg plus best-of-40-epochs for 35 local + 35 fine-tuned + 1 centralized model.
4. **Panel survivorship** — series are kept on `demand > 0` in all 60 months, which includes
   the 12 test months. Affects all rungs identically, but it is a selection peek.
5. **Recursive rollout** compounds its own predictions and freezes operational context for 12
   months — the structural cause of the 117-vs-106 rollout number.
6. **"centralized (upper bound)"** is mislabelled.
7. **FedProx and FedAdam were never run here** — the ladder is naive / seasonal-naive /
   local / FedAvg / fed+ft / centralized only.
