"""Export everything the dashboard needs into dashboard/data.json (no server framework)."""
import glob
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = next(p for p in (Path(__file__).resolve(), *Path(__file__).resolve().parents)
            if (p / "CLAUDE.md").exists())
RES = ROOT / "results"
OUT = ROOT / "dashboard"; OUT.mkdir(exist_ok=True)


def method_table():
    runs = defaultdict(list)
    for f in glob.glob(str(RES / "*_s*.json")):
        r = json.load(open(f))
        if "metrics" in r:
            runs[r["name"]].append(r)
    rows = []
    spec = [("local_delta", "local-only", False), ("fedavg_ft3_delta", "FedAvg + personalise", True),
            ("fedprox_mu0.001_ft3_delta", "FedProx + personalise", True),
            ("central_delta", "centralised (upper bound)", False)]
    for name, lab, useft in spec:
        rs = runs.get(name, [])
        if not rs:
            continue
        vals = [(r["ft_metrics"]["macro_mean"] if useft and "ft_metrics" in r else r["metrics"]["macro_mean"]) for r in rs]
        med = np.mean([(r["ft_metrics"]["median"] if useft and "ft_metrics" in r else r["metrics"]["median"]) for r in rs])
        rows.append({"method": lab, "mean": round(float(np.mean(vals)), 2),
                     "std": round(float(np.std(vals)), 2), "median": round(float(med), 2)})
    return rows


def main():
    flow = pd.read_parquet(ROOT / "reports" / "tables" / "rtt_flow.parquet")
    dec = pd.read_parquet(RES / "agentic_decisions.parquet")
    summ = json.load(open(RES / "agentic_summary.json"))
    base = json.load(open(RES / "baselines.json"))
    dstats = json.load(open(RES / "dataset_stats.json"))

    nat = flow.groupby("date")[["demand", "completed", "backlog", "breach18"]].sum()
    dates = [d.strftime("%Y-%m") for d in nat.index]

    # per-client drill-down: top 60 services by total demand (keeps the page light but rich)
    top = (dec.groupby(["branch", "dept"]).D_hat.sum().sort_values(ascending=False).head(60).index)
    clients = {}
    latest = dec.date.max()
    for b, d in top:
        fh = flow[(flow.branch == b) & (flow.dept == d)].set_index("date").sort_index()
        dh = dec[(dec.branch == b) & (dec.dept == d)].set_index("date").sort_index()
        snap = dh.loc[[latest]] if latest in dh.index else dh.tail(1)
        clients[f"{b}·{d}"] = {
            "branch": b, "dept": d,
            "rag": str(snap["rag"].iloc[0]), "wait_wk": round(float(snap["wait_wk"].iloc[0]), 1),
            "gap": int(snap["gap"].clip(lower=0).iloc[0]),
            "dates": [x.strftime("%Y-%m") for x in fh.index],
            "demand": [int(x) for x in fh["demand"].fillna(0)],
            "completed": [int(x) for x in fh["completed"].fillna(0)],
            "backlog": [int(x) for x in fh["backlog"].fillna(0)],
            "f_dates": [x.strftime("%Y-%m") for x in dh.index],
            "d_hat": [int(x) for x in dh["D_hat"].fillna(0)],
            "gap_series": [int(max(0, x)) for x in dh["gap"].fillna(0)],
        }

    data = {
        "meta": {
            "clients": dstats["n_clients"], "roster": dstats["roster_size"],
            "train_series": dstats["n_train_series"], "eval_series": dstats["n_eval_series"],
            "train_windows": dstats["n_train_windows"], "test_points": dstats["n_test_windows"],
            "features": dstats["n_features"], "bar": round(base["R01_naive_t1"]["macro_mean"], 2),
            "bar_median": round(base["R01_naive_t1"]["median"], 2),
        },
        "methods": method_table(),
        "flow_national": {
            "dates": dates,
            "demand": [round(x / 1e6, 3) for x in nat["demand"]],
            "completed": [round(x / 1e6, 3) for x in nat["completed"]],
            "backlog": [round(x / 1e6, 3) for x in nat["backlog"]],
            "breach18": [round(x / 1e6, 3) for x in nat["breach18"]],
        },
        "agentic": {
            "decision_month": summ["decision_month"],
            "rag": summ["rag_counts"],
            "national_capacity": summ["national_additional_capacity_per_month"],
            "national_backlog": summ["national_backlog"],
            "national_breach18": summ["national_breach18"],
            "icb": [{"icb": k, "add": int(v)} for k, v in summ["top_icbs_by_additional_capacity"].items()],
            "flow_identity_err": 3.8, "flow_rho": 0.40,
        },
        "clients": clients,
    }
    (OUT / "data.json").write_text(json.dumps(data))
    print(f"wrote {OUT/'data.json'} ({(OUT/'data.json').stat().st_size/1024:.0f} KB, {len(clients)} clients)")


if __name__ == "__main__":
    main()
