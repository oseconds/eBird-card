import os
import io
import re
import base64
import zipfile
import argparse
import requests
import pandas as pd
import pycountry
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

STATUS_COLORS = {
    "LC": "#3fb950",  # Least Concern
    "NT": "#a3be4a",  # Near Threatened
    "VU": "#e3b341",  # Vulnerable
    "EN": "#db6d28",  # Endangered
    "CR": "#f85149",  # Critically Endangered
    "RE": "#b32846",  # Regionally Extinct
    "EW": "#bd7b80",  # Extinct in the Wild
    "EX": "#b69295",  # Extinct
    "DD": "#8b949e",  # Data Deficient
    "NE": "#8b949e",  # Not Evaluated
}


def get_observation_country_code(row):
    """eBird exports typically encode the country in State/Province (e.g. KR-11)."""
    for column in ("Country Code", "State/Province"):
        value = row.get(column, "")
        if pd.isna(value):
            continue
        match = re.match(r"^([A-Za-z]{2})(?:[-_]|$)", str(value).strip())
        if match:
            return match.group(1).upper()
    return None


def country_name_aliases(country_code):
    """Use ISO 3166 names, not a Korea-only mapping, for regional evaluations."""
    if not country_code:
        return set()
    country = pycountry.countries.get(alpha_2=country_code.upper())
    if country is None:
        return set()
    names = {
        getattr(country, field).casefold()
        for field in ("name", "common_name", "official_name")
        if getattr(country, field, None)
    }
    names.update({
        "RU": {"russia"},
        "US": {"united states", "usa"},
        "GB": {"uk", "great britain"},
        "TR": {"turkey"},
        "CZ": {"czech republic"},
    }.get(country_code.upper(), set()))
    return names


def select_conservation_statuses(statuses, country_code):
    """Return verified global IUCN and observation-country regional categories."""
    global_status = None
    regional_status = None
    country_names = country_name_aliases(country_code)
    for entry in statuses:
        status = str(entry.get("status") or "").upper().strip()
        if status not in STATUS_COLORS:
            continue
        place = entry.get("place")
        authority = str(entry.get("authority") or "").strip().casefold()
        if place is None:
            if authority == "iucn red list" and global_status is None:
                global_status = status
        elif isinstance(place, dict) and regional_status is None and country_names:
            place_name = str(place.get("name") or "").casefold()
            if place_name in country_names:
                regional_status = status
    return global_status, regional_status


def get_inaturalist_data(scientific_name, country_code=None):
    """Get an exact-match taxon's image and optional global/regional Red List data."""
    if not isinstance(scientific_name, str) or not scientific_name.strip():
        return None, None, None

    try:
        response = requests.get(
            "https://api.inaturalist.org/v1/taxa",
            params={
                "q": scientific_name,
                "is_active": "true",
                "rank": "species",
                "per_page": 10,
            },
            timeout=10,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        taxon = next(
            (item for item in results if item.get("name", "").casefold() == scientific_name.strip().casefold()),
            None,
        )
        if not taxon:
            print(f"⚠️ No exact iNaturalist species match for {scientific_name}")
            return None, None, None
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ iNaturalist taxon lookup failed ({scientific_name}): {e}")
        return None, None, None

    image_data = None
    photo_url = (taxon.get("default_photo") or {}).get("medium_url")
    if photo_url:
        try:
            photo_response = requests.get(photo_url, timeout=10)
            photo_response.raise_for_status()
            encoded = base64.b64encode(photo_response.content).decode("ascii")
            image_data = f"data:image/jpeg;base64,{encoded}"
        except requests.RequestException as e:
            print(f"⚠️ iNaturalist photo unavailable: {e}")

    global_status = None
    regional_status = None
    try:
        status_response = requests.get(
            f"https://api.inaturalist.org/v2/taxa/{taxon['id']}",
            params={"fields": "(name:!t,conservation_statuses:all)"},
            timeout=10,
        )
        status_response.raise_for_status()
        details = status_response.json().get("results", [])
        if details and details[0].get("name", "").casefold() == taxon["name"].casefold():
            global_status, regional_status = select_conservation_statuses(
                details[0].get("conservation_statuses") or [],
                country_code,
            )
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️ iNaturalist conservation status unavailable: {e}")

    return image_data, global_status, regional_status


def get_status_color(status):
    return STATUS_COLORS.get(status, "#8b949e")


def get_twemoji_inline_svg(emoji_str):
    try:
        codepoints = [f"{ord(c):x}" for c in emoji_str if ord(c) != 0xfe0f]
        hex_code = "-".join(codepoints)
        url = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg/{hex_code}.svg"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            svg_text = res.text
            inner_match = re.search(r'<svg[^>]*>(.*)</svg>', svg_text, re.DOTALL)
            if inner_match:
                inner_content = inner_match.group(1)
                return f'<g transform="translate(30, 21) scale(0.6111)">{inner_content}</g>'
    except Exception as e:
        print(f"⚠️ Twemoji 변환 실패: {e}")
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate Newest Lifer Card with Embedded Image")
    parser.add_argument("--zip-url", type=str, help="eBird Data Download URL", required=True)
    parser.add_argument("--output", type=str, help="Output SVG path", default="./assets/new-lifer.svg")
    args = parser.parse_args()

    print("📥 Downloading eBird data for Lifer check...")
    try:
        response = requests.get(args.zip_url)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"❌ Error reading data: {e}")
        exit(1)

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by='Date')
    
    seen = set()
    lifers = []
    
    for _, row in df.iterrows():
        species = row['Common Name']
        sci_name = row.get('Scientific Name', '')
        if species not in seen:
            seen.add(species)
            lifers.append({
                'Common Name': species, 
                'Scientific Name': sci_name,
                'Date': row['Date'],
                'Country Code': get_observation_country_code(row)
            })
    
    if not lifers:
        print("⚠️ No data found.")
        exit(1)
        
    latest_lifer = lifers[-1]
    bird_name = latest_lifer['Common Name']
    sci_name = latest_lifer['Scientific Name']
    bird_date = latest_lifer['Date'].strftime("%Y-%m-%d")

    print(f"🐣 Latest Lifer: {bird_name} ({sci_name})")
    
    country_code = latest_lifer['Country Code']
    print(f"🌿 Fetching iNaturalist photo and conservation statuses for {sci_name} ({country_code or 'unknown region'})...")
    bird_image_data, global_status, regional_status = get_inaturalist_data(sci_name, country_code)

    status_rows = []
    if global_status:
        status_rows.append(("Global IUCN", global_status))
    if regional_status:
        status_rows.append((f"Regional ({country_code})", regional_status))
    status_y_positions = [168] if len(status_rows) == 1 else [155, 175]
    status_svg = "\\n".join(
        f'<circle cx="38" cy="{y}" r="4.5" fill="{get_status_color(status)}" />'
        f'<text x="50" y="{y}" class="status-label" dominant-baseline="central">'
        f'{xml_escape(label)}: {status}</text>'
        for (label, status), y in zip(status_rows, status_y_positions)
    )
    print(f"🌿 Global IUCN: {global_status or 'unavailable'} | "
          f"Regional ({country_code or 'n/a'}): {regional_status or 'unavailable'}")

    github_repo = os.environ.get("GITHUB_REPOSITORY", "your-username/eBird-card")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    card_title = "🐣 Newest Lifer"
    emoji_pattern = re.compile(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF]+')
    emoji_match = emoji_pattern.search(card_title)
    
    if emoji_match:
        emoji_str = emoji_match.group()
        text_part = emoji_pattern.sub('', card_title).strip()
        twemoji_group = get_twemoji_inline_svg(emoji_str)
        if twemoji_group:
            title_svg = f'{twemoji_group}<text x="58" y="40" class="title">{text_part}</text>'
        else:
            title_svg = f'<text x="30" y="40" class="title">{card_title}</text>'
    else:
        title_svg = f'<text x="30" y="40" class="title">{card_title}</text>'

    # 사진 원형 영역을 위쪽으로 조정 (cy=100)
    if bird_image_data:
        image_element = f'''
        <clipPath id="circle-clip">
            <circle cx="360" cy="100" r="53" />
        </clipPath>
        <circle cx="360" cy="100" r="55" fill="#21262d" stroke="#30363d" stroke-width="1px"/>
        <image x="305" y="45" width="110" height="110" href="{bird_image_data}" preserveAspectRatio="xMidYMid slice" clip-path="url(#circle-clip)"/>
        '''
    else:
        image_element = '''
        <circle cx="360" cy="100" r="55" fill="#21262d" stroke="#30363d" stroke-width="1px"/>
        <text x="360" y="105" style="font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; text-anchor: middle;" dominant-baseline="central">No Photo</text>
        '''

    svg_template = f"""
    <svg width="450" height="200" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 450 200">
        <a xlink:href="https://github.com/{github_repo}" target="_blank">
            <style>
                .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
                .title {{ font: 600 20px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #ffd700; cursor: pointer; }}
                .bird-name {{ font: 700 20px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
                .sci-name {{ font: italic 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
                .date-label {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
                .status-label {{ font: 600 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
                .footer {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; text-anchor: end; }}
            </style>
            
            <rect width="100%" height="100%" class="bg"/>
            {title_svg}
            
            <text x="30" y="85" class="bird-name">{xml_escape(str(bird_name))}</text>
            <text x="30" y="107" class="sci-name">{xml_escape(str(sci_name))}</text>
            <text x="30" y="138" class="date-label">📅 Observed on: {bird_date}</text>
            
            {status_svg}
            
            {image_element}
            
            <text x="420" y="183" class="footer">Last updated: {today_date}</text>
            <rect width="100%" height="100%" fill="transparent" cursor="pointer"/>
        </a>
    </svg>
    """

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())
        
    print(f"✅ Successfully generated New Lifer Card at {output_path}!")

if __name__ == "__main__":
    main()
