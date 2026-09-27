#!/usr/bin/env python3
"""
Selecting the most recent facilities snapshot on disk.

Snapshot filenames encode when a file was written, not the date of the data
inside it. The historical backfill wrote fifteen years of snapshots in a single
batch, so ordering by filename or by mtime returns whichever file was generated
most recently rather than the one holding the newest data. Order by the data's
own date instead.
"""

import json
from pathlib import Path


def snapshot_date(path: Path) -> str:
    """
    Return the date of the data in a snapshot as YYYY-MM-DD.

    Args:
        path (Path): Path to a facilities JSON file.

    Returns:
        str: The snapshot's source date, or "" if the file has no usable
            metadata (unreadable, not JSON, or missing both date fields).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            metadata = json.load(f).get("metadata", {})
        date = metadata.get("source_date") or metadata.get("extraction_date") or ""
    except (OSError, ValueError, AttributeError):
        return ""
    return str(date)[:10]


def latest_snapshot(data_dir: Path, pattern: str) -> Path:
    """
    Return the snapshot holding the newest data.

    Searches recursively, since historical snapshots are filed under
    per-year subdirectories while fresh ones land at the top level.

    Files whose metadata carries no usable date sort below every dated file,
    and tie-break on filename.

    Args:
        data_dir (Path): Directory to search, recursively.
        pattern (str): Glob pattern matching the snapshots to consider.

    Returns:
        Path: Path to the snapshot with the newest source date.

    Raises:
        ValueError: If no file under data_dir matches the pattern.
    """
    return max(
        (path for path in data_dir.rglob(pattern) if path.is_file()),
        key=lambda path: (snapshot_date(path), path.name),
    )
