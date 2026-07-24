# fedOPD

## Read this file, and keep the worklog — every turn

1. **Read `CLAUDE.md` (this file) at the start of every turn**, before doing anything else. It changes as the project goes; do not work from a remembered version of it.
2. **Read `WORKLOG.md`** to pick up where the last turn left off.
3. **Append to `WORKLOG.md` before ending the turn.** Every turn gets an entry — what was asked, what was done, what was decided and *why*, what was found (including failures, dead ends, and mistakes), and what is still open or running.

The worklog is the project's lab notebook: it is the record that survives when the chat context does not. Write it for someone reconstructing the reasoning months later. Facts and decisions, not narration — no filler, no restating the request. If something failed or was wrong, that goes in too; a worklog that only records successes is worthless.

## Work like a researcher — be critical

This is a research project, not a product. Think and act accordingly, in ideas, in actions, and in code.

- **Verify, don't assume.** A link, a row count, an API field, a "successful" download — check it against the actual source before building on it. State what was checked and what wasn't. "It ran without error" is not evidence it is correct.
- **Be critical of your own output.** After writing something, look for the way it is wrong: the silent failure, the off-by-one month, the filter that quietly matches nothing. Say so plainly when you find it, including when the mistake is yours.
- **Push back on the request when the data doesn't support it.** If an approach is unsound, a baseline is missing, a comparison is unfair, or a result is likely an artefact, say so instead of implementing it neatly. Disagreement is useful here.
- **Report negative and awkward results.** Missing months, empty joins, schema drift, outliers that don't fit the story — these are findings, not problems to smooth over. Never present a partial result as complete.
- **Separate what is measured from what is inferred.** Distinguish observation, assumption, and speculation explicitly.
- **No filler.** No hedging, no restating the question, no "great idea", no padding a summary to look thorough. Lead with the finding. If a result is uncertain, say how uncertain and why.
- **Prefer the simple thing that can be checked** over the clever thing that can't. Fewer moving parts means fewer places for a silent bug to hide.

## Code style — simple notebook code only

- All code in this project is written in Jupyter notebooks (under `src/`), not standalone scripts or modules.
- Keep code simple and research-grade: NO production-style safety nets — no try/except blocks, no retry wrappers, no input validation, no logging frameworks, no defensive checks. Straight-line code that does the job.
- **Comment on a per-line basis.** Nearly every line gets a trailing `#` comment saying what it does, plus a markdown cell above each section. Explain the non-obvious bits explicitly — what a regex captures, what a magic constant means, why a flag is set. Verbose comments are wanted; verbose *code* is not.
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
  `tmux new -s fetch -d '../fed_learning/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.kernel_name=fed_learning fetch_dataset.ipynb'`
- nbconvert runs in its own process, separate from the IDE kernel: its variables won't appear in the interactive session, and running the same cells manually at the same time would have both processes writing the same files.

## GPU — usable through MIG

- The box has one NVIDIA A100 80GB PCIe, driver 580.159.03, CUDA 13.0.
- **MIG mode is Enabled.** The GPU is only usable through its MIG device, not the raw GPU — currently a single `7g.80gb` slice covering the whole card (`MIG-c196af98-196a-5e8c-af32-0eff63a870e1`).
- Because that one slice spans the full card, PyTorch sees it as a normal single device: `cuda:0`, 80 GB. Use `torch.device("cuda")` as usual.
- Caveats that come with MIG: pick a device by MIG UUID via `CUDA_VISIBLE_DEVICES=MIG-<uuid>` rather than an integer index if the slice layout ever changes; per-process GPU utilisation is not reported in `nvidia-smi` under MIG; and no NVLink/peer-to-peer or multi-GPU collectives across slices, so federated "clients" run sequentially or as separate processes on the same slice, not on separate GPUs.
- Shared box: check `nvidia-smi` before launching, and run long jobs in `tmux`.
