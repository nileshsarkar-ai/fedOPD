"""Stage 6 - agentic plane (prototype v1): forecasts + operational flow state -> capacity/
staffing/allocation decisions, rolled up to ICB, backtested against what actually happened.

Decision model (transparent operations research; the policy an LLM agent would execute):
  state per (trust x dept x month t):
    D_hat(t)  = federated 1-month-ahead demand forecast (fedavg + personalisation, delta)
    B(t-1)    = observed backlog (Part_2 incomplete) at the previous month end
    C_base    = trailing-12-month mean throughput (Part_1A+1B completions)
    breach(t-1) = observed >18-week waiters (Part_2 wait bands >= 18wk)
  Little's law: mean wait (months) ~ backlog / throughput. The 18-week RTT standard (4.15 months)
    implies a sustainable backlog B* = 4.15 * D_hat (steady-state demand served FIFO).
  Required throughput to absorb demand AND burn the excess backlog over horizon H months:
    C_req(t)  = D_hat(t) + max(0, B(t-1) - B*) / H
  Capacity gap (the staffing signal):  gap(t) = C_req(t) - C_base   (>0 => allocate more capacity)
  RAG status from the current implied wait:  wait_wk = B(t-1)/C_base * 4.33
    RED >= 18wk (breaching), AMBER 12-18wk, GREEN < 12wk.
  Allocation plane: sum positive gaps trust->ICB->national -> where NHS England should direct capacity
    (allocate to trusts; independents would be commissioned -- out of scope, trusts only).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

from . import data as fdata, fed as ffed, evaluate as feval

ROOT = fdata.ROOT
WAIT_TARGET_MONTHS = 18 / 4.345           # 18-week RTT standard in months (~4.14)
HORIZON = 12                              # months to burn the backlog excess to target
RED_WK, AMBER_WK = 18.0, 12.0


def forecasts(seed=0):
    """Deployed forecaster (fedavg 40r + personalisation ft3, delta) -> per (branch,dept,month) D_hat."""
    ds = fdata.build_all()
    cd = fdata.per_client(ds)
    glob, _ = ffed.run_federated(cd, ds["n_features"], "delta", rounds=40, seed=seed)
    models = ffed.personalise(glob, cd, ds["n_features"], "delta", ft_epochs=3, seed=seed)
    pred = ffed.predict_per_client(models, ds["te_df"], ds["Xte"], lag1=ds["n_lags"] - 1)
    te = ds["te_df"].copy()
    te["D_hat"] = np.maximum(0.0, pred * te["sd"].values + te["mean"].values)  # demand can't be negative
    te["date"] = pd.to_datetime(te["month"])
    return te[["branch", "dept", "date", "actual", "D_hat"]].rename(columns={"actual": "D_actual"}), ds


def decide(seed=0):
    fc, ds = forecasts(seed)
    flow = pd.read_parquet(ROOT / "reports" / "tables" / "rtt_flow.parquet")
    flow = flow.sort_values(["branch", "dept", "date"])
    g = flow.groupby(["branch", "dept"], group_keys=False)
    flow["B_prev"] = g["backlog"].shift(1)
    flow["breach_prev"] = g["breach18"].shift(1)
    flow["C_base"] = g["completed"].transform(lambda s: s.shift(1).rolling(12, min_periods=3).mean())
    dec = fc.merge(flow[["branch", "dept", "date", "backlog", "completed", "breach18",
                         "B_prev", "breach_prev", "C_base", "icb"]],
                   on=["branch", "dept", "date"], how="left")
    dec = dec.dropna(subset=["B_prev", "C_base"])
    dec = dec[dec["C_base"] > 0].copy()

    B_star = WAIT_TARGET_MONTHS * dec["D_hat"]
    dec["C_req"] = dec["D_hat"] + np.maximum(0.0, dec["B_prev"] - B_star) / HORIZON
    dec["gap"] = dec["C_req"] - dec["C_base"]
    dec["wait_wk"] = dec["B_prev"] / dec["C_base"] * 4.345
    dec["rag"] = np.where(dec["wait_wk"] >= RED_WK, "RED",
                          np.where(dec["wait_wk"] >= AMBER_WK, "AMBER", "GREEN"))
    # backtest: when actual capacity fell short of the requirement, did the backlog grow?
    dec["dB_actual"] = dec["backlog"] - dec["B_prev"]
    dec["shortfall"] = dec["C_req"] - dec["completed"]     # >0 => under-served vs requirement
    val = dec.dropna(subset=["dB_actual", "shortfall"])
    concordance = float(np.mean(np.sign(val["shortfall"]) == np.sign(val["dB_actual"])))
    rho = float(val[["shortfall", "dB_actual"]].corr(method="spearman").iloc[0, 1])

    dec.to_parquet(ROOT / "results" / "agentic_decisions.parquet")
    latest = dec["date"].max()
    snap = dec[dec["date"] == latest]
    icb = (snap.assign(pos=snap["gap"].clip(lower=0)).groupby("icb")
           .agg(add_capacity=("pos", "sum"), red=("rag", lambda s: (s == "RED").sum()),
                clients=("branch", "nunique")).sort_values("add_capacity", ascending=False))
    summary = {
        "decision_month": str(latest.date()),
        "n_client_series": int(snap.shape[0]),
        "rag_counts": snap["rag"].value_counts().to_dict(),
        "national_additional_capacity_per_month": int(snap["gap"].clip(lower=0).sum()),
        "national_backlog": int(snap["backlog"].sum()),
        "national_breach18": int(snap["breach18"].sum()),
        "top_icbs_by_additional_capacity": {k: int(v) for k, v in icb["add_capacity"].head(8).items()},
        "backtest_sign_concordance": round(concordance, 3),
        "backtest_spearman_shortfall_vs_backlog_change": round(rho, 3),
        "horizon_months": HORIZON, "wait_target_months": round(WAIT_TARGET_MONTHS, 2), "seed": seed,
    }
    (ROOT / "results" / "agentic_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return dec, summary, icb


if __name__ == "__main__":
    decide()
