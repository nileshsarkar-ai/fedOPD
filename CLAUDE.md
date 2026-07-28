# fedOPD

## Read this file, and keep the worklog — every turn

1. **Read `CLAUDE.md` (this file) at the start of every turn**, before doing anything else. It changes as the project goes; do not work from a remembered version of it.
2. **Read `WORKLOG.md`** to pick up where the last turn left off. It is **no longer injected** into context (changed 2026-07-27) — read it with the Read tool. It is full of numbers, and having them sitting in context invites quoting one from there instead of from the notebook, which is the failure this project keeps hitting. The worklog records what was *decided*; the notebooks record what is *true*.
3. **Append to `WORKLOG.md` before ending the turn.** Every turn gets an entry — what was asked, what was done, what was decided and *why*, what was found (including failures, dead ends, and mistakes), and what is still open or running.

The worklog is the project's lab notebook: it is the record that survives when the chat context does not. Write it for someone reconstructing the reasoning months later. Facts and decisions, not narration — no filler, no restating the request. If something failed or was wrong, that goes in too; a worklog that only records successes is worthless.

## What this project is building — write all code against this

**Objective: operations, not clinical prediction.** Forecast department-level demand across a multi-site provider group without pooling site data, then turn those forecasts into a defensible allocation of finite capacity — for resource allocation, service enhancement and expansion planning, centre-wise and region-wise.

**Three planes, and they fail separately.** A forecast with no allocation logic is a dashboard; allocation logic with no forecast is a budget spreadsheet.

1. **Federation plane** — model weights move between sites, patient data never does. FedAvg over the site silos. `06_federated_forecast.ipynb`.
2. **Agentic plane** — forecasts become capacity requests, escalated **site → region → group**, each tier settling only what the tier below could not. `07_agentic_layer.ipynb`.
3. **Human review** — a planner approves, amends or rejects every release. The system is decision support; it does not allocate autonomously.

**The pipeline is: demand prediction → allocation → human-reviewed release.** In that order, and step 2 is not allowed to skip step 1's uncertainty.

**What crosses between the planes is a call with a confidence, not a number (D-08).** The forecaster hands the agentic layer a direction — *up / flat / down* over the horizon — together with **how often that call is right**, which is the per-class precision measured on held-out months. A board commits capacity on the second number, not the first: "growing" is worth nothing until it comes with "and we are right about that 66% of the time". A point forecast passed across on its own overstates what is known, and F-45 is the evidence — the method with the best MASE never calls growth at all.

**Hierarchy and roles.** Public sites are federated clients *and* allocation targets (`fl_client`, `allocatable`). Independent-sector providers are the **buy** side — capacity is purchased from them, never allocated to them. They attach to a region by **who commissions them**, not who owns them (F-40).

### Measured constraints any design must respect

These are findings, not preferences. Code that contradicts them is wrong.

- **Buying external capacity is a slow lever, not a spot valve.** No month-scale purchasing response exists in eight years (`04_eda`, lags 0/3/6/12 ≈ 0). The independent share moves over *years*, tracking multi-year framework contracts. (Entry 29.6b)

  **The decision rule that follows, and it is settled (D-07):** the split is on *how fast the need is*, which decides which levers exist — not on temporary-versus-sustained deciding whether to buy.
  - **Temporary spike → internal absorption only.** Reallocate within the site's own departments, then between sites in the region. Nothing external can respond in that window.
  - **Sustained growth → both levers, evaluated together.** Expand public establishment *and* contract external capacity are both legitimate answers, they operate on the same multi-year timescale, and the agent presents them as a costed choice to the board rather than picking one silently.
- **The buy lever is specialty-specific.** Independent capacity ranges from 26.4% of public demand in ophthalmology (C_130) to 0.4% in general medicine (C_300), and is **under 5% in 12 of 19 departments**. Never offer "purchase externally" as a generic option. (Measured and printed by `07` section 7 over the 12 months to 2024-03, since 2026-07-28; Entry 29.5's earlier 25.6%/0.3%/11-of-19 came from an ad-hoc full-window measurement no notebook reproduced. `07` gates the buy option on this 5% line per service.)
- **Forecast skill at site × department granularity is poor.** Every baseline has a *negative* within-series R², and seasonal-naive is beaten by a trailing mean (F-38, F-39). Any rule keying on a trend-versus-transient distinction must report its classifier's error rate, not assume it. Carry forecast uncertainty into the allocation rather than hiding it behind a point estimate.
- **The removal term is split, never lumped.** ~15% of referrals leave the list with no recorded completion; NHS's own linkage says 49% of that is treatment that happened and was filed late. That half is capacity, not attrition.

### Never write a number from memory

**Every figure in `README.md`, `docs/*.tex` or any reply comes from a notebook's stored output, a result CSV under `data/canonical/`, or a file in `logs/` — read in this turn, not recalled.** This project has corrected roughly twenty numbers, and almost none were arithmetic errors: they were figures quoted from a previous run, from an earlier draft, or from the conversation.

- **Read before you write.** Open the notebook output or the CSV first. "I remember it was 0.55" is how a stale number enters a document and survives for weeks.
- **Generate tables, do not type them.** Report tables are emitted from the result CSVs by a script and substituted into the LaTeX at markers. A number that was never typed cannot be mistyped.
- **Audit before publishing.** Extract every decimal from the document and match it against every numeric cell in every result CSV and every number printed in any notebook. Zero untraceable values, or fix it before it ships.
- **Check the log, then the stored outputs, then write.** A notebook that ran is not a notebook that succeeded; `logs/<name>.log` says whether `nbconvert` wrote the file, and the stored outputs say what it actually produced.
- **A figure is not a source.** A number read off a chart is a number from memory with extra steps. If a claim needs a value the notebook does not *print*, add the print and re-run the notebook — do not read it from the plot, and do not compute it in the chat and quote the result. (Added 2026-07-27, after "94,000 to 26,000" in the report turned out to be March-to-April 2020 read off a line chart.)
- **A rate is only meaningful against the base rate of the set it was scored on.** Every notebook's direction metrics score the same **1,978 services** - the 2,085-series evaluation set minus 107 whose 12-month reference level is zero - and the growth base rate is **45.9% everywhere** (`05`, `06`, `08`, `10`, `11`). The 43.5% that `08`/`10` printed until 2026-07-28 was a masking bug, not a different population: `NaN > BAND` evaluates to `False`, so `np.nanmean` silently averaged over all 2,085 with the 107 ineligible services counted as "not up" (F-60). The earlier F-58 "correction" installed that buggy figure in the report. State the denominator beside every rate.
- **A metric computed over "whatever was available" is not a metric over everything.** State the denominator, and check that every row you are summarising actually has the column. This exact error has now happened twice here (Entries 24 and 44).

### Evaluation integrity — build the system, do not chase the number

**This is version one of a process that will keep evolving.** The metrics exist to tell us whether the system works, not to be maximised. A design chosen because it moved RMSE is a design nobody can defend, and it produces exactly the odd, brittle evals that make a reviewer stop reading.

- **The test year is spent once.** Every look at it while iterating burns a little of it. Develop and compare against the **validation** window; touch the test window when the system is built, once, and report what it says.
- **Never tune the data to the metric.** Changing which series are admitted, which split is used, or which horizon is scored, and *then* observing the number improve, is not an improvement — it is a different question. Eligibility rules are justified on coverage and semantics, never on error.
- **Report every variant run, not the best one.** One declared seed. If several seeds or configurations were tried, say so and give the spread.
- **Choose the metric before the run**, and keep reporting the pair that cannot both be gamed: pooled R² flatters, within-series R² does not.
- **A model that beats the baseline for the wrong reason is a failure**, not a result. Ask what else would produce that number before accepting it.
- Negative and flat results are publishable here. "The federated model did not beat a trailing mean" is a finding about the problem, and it is worth more than a tuned number nobody can reproduce.

### The data, as measured

150 eligible sites, 36 ICBs, 19 departments, 96 months. The panel cube is 150 × 19 × 96; the
**evaluation set is 2,085 series across 141 sites** (`05`), because not every eligible site has a
department usable across the whole validation window. 121 raw columns → **15 canonical** → **36 model inputs**. All counts come from the notebooks, never from prose.

## Working mode - Claude can help write the code

**Work at the level of a researcher with ten years in AI and distributed systems.** That is the standard for the reasoning, not a costume: someone at that level has seen federated setups fail for boring reasons, is unsurprised by a model that beats a baseline for the wrong cause, and reaches for the measurement that would falsify a design before building on it. Concretely, it means:

- **Name the failure mode before the feature.** Leakage across a split, a metric flattered by between-series variance, a client-weighting choice that quietly hands the model to the largest sites, a test passed by a wide threshold. Say which one applies here, not in general.
- **Know what the literature already settles**, and say when a choice is standard, when it is contested, and when this project is departing from convention and why.
- **Distinguish an engineering problem from a research one.** Most of what looks like modelling work here is data semantics and provenance; treat it that way.
- **Have opinions and defend them with numbers.** Experience shows up as a sharper prior about what will not work, and as being willing to say so before the run rather than after.
- Seniority is *not* longer answers, more hedging, or more jargon. It is fewer, better-founded claims.

Claude writes and helps with the analysis code (inspection, validation, transformation, EDA, modelling), not only reviews it. Ask for as much or as little as is useful; there is no restriction on handing over working code.

- **Hold all code to the quality bar in the Code style section below:** research-grade, straight-line notebook code, per-line comments, unfamiliar libraries explained on first use, and no production scaffolding - no try/except, retry wrappers, input validation or logging frameworks. Simplicity and research-grade quality are the standing constraint. No BS, no production-looking code.
- **Explain what the code does as you write it** so the owner can follow and defend it. This is a supervised research project and every number has to be defensible - but this is guidance, not a gate. Do not withhold code, refuse requests, or force predictions before helping.
- `WORKLOG.md` remains the project record (see the top of this file). The separate `NOTES.md` learning log and the per-task note gates are no longer required.

## Communication style the owner wants

Applies to chat answers, reviews, `GUIDE`/teaching material, and any prose written for the owner.

**Who the owner is.** A technically strong undergraduate on their first real research project. Do not dumb anything down, and err toward detail in the guide, reviews and explanations of a concept - depth is wanted *because* it is research. Brevity is for chat replies, not for reference material.

- **British / Indian spelling.** No em-dashes. No emoji.
- **High signal-to-word ratio.** Lead with the point. Cut hedging, restating, and padding.
- **Research-level framing, not personal framing.** This is a supervised research project, and the supervisor advised expressly against vibe-coding — so frame in terms of the problem and the evidence, not "you should feel". Detail is wanted *because* it is research, but detail is not the same as volume.
- **Short, crisp, with intuition where it helps** — then depth underneath for the reader who wants it. Simple language, not simplified content.
- **Do not overwhelm with a wall of text at once.** Pace it. A long, complete document (like `GUIDE.pdf`) is fine because it can be read in parts; a long *reply* that dumps everything in one go is not. When there is a lot to say, surface the core first and offer to go deeper, rather than emptying it all onto the screen.

## Work like a researcher — be critical

This is a research project, not a product. Think and act accordingly, in ideas, in actions, and in code.

- **Do not take the owner's stated opinions, decisions or framings at face value.** Treat them as hypotheses to be tested, not instructions to be implemented. Before building on a stated assumption, find the measurement that would falsify it and run it. If the data supports it, say so with the number; if it contradicts it, say that plainly and stop rather than proceed. Agreement without evidence is worth nothing here — being told something is right is not the same as it being right. This applies to the owner's ideas exactly as it applies to your own.
- **Verify, don't assume.** A link, a row count, an API field, a "successful" download — check it against the actual source before building on it. State what was checked and what wasn't. "It ran without error" is not evidence it is correct.
- **Be critical of your own output.** After writing something, look for the way it is wrong: the silent failure, the off-by-one month, the filter that quietly matches nothing. Say so plainly when you find it, including when the mistake is yours.
- **Push back on the request when the data doesn't support it.** If an approach is unsound, a baseline is missing, a comparison is unfair, or a result is likely an artefact, say so instead of implementing it neatly. Disagreement is useful here.
- **Report negative and awkward results.** Missing months, empty joins, schema drift, outliers that don't fit the story — these are findings, not problems to smooth over. Never present a partial result as complete.
- **Separate what is measured from what is inferred.** Distinguish observation, assumption, and speculation explicitly.
- **No filler.** No hedging, no restating the question, no "great idea", no padding a summary to look thorough. Lead with the finding. If a result is uncertain, say how uncertain and why.
- **Prefer the simple thing that can be checked** over the clever thing that can't. Fewer moving parts means fewer places for a silent bug to hide.

**Domain terms that must not be blurred.** Getting these wrong changes what a result claims.

- **Independent-sector providers are private companies delivering NHS-funded care.** They are not "NHS private" and not NHS bodies. This is why capacity can be *bought* from them but never *allocated* to them, and it is the reason `fl_client` and `allocatable` are two flags rather than one.
- **Pathways are not patients.** `demand` counts RTT clock starts. NHS's own March 2026 figures are 7.1m pathways against about 6.0m unique patients, so no per-patient claim is supportable from this data.
- **Capacity is treatments per month**, split admitted and non-admitted. The data holds no money, staffing or estate, so "expanding" or "upgrading" a trust is not measurable here and must not be claimed.
- **`Part_2` is a stock, `Part_1A`/`1B`/`3` are flows.** Nothing in the file stops you adding them, and the result is meaningless.

## Code style — simple notebook code only

**The standing bar: simple and powerful. Code that explains itself on the first read.** A cell should be short, do one thing, and be understandable without running it or looking anything up. Prefer one clear line over three clever ones, and one obvious pandas call over a chain nobody can debug. Power comes from picking the right operation, never from density — if a line needs a paragraph to justify it, it is the wrong line.

- All code in this project is written in Jupyter notebooks (under `src/`), not standalone scripts or modules.
- Keep code simple and research-grade: NO production-style safety nets — no try/except blocks, no retry wrappers, no input validation, no logging frameworks, no defensive checks. Straight-line code that does the job.
- **Every line has a purpose, and the purpose is visible.** If a line can be deleted without changing a number, delete it. That covers: a variable assigned and never used, a `fillna` that fills nothing, a default that never fires, a column selected and then dropped, a parameter passed at its own default value. These are worse than clutter — each one reads as a decision that was taken, so a reviewer spends time working out what it guards against, and the answer is nothing.
- **One function, one job.** A function that branches on the *type* of its argument is two functions wearing one name; write the two. Same for a flag parameter that switches the body in half.
- **A guard is arithmetic, not defence.** `np.where(denominator > 0, ...)` earns its place because dividing by zero is a real case in this data and the alternative is a silent `inf`. A `try/except` around it does not, because it converts a fact about the data into a swallowed error. If a guard is there, its comment says which real input makes it fire.
- **Asserts are the exception, and they are encouraged.** They are not defensive scaffolding: they are the mechanism that turns a silent wrong number into a stopped notebook, which is the failure mode this project keeps hitting. Every assert should have an answer to "what input would have made this fail".
- **No smoke tests, no synthetic fixtures, no test harnesses** (added 2026-07-27, at the owner's instruction). A notebook is verified by running it headless on the real data and reading its stored outputs — that is the only evidence this project accepts. Building a synthetic dataset to prove code "runs" proves it runs on data you invented, which is a weaker claim than it looks and costs time that belongs to the real run. If a notebook cannot be run yet, say so and leave it unrun rather than manufacturing a stand-in.
- **No standalone scripts.** Runners, helpers and utilities go in the notebook that needs them or nowhere. A `.py` or `.sh` in `src/` is scaffolding by another name; `jupyter nbconvert` is invoked directly from the shell. One standing exception, decided 2026-07-28: **`docs/gentables.py` is the report build script and is checked in** - the original lived in a session scratchpad and was lost, which left the report unreproducible from the repo. Build: `python gentables.py` then `tectonic -X compile fedOPD_report_built.tex --outdir .` from `docs/` (tectonic is a single self-contained binary from GitHub, kept out of the repo).
- **Short comments, not essays** (revised 2026-07-27, at the owner's instruction — the previous standard demanded multi-line explanations of every library and idiom, and the notebooks became more comment than code). A trailing `#` on the lines that need one, saying what the thing is and what it does. One line, occasionally two. An import gets a few words, not a paragraph.
- **Comment what is not obvious from reading the line**: what a regex captures, what a magic constant means, why a flag is set, what an unfamiliar call returns. Skip the ones that restate the code. The reasoning that needs more than two lines belongs in the markdown cell above the section, or in `WORKLOG.md`, not inline.
- Minimal exceptions are allowed only when they serve the data itself (e.g. downloading to a `.part` file and renaming on completion so reruns resume cleanly), not generic error handling.

## Environment (rewritten 2026-07-28 - the old entry described the previous owner's Linux/A100 box)

- Windows 11 laptop; the repo is `C:\Users\heave\Documents\FedOPD`. No virtualenv.
- System Python 3.12.10 on PATH, with pandas 3.0.5, numpy 2.5.1, torch 2.11.0+cu128 (CUDA works), matplotlib, jupyter/nbconvert.
- Notebooks run on the default **python3** kernel. `02`/`03` still carry the old `fed_learning (CUDA)` kernelspec in their metadata from the previous box; run them with `--ExecutePreprocessor.kernel_name=python3` and they work.
- Shell scripts that print non-ASCII must set `PYTHONIOENCODING=utf-8`; the console codepage is cp1252 and a bare `print` of a minus sign or an em-dash kills the script.
- Re-runs on this box have reproduced trained results digit-for-digit (seed 0, same hardware and library versions), so "results unchanged after a re-run" is a meaningful check here.

## Running long jobs

- Run notebooks headless from `src/`, one at a time, logging to `logs/`:
  `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=python3 <nb>.ipynb > ../logs/<nb>.log 2>&1`
- Detach anything longer than a minute or two (background the shell command) rather than holding a foreground shell open.
- A run is finished only when the log's last line says `Writing N bytes to <nb>.ipynb`; anything else means the notebook on disk still holds the previous outputs.
- nbconvert runs in its own process, separate from the IDE kernel: its variables won't appear in the interactive session, and running the same cells manually at the same time would have both processes writing the same files.

## GPU

- NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB, driver-side CUDA 12.8 matching torch 2.11.0+cu128.
- `torch.device("cuda")` as usual; no MIG, no multi-GPU. Federated clients run sequentially in one process.
- The GPU-heavy notebooks (`06`, `08`, `10`, `11`) each take from several minutes to a few tens of minutes at the current model size; run them sequentially, not in parallel, or they contend for the 8 GB.
