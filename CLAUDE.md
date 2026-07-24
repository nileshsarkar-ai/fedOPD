# fedOPD

## Code style — simple notebook code only

- All code in this project is written in Jupyter notebooks (under `src/`), not standalone scripts or modules.
- Keep code simple and research-grade: NO production-style safety nets — no try/except blocks, no retry wrappers, no input validation, no logging frameworks, no defensive checks. Straight-line code that does the job.
- Comment and explain the code (markdown cells + inline comments), but don't bloat it.
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
