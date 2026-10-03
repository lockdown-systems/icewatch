import json
import pytest
import tempfile
import shutil
from pathlib import Path
from time import sleep

from icewatch.render_facilities_map import (
    Facility,
    Metadata,
    get_latest_file,
    load_facilities,
    save_facilities,
    timeline_to_js,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    data_dir = tempfile.mkdtemp()
    yield Path(data_dir)
    shutil.rmtree(data_dir)


def test_empty_directory(temp_data_dir: Path):
    """Test that get_latest_file raises error when no files are found."""
    with pytest.raises(RuntimeError, match="No geocoded facilites found"):
        _ = get_latest_file(temp_data_dir)


@pytest.mark.parametrize(
    "files,expected",
    [
        (
            [
                "facilities_geocoded_20250101.json",
                "facilities_geocoded_20250201.json",
                "facilities_geocoded_20250301.json",
            ],
            "facilities_geocoded_20250301.json",
        ),
        (
            [
                "facilities_geocoded_20250301.json",
                "facilities_geocoded_20250201.json",
                "facilities_geocoded_20250101.json",
            ],
            "facilities_geocoded_20250301.json",
        ),
    ],
)
def test_get_latest_file_ordered_creation(
    temp_data_dir: Path, files: list[str], expected: str
):
    """Test files with different ordered creation timestamps."""
    for filename in files:
        sleep(0.1)
        (temp_data_dir / filename).touch()

    result = get_latest_file(temp_data_dir)
    assert result.name == expected


def _write_snapshot(path: Path, source_date: str | None = None) -> None:
    """Write a minimal geocoded snapshot, optionally carrying a source date."""
    metadata: dict[str, object] = {"total_facilities": 0}
    if source_date is not None:
        metadata["source_date"] = source_date
    path.write_text(json.dumps({"metadata": metadata, "facilities": []}))


def test_get_latest_file_prefers_source_date_over_filename(temp_data_dir: Path):
    """The newest data wins even when another file was generated later.

    Filenames record when a file was written. The historical backfill wrote
    fifteen years of old snapshots in one batch, so the latest filename here
    holds the oldest data.
    """
    _write_snapshot(
        temp_data_dir / "facilities_geocoded_20260619_201903.json", "2025-07-24"
    )
    _write_snapshot(
        temp_data_dir / "facilities_geocoded_20260503_092548.json", "2026-04-09"
    )

    result = get_latest_file(temp_data_dir)
    assert result.name == "facilities_geocoded_20260503_092548.json"


def test_get_latest_file_ranks_dated_above_undated(temp_data_dir: Path):
    """A snapshot with no usable date loses to one that has a date."""
    (temp_data_dir / "facilities_geocoded_20250717_110750.json").touch()
    _write_snapshot(temp_data_dir / "facilities_geocoded_20250704.json", "2025-07-04")

    result = get_latest_file(temp_data_dir)
    assert result.name == "facilities_geocoded_20250704.json"


def test_save_facilities_round_trip(temp_data_dir: Path):
    """save_facilities writes a file that load_facilities reads back unchanged.

    Guards the --update-last-checked write-back: it rewrites the source
    snapshot in place, so it must not drop metadata keys or coerce a
    zero-padded zip into a number.
    """
    path = temp_data_dir / "facilities_geocoded_20260101.json"
    metadata: Metadata = {
        "source_file": "data/xlsx/2026/FY26_detentionStats01012026.xlsx",
        "extraction_date": "2026-01-01",
        "last_checked_date": "2026-01-01T12:00:00",
        "total_facilities": 1,
        "source_date": "2026-01-01",
    }
    facility: Facility = {
        "Name": "BERLIN FED. CORR. INST.",
        "Address": "1 SUCCESS LOOP DR.",
        "City": "BERLIN",
        "State": "NH",
        "Zip": "03570",
        "Male Crim": 21.0,
        "Male Non-Crim": 61.0,
        "Female Crim": 0.0,
        "Female Non-Crim": 0.0,
        "ICE Threat Level 1": 1.0,
        "ICE Threat Level 2": 2.0,
        "ICE Threat Level 3": 3.0,
        "No ICE Threat Level": 4.0,
        "latitude": 44.52160410997109,
        "longitude": -71.15084393084551,
    }

    save_facilities(path, [facility], metadata)
    loaded_facilities, loaded_metadata = load_facilities(path)

    assert loaded_metadata == metadata
    assert loaded_facilities == [facility]
    # The leading zero must survive as a string, not become 3570.
    assert loaded_facilities[0]["Zip"] == "03570"


def test_timeline_to_js_round_trips_one_line_per_facility():
    """Output parses back to the same data, with each facility on its own line.

    The timeline is embedded in the page, so a single-line blob makes every
    re-render an unreviewable multi-megabyte diff.
    """
    timeline = {
        "2026-04-09": [{"name": "A", "lat": 1.0}, {"name": "B", "lat": 2.0}],
        "2021-01-01": [{"name": "C", "lat": 3.0}],
        "2025-01-01": [],
    }
    out = timeline_to_js(timeline)

    assert json.loads(out) == timeline
    # One line per facility, plus a line for each snapshot's open and close.
    assert sum(1 for line in out.splitlines() if line.startswith('{"name"')) == 3
    # Dates in order, so repeated renders of the same data are byte-identical.
    assert list(json.loads(out)) == ["2021-01-01", "2025-01-01", "2026-04-09"]
    assert timeline_to_js(timeline) == out
