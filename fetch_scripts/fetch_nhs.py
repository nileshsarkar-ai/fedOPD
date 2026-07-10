#!/usr/bin/env python3
"""Reproducible downloader + unzipper for the NHS RTT / A&E / DM01 monthly files.

Driven entirely by ``fetch_scripts/nhs_manifest.json`` (a checked-in record of the
exact source URLs). Two idempotent phases, both safe to re-run:

  1. download  -> raw files land in  data/archives/<dataset>/<dataset>-<month>.<ext>
  2. extract   -> the CSV inside each archive is unzipped/copied, renamed
                  uniformly, into a specifically-named per-dataset folder:
                    data/nhs_rtt_referral_to_treatment/rtt_<month>.csv
                    data/nhs_ae_attendances_emergency_admissions/ae_<month>.csv
                    data/nhs_dm01_monthly_diagnostics/dm01_<month>.csv

Everything stays under ``data/`` (git-ignored) so nothing is scattered through
the codebase. Raw archives are preserved alongside the extracted CSVs.

    python fetch_scripts/fetch_nhs.py                 # download everything, then extract
    python fetch_scripts/fetch_nhs.py --dataset rtt   # one dataset only
    python fetch_scripts/fetch_nhs.py --no-extract    # download archives only
    python fetch_scripts/fetch_nhs.py --extract-only  # (re)extract from existing archives
    python fetch_scripts/fetch_nhs.py --list          # show the plan; touch nothing

Stdlib only — no third-party packages required.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MANIFEST = os.path.join(HERE, "nhs_manifest.json")
DATA_DIR = os.path.join(ROOT, "data")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archives")
UA = "Mozilla/5.0 (compatible; fedopd-fetch/1.0)"
MIN_BYTES = 20_000  # smaller than this is almost certainly an error page, not data

# The specifically-named, analysis-ready folder for each dataset's extracted CSVs.
EXTRACT_FOLDER = {
    "rtt": "nhs_rtt_referral_to_treatment",
    "ae": "nhs_ae_attendances_emergency_admissions",
    "dm01": "nhs_dm01_monthly_diagnostics",
}


def load_manifest() -> dict:
    if not os.path.exists(MANIFEST):
        sys.exit(f"manifest not found: {MANIFEST}")
    with open(MANIFEST) as fh:
        return json.load(fh)


def archive_path(entry: dict) -> str:
    ext = entry.get("filetype", "bin").lstrip(".")
    return os.path.join(ARCHIVE_DIR, entry["dataset"], f"{entry['dataset']}-{entry['month']}.{ext}")


def extracted_path(entry: dict) -> str:
    ds = entry["dataset"]
    return os.path.join(DATA_DIR, EXTRACT_FOLDER[ds], f"{ds}_{entry['month']}.csv")


def fmt_size(n: int) -> str:
    if n >= 1024 ** 3:
        return f"{n / 1024**3:.2f}GB"
    if n >= 1024 ** 2:
        return f"{n / 1024**2:.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.0f}KB"
    return f"{n}B"


def download(url: str, dest: str) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out, length=1 << 16)
    total = os.path.getsize(tmp)
    if total < MIN_BYTES:
        os.remove(tmp)
        raise IOError(f"suspiciously small download ({total} bytes)")
    os.replace(tmp, dest)
    return total


def extract(entry: dict) -> int:
    """Materialise the archive's CSV into the dataset's extracted folder.

    A zip is opened and its (largest) CSV member is streamed out; a raw csv is
    copied verbatim. Returns the extracted file size in bytes.
    """
    src = archive_path(entry)
    dest = extracted_path(entry)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"

    if entry.get("filetype") == "zip":
        with zipfile.ZipFile(src) as zf:
            members = [m for m in zf.infolist() if m.filename.lower().endswith(".csv")]
            if not members:
                raise IOError(f"no CSV inside {src}")
            member = max(members, key=lambda m: m.file_size)  # the data CSV, not a sidecar
            with zf.open(member) as fin, open(tmp, "wb") as fout:
                shutil.copyfileobj(fin, fout, length=1 << 16)
    else:  # already a plain csv archive
        shutil.copyfile(src, tmp)

    os.replace(tmp, dest)
    return os.path.getsize(dest)


def prune_archives(files) -> None:
    """Delete each raw archive whose extracted CSV is verified present & valid.

    Safe by construction: an archive is only removed once its extracted CSV
    exists and is non-trivial. Anything still missing an extract keeps its
    archive (and the run exits non-zero so the gap is obvious). Everything is
    re-fetchable from the manifest.
    """
    removed = kept = 0
    freed = 0
    missing = []
    for f in files:
        ex, ar = extracted_path(f), archive_path(f)
        if not (os.path.exists(ex) and os.path.getsize(ex) >= MIN_BYTES):
            missing.append(f); kept += 1
            continue
        if os.path.exists(ar):
            freed += os.path.getsize(ar); os.remove(ar); removed += 1

    # tidy now-empty archive directories
    for ds in EXTRACT_FOLDER:
        d = os.path.join(ARCHIVE_DIR, ds)
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    if os.path.isdir(ARCHIVE_DIR) and not os.listdir(ARCHIVE_DIR):
        os.rmdir(ARCHIVE_DIR)

    verified = len(files) - len(missing)
    print(f"prune: {verified}/{len(files)} extracts verified present; "
          f"removed {removed} archives ({fmt_size(freed)} freed), kept {kept}")
    if missing:
        print("  ! extracted CSV MISSING — archive KEPT (re-run fetch to fix):")
        for f in missing:
            print(f"     {f['dataset']} {f['month']}")
        sys.exit(1)


def select(files, dataset, only_ok):
    if dataset:
        files = [f for f in files if f["dataset"] == dataset]
    if only_ok:
        files = [f for f in files if f.get("ok", True)]
    return sorted(files, key=lambda f: (f["dataset"], f["month"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", choices=list(EXTRACT_FOLDER), help="restrict to one dataset")
    ap.add_argument("--only-ok", action="store_true", help="skip entries the manifest marked ok=false")
    ap.add_argument("--force", action="store_true", help="re-download / re-extract even if present")
    ap.add_argument("--no-extract", action="store_true", help="download archives only, do not unzip")
    ap.add_argument("--extract-only", action="store_true", help="skip download; (re)extract existing archives")
    ap.add_argument("--prune-archives", action="store_true",
                    help="delete each raw archive whose extracted CSV is present & valid (reclaim disk; "
                         "re-fetchable from the manifest). Archives for any missing extract are kept.")
    ap.add_argument("--list", action="store_true", help="print the plan; download/extract nothing")
    args = ap.parse_args()

    manifest = load_manifest()
    files = select(manifest["files"], args.dataset, args.only_ok)
    print(f"manifest: {len(files)} files (generated {manifest.get('generated', '?')})")

    if args.prune_archives:
        prune_archives(files)
        return

    if args.list:
        for f in files:
            a = archive_path(f); e = extracted_path(f)
            a_state = "have" if os.path.exists(a) and os.path.getsize(a) >= MIN_BYTES else "MISS"
            e_state = "have" if os.path.exists(e) and os.path.getsize(e) >= MIN_BYTES else "MISS"
            print(f"  {f['dataset']:<4} {f['month']}  archive:{a_state}  extracted:{e_state}  "
                  f"{fmt_size(f.get('content_length', 0)):>8}  {os.path.relpath(e, ROOT)}")
        return

    # ---- phase 1: download ----
    dl_fetched = dl_skipped = dl_failed = 0
    dl_bytes = 0
    if not args.extract_only:
        for f in files:
            dest = archive_path(f)
            if os.path.exists(dest) and os.path.getsize(dest) >= MIN_BYTES and not args.force:
                dl_skipped += 1
                continue
            try:
                n = download(f["url"], dest)
                dl_bytes += n; dl_fetched += 1
                print(f"  ↓ {f['dataset']:<4} {f['month']}  {fmt_size(n):>8}  -> {os.path.relpath(dest, ROOT)}")
            except (HTTPError, URLError, IOError) as e:
                dl_failed += 1
                print(f"  ✗ {f['dataset']:<4} {f['month']}  DOWNLOAD FAILED: {e}")
        print(f"download: {dl_fetched} fetched ({fmt_size(dl_bytes)}), {dl_skipped} present, {dl_failed} failed")

    # ---- phase 2: extract ----
    ex_done = ex_skipped = ex_failed = 0
    ex_bytes = 0
    if not args.no_extract:
        for f in files:
            src, dest = archive_path(f), extracted_path(f)
            if not (os.path.exists(src) and os.path.getsize(src) >= MIN_BYTES):
                continue  # nothing downloaded to extract
            if os.path.exists(dest) and os.path.getsize(dest) >= MIN_BYTES and not args.force:
                ex_skipped += 1
                continue
            try:
                n = extract(f)
                ex_bytes += n; ex_done += 1
                print(f"  ⇪ {f['dataset']:<4} {f['month']}  {fmt_size(n):>8}  -> {os.path.relpath(dest, ROOT)}")
            except (zipfile.BadZipFile, IOError) as e:
                ex_failed += 1
                print(f"  ✗ {f['dataset']:<4} {f['month']}  EXTRACT FAILED: {e}")
        print(f"extract: {ex_done} extracted ({fmt_size(ex_bytes)} on disk), {ex_skipped} present, {ex_failed} failed")

    if dl_failed or ex_failed:
        sys.exit(1)


if __name__ == "__main__":
    main()