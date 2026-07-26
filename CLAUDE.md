# fedOPD

## Read this file, and keep the worklog — every turn

1. **Read `CLAUDE.md` (this file) at the start of every turn**, before doing anything else. It changes as the project goes; do not work from a remembered version of it.
2. **Read `WORKLOG.md`** to pick up where the last turn left off.
3. **Append to `WORKLOG.md` before ending the turn.** Every turn gets an entry — what was asked, what was done, what was decided and *why*, what was found (including failures, dead ends, and mistakes), and what is still open or running.

The worklog is the project's lab notebook: it is the record that survives when the chat context does not. Write it for someone reconstructing the reasoning months later. Facts and decisions, not narration — no filler, no restating the request. If something failed or was wrong, that goes in too; a worklog that only records successes is worthless.

## Working mode - Claude can help write the code

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
- **Comment on a per-line basis.** Nearly every line gets a trailing `#` comment saying what it does, plus a markdown cell above each section. Explain the non-obvious bits explicitly — what a regex captures, what a magic constant means, why a flag is set. Verbose comments are wanted; verbose *code* is not.
- **Explain every unfamiliar library, function, method or idiom the first time it appears** — say what the thing *is*, not just what the line does. The reader is a researcher, not a Python specialist, and should never have to look something up to follow the notebook. For example: `zipfile.testzip()` decompresses every member of an archive and returns the name of the first corrupt one, or `None` if all pass; `pd.MultiIndex.from_product` builds every combination of the given lists, which is how a ragged table is made rectangular; `np.polyfit(x, y, 1)` fits a straight line and returns `[slope, intercept]`; the walrus `:=` assigns inside a condition so a read can be tested and reused in one line. Name the library too when it is not obvious which one a call belongs to.
- Minimal exceptions are allowed only when they serve the data itself (e.g. downloading to a `.part` file and renaming on completion so reruns resume cleanly), not generic error handling.

## Environment

- Virtualenv: `fed_learning/` at the repo root. Activate with `source fed_learning/bin/activate`, or call `./fed_learning/bin/python` directly.
- Python 3.10.12, CUDA-enabled PyTorch (torch 2.13.0+cu130), flwr 1.30.0, pandas/scikit-learn/statsmodels, Jupyter.
- Jupyter kernel is registered as **fed_learning (CUDA)** — select it in the IDE, otherwise notebooks run against system Python which lacks these packages.

## Running long jobs — always tmux or nohup

- **Never run a long job in the foreground of a shell.** Anything that takes more than a minute or two — dataset downloads, training runs, full-notebook executions — must be detached so it survives a dropped SSH connection or a closed terminal.
- Preferred, because you can reattach and watch it: `tmux new -s <job>` then run inside; detach with `Ctrl-b d`, reattach with `tmux attach -t <job>`.
- Otherwise: `nohup ./fed_learning/bin/python ... > logs/<job>.log 2>&1 &`, then `tail -f logs/<job>.log`.
- To run a whole notebook headless and keep the outputs in the file:
  `tmux new -s fetch -d '../fed_learning/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=fed_learning 01_fetch_dataset.ipynb'`
- nbconvert runs in its own process, separate from the IDE kernel: its variables won't appear in the interactive session, and running the same cells manually at the same time would have both processes writing the same files.

## GPU — usable through MIG

- The box has one NVIDIA A100 80GB PCIe, driver 580.159.03, CUDA 13.0.
- **MIG mode is Enabled.** The GPU is only usable through its MIG device, not the raw GPU — currently a single `7g.80gb` slice covering the whole card (`MIG-c196af98-196a-5e8c-af32-0eff63a870e1`).
- Because that one slice spans the full card, PyTorch sees it as a normal single device: `cuda:0`, 80 GB. Use `torch.device("cuda")` as usual.
- Caveats that come with MIG: pick a device by MIG UUID via `CUDA_VISIBLE_DEVICES=MIG-<uuid>` rather than an integer index if the slice layout ever changes; per-process GPU utilisation is not reported in `nvidia-smi` under MIG; and no NVLink/peer-to-peer or multi-GPU collectives across slices, so federated "clients" run sequentially or as separate processes on the same slice, not on separate GPUs.
- Shared box: check `nvidia-smi` before launching, and run long jobs in `tmux`.
