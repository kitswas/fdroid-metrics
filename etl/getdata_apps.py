"""
Download app metrics data from F-Droid HTTP servers
"""

import argparse
import json
import logging
import pathlib
from datetime import datetime

import requests as re

BASE_URL = "https://fdroid.gitlab.io/metrics"
SERVERS = [
    "http01.fdroid.net",
    "http02.fdroid.net",
    "http03.fdroid.net",
    "originserver.f-droid.org",
]
RAW_DATA_DIR = pathlib.Path(__file__).parent / "raw"
SUB_DATA_DIR = RAW_DATA_DIR / "apps"

logger = logging.getLogger(__name__)


def fetch_index(server: str) -> list[str]:
    """Fetch and return the index of available data files for a server."""
    logger.info(f"Fetching index for {server}...")
    index_url = f"{BASE_URL}/{server}/index.json"
    response = re.get(index_url)
    response.raise_for_status()
    index = response.json()
    logger.info(f"Found {len(index)} available files for {server}")
    return index


def filter_files_for_month(index: list[str], year: int, month: int) -> list[str]:
    """Filter files for a specific month and year."""
    month_files = []
    for filename in index:
        try:
            # Parse date from filename (format: YYYY-MM-DD.json)
            date_str = filename.replace(".json", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")

            if file_date.year == year and file_date.month == month:
                month_files.append(filename)
        except ValueError:
            # Skip files that don't match the expected date format
            continue

    return sorted(month_files)


def download_file(server: str, filename: str) -> bool:
    """Download a single data file for a server."""
    url = f"{BASE_URL}/{server}/{filename}"
    server_dir = SUB_DATA_DIR / server
    server_dir.mkdir(parents=True, exist_ok=True)
    filepath = server_dir / filename

    # Check if file already exists
    if filepath.exists():
        logger.debug(f"{server}/{filename} already exists, skipping")
        return True

    try:
        logger.info(f"Downloading {server}/{filename}...")
        response = re.get(url)
        response.raise_for_status()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(response.json(), f, indent=2)

        logger.info(f"✓ {server}/{filename} downloaded successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to download {server}/{filename}: {e}")
        return False


def download_month_data(year: int, month: int) -> None:
    """Download all app metrics data for a specific month from all servers."""
    # Create data directory if it doesn't exist
    SUB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    total_successful = 0
    total_failed = 0

    for server in SERVERS:
        logger.info("=" * 50)
        logger.info(f"Processing {server}")
        logger.info("=" * 50)

        try:
            # Fetch index for this server
            index = fetch_index(server)

            # Filter files for the specified month
            month_files = filter_files_for_month(index, year, month)

            if not month_files:
                logger.info(f"No files found for {server} in {year}-{month:02d}")
                continue

            # Download files for this server
            logger.info(f"Downloading {len(month_files)} files for {server}...")
            successful = 0
            failed = 0

            for filename in month_files:
                if download_file(server, filename):
                    successful += 1
                else:
                    failed += 1

            logger.info(f"{server} download complete:")
            logger.info(f"✓ {successful} files downloaded successfully")
            if failed > 0:
                logger.warning(f"✗ {failed} files failed to download")

            total_successful += successful
            total_failed += failed

        except Exception as e:
            logger.error(f"Failed to process {server}: {e}")
            continue

    logger.info("=" * 50)
    logger.info("OVERALL SUMMARY")
    logger.info("=" * 50)
    logger.info(
        f"✓ {total_successful} files downloaded successfully across all servers"
    )
    if total_failed > 0:
        logger.warning(f"✗ {total_failed} files failed to download")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download FDroid app metrics data for a specific month from HTTP servers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Default to current month
    now = datetime.now()

    parser.add_argument(
        "year", type=int, nargs="?", default=now.year, help="Year to download data for"
    )

    parser.add_argument(
        "month",
        type=int,
        nargs="?",
        default=now.month,
        choices=range(1, 13),
        help="Month to download data for (1-12)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    logger.info(f"Downloading app metrics data for {args.year}-{args.month:02d}")
    download_month_data(args.year, args.month)
