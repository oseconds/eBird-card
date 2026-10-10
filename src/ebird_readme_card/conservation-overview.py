"""Generate an SVG chart of global IUCN categories across unique eBird taxa.

No API key required. Unresolved taxonomy and unavailable assessments are
reported separately from IUCN Data Deficient (DD).
"""
import argparse
import io
import json
import os
import re
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import pandas as pd
import requests

API = "https://api.inaturalist.org"
COLORS = {
    "LC": "#3fb950",
    "NT": "#a3be4a",
    "VU": "#e3b341",
    "EN": "#db6d28",
    "CR": "#f85149",
    "EW": "#bd7b80",
    "EX": "#b69295",
    "DD": "#8b949e",
    "N/A": "#586069",
}
BINOMIAL = re.compile(r"^[A-Z][a-z]+ [a-z]+$")
BASE_CATEGORIES = ["CR", "EN", "VU", "NT", "LC", "DD", "N/A"]


def read_taxa(zip_content):
    with zipfile.ZipFile(io.BytesIO(zip_content)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise ValueError("No CSV in eBird ZIP")
        with archive.open(names[0]) as stream:
            frame = pd.read_csv(stream)
    if "Scientific Name" not in frame:
        raise ValueError("Missing Scientific Name column")
    return sorted({
        name.strip()
        for name in frame["Scientific Name"].dropna()
        if isinstance(name, str) and name.strip()
    })


class INatClient:
    """Rate-limited, retrying client suitable for a manual GitHub Action."""

    def __init__(self):
        self.session = requests.Session()
        self.last_request = 0.0

    def get(self, endpoint, **params):
        for attempt in range(3):
            wait = 1.0 - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            try:
                response = self.session.get(
                    API + endpoint, params=params, timeout=20
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError("Retryable status " + str(response.status_code))
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                if attempt == 2:
                    print(f"⚠️ iNaturalist lookup failed: {endpoint}: {exc}")
                    return None
                time.sleep(2 ** attempt)
        return None


def fetch_global_statuses(taxa, client):
    """Only exact species-name matches and verified global IUCN entries count."""
    taxon_ids = {}
    for index, scientific_name in enumerate(taxa, start=1):
        if not BINOMIAL.fullmatch(scientific_name):
            continue  # subspecies, slashes, and aggregates are unverified
        result = client.get(
            "/v1/taxa",
            q=scientific_name,
            is_active="true",
            rank="species",
            per_page=10,
        )
        if not result:
            continue
        exact = next(
            (taxon for taxon in result.get("results", [])
             if taxon.get("name", "").casefold() == scientific_name.casefold()
             and taxon.get("rank") == "species"),
            None,
        )
        if exact and exact.get("id"):
            taxon_ids[int(exact["id"])] = scientific_name
        if index % 10 == 0:
            print(f"🔍 Resolved {index}/{len(taxa)} taxon names")

    statuses = {}
    ids = list(taxon_ids)
    for offset in range(0, len(ids), 20):
        batch = ids[offset: offset + 20]
        result = client.get(
            "/v2/taxa/" + ",".join(map(str, batch)),
            fields="(name:!t,conservation_statuses:all)",
        )
        if not result:
            continue
        for taxon in result.get("results", []):
            name = taxon_ids.get(taxon.get("id"))
            if not name or taxon.get("name", "").casefold() != name.casefold():
                continue
            for entry in taxon.get("conservation_statuses") or []:
                category = str(entry.get("status") or "").upper().strip()
                if (
                    entry.get("place") is None
                    and str(entry.get("authority") or "").casefold() == "iucn red list"
                    and category in COLORS
                    and category != "N/A"
                ):
                    statuses[name] = category
                    break
    return statuses


def draw_svg(taxa, statuses):
    counts = Counter(statuses.get(name, "N/A") for name in taxa)
    total = len(taxa)
    assessed = total - counts["N/A"]
    threatened = sum(counts[category] for category in ("VU", "EN", "CR"))
    categories = (
        ["EX"] if counts["EX"] else []
    ) + (["EW"] if counts["EW"] else []) + BASE_CATEGORIES

    height = 160 + 30 * len(categories)
    rows = []
    for index, category in enumerate(categories):
        count = counts[category]
        y = 118 + index * 30
        pct = (100 * count / total) if total else 0
        # Bars are proportional to all unique taxa, not the largest category.
        bar_width = 222 * count / total if total else 0
        color = COLORS[category]
        title = escape(f"{category}: {count} taxa ({pct:.1f}%)")
        rows.append(
            f'<text x="30" y="{y+8}" class="label" fill="{color}">{category}</text>'
            f'<rect x="103" y="{y-2}" width="222" height="13" rx="5" fill="#21262d"/>'
            f'<rect x="103" y="{y-2}" width="{bar_width:.2f}" height="13" rx="5" fill="{color}">'
            f'<title>{title}</title></rect>'
            f'<text x="340" y="{y+8}" class="count">{count}</text>'
            f'<text x="414" y="{y+8}" class="percent">{pct:.0f}%</text>'
        )

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    graphic = "\n".join(rows)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="{height}" viewBox="0 0 450 {height}" role="img" aria-label="Global IUCN conservation distribution">
  <title>Bird Conservation Overview</title>
  <desc>Global IUCN categories across {total} distinct scientific-name labels observed in eBird. N/A means no verified global assessment or an unresolved taxon; DD means the official Data Deficient category.</desc>
  <style>
    .heading {{ font: 600 19px 'Segoe UI', Ubuntu, sans-serif; fill: #e6edf3; }}
    .sub {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; }}
    .figure {{ font: 700 17px 'Segoe UI', Ubuntu, sans-serif; fill: #e6edf3; }}
    .label {{ font: 700 12px 'Segoe UI', Ubuntu, sans-serif; }}
    .count {{ font: 600 12px 'Segoe UI', Ubuntu, sans-serif; fill: #c9d1d9; text-anchor: end; }}
    .percent {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #8b949e; text-anchor: end; }}
    .foot {{ font: 400 10px 'Segoe UI', Ubuntu, sans-serif; fill: #6e7681; }}
  </style>
  <rect x=".5" y=".5" width="449" height="{height-1}" rx="10" fill="#0d1117" stroke="#30363d"/>
  <text x="30" y="38" class="heading">🌿 Conservation Overview</text>
  <text x="30" y="60" class="sub">Global IUCN · Unique eBird taxa</text>
  <text x="30" y="91" class="figure">{total} <tspan class="sub">taxa</tspan></text>
  <text x="166" y="91" class="figure">{assessed} <tspan class="sub">verified</tspan></text>
  <text x="318" y="91" class="figure" fill="#e3b341">{threatened} <tspan class="sub">threatened</tspan></text>
  {graphic}
  <line x1="30" x2="420" y1="{height-37}" y2="{height-37}" stroke="#21262d"/>
  <text x="30" y="{height-22}" class="foot">DD = Data Deficient · N/A = not verified / unmatched</text>
  <text x="30" y="{height-9}" class="foot">Source: iNaturalist / IUCN Red List · Updated {updated}</text>
</svg>"""


def main():
    parser = argparse.ArgumentParser(description="Generate eBird Conservation Overview")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--zip-url", help="eBird data ZIP URL")
    inputs.add_argument("--zip-file", help="Local eBird ZIP, for testing")
    parser.add_argument("--output", default="assets/conservation-overview.svg")
    parser.add_argument("--status-json", help="Optional offline test fixture: scientific name -> IUCN category")
    args = parser.parse_args()

    if args.zip_file:
        with open(args.zip_file, "rb") as stream:
            content = stream.read()
    else:
        response = requests.get(args.zip_url, timeout=60)
        response.raise_for_status()
        content = response.content

    taxa = read_taxa(content)
    if not taxa:
        raise SystemExit("No taxa found")

    if args.status_json:
        with open(args.status_json, encoding="utf-8") as stream:
            statuses = json.load(stream)
    else:
        statuses = fetch_global_statuses(taxa, INatClient())

    graphic = draw_svg(taxa, statuses)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as stream:
        stream.write(graphic)
    print(f"✅ Conservation overview: {len(taxa)} taxa, {len(statuses)} verified. Saved {args.output}")


if __name__ == "__main__":
    main()
