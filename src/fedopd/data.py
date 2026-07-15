"""fedOPD data plane: panel freeze -> windowed tensors, identical to build.ipynb Steps 1-2.

Single source for every experiment (notebook, run.py, Flower) so all methods train on the
identical series set and are scored on the identical (series, month) test points.
Default parameters reproduce results/panel.json (hash e3aa353ecef2cbcb) and
results/dataset_stats.json exactly: 1544 train series, 108065x33 train, 18191x33 test.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

W = 12                                   # input window (D-04; F-20 persistence, F-22 weak seasonality)
TRAIN_END = pd.Timestamp("2025-03-01")   # last train target month; test = 2025-04..2026-03
MIN_TRAIN_WINDOWS = 24

ROOT = next(p for p in (Path(__file__).resolve(), *Path(__file__).resolve().parents)
            if (p / "CLAUDE.md").exists())


def load_canonical():
    canon = pd.read_parquet(ROOT / "reports" / "tables" / "rtt_canonical.parquet")
    assert len(canon) == 227344 and canon.date.nunique() == 96, "canonical drifted from EDA"
    return canon


def freeze_panel(canon, depts_mode="stable18", min_coverage=0.5, panel_min_months=96, w=W):
    """Step 1: panel trusts + department roster + eval/train-only series (D-02/D-03/D-07)."""
    months = pd.Index(sorted(canon.date.unique()))
    pm = canon.groupby("branch").date.nunique()
    panel = sorted(pm.index[pm >= panel_min_months])
    pset = set(panel)

    dept_months = canon.groupby("dept").date.nunique()
    stable18 = sorted(dept_months.index[dept_months == 96])
    roster_full = {"stable18": stable18,
                   "all24": sorted(canon.dept.unique()),
                   "no_x": sorted(d for d in canon.dept.unique() if not str(d).startswith("X"))}
    cov = canon[canon.branch.isin(pset)].groupby("dept").branch.nunique() / len(panel)
    roster = [d for d in roster_full[depts_mode] if cov.get(d, 0) >= min_coverage]

    tr_idx = [i for i, m in enumerate(months) if i >= w and m <= TRAIN_END]
    te_idx = [i for i, m in enumerate(months) if m > TRAIN_END]
    pres = (canon.assign(one=1).pivot_table("one", ["branch", "dept"], "date", fill_value=0)
            .reindex(columns=months, fill_value=0).astype(bool))

    eval_series, train_only = [], []
    for (b, d), row in pres.iterrows():
        if b not in pset or d not in roster:
            continue
        v = row.values
        tr = sum(bool(v[i]) and bool(v[i - w:i].all()) for i in tr_idx)
        te = sum(bool(v[i]) and bool(v[i - w:i].all()) for i in te_idx)
        if tr < MIN_TRAIN_WINDOWS:
            continue
        if te >= 1:
            eval_series.append((b, d))
        elif bool(v[te_idx].any()):          # active interior-gap -> train-only (Step-1 revision)
            train_only.append((b, d))
    return dict(months=months, panel=panel, roster=roster, w=w,
                eval_series=eval_series, train_only=train_only)


def build_tensors(canon, panel):
    """Step 2: windowed features + per-series TRAIN-only scalers excl. outlier-flagged months."""
    months, roster, w = panel["months"], panel["roster"], panel.get("w", W)
    reg = pd.read_csv(ROOT / "reports" / "tables" / "07_outlier_register.csv", parse_dates=["date"])
    flagged = set(zip(reg.branch, reg.dept, reg.date))
    dem = canon.pivot_table("demand", ["branch", "dept"], "date").reindex(columns=months)

    mo = np.array([m.month for m in months])
    msin, mcos = np.sin(2 * np.pi * mo / 12), np.cos(2 * np.pi * mo / 12)
    covid = ((months >= "2020-03-01") & (months <= "2021-03-01")).astype(float)
    strike = ((months >= "2022-12-01") & (months <= "2023-12-01")).astype(float)
    ridx = {d: i for i, d in enumerate(roster)}
    nr = len(roster)
    tr_targets = [i for i in range(w, len(months)) if months[i] <= TRAIN_END]
    te_targets = [i for i in range(w, len(months)) if months[i] > TRAIN_END]

    def fit_scaler(b, d, row):
        keep = [row[i] for i in range(len(months))
                if months[i] <= TRAIN_END and not np.isnan(row[i]) and (b, d, months[i]) not in flagged]
        if not keep:
            return 0.0, 1.0
        a = np.asarray(keep)
        return float(a.mean()), max(float(a.std()), 1e-6)

    def make(row, t, mean, sd, oh):
        return np.concatenate([(row[t - w:t] - mean) / sd,
                               [msin[t], mcos[t], covid[t], strike[t]], oh])

    Xtr, ytr, owner = [], [], []
    Xte, yte, meta = [], [], []
    scalers = {}
    for b, d in panel["eval_series"] + panel["train_only"]:
        row = dem.loc[(b, d)].values
        mean, sd = fit_scaler(b, d, row)
        scalers[(b, d)] = (mean, sd)
        oh = np.zeros(nr); oh[ridx[d]] = 1.0
        for t in tr_targets:
            if np.isnan(row[t]) or np.isnan(row[t - w:t]).any():
                continue
            Xtr.append(make(row, t, mean, sd, oh)); ytr.append((row[t] - mean) / sd); owner.append(b)
    for b, d in panel["eval_series"]:
        row = dem.loc[(b, d)].values
        mean, sd = scalers[(b, d)]
        oh = np.zeros(nr); oh[ridx[d]] = 1.0
        for t in te_targets:
            if np.isnan(row[t]) or np.isnan(row[t - w:t]).any():
                continue
            Xte.append(make(row, t, mean, sd, oh)); yte.append((row[t] - mean) / sd)
            meta.append((b, d, str(months[t].date()), mean, sd, float(row[t]), float(row[t - 1])))

    Xtr = np.asarray(Xtr, np.float32); ytr = np.asarray(ytr, np.float32)
    Xte = np.asarray(Xte, np.float32); yte = np.asarray(yte, np.float32)
    te_df = pd.DataFrame(meta, columns=["branch", "dept", "month", "mean", "sd", "actual", "naive_raw"])
    owner = np.asarray(owner)

    # leakage gate (same 5 asserts as the notebook)
    tm = pd.to_datetime(te_df.month)
    assert ((tm >= "2025-04-01") & (tm <= "2026-03-01")).all()
    assert not (np.isnan(Xtr).any() or np.isnan(Xte).any())
    assert set(te_df.branch) <= set(owner) and len(te_df.branch.unique()) > 0
    assert len(ytr) > 0 and len(yte) > 0
    return dict(Xtr=Xtr, ytr=ytr, owner=owner, Xte=Xte, yte=yte, te_df=te_df,
                n_features=Xtr.shape[1], n_lags=w, clients=sorted(set(owner)))


def per_client(ds):
    """Split the pooled train tensors by owning trust -> {client: (X, y)}."""
    out = {}
    for b in ds["clients"]:
        m = ds["owner"] == b
        out[b] = (ds["Xtr"][m], ds["ytr"][m])
    return out


def build_all(depts_mode="stable18", min_coverage=0.5, panel_min_months=96, window=W):
    canon = load_canonical()
    panel = freeze_panel(canon, depts_mode, min_coverage, panel_min_months, w=window)
    ds = build_tensors(canon, panel)
    ds["panel"] = panel
    return ds
