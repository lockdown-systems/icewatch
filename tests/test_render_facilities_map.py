import pytest
import tempfile
import shutil
from pathlib import Path
from time import sleep

from icewatch.render_facilities_map import (
    get_latest_file,
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
