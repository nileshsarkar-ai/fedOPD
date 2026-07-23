"""Fetch NHS England RTT monthly "Full CSV" files listed in nhs_manifest.json.

Stdlib only, idempotent: a month already present as a CSV is skipped. Downloads the zip
to data/archives/rtt/ and extracts the single CSV to
data/nhs_rtt_referral_to_treatment/rtt_YYYY-MM.csv.

    python fetch_scripts/fetch_nhs.py                 # every month in the manifest
    python fetch_scripts/fetch_nhs.py 2026-04 2026-05 # only these months
"""

import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "fetch_scripts", "nhs_manifest.json")
CSV_DIR = os.path.join(ROOT, "data", "nhs_rtt_referral_to_treatment")
ZIP_DIR = os.path.join(ROOT, "data", "archives", "rtt")
UA = {"User-Agent": "Mozilla/5.0 (fedOPD data fetch)"}


def fetch(entry):
    month, url = entry["month"], entry["url"]
    csv_path = os.path.join(CSV_DIR, f"rtt_{month}.csv")
    if os.path.exists(csv_path):
        print(f"{month}: csv present, skipping")
        return
    zip_path = os.path.join(ZIP_DIR, f"rtt-{month}.zip")
    if not os.path.exists(zip_path):
        print(f"{month}: downloading ...", end=" ", flush=True)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req) as r, open(zip_path + ".part", "wb") as out:
            out.write(r.read())
        os.replace(zip_path + ".part", zip_path)
        print(f"{os.path.getsize(zip_path):,} bytes")
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise SystemExit(f"{month}: expected 1 csv in zip, found {names}")
        with z.open(names[0]) as src, open(csv_path + ".part", "wb") as out:
            while chunk := src.read(1 << 20):
                out.write(chunk)
    os.replace(csv_path + ".part", csv_path)
    print(f"{month}: extracted -> {os.path.getsize(csv_path):,} bytes")


def main():
    os.makedirs(CSV_DIR, exist_ok=True)
    os.makedirs(ZIP_DIR, exist_ok=True)
    files = json.load(open(MANIFEST))["files"]
    wanted = set(sys.argv[1:])
    todo = [f for f in files if not wanted or f["month"] in wanted]
    if wanted:
        missing = wanted - {f["month"] for f in files}
        if missing:
            raise SystemExit(f"not in manifest: {sorted(missing)}")
    for entry in todo:
        fetch(entry)
    print(f"done: {len(todo)} month(s) processed")


if __name__ == "__main__":
    main()
