import os
import io
import re
import zipfile
import argparse
import requests
import pandas as pd
from datetime import datetime

def get_inaturalist_data(scientific_name):
    """
    iNaturalist API로 사진 URL과 IUCN 보전 상태를 가져옵니다.
    """
    if not scientific_name or pd.isna(scientific_name):
        return None, "unknown"
        
    url = "https://api.inaturalist.org/v1/taxa"
    params = {
        "q": scientific_name,
        "is_active": "true",
        "rank": "species",
        "per_page": 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=5).json()
        results = response.get("results", [])
        
        if not results:
            return None, "unknown"
            
        data = results[0]
        photo_url = data.get("default_photo", {}).get("medium_url")
        
        status = "unknown"
        if data.get("conservation_status"):
            status = data["conservation_status"].get("status", "").lower()
            
        return photo_url, status
        
    except Exception as e:
        print(f"⚠️ iNaturalist 검색 오류 ({scientific_name}): {e}")
        return None, "unknown"

def get_status_color(status):
    """보전 상태에 따른 동그라미 색상 반환"""
    if status in ['cr', 'en']:
        return "#f85149" # Red (위기/멸종위기)
    elif status in ['vu', 'nt']:
        return "#d29922" # Orange (취약/준위협)
    elif status in ['lc']:
        return "#3fb950" # Green (관심대상)
    else:
        return "#8b949e" # Gray (기타/정보없음)

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
    parser = argparse.ArgumentParser(description="Generate Newest Lifer Card with iNaturalist Image")
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
                'Date': row['Date']
            })
    
    if not lifers:
        print("⚠️ No data found.")
        exit(1)
        
    latest_lifer = lifers[-1]
    bird_name = latest_lifer['Common Name']
    sci_name = latest_lifer['Scientific Name']
    bird_date = latest_lifer['Date'].strftime("%Y-%m-%d")

    print(f"🐣 Latest Lifer: {bird_name} ({sci_name})")
    
    print(f"🌿 Fetching iNaturalist data for {sci_name}...")
    bird_image_url, conservation_status = get_inaturalist_data(sci_name)
    dot_color = get_status_color(conservation_status)

    github_repo = os.environ.get("GITHUB_REPOSITORY", "your-username/eBird-card")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    card_title = "🐣 Newest Lifer"
    emoji_pattern = re.compile(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF]+')
    emoji_match = emoji_pattern.search(card_title)
    
    if emoji_match:
        emoji_str = emoji_match.group()
        text_part = emoji_pattern.sub('', card_title).strip()
        twemoji_group = get_twemoji_inline_svg(emoji_str)
        title_svg = f'{twemoji_group}<text x="58" y="40" class="title">{text_part}</text>'
    else:
        title_svg = f'<text x="30" y="40" class="title">{card_title}</text>'

    if bird_image_url:
        image_element = f'''
        <clipPath id="circle-clip">
            <circle cx="360" cy="115" r="53" />
        </clipPath>
        <circle cx="360" cy="115" r="55" fill="#21262d" stroke="#30363d" stroke-width="1px"/>
        <image x="307" y="62" width="106" height="106" href="{bird_image_url}" preserveAspectRatio="xMidYMid slice" clip-path="url(#circle-clip)"/>
        '''
    else:
        image_element = '''
        <circle cx="360" cy="115" r="55" fill="#21262d" stroke="#30363d" stroke-width="1px"/>
        <text x="360" y="120" style="font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; text-anchor: middle;">No Photo</text>
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
            
            <text x="30" y="85" class="bird-name">{bird_name}</text>
            <text x="30" y="107" class="sci-name">{sci_name}</text>
            <text x="30" y="138" class="date-label">📅 Observed on: {bird_date}</text>
            
            <!-- 상태를 나타내는 동그라미 컬러 점과 텍스트 -->
            <circle cx="38" cy="167" r="5" fill="{dot_color}" />
            <text x="50" y="171" class="status-label">IUCN: {conservation_status.upper()}</text>
            
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
