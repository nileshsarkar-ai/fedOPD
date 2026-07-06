"""Load NHS RTT monthly CSVs into the canonical [date, branch, dept, demand] table.

EDA data-prep helper (Steps 2 & 5). Reduces the raw 121-column Full CSV files to the
minimal long-format table we analyse and (later) forecast on.

Rules applied here (all decided during EDA Step 1-2):
  * demand      = rows where RTT Part Type == 'Part_3'  (New RTT Periods = new referrals)
  * NHS trusts  = Provider Org Code is a 3-char code starting 'R'  (drops independents)
  * drop        = Treatment Function 'C_999' (the 'Total' aggregate specialty)
  * sum         = across commissioners, to get provider x specialty x month demand

Usage (from a notebook at repo root):
    import sys; sys.path.insert(0, r"C:\\Users\\heave\\Documents\\FedOPD")
    from src import rtt
    df = rtt.load_all()            # all 60 months, trusts only -> canonical table
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Folder of extracted monthly CSVs (…/data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv)
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "nhs_rtt_referral_to_treatment"

DEMAND_PART = "Part_3"    # New RTT Periods — our demand signal
TOTAL_DEPT = "C_999"      # the 'Total' treatment-function aggregate to drop

# Only these columns are read (faster + less memory than all 121).
USECOLS = [
    "Period",
    "Provider Org Code", "Provider Org Name",
    "Provider Parent Org Code", "Provider Parent Name",   # Provider Parent = ICB (the region)
    "Treatment Function Code", "Treatment Function Name",
    "RTT Part Type", "Total All",
]

# month name -> number, lower-cased so 'MARCH' and 'March' both match (format changes in 2023)
_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], start=1)}


def is_nhs_trust(code: object) -> bool:
    """True for NHS trust / foundation-trust ODS codes (3 chars, starting 'R')."""
    return isinstance(code, str) and len(code) == 3 and code[0] == "R"


def parse_period(period: object) -> pd.Timestamp:
    """'RTT-March-2026' or 'RTT-MARCH-2026' -> Timestamp('2026-03-01')."""
    _, month, year = str(period).split("-")          # e.g. ['RTT', 'March', '2026']
    return pd.Timestamp(year=int(year), month=_MONTHS[month.lower()], day=1)


def list_months() -> list[Path]:
    """All 60 monthly CSV paths, in date order."""
    return sorted(DATA_DIR.glob("rtt_*.csv"))


def load_month(path: Path, trusts_only: bool = True) -> pd.DataFrame:
    """Read ONE month and reduce it to canonical rows (one per branch x dept)."""
    df = pd.read_csv(path, usecols=USECOLS, low_memory=False)

    # keep only the demand pathway and real specialties
    df = df[df["RTT Part Type"] == DEMAND_PART]
    df = df[df["Treatment Function Code"] != TOTAL_DEPT]
    if trusts_only:
        df = df[df["Provider Org Code"].map(is_nhs_trust)]

    # a provider x specialty appears once PER commissioner -> sum to provider level
    df = df.assign(
        date=df["Period"].map(parse_period),
        demand=pd.to_numeric(df["Total All"], errors="coerce"),
    )
    out = df.groupby(
        ["date", "Provider Org Code", "Treatment Function Code"], as_index=False
    ).agg(
        branch_name=("Provider Org Name", "first"),
        icb=("Provider Parent Org Code", "first"),
        icb_name=("Provider Parent Name", "first"),
        dept_name=("Treatment Function Name", "first"),
        demand=("demand", "sum"),
    ).rename(columns={
        "Provider Org Code": "branch",
        "Treatment Function Code": "dept",
    })
    return out[["date", "branch", "branch_name", "icb", "icb_name", "dept", "dept_name", "demand"]]


def load_all(trusts_only: bool = True) -> pd.DataFrame:
    """Load all 60 months into one canonical long table, sorted by series then time."""
    frames = [load_month(p, trusts_only=trusts_only) for p in list_months()]
    df = pd.concat(frames, ignore_index=True)
    return df.sort_values(["branch", "dept", "date"]).reset_index(drop=True)
