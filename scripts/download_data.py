"""
Download North American monthly station files (raw and FLs.52j for TMAX and TMIN).

Each element directory contains one file per station:
    {station_id}.raw.tmax, {station_id}.FLs.52j.tmax, etc.

Usage:
    # Download all North American stations (~30k per directory)
    python scripts/download_data.py --out data/raw

    # Download a specific list of stations
    python scripts/download_data.py --out data/raw --station-list stations.txt
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

NORTHAM_BASE = "https://www.ncei.noaa.gov/data/north-american-dataset/access/"

NORTHAM_DIRS = {
    "tmax-raw":    "raw.tmax",
    "tmax-FLs.52j": "FLs.52j.tmax",
    "tmin-raw":    "raw.tmin",
    "tmin-FLs.52j": "FLs.52j.tmin",
}


def list_northam_station_ids() -> list[str]:
    """List all station IDs available in the North American dataset."""
    url = NORTHAM_BASE + "tmax-raw/"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    filenames = re.findall(r'href="([A-Z0-9]+\.raw\.tmax)"', r.text)
    return [f.split(".")[0] for f in filenames]


def download_one(station_id: str, subdir: str, suffix: str,
                 northam_dir: Path, session: requests.Session) -> bool:
    dest = northam_dir / subdir / f"{station_id}.{suffix}"
    if dest.exists():
        return True
    url = NORTHAM_BASE + subdir + "/" + f"{station_id}.{suffix}"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 404:
            return False
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return True
    except Exception:
        return False


def download_northam(out_dir: Path, station_ids: list[str], workers: int) -> dict:
    northam_dir = out_dir / "northam"
    session = requests.Session()
    provenance = {}
    downloaded_at = datetime.now(timezone.utc).isoformat()

    for subdir, suffix in NORTHAM_DIRS.items():
        n_ok = n_miss = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(download_one, sid, subdir, suffix, northam_dir, session): sid
                for sid in station_ids
            }
            for fut in tqdm(as_completed(futures), total=len(futures), desc=subdir):
                if fut.result():
                    n_ok += 1
                else:
                    n_miss += 1
        print(f"  {subdir}: {n_ok:,} downloaded, {n_miss:,} not found")
        provenance[subdir] = {
            "base_url": NORTHAM_BASE + subdir + "/",
            "n_stations": n_ok,
            "downloaded_utc": downloaded_at,
        }
    return provenance


def save_provenance(provenance: dict, processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    ppath = processed_dir / "provenance.json"
    existing = {}
    if ppath.exists():
        with open(ppath) as fh:
            existing = json.load(fh)
    existing.update(provenance)
    with open(ppath, "w") as fh:
        json.dump(existing, fh, indent=2)
    print(f"Provenance saved to {ppath}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download North American monthly station files."
    )
    parser.add_argument("--out", default="data/raw", help="Output directory for raw data")
    parser.add_argument(
        "--station-list",
        help="File with station IDs (one per line); if omitted, downloads all stations",
    )
    parser.add_argument(
        "--workers", type=int, default=16,
        help="Parallel download workers (default: 16)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)

    if args.station_list:
        with open(args.station_list) as fh:
            station_ids = [line.strip() for line in fh if line.strip()]
        print(f"Downloading {len(station_ids)} stations from station list...")
    else:
        print("Listing all North American station IDs...")
        station_ids = list_northam_station_ids()
        print(f"  found {len(station_ids):,} stations")

    provenance = download_northam(out_dir, station_ids, args.workers)
    save_provenance(provenance, out_dir.parent / "processed")
    print("Done.")


if __name__ == "__main__":
    main()
