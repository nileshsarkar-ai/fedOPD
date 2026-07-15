"""Scoring, identical to build.ipynb Step 3: sMAPE on RAW counts, per series over its test
months, then macro-mean (headline) / median / volume-weighted. Every method is scored on
exactly the same (series, month) points -- te_df rows are 1:1 with X_test."""
from __future__ import annotations
import numpy as np


def smape_raw(a, p):
    a, p = np.asarray(a, float), np.asarray(p, float)
    return np.mean(2 * np.abs(p - a) / (np.abs(p) + np.abs(a) + 1e-6)) * 100


def score_raw(te_df, pred_raw):
    df = te_df.assign(pred=np.asarray(pred_raw, float))
    per = df.groupby(["branch", "dept"], sort=False).apply(
        lambda g: smape_raw(g.actual.values, g.pred.values), include_groups=False)
    mass = df.groupby(["branch", "dept"], sort=False).actual.sum()
    return {"macro_mean": float(per.mean()), "median": float(per.median()),
            "vol_weighted": float((per * mass).sum() / mass.sum()), "n_series": int(len(per))}


def score_scaled(te_df, pred_scaled):
    """Inverse-transform scaled predictions with each row's per-series (mean, sd), then score."""
    raw = np.asarray(pred_scaled, float) * te_df["sd"].values + te_df["mean"].values
    return score_raw(te_df, raw)


def per_series_smape(te_df, pred_scaled):
    """Per-series sMAPE frame (for per-client breakdowns and the H1 test)."""
    raw = np.asarray(pred_scaled, float) * te_df["sd"].values + te_df["mean"].values
    df = te_df.assign(pred=raw)
    per = df.groupby(["branch", "dept"], sort=False).apply(
        lambda g: smape_raw(g.actual.values, g.pred.values), include_groups=False)
    return per.rename("smape").reset_index()


def naive_bar(te_df):
    """R-01 on this exact point set (te_df carries the raw t-1 predecessor)."""
    return score_raw(te_df, te_df["naive_raw"].values)
