# CLAUDE.md — project rules

Read and follow this file on every turn. These rules override default habits.

## Mindset

Write like a researcher with 20 years of coding and research experience. Research-grade code, no production BS. The standing bar: **simple and powerful — code that explains itself on the first read.** A cell should be short, do one thing, and be understandable without running it or looking anything up. One clear line over three clever ones; power comes from picking the right operation, never from density. If a line needs a paragraph to justify it, it is the wrong line.

## Structure

- All code lives in Jupyter notebooks under `src/` — no standalone scripts or modules.
- One standing exception: `docs/gentables.py` is the report build script and is checked in (decided 2026-07-28, because the report must be reproducible from the repo).
- Runners, helpers and utilities go in the notebook that needs them or nowhere; `jupyter nbconvert` is invoked directly from the shell.

## No production scaffolding

- No try/except blocks, no retry wrappers, no input validation, no logging frameworks, no defensive checks. Straight-line research-grade code that does the job.
- The only permitted exceptions are ones that serve the data itself (e.g. downloading to a `.part` file and renaming on completion so re-runs resume cleanly) — never generic error handling.

## Every line has a visible purpose

If a line can be deleted without changing a number, delete it: a variable assigned and never read, a `fillna` that fills nothing, a default that never fires, a parameter passed at its own default. These are worse than clutter — a reviewer wastes time working out what they guard against, and the answer is nothing.

## One function, one job

A function that branches on the type of its argument is two functions wearing one name — write the two. Same for a flag parameter that switches half the body.

## Guards are arithmetic, not defence

`np.where(denominator > 0, ...)` earns its place because a zero denominator is a real case in this data and the alternative is a silent `inf`. A try/except around it does not — it swallows a fact about the data. A guard's comment says which real input makes it fire.

## Asserts are encouraged

They are the mechanism that turns a silent wrong number into a stopped notebook, which is the failure mode this project keeps hitting. Every assert must have an answer to "what input would have made this fail" (e.g. the `assert score_cols.sum() == H` that keeps the sealed test year out of scoring).

## Comments

Comments teach — the reader knows basic Python only (updated 2026-07-29, supersedes the earlier "short comments" rule).

- Imports: say what the library is, what it does, and what it is used for in this notebook — not just a label.
- Loops, statements, and API calls: say what is happening to the data and why the step is necessary. Explain the mechanism when it isn't obvious (`stream=True`, a regex, a set comprehension, `.get` with a default).
- Each code cell opens with a short `# Goal:` block stating what the cell produces.
- Multi-line trailing comment blocks are fine; longer narrative still goes in the markdown cell above the section.
- Still never restate the code word-for-word ("increment i") — explain intent, data, and consequence, not syntax ceremony.

## Verification

No smoke tests, no synthetic fixtures, no test harnesses. A notebook is verified by running it headless on the real data and reading its stored outputs — that is the only evidence the project accepts. If a notebook cannot be run yet, it stays unrun rather than being "proven" on invented data.

## Evaluation rules (govern code as much as prose)

- Develop on validation, never touch the sealed test year.
- Never tune eligibility, splits or horizons against the metric.
- One declared seed, every variant reported.
- State the denominator beside every rate.
- Never write a number from memory — every figure comes from a stored output or result CSV read in the current turn.
