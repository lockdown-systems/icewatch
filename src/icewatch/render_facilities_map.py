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
        "Zip": int,
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


def make_popup(fac: Facility):
    name = fac.get("Name", "Unknown")
    addr = fac.get("Address", "")
    city = fac.get("City", "")
    state = fac.get("State", "")
    zipc = fac.get("Zip", "")
    criminals = safe_int(fac.get("Male Crim")) + safe_int(fac.get("Female Crim"))
    noncriminals = safe_int(fac.get("Male Non-Crim")) + safe_int(
        fac.get("Female Non-Crim")
    )
    total = criminals + noncriminals
    if total > 0:
        pct_criminal = f"{round(100 * criminals / total)}%"
    else:
        pct_criminal = "N/A"
    lines = [
        f"<b>{name}</b>",
        f"{addr}, {city}, {state} {zipc}",
        f"Criminals: <b>{criminals}</b>",
        f"Non-Criminals: <b>{noncriminals}</b>",
        f"Percentage Criminal: <b>{pct_criminal}</b>",
    ]
    # Add ICE Threat Level breakdown if present
    threat_levels = [
        ("ICE Threat Level 1", fac.get("ICE Threat Level 1")),
        ("ICE Threat Level 2", fac.get("ICE Threat Level 2")),
        ("ICE Threat Level 3", fac.get("ICE Threat Level 3")),
        ("No ICE Threat Level", fac.get("No ICE Threat Level")),
    ]
    if any(val is not None for _, val in threat_levels):
        lines.append('<hr style="margin:0.3em 0;">')
        lines.append("<b>ICE Threat Level Breakdown</b>")
        for label, val in threat_levels:
            if val is not None:
                lines.append(f"{label}: <b>{safe_int(val)}</b>")
    return "<br/>".join(lines)


def get_marker_style(total: int) -> tuple[str, int]:
    # Define thresholds for color and size (smaller, semi-transparent)
    if total < 50:
        color = "rgba(76,175,80,0.7)"  # green
        size = 12
    elif total < 200:
        color = "rgba(255,235,59,0.7)"  # yellow
        size = 18
    elif total < 500:
        color = "rgba(255,152,0,0.7)"  # orange
        size = 24
    else:
        color = "rgba(244,67,54,0.7)"  # red
        size = 30
    return color, size


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

    # Center on US
    center_lat, center_lon = 39.8283, -98.5795

    # Build the header stats with last checked date
    header_stats = f'<div class="stat-item"><strong>{total_people:,}</strong> people in ICE detention</div>'
    header_stats += f'<div class="stat-item"><strong>{pct_noncriminal}</strong> without criminal records</div>'
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

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>ICE Detention Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="css/styles.css" />
    <script defer data-domain="watchice.org" src="https://plausible.io/js/script.outbound-links.js"></script>
</head>
<body>
    <header>
        <nav id="header-bar">
            <div id="header-left">
                <div id="header-title">ICE Detention Map</div>
            </div>
            <div id="header-stats">{header_stats}</div>
            <div id="header-nav">
                <a href="index.html" class="active">Map</a>
                <a href="info.html">Info</a>
                <a id="donate-link" href="https://opencollective.com/lockdown-systems" target="_blank" rel="noopener">Donate</a>
            </div>
        </nav>
    </header>
    <main>
        <div id="map"></div>
        <button id="legend-toggle" onclick="toggleLegend()">Show Legend</button>
        <div class="legend" id="legend-box">
            <div style="font-weight:600; margin-bottom:0.5em;">Legend</div>
            <div class="legend-row"><span class="legend-icon" style="background:rgba(76,175,80,0.7);width:12px;height:12px;border-radius:50%;border:2px solid #222;"></span><span class="legend-label">&lt; 50 people</span></div>
            <div class="legend-row"><span class="legend-icon" style="background:rgba(255,235,59,0.7);width:18px;height:18px;border-radius:50%;border:2px solid #222;"></span><span class="legend-label">50–199 people</span></div>
            <div class="legend-row"><span class="legend-icon" style="background:rgba(255,152,0,0.7);width:24px;height:24px;border-radius:50%;border:2px solid #222;"></span><span class="legend-label">200–499 people</span></div>
            <div class="legend-row"><span class="legend-icon" style="background:rgba(244,67,54,0.7);width:30px;height:30px;border-radius:50%;border:2px solid #222;"></span><span class="legend-label">500+ people</span></div>
        </div>
    </main>
    <div id="last-updated">last checked: {formatted_date} | last updated: {extraction_date}</div>
    <a id="logo-link" href="https://lockdown.systems/" target="_blank" rel="noopener">
        <img id="footer-logo" src="img/logo-wide.svg" alt="Lockdown Systems" />
    </a>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    var map = L.map('map').setView([{center_lat}, {center_lon}], 4);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 18,
        attribution: '© OpenStreetMap contributors'
    }}).addTo(map);

    // Legend toggle for mobile
    function toggleLegend() {{
        var legend = document.getElementById('legend-box');
        var btn = document.getElementById('legend-toggle');
        if (legend.style.display === 'none') {{
            legend.style.display = '';
            btn.textContent = 'Hide Legend';
            btn.style.bottom = '100px';
            btn.style.left = 'auto';
            btn.style.right = '30px'; // Position button to the right of legend
        }} else {{
            legend.style.display = 'none';
            btn.textContent = 'Show Legend';
            btn.style.bottom = '30px';
            btn.style.left = '20px';
            btn.style.right = 'auto'; // Return to original left position
        }}
    }}
    // On load, hide legend and show toggle on mobile
    if (window.innerWidth <= 700) {{
        document.getElementById('legend-box').style.display = 'none';
        document.getElementById('legend-toggle').textContent = 'Show Legend';
    }}
    window.addEventListener('resize', function() {{
        if (window.innerWidth <= 700) {{
            document.getElementById('legend-toggle').style.display = 'block';
            document.getElementById('legend-box').style.display = 'none';
            document.getElementById('legend-toggle').textContent = 'Show Legend';
        }} else {{
            document.getElementById('legend-toggle').style.display = 'none';
            document.getElementById('legend-box').style.display = '';
        }}
    }});
    """
    for fac in facilities:
        lat = fac.get("latitude")
        lon = fac.get("longitude")
        if lat is None or lon is None:
            continue
        criminals = safe_int(fac.get("Male Crim")) + safe_int(fac.get("Female Crim"))
        noncriminals = safe_int(fac.get("Male Non-Crim")) + safe_int(
            fac.get("Female Non-Crim")
        )
        total = criminals + noncriminals
        color, size = get_marker_style(total)
        popup = make_popup(fac).replace("'", "&#39;").replace("\n", " ")
        html += f"""
    L.marker([{lat}, {lon}], {{
        icon: L.divIcon({{
            className: 'custom-marker',
            html: `<span style=\"display:inline-block;width:{size}px;height:{size}px;background:{color};opacity:0.7;border:2px solid #222;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,0.12);\"></span>`
        }})
    }}).addTo(map)
        .bindPopup('{popup}');
    """
    html += """
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Map written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Render a static HTML map of facilities."
    )
    parser.add_argument(
        "--input", required=True, help="Input geocoded facilities JSON file"
    )
    parser.add_argument("--output", help="Output HTML file (default: docs/index.html)")
    args = parser.parse_args()
    input_path = Path(args.input)
    if args.output:
        output_path = args.output
    else:
        output_path = Path("docs/index.html")
    # Ensure the output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    facilities, metadata = load_facilities(input_path)
    render_html(facilities, output_path, metadata)
    if not os.getenv("GITHUB_ACTIONS"):
        try:
            webbrowser.open(str(output_path))
        except Exception as e:
            print(f"Unable to open map: {e}")


if __name__ == "__main__":
    main()
