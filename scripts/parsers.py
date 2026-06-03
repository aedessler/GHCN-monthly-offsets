"""
Fixed-width parser for North American monthly station files.
"""

import gzip
from typing import Iterator

MISSING = -9999


def parse_northam_line(line: str) -> dict:
    """
    Parse one line of a North American monthly fixed-width file.

    Returns a dict with station_id, year, and a list of 12 monthly records.
    Each monthly record has: value_raw (int), value_c (float|None),
    dmflag, qcflag, dsflag.
    """
    station_id = line[0:11]
    year = int(line[12:16])
    months = []
    for m in range(1, 13):
        start = 16 + (m - 1) * 9
        raw = int(line[start : start + 6])
        dmflag = line[start + 6 : start + 7]
        qcflag = line[start + 7 : start + 8]
        dsflag = line[start + 8 : start + 9]
        value_c = None if raw == MISSING else raw / 100.0
        months.append(
            {
                "month": m,
                "value_raw": raw,
                "value_c": value_c,
                "dmflag": dmflag,
                "qcflag": qcflag,
                "dsflag": dsflag,
            }
        )
    return {"station_id": station_id, "year": year, "months": months}


def iter_northam_file(path: str) -> Iterator[dict]:
    """Yield parsed records from a North American monthly file (plain or gzip)."""
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="ascii", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if len(line) < 16 + 12 * 9:
                continue
            yield parse_northam_line(line)
