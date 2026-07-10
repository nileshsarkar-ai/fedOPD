#!/usr/bin/env python3
"""Scrape NHS England's RTT financial-year pages and emit fetch_scripts/nhs_manifest.json.

Produces the manifest consumed by fetch_nhs.py: one entry per monthly
"Full CSV data file" (.zip). The download URLs carry unpredictable hashes, so
they must be scraped from the live pages rather than constructed.

Target window: 60 months (5 financial years) = Apr 2021 -> Mar 2026, i.e. the
five FY pages 2021-22 .. 2025-26. Adjust FY_PAGES to change the range.

    python fetch_scripts/build_rtt_manifest.py            # scrape + write manifest
    python fetch_scripts/build_rtt_manifest.py --no-head  # skip Content-Length probes (faster)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, "nhs_manifest.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BASE = "https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times"

# Five financial years = exactly 60 months (Apr 2021 .. Mar 2026).
FY_PAGES = {
    "2021-22": f"{BASE}/rtt-data-2021-22/",
    "2022-23": f"{BASE}/rtt-data-2022-23/",
    "2023-24": f"{BASE}/rtt-data-2023-24/",
    "2024-25": f"{BASE}/rtt-data-2024-25/",
    "2025-26": f"{BASE}/rtt-data-2025-26",
}

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# Full absolute URL to a Full-CSV zip, capturing the Mon + YY token in the filename.
URL_RE = re.compile(
    r"https://www\.england\.nhs\.uk/statistics/wp-content/uploads/[^\"'\s>]*"
    r"Full-CSV-data-file-([A-Za-z]{3})(\d{2})[^\"'\s>]*\.zip",
    re.IGNORECASE,
)


def scrape_page(url: str) -> dict[str, str]:
    """Return {YYYY-MM: url} for every Full-CSV zip found on one FY page."""
    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    found: dict[str, str] = {}
    for m in URL_RE.finditer(r.text):
        full, mon, yy = m.group(0), m.group(1).lower(), m.group(2)
        month_num = MONTHS.get(mon)
        if not month_num:
            continue
        key = f"20{yy}-{month_num:02d}"
        found.setdefault(key, full)  # keep first occurrence per month
    return found


def content_length(url: str) -> int:
    try:
        r = requests.head(url, headers={"User-Agent": UA}, allow_redirects=True, timeout=30)
        return int(r.headers.get("Content-Length", 0))
    except Exception:
        return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-head", action="store_true", help="skip Content-Length probes")
    args = ap.parse_args()

    by_month: dict[str, str] = {}
    for fy, url in FY_PAGES.items():
        got = scrape_page(url)
        print(f"  {fy}: {len(got):>2} months  ({url})")
        for k, v in got.items():
            by_month.setdefault(k, v)

    months = sorted(by_month)
    print(f"\nTotal distinct months found: {len(months)}"
          f"  ({months[0]} .. {months[-1]})" if months else "none")

    files = []
    for i, month in enumerate(months, 1):
        url = by_month[month]
        size = 0 if args.no_head else content_length(url)
        if not args.no_head:
            print(f"  [{i:>2}/{len(months)}] {month}  {size/1024**2:6.1f}MB  {os.path.basename(url)}")
        files.append({
            "dataset": "rtt",
            "month": month,
            "url": url,
            "filetype": "zip",
            "content_length": size,
            "ok": True,
        })

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    manifest = {
        "generated": "2026-07-06",
        "source": "NHS England Consultant-led RTT Waiting Times (Full CSV data files)",
        "files": files,
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nWrote {len(files)} entries -> {MANIFEST}")
    if len(files) != 60:
        print(f"  ! expected 60, got {len(files)} — check the FY pages before downloading",
              file=sys.stderr)


if __name__ == "__main__":
    main()
