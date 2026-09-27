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
