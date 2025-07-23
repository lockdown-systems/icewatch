# ICE Detention Map

A Python-based dashboard for ICE detention statistics. This project downloads and renders publically available detention data from the [ICE Detention Management page](https://www.ice.gov/detain/detention-management).

## Overview

This project consists of three Python scripts:

1. **`ice_detention_scraper.py`** - Downloads ICE detention Excel files and parses the facilities data, outputting a JSON file
2. **`geocode_facilities.py`** - Geocodes the facilities data using the JSON file from the previous step
3. **`render_facilties_map.py`** - Simple script that renders a single page static site

## Installation

1. Install using pip

```bash
pip install git+https://github.com/lockdown-systems/icewatch.git@main
```

## Usage

### Step 1: ICE Detention Scraper

Download the latest detention statistics (this should auto-find the latest link):

```bash
icewatch scrape
```

Then, extract the data about facilities to a JSON file (you can also do this in one step, see options below):

```bash
icewatch scrape --extract-from-file data/YOUR_FILE_HERE.xlsx
```

#### Command Line Options

The script supports the following options:

- `--url`: Direct URL to the Excel file (optional, auto-finds by default)
- `--output-dir`: Directory to save the downloaded file (default: data)
- `--verify`: Verify the downloaded file by attempting to read it
- `--no-auto-find`: Disable auto-finding the latest link (use default URL instead)
- `--extract-json`: Extract facilities data to JSON file after downloading
- `--extract-from-file`: Extract facilities data to JSON from an existing Excel file

#### Examples

```bash
# Download to a custom directory
icewatch scrape --output-dir ./data

# Download and verify the file
icewatch scrape --verify

# Use a specific URL instead of auto-finding
icewatch scrape --url "https://custom-url.xlsx"

# Download to current directory
icewatch scrape --output-dir .

# Disable auto-find and use default URL
icewatch scrape --no-auto-find

# Download and extract facilities data to JSON
icewatch scrape --extract-json

# Extract JSON from an existing Excel file
icewatch scrape --extract-from-file "path/to/existing/file.xlsx"
```

### Step 2: Geocode ICE facilities

You can geocode the facilities in your JSON file using OpenStreetMap Nominatim API. This will add latitude and longitude to each facility and stores address lookups in a cache file to avoid unnecessary API requests. If the OpenStreetMap API doesn't provide a result for a specific facility, you can enter it in the cache file manually once you locate the latitude and longitude.

### Usage

```bash
icewatch geocode --input data/ice_facilities_YYYYMMDD.json
```

- By default, this will create a new file like `data/facilities_geocoded_YYYYMMDD_HHMMSS.json` and update (or create) `data/geocode_cache.json` in the same directory.
- You can specify custom output or cache files with `--output` and `--cache`.
- You can adjust the delay between API requests (default: 2 seconds) with `--delay`.

### Example

```bash
icewatch geocode --input data/ice_facilities_YYYYMMDD.json --output data/facilities_geocoded_YYYYMMDD.json --cache data/geocode_cache.json
```

### User-Agent Requirement

**You must set a valid User-Agent string in the script before running it.**

Edit the `USER_AGENT` variable in `geocode_facilities.py`:

```python
USER_AGENT = "icewatch/1.0 (your_email@example.com)"
```

Replace `your_email@example.com` with your actual email or project contact. This is required by the [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/).

### Step 3: Rendering and Viewing the Facilities Map

You can create a static interactive map of all geocoded facilities using the provided script. The map will show each facility as a marker, with popups displaying the name, address, and rounded counts of criminal and non-criminal detainees.

#### Usage

```bash
icewatch render --input data/facilities_geocoded_YYYYMMDD.json
```

- By default, this will create `docs/index.html` (and the `docs` directory if it doesn't exist).
- You can specify a custom output path with `--output` if desired.

## Development

### Install `uv`

`icewatch` uses [uv](https://astral.sh/uv/) as its project manager. Please install using the official [installer](https://docs.astral.sh/uv/#installation):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify your installation by running:

```bash
uv --version
```

### Clone repository

Clone the `icewatch` repo:

```bash
git clone https://github.com/lockdown-systems/icewatch.git
cd icewatch
```

If you have the [gh](https://github.com/cli/cli) command line tool installed, clone the repo with the following command:

```bash
gh repo clone lockdown-systems/icewatch
cd icewatch
```

### Setup virtual environment

In your cloned repository,set up your Python virtual environment with all development dependencies:

```bash
# Create project virtual environment with all dependencies
uv sync --dev

# Source the newly created virtual environment
source .venv/bin/activate
```

Verify that your environment was set up correctly by running `icewatch` with `uv`:

```bash
uv run icewatch --help
```

### Setup pre-commit git hooks (Optional)

This step is optional and runs the same checks on your local codebase that run on every PR.

Install [pre-commit](https://github.com/pre-commit/pre-commit):

```bash
# Install pre-commit globally using pre-commit
uv tool install pre-commit

# Install git hooks for your local repository
pre-commit install
```

Verify that `pre-commit` git hooks were set up correctly by running them manually:

```bash
pre-commit run --all-files
```

## Disclaimer

This tool is for educational and research purposes. Please ensure compliance with the ICE website's terms of service and respect rate limiting.
