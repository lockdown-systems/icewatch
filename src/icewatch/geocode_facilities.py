#!/usr/bin/env python3
"""
Geocode facilities from a JSON file using OpenStreetMap Nominatim, with caching.
"""

import argparse
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import requests

CACHE_FILENAME = "geocode_cache.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "icewatch/1.0 (collective@lockdown.systems)"

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


def build_address(facility: dict) -> str:
    parts = [
        facility.get("Address", ""),
        facility.get("City", ""),
        facility.get("State", ""),
        str(facility.get("Zip", "")),
    ]
    return ", ".join([str(p).strip() for p in parts if p and str(p).strip()])


def geocode_address(
    address: str, session: requests.Session | None = None
) -> dict | None:
    params = {
        "q": address,
        "format": "json",
        "limit": "1",  # set as string to match request param type
    }
    headers = {"User-Agent": USER_AGENT}
    s = session or requests.Session()
    response = s.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
    response.raise_for_status()
    results = response.json()
    if results:
        return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"])}
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Geocode facilities JSON using OpenStreetMap Nominatim with caching."
    )
    parser.add_argument("--input", required=True, help="Input facilities JSON file")
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
    args = parser.parse_args()

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
                result = geocode_address(address, session=session)
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
    print(output_path)

    if updated:
        logger.info(f"Updating geocode cache: {cache_path}")
        save_cache(cache, cache_path)
    else:
        logger.info("No new addresses geocoded; cache unchanged.")

    logger.info("Done.")


if __name__ == "__main__":
    main()
