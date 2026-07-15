"""Extract the RTT operational-flow state for the agentic plane, same grain as the canonical
demand table: [date, branch, dept] x {demand, completed, backlog, breach18}.

  demand    = Part_3  Total All            (new RTT clocks started  -> the forecast target)
  completed = Part_1A + Part_1B Total All  (clocks stopped this month -> throughput)
  backlog   = Part_2  Total All            (incomplete pathways at month end -> the stock)
  breach18  = Part_2  sum of wait bands with lower bound >= 18 weeks (the >18-week waiters)

Flow identity (standard NHS RTT, approximate): backlog(t) ~ backlog(t-1) + demand(t) - completed(t).
Trusts only (R##), drop C_999, sum over commissioner -- identical filters to the demand build.
"""
import re
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = next(p for p in (Path(__file__).resolve(), *Path(__file__).resolve().parents)
            if (p / "CLAUDE.md").exists())
DATA = ROOT / "data" / "nhs_rtt_referral_to_treatment"
MONTHS = {m.upper(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def parse_period(p):
    g = re.search(r"([A-Za-z]+)[-_ ](\d{4})", str(p))
    return pd.Timestamp(int(g.group(2)), MONTHS[g.group(1).upper()], 1)


def band_lower(col):
    m = re.match(r"Gt (\d+)", col)
    return int(m.group(1)) if m else None


def load_month(path):
    head = pd.read_csv(path, nrows=0).columns
    band_cols = [c for c in head if band_lower(c) is not None]
    b18 = [c for c in band_cols if band_lower(c) >= 18]
    use = ["Period", "Provider Org Code", "Provider Parent Org Code",
           "Treatment Function Code", "RTT Part Type", "Total All"] + b18
    d = pd.read_csv(path, usecols=use, low_memory=False)
    c = d["Provider Org Code"].astype(str).str.strip()
    d = d[(c.str.len() == 3) & c.str.upper().str.startswith("R")]
    d = d[d["Treatment Function Code"] != "C_999"].copy()
    d["Total All"] = pd.to_numeric(d["Total All"], errors="coerce")
    for col in b18:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d["_b18"] = d[b18].sum(axis=1) if b18 else 0.0
    key = ["Provider Org Code", "Provider Parent Org Code", "Treatment Function Code"]
    g = d.groupby(key + ["RTT Part Type"], as_index=False).agg(tot=("Total All", "sum"),
                                                               b18=("_b18", "sum"))
    piv = g.pivot_table(index=key, columns="RTT Part Type", values="tot", fill_value=0.0)
    b18 = (g[g["RTT Part Type"] == "Part_2"].set_index(key)["b18"])
    out = pd.DataFrame(index=piv.index)
    out["demand"] = piv.get("Part_3", 0.0)
    out["completed"] = piv.get("Part_1A", 0.0) + piv.get("Part_1B", 0.0)
    out["backlog"] = piv.get("Part_2", 0.0)
    out["breach18"] = b18.reindex(out.index).fillna(0.0)
    out = out.reset_index().rename(columns={"Provider Org Code": "branch",
                                            "Provider Parent Org Code": "icb",
                                            "Treatment Function Code": "dept"})
    out.insert(0, "date", parse_period(d["Period"].iloc[0]))
    return out


def main():
    files = sorted(DATA.glob("rtt_*.csv"))
    assert len(files) == 96
    flow = pd.concat([load_month(f) for f in files], ignore_index=True)
    flow = flow.sort_values(["date", "branch", "dept"]).reset_index(drop=True)
    out = ROOT / "reports" / "tables" / "rtt_flow.parquet"
    flow.to_parquet(out)
    print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB) rows {len(flow):,} months {flow.date.nunique()}")
    nat = flow.groupby("date")[["demand", "completed", "backlog", "breach18"]].sum()
    print("national totals 2026-03:", nat.iloc[-1].astype("int64").to_dict())
    # flow-identity sanity: backlog(t) vs backlog(t-1)+demand-completed
    b = nat["backlog"]; pred = (b.shift(1) + nat["demand"] - nat["completed"]).iloc[1:]
    err = ((pred - b.iloc[1:]) / b.iloc[1:]).abs()
    print(f"flow identity national median abs err: {err.median():.1%} (approx; clock pauses/removals)")


if __name__ == "__main__":
    main()
