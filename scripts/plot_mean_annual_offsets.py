"""
Plot the mean annual TMAX and TMIN adjustment offsets averaged over all stations.

Usage:
    python scripts/plot_mean_annual_offsets.py \
        --nc data/processed/monthly_offsets.nc \
        --out mean_annual_offsets.png
"""

import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import xarray as xr


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot mean annual adjustment offsets.")
    parser.add_argument("--nc", default="/Volumes/adessler_lab/GHCND/monthly_data/processed/monthly_offsets.nc")
    parser.add_argument("--out", default="mean_annual_offsets.png")
    parser.add_argument(
        "--min-stations", type=int, default=100,
        help="Minimum stations required to plot a year (default: 100)",
    )
    args = parser.parse_args()

    ds = xr.open_dataset(args.nc)

    n_tmax = ds.tmax_offset.count(dim="station").resample(time="YE").mean()
    n_tmin = ds.tmin_offset.count(dim="station").resample(time="YE").mean()

    tmax_ann = ds.tmax_offset.mean(dim="station").resample(time="YE").mean()
    tmin_ann = ds.tmin_offset.mean(dim="station").resample(time="YE").mean()

    years = tmax_ann.time.dt.year.values
    tmax_vals = np.where(n_tmax.values >= args.min_stations, tmax_ann.values, np.nan)
    tmin_vals = np.where(n_tmin.values >= args.min_stations, tmin_ann.values, np.nan)

    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(years, tmax_vals, color="#d62728", lw=1.5, label="TMAX offset")
    ax.plot(years, tmin_vals, color="#1f77b4", lw=1.5, label="TMIN offset")
    ax.axhline(0, color="black", lw=0.7, ls="--", alpha=0.5)

    ax.set_xlabel("Year")
    ax.set_ylabel("Mean offset (°C)")
    ax.set_title(
        "Mean annual temperature adjustment offset (FLs.52j − raw)\n"
        "averaged over all North American stations"
    )
    ax.legend()
    first_valid = years[~np.isnan(tmax_vals)]
    ax.set_xlim(first_valid[0] - 1, years[-1] + 1)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(5))
    ax.grid(True, which="major", alpha=0.3)
    ax.grid(True, which="minor", alpha=0.1)

    ax2 = ax.twinx()
    ax2.fill_between(years, n_tmax.values, alpha=0.08, color="gray", label="Station count")
    ax2.set_ylabel("Stations reporting", color="gray")
    ax2.tick_params(axis="y", labelcolor="gray")
    ax2.set_ylim(0, n_tmax.values.max() * 4)

    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
