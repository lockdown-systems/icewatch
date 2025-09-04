#!/usr/bin/env python3
"""
Geocode facilities from a JSON file with caching.
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests

from icewatch.geocode import geocode_address

CACHE_FILENAME = "geocode_cache.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_json(path: Path | str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path | str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_cache(cache_path: Path | str) -> dict:
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_path: Path | str) -> None:
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def get_latest_file(data_dir: Path) -> Path:
    ts, file_path = 0, None
    for facility in data_dir.glob("ice_facilities*.json"):
        created_time = facility.lstat().st_ctime
        if created_time > ts:
            file_path = facility
    if file_path is None:
        raise RuntimeError("No geocoded facilites found")
    return file_path


def build_address(facility: dict) -> str:
    parts = [
        facility.get("Address", ""),
        facility.get("City", ""),
        facility.get("State", ""),
        str(facility.get("Zip", "")),
    ]
    return ", ".join([str(p).strip() for p in parts if p and str(p).strip()])


def main():
    parser = argparse.ArgumentParser(
        description="Geocode facilities JSON using OpenStreetMap Nominatim with caching."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--latest",
        action="store_true",
        help="Latest facilities JSON file",
    )
    group.add_argument("--input", type=Path, help="Input facilities JSON file")
    parser.add_argument(
        "--output",
        help="Output JSON file (default: facilities_geocoded_TIMESTAMP.json in same dir)",
    )
    parser.add_argument(
        "--cache",
        help="Geocode cache file (default: geocode_cache.json in same dir as input)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2,
        help="Delay between API requests (seconds, default: 2)",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
    )

    args = parser.parse_args()

    if args.quiet:
        logger.disabled = True

    if args.latest:
        data_dir = Path("data")
        try:
            assert data_dir.exists()
        except AssertionError:
            logger.warning(
                "Could not find data directory, please provide --input instead"
            )
        input_path = get_latest_file(data_dir)
    else:
        input_path = Path(args.input)
    output_path = args.output or str(
        input_path.parent
        / f"facilities_geocoded_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    cache_path = args.cache or str(input_path.parent / CACHE_FILENAME)

    logger.info(f"Loading facilities from: {input_path}")
    data = load_json(input_path)
    facilities = data.get("facilities", [])

    logger.info(f"Loading geocode cache from: {cache_path}")
    cache = load_cache(cache_path)

    session = requests.Session()
    updated = False
    for i, facility in enumerate(facilities):
        address = build_address(facility)
        if not address:
            logger.info(
                f"[{i + 1}/{len(facilities)}] No address for facility, skipping."
            )
            facility["latitude"] = None
            facility["longitude"] = None
            continue
        if address in cache and cache[address] is not None:
            result = cache[address]
            logger.info(f"[{i + 1}/{len(facilities)}] Cached: {address} -> {result}")
        else:
            logger.info(f"[{i + 1}/{len(facilities)}] Geocoding: {address}")
            try:
                result = geocode_address(address, logger, session)
                time.sleep(args.delay)
            except Exception as e:
                logger.info(f"    Error geocoding '{address}': {e}")
                result = None
            if result is not None:
                cache[address] = result
                updated = True
            elif address in cache:
                # Remove failed/None result from cache if present
                del cache[address]
        if result:
            facility["latitude"] = result["lat"]
            facility["longitude"] = result["lon"]
        else:
            facility["latitude"] = None
            facility["longitude"] = None

    logger.info(f"Writing geocoded facilities to: {output_path}")
    save_json(data, output_path)

    if updated:
        logger.info(f"Updating geocode cache: {cache_path}")
        save_cache(cache, cache_path)
    else:
        logger.info("No new addresses geocoded; cache unchanged.")

    logger.info("Done.")
    print(output_path)


if __name__ == "__main__":
    main()
