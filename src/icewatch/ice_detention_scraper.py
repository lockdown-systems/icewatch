#!/usr/bin/env python3
"""
ICE Detention Statistics Scraper and Downloader

This script scrapes the ICE detention management page to find the latest
detention statistics Excel file and downloads it. It can handle dynamic
links that may change over time.

Author: Your Name
Date: 2024
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_valid_date(year: int, month: int, day: int) -> bool:
    """
    Determine if extracted year, month, and day are valid
    """
    try:
        dt = datetime(year=year, month=month, day=day)
        return dt > datetime(year=2025, month=1, day=1)
    except ValueError:
        return False


def extract_date_from_filename(url: str) -> str | None:
    """
    Extract the date from the Excel filename URL.

    Args:
        url (str): URL of the Excel file

    Returns:
        str: Date in YYYY-MM-DD format, or None if not found
    """
    try:
        # Extract filename from URL
        filename = os.path.basename(urlparse(url).path)

        # Look for date patterns in the filename
        # Common patterns: FY25_detentionStats06202025.xlsx, detentionStats06202025.xlsx, etc.

        date_patterns = [
            r"(?P<month>\d{2})(?P<day>\d{2})(?P<year>\d{4})\.xlsx",  # MMDDYYYY
            r"(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\.xlsx",  # YYYYMMDD
            r"(?P<month>\d{2})(?P<day>\d{2})(?P<year>\d{2})\.xlsx",  # MMDDYY
        ]

        for pattern in date_patterns:
            if date_match := re.search(pattern, filename):
                year, month, day = (
                    int(date_match.group("year")),
                    int(date_match.group("month")),
                    int(date_match.group("day")),
                )
                if year < 100:
                    year += 2000
                if is_valid_date(year, month, day):
                    return f"{year}-{month:02}-{day:02}"

        logger.warning(f"Could not extract date from filename: {filename}")
        return None

    except Exception as e:
        logger.error(f"Error extracting date from filename: {e}")
        return None


def find_detention_stats_link(
    base_url: str = "https://www.ice.gov/detain/detention-management",
) -> str | None:
    """
    Scrape the ICE detention management page to find the latest statistics download link.

    Args:
        base_url (str): URL of the ICE detention management page.

    Returns:
        str: URL of the detention statistics Excel file, or None if not found.
    """

    try:
        logger.info(f"Scraping page: {base_url}")

        # Set up headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Get the page content
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.content, "html.parser")

        # Look for links containing detention statistics keywords
        keywords = [
            "detention",
            "statistics",
            "FY25",
            "YTD",
            "xlsx",
            "excel",
            "detentionStats",
            "FY2025",
        ]

        class RelevantLink(TypedDict):
            url: str
            text: str
            relevance_score: int

        found_links: list[RelevantLink] = []

        # Search for all links on the page
        for link in soup.find_all("a", href=True):
            assert isinstance(link, Tag)  # this pleases mypy
            href = str(link.get("href", "")).lower()
            text = link.get_text().lower()

            # Check if link text or href contains relevant keywords
            is_relevant = any(
                keyword.lower() in href or keyword.lower() in text
                for keyword in keywords
            )

            if is_relevant:
                full_url = urljoin(base_url, str(link["href"]))
                link_text = link.get_text().strip()
                found_links.append(
                    {
                        "url": full_url,
                        "text": link_text,
                        "relevance_score": sum(
                            1
                            for keyword in keywords
                            if keyword.lower() in href or keyword.lower() in text
                        ),
                    }
                )
                logger.info(f"Found potential link: {link_text} -> {full_url}")

        if not found_links:
            logger.warning("No relevant links found on the page")
            return None

        # Sort by relevance score and prefer .xlsx files
        found_links.sort(
            key=lambda x: (x["relevance_score"], ".xlsx" in x["url"].lower()),
            reverse=True,
        )

        # Return the most relevant link
        best_match = found_links[0]
        logger.info(f"Selected best match: {best_match['text']} -> {best_match['url']}")

        return best_match["url"]

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to scrape page: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while scraping: {e}")
        return None


def download_ice_detention_stats(
    url: str | None = None,
    output_dir: str = "data",
    auto_find_link: bool = True,
) -> tuple[str | None, str | None]:
    """
    Download ICE detention statistics Excel file.

    Args:
        url (str, optional): Direct URL to the Excel file. If None, auto-finds the latest link.
        output_dir (str): Directory to save the downloaded file.
        auto_find_link (bool): Whether to automatically find the latest link from the website (default: True).

    Returns:
        tuple: (filepath, source_date) where filepath is the path to the downloaded file and source_date is the extracted date, or (None, None) if download failed.
    """

    # Auto-find the latest link by default
    if auto_find_link:
        logger.info("Auto-finding latest detention statistics link...")
        found_url = find_detention_stats_link()
        if found_url:
            url = found_url
            logger.info(f"Found latest URL: {url}")
        else:
            logger.warning("Could not find latest link, using default URL")
            if url is None:
                url = "https://www.ice.gov/doclib/detention/FY25_detentionStats06202025.xlsx"
    elif url is None:
        # Fallback to default URL if auto-find is disabled and no URL provided
        url = "https://www.ice.gov/doclib/detention/FY25_detentionStats06202025.xlsx"

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Extract date from the URL filename
    source_date = extract_date_from_filename(url)

    # Use original filename from URL, or generate one with timestamp
    original_filename = os.path.basename(urlparse(url).path)
    if original_filename and original_filename.endswith(".xlsx"):
        filename = original_filename
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ice_detention_stats_{timestamp}.xlsx"

    filepath = os.path.join(output_dir, filename)

    try:
        logger.info(f"Starting download from: {url}")

        # Set up headers to mimic a browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,application/octet-stream",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # Download the file
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        # Check if the response contains Excel content
        content_type = response.headers.get("content-type", "").lower()
        if (
            "excel" not in content_type
            and "spreadsheet" not in content_type
            and "octet-stream" not in content_type
        ):
            logger.warning(f"Unexpected content type: {content_type}")

        # Get file size
        file_size = int(response.headers.get("content-length", 0))
        logger.info(f"File size: {file_size / 1024:.1f} KB")

        # Save the file
        with open(filepath, "wb") as f:
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # Log progress for large files
                    if (
                        file_size > 0 and downloaded_size % (1024 * 1024) == 0
                    ):  # Every MB
                        progress = (downloaded_size / file_size) * 100
                        logger.info(f"Download progress: {progress:.1f}%")

        logger.info("Download completed successfully!")
        logger.info(f"File saved to: {filepath}")
        logger.info(f"File size: {os.path.getsize(filepath) / 1024:.1f} KB")
        if source_date:
            logger.info(f"Source date extracted: {source_date}")

        return filepath, source_date

    except requests.exceptions.RequestException as e:
        logger.error(f"Download failed: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None, None


def extract_facilities_data(filepath, source_date=None):
    """
    Extract facilities data from the "Facilities FY25" tab and convert to JSON.

    Args:
        filepath (str): Path to the downloaded Excel file.
        source_date (str, optional): Source date from the Excel filename.

    Returns:
        dict: Dictionary containing the facilities data, or None if extraction failed.
    """
    try:
        import pandas as pd

        # Read the "Facilities FY25" sheet, starting from row 7 (index 6)
        df = pd.read_excel(filepath, sheet_name="Facilities FY25", header=6)
        # Expected column names
        expected_columns = [
            "Name",
            "Address",
            "City",
            "State",
            "Zip",
            "Male Crim",
            "Male Non-Crim",
            "Female Crim",
            "Female Non-Crim",
            "ICE Threat Level 1",
            "ICE Threat Level 2",
            "ICE Threat Level 3",
            "No ICE Threat Level",
        ]

        # Check if we have the expected columns
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"Missing expected columns: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")

        # Clean the data
        # Remove rows where all values are NaN
        df = df.dropna(how="all")

        # Convert to list of dictionaries
        facilities_data = []
        for index, row in df.iterrows():
            facility = {}
            for col in expected_columns:
                if col in df.columns:
                    value = row[col]
                    # Convert NaN to None for JSON serialization
                    if pd.isna(value):
                        facility[col] = None
                    else:
                        facility[col] = value
                else:
                    facility[col] = None
            facilities_data.append(facility)

        logger.info(f"Extracted {len(facilities_data)} facilities from the Excel file")

        metadata = {
            "source_file": filepath,
            "extraction_date": source_date,
            "last_checked_date": datetime.now().isoformat(),
            "total_facilities": len(facilities_data),
        }

        if source_date:
            metadata["source_date"] = source_date

        return {"metadata": metadata, "facilities": facilities_data}

    except Exception as e:
        logger.error(f"Failed to extract facilities data: {e}")
        return None


def save_facilities_json(data, output_dir="data"):
    """
    Save facilities data to a JSON file.

    Args:
        data (dict): Facilities data dictionary.
        output_dir (str): Directory to save the JSON file.

    Returns:
        str: Path to the saved JSON file, or None if save failed.
    """
    try:
        import json

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ice_facilities_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        # Save to JSON file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Facilities data saved to: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save facilities JSON: {e}")
        return None


def verify_download(filepath):
    """
    Verify that the downloaded file is a valid Excel file.

    Args:
        filepath (str): Path to the downloaded file.

    Returns:
        bool: True if file is valid, False otherwise.
    """
    try:
        import pandas as pd

        # Try to read the Excel file
        df = pd.read_excel(filepath, sheet_name=None)

        # Log information about the sheets
        logger.info(f"Excel file contains {len(df)} sheets:")
        for sheet_name in df.keys():
            sheet_info = df[sheet_name]
            logger.info(
                f"  - {sheet_name}: {len(sheet_info)} rows, {len(sheet_info.columns)} columns"
            )

        return True

    except Exception as e:
        logger.error(f"File verification failed: {e}")
        return False


def main():
    """Main function to run the scraper and downloader."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download ICE detention statistics Excel file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ice_detention_scraper.py
  python ice_detention_scraper.py --output-dir ./data --verify
  python ice_detention_scraper.py --url "https://custom-url.xlsx"
  python ice_detention_scraper.py --no-auto-find
  python ice_detention_scraper.py --extract-json
  python ice_detention_scraper.py --extract-from-file "path/to/existing/excel.xlsx"
        """,
    )

    parser.add_argument(
        "--url", help="Direct URL to the Excel file (optional)", default=None
    )

    parser.add_argument(
        "--output-dir",
        help="Directory to save the downloaded file (default: data)",
        default="data",
    )

    parser.add_argument(
        "--no-auto-find",
        action="store_true",
        help="Disable auto-finding the latest link (use default URL instead)",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the downloaded file by attempting to read it",
    )

    parser.add_argument(
        "--extract-json",
        action="store_true",
        help="Extract facilities data to JSON file after downloading",
    )

    parser.add_argument(
        "--extract-from-file",
        help="Extract facilities data to JSON from an existing Excel file",
    )

    args = parser.parse_args()

    logger.info("ICE Detention Statistics Scraper and Downloader")
    logger.info("=" * 50)

    # Handle extraction from existing file
    if args.extract_from_file:
        logger.info(
            f"Extracting facilities data from existing file: {args.extract_from_file}"
        )
        if not os.path.exists(args.extract_from_file):
            logger.error(f"File not found: {args.extract_from_file}")
            sys.exit(1)

        # Extract date from the filename
        source_date = extract_date_from_filename(args.extract_from_file)
        if facilities_data := extract_facilities_data(
            args.extract_from_file, source_date
        ):
            json_filepath = save_facilities_json(facilities_data, args.output_dir)
            if json_filepath:
                logger.info("JSON extraction completed successfully!")
                return
            else:
                logger.error("Failed to save JSON file!")
                sys.exit(1)
        else:
            logger.error("Failed to extract facilities data!")
            sys.exit(1)

    # Download the file
    result = download_ice_detention_stats(
        url=args.url, output_dir=args.output_dir, auto_find_link=not args.no_auto_find
    )

    if result[0]:  # filepath is not None
        filepath, source_date = result
        logger.info("Download completed successfully!")

        # Verify the file if requested
        if args.verify:
            logger.info("Verifying downloaded file...")
            if verify_download(filepath):
                logger.info("File verification successful!")
            else:
                logger.error("File verification failed!")
                sys.exit(1)

        # Extract JSON if requested
        if args.extract_json:
            logger.info("Extracting facilities data to JSON...")
            facilities_data = extract_facilities_data(filepath, source_date)
            if facilities_data:
                json_filepath = save_facilities_json(facilities_data, args.output_dir)
                if json_filepath:
                    logger.info("JSON extraction completed successfully!")
                else:
                    logger.error("Failed to save JSON file!")
                    sys.exit(1)
            else:
                logger.error("Failed to extract facilities data!")
                sys.exit(1)
    else:
        logger.error("Download failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
