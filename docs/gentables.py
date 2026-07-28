# Report build script, reconstructed 2026-07-28 (Entry 52). The original (Entry 45) lived in a
# session scratchpad and was lost; this one is checked in so the report is reproducible from the repo.
# Reads:  ../data/canonical/*.csv, ../src/*.ipynb, fedOPD_report.tex (the template)
# Writes: fedOPD_report_built.tex, figures/nbXX_figN.png (re-extracted from stored outputs)
# Then:   tectonic -X compile fedOPD_report_built.tex --outdir .   (binary not in repo; see WORKLOG)
# Every number emitted here comes from a result CSV or a notebook file read at build time.

import base64
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

DOCS = Path(__file__).parent
CANON = DOCS / ".." / "data" / "canonical"
SRC = DOCS / ".." / "src"

def esc(s):
    return str(s).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")

def r2(v):                                             # within/pooled R2, 4 dp, maths minus
    return f"${v:.4f}$" if v < 0 else f"{v:.4f}"

NC = r"\textit{n/c}"                                   # metric not computed by that notebook

# ---------------------------------------------------------------- TABLE:ALG - 08, sorted by MASE
alg = pd.read_csv(CANON / "algorithm_comparison.csv").sort_values("MASE_median")
def alg_row(r):
    name = esc(r.config)
    if name.startswith("baseline"):
        name = rf"\textit{{{name}}}"                   # the untrained reference, set off from the models
    return (f"{name} & {r.MASE_median:.4f} & {r.RMSE_median:.2f} & {r.RMSE_pooled:.1f} & "
            f"{r.R2_pooled:.4f} & {r2(r.R2_within_median)} & {r.precision_up_pct:.1f}\\% \\\\")
T_ALG = "\n".join(alg_row(r) for r in alg.itertuples())

# ------------------------------------------------- TABLE:HEADLINE - 11's two conditions + naive
pc = pd.read_csv(CANON / "postcovid_training.csv")
base = pd.read_csv(CANON / "baselines.csv", index_col=0)
def pc_at(start, L):
    return pc[(pc.start == start) & (pc.lookback == L)].iloc[0]
def headline_row(label, r, bold=False):
    b = (lambda s: rf"\textbf{{{s}}}") if bold else (lambda s: s)
    return (f"{b(label)} & {int(r.lookback)} & {int(r.windows_per_series)} & {b(f'{r.MASE_plateau:.4f}')} & "
            f"{b(f'{r.RMSE_plateau:.2f}')} & {r.R2_pooled_plateau:.4f} & {r2(r.R2_within_plateau)} & "
            f"{b(f'{r.precision_plateau:.1f}')}\\% \\\\")
nv = base.loc["naive"]
T_HEADLINE = "\n".join([
    headline_row("Full dataset, 6 years of history", pc_at("2018-04", 24), bold=True),
    rf"\textbf{{Post-COVID, 2022--2026 only}} & 12 & 1 & {pc_at('2022-04', 12).MASE_plateau:.4f} & "
    rf"{pc_at('2022-04', 12).RMSE_plateau:.2f} & {pc_at('2022-04', 12).R2_pooled_plateau:.4f} & "
    rf"{r2(pc_at('2022-04', 12).R2_within_plateau)} & {pc_at('2022-04', 12).precision_plateau:.1f}\% \\",
    rf"\textbf{{Post-COVID, 2022--2026 only}} & 6 & 7 & {pc_at('2022-04', 6).MASE_plateau:.4f} & "
    rf"{pc_at('2022-04', 6).RMSE_plateau:.2f} & {pc_at('2022-04', 6).R2_pooled_plateau:.4f} & "
    rf"{r2(pc_at('2022-04', 6).R2_within_plateau)} & {pc_at('2022-04', 6).precision_plateau:.1f}\% \\",
    r"\midrule",
    rf"\textit{{naive baseline (no training)}} & --- & --- & {nv.MASE_median:.4f} & {nv.RMSE_median:.2f} & "
    rf"{nv.R2_pooled:.4f} & {r2(nv.R2_within_median)} & --- \\",
])
# The bold full-dataset row above uses headline_row; keep the two subset rows unbolded on metrics.

# --------------------------------------------- TABLE:BOTH - same algorithms on the two datasets
pa = pd.read_csv(CANON / "postcovid_algorithms.csv", index_col=0)
alg_ix = pd.read_csv(CANON / "algorithm_comparison.csv", index_col=0)
MAP08 = {"fedavg": "reference: mlp / train_mean / fedavg / demand", "fedprox": "algorithm: fedprox",
         "fedavgm": "algorithm: fedavgm", "central": "mode: central (matched budget)",
         "local": "mode: local (matched budget)"}
rows = []
for name in ["fedavg", "fedprox", "fedavgm", "central", "local"]:
    a, b8 = pa.loc[name], alg_ix.loc[MAP08[name]]
    rows.append(rf"\texttt{{{name}}} & {b8.MASE_median:.4f} & {b8.RMSE_median:.2f} & "
                rf"{r2(b8.R2_within_median)} & {b8.precision_up_pct:.1f}\% & "
                rf"{a.MASE_plateau:.4f} & {a.RMSE_plateau:.2f} & {r2(a.R2_within_plateau)} & "
                rf"{a.precision_plateau:.1f}\% \\")
T_BOTH = "\n".join(rows)

# ----------------------------------------------------- TABLE:WINDOW - the full 11 cutoff sweep
LABEL = {"all months": "6 years (all of it)", "drop first year": "5 years",
         "from the collapse": "4 years", "after the trough": "3 yr 8 mth",
         "after the schema break": "3 years", "2022 onwards": "2 years"}
rows = []
for L in [24, 12, 6]:
    rows.append(r"\midrule")
    rows.append(rf"\multicolumn{{8}}{{@{{}}l}}{{\textit{{Lookback {L} months}}}} \\[2pt]")
    for r in pc[pc.lookback == L].itertuples():
        rows.append(f"{LABEL[r.label]} (from {r.start}) & {int(r.lookback)} & {int(r.windows_per_series)} & "
                    f"{r.MASE_plateau:.4f} & {r.RMSE_plateau:.2f} & {r.R2_pooled_plateau:.4f} & "
                    f"{r2(r.R2_within_plateau)} & {r.precision_plateau:.1f}\\% \\\\")
T_WINDOW = "\n".join(rows)

# ------------------------------- TABLE:HYPER - constants read out of the notebook source itself
WHITELIST = ["MIN_MONTHS", "H", "SEASON", "MIN_TRAIN", "GROWTH_THRESH", "L", "HIDDEN", "ROUNDS",
             "BAND", "FT_EPOCHS", "MAX_ROUNDS", "PLATEAU", "HORIZON", "TARGET_PCT"]
def hyper_of(nb_path):
    code = "\n".join("".join(c["source"]) for c in json.load(open(nb_path, encoding="utf-8"))["cells"]
                     if c["cell_type"] == "code")
    found = []
    for line in code.splitlines():
        m = re.match(r"^([A-Z_]+(?:, [A-Z_]+)?) = ([0-9e.\-]+(?:, [0-9e.\-]+)?|\([0-9, ]+\))(?:\s*#.*)?$",
                     line.strip())
        if m and m.group(1).split(",")[0].strip() in WHITELIST:
            found.append(f"{m.group(1).split(',')[0].strip()}={m.group(2)}")
    if "import torch" in code:                          # the shared training recipe, read from source
        lr = re.search(r"lr=([0-9e.\-]+)\)?:", code) or re.search(r"lr=([0-9e.\-]+)", code)
        drop = re.search(r"Dropout\(([0-9.]+)\)", code)
        batch = re.search(r"range\(0, len\(\w+\), (\d+)\)", code)
        seed = re.search(r"manual_seed\((\d+)\)", code)
        found += [f"lr={lr.group(1)}", f"dropout={drop.group(1)}", f"batch={batch.group(1)}",
                  f"seed={seed.group(1)}", "loss=L1Loss", "optim=Adam"]
    return ", ".join(found)
HYPER_NBS = ["03_data_processing", "05_baselines", "06_federated_forecast", "07_agentic_layer",
             "08_algorithm_comparison", "09_allocation_policies", "10_training_length",
             "11_postcovid_training"]
T_HYPER = "\n".join(rf"\texttt{{{esc(n)}}} & {esc(hyper_of(SRC / (n + '.ipynb')))} \\" for n in HYPER_NBS)

# --------------------------------------- TABLE:MANIFEST - run evidence from the notebook files
rows = []
for p in sorted(SRC.glob("*.ipynb")):
    nb = json.load(open(p, encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    with_out = sum(1 for c in code if c.get("outputs"))
    errors = sum(1 for c in code for o in c.get("outputs", []) if o.get("output_type") == "error")
    ran = all(c.get("execution_count") is not None for c in code)
    status = "completed" if ran and errors == 0 else "INCOMPLETE"
    mtime = datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %H:%M")
    rows.append(rf"\texttt{{{esc(p.stem)}}} & {len(code)} & {with_out} & {errors} & {status} & {mtime} \\")
T_MANIFEST = "\n".join(rows)

# ------------------------------------------------ TABLE:APPENDIX - every configuration, one table
fl = pd.read_csv(CANON / "fl_results.csv", index_col=0)
tl = pd.read_csv(CANON / "training_length.csv")
tl2 = tl[tl.local_epochs == 2]
plateau = tl2[tl2["round"].between(8, 20)]
r60 = tl2[tl2["round"] == 60].iloc[0]
rows = [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{Baselines (05)}} \\[2pt]"]
for r in base.itertuples():
    rows.append(f"{esc(r.Index)} & {r.MASE_median:.4f} & {r.RMSE_median:.2f} & {r.RMSE_pooled:.1f} & "
                f"{r.R2_pooled:.4f} & {r2(r.R2_within_median)} & \\texttt{{05}} \\\\")
rows += [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{Federated, unmatched training budget (06)}} \\[2pt]"]
for r in fl.itertuples():
    rows.append(f"{esc(r.Index)} & {r.MASE_median:.4f} & {r.RMSE_median:.2f} & {r.RMSE_pooled:.1f} & "
                f"{r.R2_pooled:.4f} & {r2(r.R2_within_median)} & \\texttt{{06}} \\\\")
rows += [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{Matched training budget (08)}} \\[2pt]"]
for r in alg.itertuples():
    rows.append(f"{esc(r.config)} & {r.MASE_median:.4f} & {r.RMSE_median:.2f} & {r.RMSE_pooled:.1f} & "
                f"{r.R2_pooled:.4f} & {r2(r.R2_within_median)} & \\texttt{{08}} \\\\")
rows += [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{Training length (10)}} \\[2pt]",
         f"fedavg, plateau rounds 8-20 & {plateau.val_MASE.mean():.4f} & {plateau.val_RMSE.mean():.2f} & "
         f"{NC} & {plateau.R2_pooled.mean():.4f} & {r2(plateau.R2_within.mean())} & \\texttt{{10}} \\\\",
         f"fedavg, best single round & {tl2.val_MASE.min():.4f} & {NC} & {NC} & {NC} & {NC} & \\texttt{{10}} \\\\",
         f"fedavg, 60 rounds & {r60.val_MASE:.4f} & {r60.val_RMSE:.2f} & {NC} & {r60.R2_pooled:.4f} & "
         f"{r2(r60.R2_within)} & \\texttt{{10}} \\\\"]
rows += [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{Training window (11)}} \\[2pt]"]
for L in [24, 12, 6]:
    for r in pc[pc.lookback == L].itertuples():
        rows.append(f"{r.start} onwards, L={int(r.lookback)} & {r.MASE_plateau:.4f} & {r.RMSE_plateau:.2f} & "
                    f"{r.RMSE_pooled_plateau:.1f} & {r.R2_pooled_plateau:.4f} & "
                    f"{r2(r.R2_within_plateau)} & \\texttt{{11}} \\\\")
rows += [r"\midrule", r"\multicolumn{7}{@{}l}{\textit{2022--2026 only, every algorithm (11)}} \\[2pt]"]
for r in pa.itertuples():
    rows.append(f"{esc(r.Index)} & {r.MASE_plateau:.4f} & {r.RMSE_plateau:.2f} & {NC} & "
                f"{r.R2_pooled_plateau:.4f} & {r2(r.R2_within_plateau)} & \\texttt{{11}} \\\\")
T_APPENDIX = "\n".join(rows)

# ---------------------------------------------------------------- figures, from stored outputs
changed = 0
for p in sorted(SRC.glob("*.ipynb")):
    nbnum = p.stem[:2]
    n = 0
    for c in json.load(open(p, encoding="utf-8"))["cells"]:
        for o in c.get("outputs", []):
            png = o.get("data", {}).get("image/png")
            if png:
                n += 1
                dest = DOCS / "figures" / f"nb{nbnum}_fig{n}.png"
                data = base64.b64decode(png)
                if not dest.exists() or dest.read_bytes() != data:
                    dest.write_bytes(data)
                    changed += 1
print(f"figures re-extracted from stored outputs, {changed} changed on disk")

# ------------------------------------------------------------------------- substitute and write
TABLES = {"ALG": T_ALG, "HEADLINE": T_HEADLINE, "BOTH": T_BOTH, "WINDOW": T_WINDOW,
          "HYPER": T_HYPER, "MANIFEST": T_MANIFEST, "APPENDIX": T_APPENDIX}
tex = (DOCS / "fedOPD_report.tex").read_text(encoding="utf-8")
for name, body in TABLES.items():
    marker = f"%%TABLE:{name}%%"
    assert marker in tex, f"marker {marker} missing from the template"
    tex = tex.replace(marker, body)
assert "%%TABLE:" not in tex, "a marker survived substitution - a table failed to generate"
(DOCS / "fedOPD_report_built.tex").write_text(tex, encoding="utf-8")
print("written: fedOPD_report_built.tex  (compile with tectonic, then check the page count)")
