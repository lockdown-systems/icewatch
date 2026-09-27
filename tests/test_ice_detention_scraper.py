import pytest

from icewatch.ice_detention_scraper import date_from_filename, pick_facilities_sheet


@pytest.mark.parametrize(
    "sheet_names,expected",
    [
        # The workbook ICE publishes today.
        (
            ["Facilities FY26", "Facilities FY25", "Segregation", "Notes"],
            "Facilities FY26",
        ),
        # The next fiscal year must be picked up without a code change.
        (["Facilities FY26", "Facilities FY27"], "Facilities FY27"),
        # Fiscal years are ordered numerically, not lexically: FY9 < FY26.
        (["Facilities FY9", "Facilities FY26"], "Facilities FY26"),
        # Four-digit spelling, and whitespace pandas preserves from the file.
        (["  Facilities FY2026  "], "  Facilities FY2026  "),
        # A single historical sheet is still the newest one present.
        (["Facilities FY21", "Notes"], "Facilities FY21"),
        # 2021-era workbooks qualify the sheet name.
        (
            ["Header", "Detention FY21 YTD", "Facilities FY21 YTD", "Footnotes"],
            "Facilities FY21 YTD",
        ),
    ],
)
def test_pick_facilities_sheet(sheet_names: list[int | str], expected: str):
    """The highest fiscal year present wins, spelled as the workbook spells it."""
    assert pick_facilities_sheet(sheet_names) == expected


@pytest.mark.parametrize(
    "sheet_names",
    [
        [],
        ["Segregation", "Notes"],
        ["Facilities"],
        ["Detention FY26"],
    ],
)
def test_pick_facilities_sheet_no_match(sheet_names: list[int | str]):
    """No facilities sheet returns None so the caller can report the workbook."""
    assert pick_facilities_sheet(sheet_names) is None


@pytest.mark.parametrize(
    "filename,expected",
    [
        # MMDDYYYY, the convention in ICE's published filenames.
        ("data/xlsx/2025-2026/FY26_detentionStats_04092026.xlsx", "2026-04-09"),
        ("FY25_detentionStats06252025.xlsx", "2025-06-25"),
        ("FY21-detentionstats02012021.xlsx", "2021-02-01"),
        # YYYYMMDD, used by files we named ourselves on download.
        ("data/ice_detention_stats_20250704_160809.xlsx", "2025-07-04"),
        # Unparseable as MMDDYYYY (month 20), so read as YYYYMMDD.
        ("stats_20260115.xlsx", "2026-01-15"),
        # No eight-digit run, and eight digits that are not a date.
        ("detentionStats.xlsx", None),
        ("stats_99999999.xlsx", None),
    ],
)
def test_date_from_filename(filename: str, expected: str | None):
    """The publication date comes from the filename, in either digit order."""
    assert date_from_filename(filename) == expected
