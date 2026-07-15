# What to send the supervisor — the end-to-end package

Everything a reviewer needs to see that the project was **built, validated, and deployed** end to end.
Send items 1–4; have 5–6 ready if asked. The email text at the bottom can be sent as-is.

## The package (in this order)

| # | Item | What it proves |
|---|---|---|
| 1 | **`reports/project_report.pdf`** (14 pp) | the whole story for someone new: raw data → every cleaning decision with reasons (incl. why private/independent providers are excluded) → EDA → federated build → agentic layer → results → limitations. *This is the primary document.* |
| 2 | **Live dashboard link** (ngrok URL; see OPS.md to restart) | it *runs*: architecture, results, national flow, ICB allocation ranking, per-service drill-down. Deployment = the "end" of end-to-end. |
| 3 | **Repo link + tags** `eda-v2 → build-v1 → system-v1` | reproducibility: gated build log (`docs/BUILD_LOG.md`), one JSON per experiment (config/seed/git-sha), three clean notebooks (EDA / build / agentic), CPU-only, minutes to re-run. |
| 4 | **The three headline numbers** (below, in the email) | the results, stated honestly against noise. |
| 5 | (if asked) `reports/eda_report.pdf` — the 25-pp EDA deep-dive (F-01..28) | data diligence. |
| 6 | (if asked) `reports/system_report.pdf` — the 10-pp technical system report | method detail beyond the narrative. |

Do **not** send raw figure files separately — every graph is already embedded in the reports and live
on the dashboard. Loose PNGs without captions invite misreading.

## What to say — the results in four sentences

1. **Privacy result (the core claim):** 117 NHS trusts jointly trained one demand forecaster without
   any raw data leaving a site; the federated + personalised model scores **16.24 ± 0.07** sMAPE vs
   **16.90** for trusts training alone — federation beats isolation by 0.66 points, far outside seed
   noise, and a hand-written loop matches the Flower framework to 0.004.
2. **Honest benchmark:** against a strong persistence baseline (16.34) the federated model ties on the
   average and clearly wins on the median service (11.4 vs 12.9); the pooled-data upper bound (15.81)
   shows there is real shared structure and quantifies the price of privacy (~0.4 points).
3. **Decision layer:** a validated flow model (backlog ≈ backlog + demand − completions, 3.8% national
   error) plus a Little's-law capacity policy turns the forecasts into decisions — for 2026-03 it flags
   **969 of 1,509 services RED** (>18-week waits), computes **~216k additional pathways/month** needed,
   and ranks ICBs for allocation; RED services verifiably carry the highest real >18-week share
   (49% vs 27% amber / 12% green).
4. **Everything is reproducible and logged** — 10 gated build steps, pre-registered hypotheses
   (including one refuted and reported as such), and a written Tier-1→4 improvement roadmap already
   scheduled.

## What he will likely ask → where the answer lives

- *Why exclude private hospitals?* → project_report §2.3 (paid per activity; commissioned, not
  allocatable; no demand–supply loop to plan).
- *Why only tie the naive baseline?* → §9 limitations (84-point monthly series; the win is median +
  privacy; Tier-1/2 roadmap targets the macro-mean).
- *Is the agentic layer real or a demo?* → validated three ways (flow identity 3.8%, ρ=0.40,
  RAG-vs-wait-bands 12/27/49%), but v1 policy is deterministic OR — the LLM-agent wrapper is roadmap.
- *Can I re-run it?* → `git clone` + fetch script + `bash scripts/run_grid.sh` (CPU, minutes); every
  number traces to `results/*.json`.

## Draft email

> Subject: fedOPD — end-to-end prototype complete (report + live demo)
>
> Dear <supervisor>,
>
> The fedOPD prototype is complete end to end: data → EDA → federated forecaster → decision layer →
> deployed dashboard. Attached is the full project report (14 pp) written to be self-contained; a live
> interactive demo is at <ngrok-url> (per-service drill-down included).
>
> Headline results: 117 NHS trusts jointly train one demand forecaster with no raw data leaving any
> site — 16.24 ± 0.07 sMAPE vs 16.90 training alone (federation beats isolation, ≫ seed noise), tying
> a strong persistence baseline (16.34) on the mean and beating it on the median service; the pooled
> upper bound (15.81) prices privacy at ~0.4 points. On top, a validated capacity model flags 969/1,509
> services as breaching 18 weeks and ranks ICBs by the ~216k extra monthly pathways needed to recover.
>
> The report documents every assumption and exclusion (including why independent-sector providers are
> out of scope), the negative results, and the improvement roadmap. Repo tags eda-v2/build-v1/system-v1
> reproduce everything on CPU in minutes. I'd value your view on the six open decisions in §... —
> particularly the department roster and panel strictness, where I've included sensitivity numbers so
> the choice doesn't have to be made blind.
>
> Best regards, Nilesh

