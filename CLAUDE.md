# fedOPD

## Code style — simple notebook code only

- All code in this project is written in Jupyter notebooks (under `src/`), not standalone scripts or modules.
- Keep code simple and research-grade: NO production-style safety nets — no try/except blocks, no retry wrappers, no input validation, no logging frameworks, no defensive checks. Straight-line code that does the job.
- Comment and explain the code (markdown cells + inline comments), but don't bloat it.
- Minimal exceptions are allowed only when they serve the data itself (e.g. downloading to a `.part` file and renaming on completion so reruns resume cleanly), not generic error handling.
