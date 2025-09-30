#!/usr/bin/env python3
"""
Render a static HTML map of facilities using Leaflet.js.
Popups show name, address, rounded criminal/non-criminal counts, and ICE Threat Level.
"""

import argparse
import json
import os
import webbrowser
from datetime import datetime
from math import isnan
from pathlib import Path
from typing import Any, TypedDict
from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader("icewatch"))
template = env.get_template("map.html")


class Metadata(TypedDict):
    source_file: str
    extraction_date: str
    last_checked_date: str
    total_facilities: int


Facility = TypedDict(
    "Facility",
    {
        "Name": str,
        "Address": str,
        "City": str,
        "Zip": str,
        "State": str,
        "Male Crim": float,
        "Male Non-Crim": float,
        "Female Crim": float,
        "Female Non-Crim": float,
        "ICE Threat Level 1": float,
        "ICE Threat Level 2": float,
        "ICE Threat Level 3": float,
        "No ICE Threat Level": float,
        "latitude": float,
        "longitude": float,
    },
)


def get_latest_file(data_dir: Path) -> Path:
    try:
        return max(data_dir.glob("facilities_geocoded*.json"))
    except ValueError:
        raise RuntimeError("No geocoded facilites found")


def load_facilities(path: Path | str) -> tuple[list[Facility], Metadata]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    facilities = data.get("facilities", [])
    metadata = data.get("metadata", {})
    return facilities, metadata


def safe_int(val: Any) -> int:
    try:
        if val is None or (isinstance(val, float) and isnan(val)):
            return 0
        return int(round(float(val)))
    except Exception:
        return 0


def facility_to_embedded_js(facility: Facility) -> str:
    embedded_json = {
        "name": facility.get("Name"),
        "addr": facility.get("Address"),
        "city": facility.get("City"),
        "state": facility.get("State"),
        "zipc": facility.get("Zip"),
        "lat": facility.get("latitude"),
        "lon": facility.get("longitude"),
        "criminals": safe_int(facility.get("Male Crim"))
        + safe_int(facility.get("Female Crim")),
        "noncriminals": safe_int(facility.get("Male Non-Crim"))
        + safe_int(facility.get("Female Non-Crim")),
        "threatLevels": [
            safe_int(facility.get(level))
            for level in (
                "No ICE Threat Level",
                "ICE Threat Level 1",
                "ICE Threat Level 2",
                "ICE Threat Level 3",
            )
        ],
    }
    return json.dumps(embedded_json)


def render_html(
    facilities: list[Facility],
    output_path: Path | str,
    metadata: Metadata | None = None,
):
    # Calculate totals
    total_criminals = 0
    total_noncriminals = 0
    for fac in facilities:
        total_criminals += safe_int(fac.get("Male Crim")) + safe_int(
            fac.get("Female Crim")
        )
        total_noncriminals += safe_int(fac.get("Male Non-Crim")) + safe_int(
            fac.get("Female Non-Crim")
        )
    total_people = total_criminals + total_noncriminals
    if total_people > 0:
        pct_noncriminal = f"{round(100 * total_noncriminals / total_people)}%"
    else:
        pct_noncriminal = "N/A"

    # Get dates from metadata
    extraction_date = None
    last_checked_date = None
    if metadata:
        extraction_date = metadata.get("extraction_date")
        last_checked_date = metadata.get("last_checked_date")

    formatted_date = datetime.now().strftime("%Y-%m-%d")
    if last_checked_date:
        # Format extraction date nicely (remove time if present)
        try:
            parsed_date = datetime.fromisoformat(
                last_checked_date.replace("Z", "+00:00")
            )
            formatted_date = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = last_checked_date.split("T")[
                0
            ]  # Fallback to just the date part

    html = template.render(
        total_people=total_people,
        pct_noncriminal=pct_noncriminal,
        formatted_date=formatted_date,
        extraction_date=extraction_date,
        facilities=[facility_to_embedded_js(facility) for facility in facilities],
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Map written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Render a static HTML map of facilities."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--input",
        type=Path,
        help="Input geocoded facilities JSON file",
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Latest geocoded facilities JSON file",
    )
    parser.add_argument("--output", help="Output HTML file (default: docs/index.html)")
    parser.add_argument("--web", help="Open HTML file in browser", action="store_true")
    parser.add_argument(
        "--update-last-checked",
        help="Update 'last checked' date to today",
        action="store_true",
    )
    args = parser.parse_args()
    if args.latest:
        data_dir = Path("data")
        assert data_dir.exists()
        input_path = get_latest_file(data_dir)
    else:
        input_path = Path(args.input)
    if args.output:
        output_path = args.output
    else:
        output_path = Path("docs/index.html")
    # Ensure the output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    facilities, metadata = load_facilities(input_path)
    if args.update_last_checked:
        metadata["last_checked_date"] = datetime.now().isoformat()
    render_html(facilities, output_path, metadata)
    if args.web and not os.getenv("GITHUB_ACTIONS"):
        try:
            webbrowser.open(str(output_path))
        except Exception as e:
            print(f"Unable to open map: {e}")


if __name__ == "__main__":
    main()
