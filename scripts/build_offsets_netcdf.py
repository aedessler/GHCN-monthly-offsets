"""
Build a NetCDF file of monthly temperature adjustment offsets.

Reads North American per-station monthly files (raw and FLs.52j),
computes offset = FLs.52j - raw for TMAX and TMIN, and writes a
NetCDF with dimensions (station, time) where time is year-month.

Usage:
    python scripts/build_offsets_netcdf.py --raw-dir data/raw --out data/processed/monthly_offsets.nc
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).parent))
from parsers import iter_northam_file

MISSING = -9999


def load_northam_dir(subdir_path: Path) -> dict[str, dict[tuple, float | None]]:
    """
    Read all per-station files in a North American directory.

    Returns: {station_id: {(year, month): value_c}}
    """
    data = {}
    for fpath in sorted(subdir_path.glob("*")):
        station_id = fpath.name.split(".")[0]
        ym = {}
        try:
            for rec in iter_northam_file(str(fpath)):
                for m in rec["months"]:
                    ym[(rec["year"], m["month"])] = m["value_c"]
        except Exception as exc:
            print(f"  WARNING: {fpath.name}: {exc}", file=sys.stderr)
            continue
        if ym:
            data[station_id] = ym
    return data


def build_dataframe(raw_dir: Path) -> pd.DataFrame:
    northam_dir = raw_dir / "northam"

    print("Loading tmax-raw...")
    tmax_raw = load_northam_dir(northam_dir / "tmax-raw")
    print(f"  {len(tmax_raw)} stations")

    print("Loading tmax-FLs.52j...")
    tmax_fls = load_northam_dir(northam_dir / "tmax-FLs.52j")
    print(f"  {len(tmax_fls)} stations")

    print("Loading tmin-raw...")
    tmin_raw = load_northam_dir(northam_dir / "tmin-raw")
    print(f"  {len(tmin_raw)} stations")

    print("Loading tmin-FLs.52j...")
    tmin_fls = load_northam_dir(northam_dir / "tmin-FLs.52j")
    print(f"  {len(tmin_fls)} stations")

    # Only include stations that have both raw and FLs.52j data for at least one element
    usable = (set(tmax_raw) & set(tmax_fls)) | (set(tmin_raw) & set(tmin_fls))
    all_stations = sorted(usable)
    print(f"\nBuilding offset table for {len(all_stations)} stations "
          f"(with raw+FLs.52j for TMAX and/or TMIN)...")

    rows = []
    for station_id in all_stations:
        all_ym = set()
        for d in (tmax_raw.get(station_id, {}), tmax_fls.get(station_id, {}),
                  tmin_raw.get(station_id, {}), tmin_fls.get(station_id, {})):
            all_ym |= set(d)

        for (year, month) in all_ym:
            tr = tmax_raw.get(station_id, {}).get((year, month))
            tf = tmax_fls.get(station_id, {}).get((year, month))
            nr = tmin_raw.get(station_id, {}).get((year, month))
            nf = tmin_fls.get(station_id, {}).get((year, month))

            tmax_offset = tf - tr if (tr is not None and tf is not None) else np.nan
            tmin_offset = nf - nr if (nr is not None and nf is not None) else np.nan

            rows.append({
                "station_id": station_id,
                "year": year,
                "month": month,
                "tmax_offset_c": tmax_offset,
                "tmin_offset_c": tmin_offset,
            })

    return pd.DataFrame(rows)


def build_netcdf(df: pd.DataFrame, out_path: Path) -> None:
    # Build time coordinate as datetime64 (first of each year-month)
    df["time"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )

    stations = sorted(df["station_id"].unique())
    times = sorted(df["time"].unique())

    n_sta = len(stations)
    n_time = len(times)
    print(f"NetCDF dimensions: {n_sta} stations × {n_time} time steps")

    sta_idx = {s: i for i, s in enumerate(stations)}
    time_idx = {t: i for i, t in enumerate(times)}

    tmax_arr = np.full((n_sta, n_time), np.nan, dtype=np.float32)
    tmin_arr = np.full((n_sta, n_time), np.nan, dtype=np.float32)

    for row in df.itertuples(index=False):
        i = sta_idx[row.station_id]
        j = time_idx[row.time]
        tmax_arr[i, j] = row.tmax_offset_c
        tmin_arr[i, j] = row.tmin_offset_c

    ds = xr.Dataset(
        {
            "tmax_offset": xr.DataArray(
                tmax_arr,
                dims=["station", "time"],
                attrs={
                    "long_name": "TMAX monthly adjustment offset (FLs.52j minus raw)",
                    "units": "degC",
                    "description": (
                        "Monthly station-level TMAX offset computed as "
                        "North American FLs.52j minus raw. NaN where either "
                        "value is missing."
                    ),
                },
            ),
            "tmin_offset": xr.DataArray(
                tmin_arr,
                dims=["station", "time"],
                attrs={
                    "long_name": "TMIN monthly adjustment offset (FLs.52j minus raw)",
                    "units": "degC",
                    "description": (
                        "Monthly station-level TMIN offset computed as "
                        "North American FLs.52j minus raw. NaN where either "
                        "value is missing."
                    ),
                },
            ),
        },
        coords={
            "station_id": xr.DataArray(
                stations,
                dims=["station"],
                attrs={"long_name": "Station identifier"},
            ),
            "time": xr.DataArray(
                times,
                dims=["time"],
                attrs={"long_name": "Year-month (first of month)"},
            ),
        },
        attrs={
            "title": "North American Dataset monthly temperature adjustment offsets",
            "source": "NOAA/NCEI North American Dataset (https://www.ncei.noaa.gov/data/north-american-dataset/access/)",
            "description": (
                "offset = FLs.52j - raw for TMAX and TMIN. "
                "These offsets can be applied to GHCN-Daily raw observations "
                "to produce monthly-adjusted daily temperatures."
            ),
            "conventions": "CF-1.8",
        },
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(out_path)
    print(f"Wrote {out_path}")
    size_mb = out_path.stat().st_size / 1e6
    print(f"  file size: {size_mb:.1f} MB")

    # Quick sanity check
    n_tmax_valid = int(np.isfinite(tmax_arr).sum())
    n_tmin_valid = int(np.isfinite(tmin_arr).sum())
    print(f"  valid tmax offsets: {n_tmax_valid:,}")
    print(f"  valid tmin offsets: {n_tmin_valid:,}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build monthly offset NetCDF.")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--out", default="data/processed/monthly_offsets.nc")
    args = parser.parse_args()

    df = build_dataframe(Path(args.raw_dir))
    build_netcdf(df, Path(args.out))


if __name__ == "__main__":
    main()
