"""
Unit tests for the North American monthly parser, unit conversion,
missing value handling, and offset calculation.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from parsers import parse_northam_line, MISSING


def _make_northam_line(station_id: str, year: int, months: list[tuple]) -> str:
    """
    Build a synthetic North American fixed-width line.
    months: list of 12 tuples (value_int, dmflag, qcflag, dsflag)
    """
    line = f"{station_id:<11} {year:4d}"
    for val, dm, qc, ds in months:
        line += f"{val:6d}{dm}{qc}{ds}"
    return line


class TestNorthamParser:
    def test_basic_parse(self):
        months = [(2150, " ", " ", "S")] * 12
        line = _make_northam_line("USC00026481", 1990, months)
        rec = parse_northam_line(line)
        assert rec["station_id"] == "USC00026481"
        assert rec["year"] == 1990
        assert len(rec["months"]) == 12
        assert rec["months"][0]["value_raw"] == 2150
        assert abs(rec["months"][0]["value_c"] - 21.50) < 1e-6
        assert rec["months"][0]["dmflag"] == " "
        assert rec["months"][0]["dsflag"] == "S"
        assert rec["months"][0]["month"] == 1

    def test_missing_value(self):
        months = [(-9999, " ", " ", " ")] * 12
        line = _make_northam_line("USC00026481", 2000, months)
        rec = parse_northam_line(line)
        assert rec["months"][0]["value_c"] is None
        assert rec["months"][0]["value_raw"] == MISSING

    def test_negative_temperature(self):
        months = [(-1500, " ", " ", " ")] + [(0, " ", " ", " ")] * 11
        line = _make_northam_line("CA001010160", 1961, months)
        rec = parse_northam_line(line)
        assert abs(rec["months"][0]["value_c"] - (-15.00)) < 1e-6

    def test_month_indices(self):
        months = [(i * 100, " ", " ", " ") for i in range(12)]
        line = _make_northam_line("USW00094728", 2010, months)
        rec = parse_northam_line(line)
        for m in rec["months"]:
            expected = (m["month"] - 1) * 100 / 100.0
            assert abs(m["value_c"] - expected) < 1e-6

    def test_flags_preserved(self):
        months = [(1000, "E", "I", "0")] + [(0, " ", " ", " ")] * 11
        line = _make_northam_line("USC00012345", 1985, months)
        rec = parse_northam_line(line)
        assert rec["months"][0]["dmflag"] == "E"
        assert rec["months"][0]["qcflag"] == "I"
        assert rec["months"][0]["dsflag"] == "0"

    def test_real_format(self):
        # Actual line format from the North American dataset
        line = "USC00010063 2001 -9999    -9999    -9999     2267     2680     2914a    3150a    3080c    2651     2170b    2145d    1431c  "
        rec = parse_northam_line(line)
        assert rec["station_id"] == "USC00010063"
        assert rec["year"] == 2001
        assert rec["months"][0]["value_c"] is None   # Jan: -9999
        assert abs(rec["months"][3]["value_c"] - 22.67) < 1e-4  # Apr: 2267
        assert rec["months"][5]["dmflag"] == "a"     # Jun flagged


class TestUnitConversion:
    def test_northam_to_celsius(self):
        assert abs(2150 / 100.0 - 21.5) < 1e-9
        assert abs(-150 / 100.0 - (-1.5)) < 1e-9

    def test_missing_not_converted(self):
        raw = MISSING
        value_c = None if raw == MISSING else raw / 100.0
        assert value_c is None


class TestMissingValues:
    def test_all_missing(self):
        months = [(-9999, " ", " ", " ")] * 12
        line = _make_northam_line("USC00026481", 2000, months)
        rec = parse_northam_line(line)
        for m in rec["months"]:
            assert m["value_c"] is None


class TestOffsetCalculation:
    def test_basic_offset(self):
        raw_c, fls_c = 21.50, 21.75
        assert abs((fls_c - raw_c) - 0.25) < 1e-9

    def test_negative_offset(self):
        raw_c, fls_c = 10.00, 9.80
        assert abs((fls_c - raw_c) - (-0.20)) < 1e-9

    def test_zero_offset(self):
        assert (15.00 - 15.00) == 0.0

    def test_offset_missing_when_raw_missing(self):
        raw_c, fls_c = None, 20.0
        offset = fls_c - raw_c if (raw_c is not None and fls_c is not None) else None
        assert offset is None

    def test_offset_missing_when_fls_missing(self):
        raw_c, fls_c = 20.0, None
        offset = fls_c - raw_c if (raw_c is not None and fls_c is not None) else None
        assert offset is None
