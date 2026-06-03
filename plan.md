You are working in this repository. Build a Python pipeline to create a North American monthly-adjusted daily station temperature dataset.

Goal
----
For every station in the NOAA/NCEI North American monthly dataset, compute monthly adjustment offsets from:

    offset = FLs.52j - raw

for TMAX and TMIN separately. Then apply those station-year-month offsets to the corresponding raw GHCN-Daily TMAX and TMIN observations. Derive adjusted daily TAVG from the adjusted TMAX and adjusted TMIN.

This is not a true daily homogenization. It is a monthly-offset daily product. The offset is constant within each station-month.

Primary data sources
--------------------
North American monthly station data:
    https://www.ncei.noaa.gov/data/north-american-dataset/access/

Relevant monthly directories:
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tmax-raw/
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tmax-FLs.52j/
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tmin-raw/
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tmin-FLs.52j/
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tavg-raw/
    https://www.ncei.noaa.gov/data/north-american-dataset/access/tavg-FLs.52j/

North American documentation:
    https://www.ncei.noaa.gov/data/north-american-dataset/documentation/readme.txt
    https://www.ncei.noaa.gov/data/north-american-dataset/documentation/readme.NORTHAMv1.0

GHCN-Daily data:
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/
    data can also be found on disk at /Volumes/adessler_lab/GHCND/

Relevant GHCN-Daily files:
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd_all.tar.gz

Individual daily station files are in:
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/{station_id}.dly

For example:
    https://www.ncei.noaa.gov/pub/data/ghcn/daily/all/USC00026481.dly

Scientific method
-----------------
For each station, year, and month:

    tmax_offset_c = northam_tmax_FLs52j_c - northam_tmax_raw_c
    tmin_offset_c = northam_tmin_FLs52j_c - northam_tmin_raw_c

Then for every daily observation in the same station-year-month:

    tmax_adj_c = ghcnd_tmax_raw_c + tmax_offset_c
    tmin_adj_c = ghcnd_tmin_raw_c + tmin_offset_c
    tavg_adj_c = (tmax_adj_c + tmin_adj_c) / 2

Also keep:

    tmax_raw_c
    tmin_raw_c
    tmax_offset_c
    tmin_offset_c
    tavg_raw_c = (tmax_raw_c + tmin_raw_c) / 2
    date
    station_id
    year
    month
    day
    daily quality flags
    monthly flags from the raw and FLs.52j files
    monthly validation diagnostics

Units
-----
North American monthly temperature values are stored as integer hundredths of degrees C:

    monthly_c = monthly_raw_integer / 100.0

GHCN-Daily TMAX and TMIN values are stored as integer tenths of degrees C:

    daily_c = daily_raw_integer / 10.0

Missing value is:

    -9999

Do not treat -9999 as a real temperature.

Expected file formats
---------------------
North American monthly files are fixed width. Each file is already element-specific, so there is no TMAX/TMIN/TAVG element column in the row.

Use this parser:

    station_id: line[0:11]
    year:       int(line[12:16])

Then for each month m = 1..12:

    start = 16 + (m - 1) * 9

    value:  int(line[start:start+6])
    dmflag: line[start+6:start+7]
    qcflag: line[start+7:start+8]
    dsflag: line[start+8:start+9]

Convert value to deg C by dividing by 100.0 unless value is -9999.

GHCN-Daily .dly files are fixed width. Each line has one station-month-element record.

Use this parser:

    station_id: line[0:11]
    year:       int(line[11:15])
    month:      int(line[15:17])
    element:    line[17:21]

Then for each day d = 1..31:

    start = 21 + (d - 1) * 8

    value: int(line[start:start+5])
    mflag: line[start+5:start+6]
    qflag: line[start+6:start+7]
    sflag: line[start+7:start+8]

Only keep real calendar days for the month. Convert TMAX and TMIN values to deg C by dividing by 10.0 unless value is -9999.

Daily quality-control rule
--------------------------
Default behavior:

    Keep daily TMAX/TMIN values only when qflag is blank.

Add a command-line option:

    --keep-failed-qc

If this option is supplied, keep nonblank daily qflag values but preserve the flags in the output.

Monthly quality-control rule
----------------------------
Compute offsets only when both raw and FLs.52j monthly values are nonmissing.

Preserve the monthly flags:

    raw_dmflag
    raw_qcflag
    raw_dsflag
    fls_dmflag
    fls_qcflag
    fls_dsflag

If the offset is missing, daily adjusted values for that station-year-month should be missing.

Station matching
----------------
Assume first that North American station IDs match GHCN-Daily station IDs directly.

Build a station crosswalk by:

    1. Reading all station IDs from the North American monthly files.
    2. Reading ghcnd-stations.txt.
    3. Reading ghcnd-inventory.txt.
    4. Checking which North American station IDs exist in GHCN-Daily.
    5. Checking which matched stations have both TMAX and TMIN in GHCN-Daily.

Do not use nearest-neighbor matching for production. It is okay to create a diagnostic table of unmatched stations.

Validation diagnostics
----------------------
For every station-year-month, compute raw monthly means from GHCN-Daily:

    daily_tmax_monthly_mean_c = mean(valid daily TMAX)
    daily_tmin_monthly_mean_c = mean(valid daily TMIN)

Then compare these to the North American raw monthly values:

    tmax_raw_daily_minus_monthly_c =
        daily_tmax_monthly_mean_c - northam_tmax_raw_c

    tmin_raw_daily_minus_monthly_c =
        daily_tmin_monthly_mean_c - northam_tmin_raw_c

After applying the adjustment, compute:

    tmax_adjusted_monthly_mean_c = mean(tmax_adj_c)
    tmin_adjusted_monthly_mean_c = mean(tmin_adj_c)

And compare these to the North American FLs.52j values:

    tmax_closure_error_c =
        tmax_adjusted_monthly_mean_c - northam_tmax_FLs52j_c

    tmin_closure_error_c =
        tmin_adjusted_monthly_mean_c - northam_tmin_FLs52j_c

Flag monthly match quality:

    good:
        abs(raw_daily_minus_monthly_c) <= 0.05 C

    questionable:
        0.05 C < abs(raw_daily_minus_monthly_c) <= 0.25 C

    bad:
        abs(raw_daily_minus_monthly_c) > 0.25 C

Use separate flags for TMAX and TMIN.

Output files
------------
Create these outputs:

1. data/processed/monthly_offsets.parquet

Columns:

    station_id
    year
    month
    tmax_raw_monthly_c
    tmax_fls52j_monthly_c
    tmax_offset_c
    tmax_raw_dmflag
    tmax_raw_qcflag
    tmax_raw_dsflag
    tmax_fls_dmflag
    tmax_fls_qcflag
    tmax_fls_dsflag
    tmin_raw_monthly_c
    tmin_fls52j_monthly_c
    tmin_offset_c
    tmin_raw_dmflag
    tmin_raw_qcflag
    tmin_raw_dsflag
    tmin_fls_dmflag
    tmin_fls_qcflag
    tmin_fls_dsflag

2. data/processed/station_crosswalk.parquet

Columns:

    station_id
    lat
    lon
    elev_m
    state
    name
    in_northam
    in_ghcnd_stations
    has_ghcnd_tmax
    has_ghcnd_tmin
    first_year_tmax
    last_year_tmax
    first_year_tmin
    last_year_tmin
    usable_for_daily_adjustment

3. data/processed/daily_adjusted/

Write partitioned Parquet, preferably partitioned by year or station prefix.

Columns:

    station_id
    date
    year
    month
    day
    tmax_raw_c
    tmin_raw_c
    tavg_raw_c
    tmax_offset_c
    tmin_offset_c
    tmax_adj_c
    tmin_adj_c
    tavg_adj_c
    tmax_qflag
    tmin_qflag
    tmax_mflag
    tmin_mflag
    tmax_sflag
    tmin_sflag
    tmax_monthly_match_flag
    tmin_monthly_match_flag

4. data/processed/monthly_validation.parquet

Columns:

    station_id
    year
    month
    n_tmax_days
    n_tmin_days
    daily_tmax_monthly_mean_c
    daily_tmin_monthly_mean_c
    northam_tmax_raw_monthly_c
    northam_tmin_raw_monthly_c
    northam_tmax_fls52j_monthly_c
    northam_tmin_fls52j_monthly_c
    tmax_offset_c
    tmin_offset_c
    tmax_raw_daily_minus_monthly_c
    tmin_raw_daily_minus_monthly_c
    tmax_closure_error_c
    tmin_closure_error_c
    tmax_monthly_match_flag
    tmin_monthly_match_flag

5. reports/summary.md

Include:

    number of North American stations
    number matched to GHCN-Daily
    number with both TMAX and TMIN
    number of station-month offsets generated
    number of adjusted daily rows
    distribution of raw daily-minus-monthly differences
    distribution of closure errors
    count of good/questionable/bad station-months
    examples of unmatched stations
    examples of bad station-months

Code requirements
-----------------
Use Python.

Suggested packages:

    pandas
    numpy
    pyarrow
    requests
    tqdm

Create a clean command-line interface. Example commands:

    python scripts/download_data.py --out data/raw
    python scripts/build_monthly_offsets.py --raw-dir data/raw --out data/processed/monthly_offsets.parquet
    python scripts/build_crosswalk.py --raw-dir data/raw --out data/processed/station_crosswalk.parquet
    python scripts/build_daily_adjusted.py --raw-dir data/raw --processed-dir data/processed
    python scripts/validate_monthly_closure.py --processed-dir data/processed
    python scripts/make_summary_report.py --processed-dir data/processed --out reports/summary.md

Also create:

    README.md
    requirements.txt
    .gitignore
    tests/

Implementation details
----------------------
The download script should:

    1. Download ghcnd-stations.txt.
    2. Download ghcnd-inventory.txt.
    3. Download ghcnd_all.tar.gz or, if a --station-list option is provided, download only individual .dly files from the all/ directory.
    4. Download the latest files from these North American directories:
        tmax-raw
        tmax-FLs.52j
        tmin-raw
        tmin-FLs.52j
        optionally tavg-raw and tavg-FLs.52j for diagnostics.

The North American access directories may contain dated files. Do not hard-code a single filename unless needed. Parse the directory listing and choose the latest matching file. Save the exact downloaded filenames and access time in data/processed/provenance.json.

The daily-adjusted builder should be able to run in two modes:

    --all-stations
    --station-list path/to/stations.txt

For initial testing, use --station-list with 5 to 10 stations.

Do not load all GHCN-Daily data into memory if avoidable. Process station files one at a time, append results to partitioned Parquet, and keep memory bounded.

Testing requirements
--------------------
Write unit tests for:

    1. North American monthly fixed-width parser.
    2. GHCN-Daily .dly fixed-width parser.
    3. Unit conversion.
    4. Missing value handling.
    5. Offset calculation.
    6. Daily adjustment calculation.
    7. Monthly validation/closure calculation.

Use small artificial fixed-width lines in the tests so they run without downloading NOAA data.

Important interpretation
------------------------
Document the product carefully:

    This product applies monthly station-level North American Dataset FLs.52j-minus-raw temperature offsets to GHCN-Daily raw TMAX and TMIN values. The offsets are constant within each station-month. Adjusted daily TAVG is computed from adjusted daily TMAX and TMIN. This product should be viewed as monthly-adjusted daily data, not as an independently homogenized daily dataset.

Now inspect the repository, create the scripts, tests, README, and run the tests. Then run a small sample workflow for a few stations to prove the pipeline works.