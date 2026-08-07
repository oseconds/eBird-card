import os
import io
import re
import base64
import zipfile
import argparse
import requests
import pandas as pd

def get_inaturalist_image(scientific_name):
    """
    iNaturalist API로 사진 URL을 가져온 뒤, Base64로 변환합니다.
    """
    if not scientific_name or pd.isna(scientific_name):
        return None
        
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
            return None
            
        data = results[0]
        photo_url = data.get("default_photo", {}).get("medium_url")
        
        base64_image = None
        if photo_url:
            img_res = requests.get(photo_url, timeout=5)
            if img_res.status_code == 200:
                encoded = base64.b64encode(img_res.content).decode('utf-8')
                base64_image = f"data:image/jpeg;base64,{encoded}"
                
        return base64_image
        
    except Exception as e:
        print(f"⚠️ iNaturalist 데이터 처리 오류 ({scientific_name}): {e}")
        return None

def get_twemoji_inline_svg_compact(emoji_str):
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
                return f'<g transform="translate(16, 10) scale(0.38)">{inner_content}</g>'
    except Exception as e:
        print(f"⚠️ Twemoji 변환 실패: {e}")
    return None

def main():
    parser = argparse.ArgumentParser(description="Generate Tiny Compact New Lifer Card")
    parser.add_argument("--zip-url", type=str, help="eBird Data Download URL", required=True)
    parser.add_argument("--output", type=str, help="Output SVG path", default="./assets/new-lifer-compact.svg")
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
                'Scientific Name': sci_name
            })
    
    if not lifers:
        print("⚠️ No data found.")
        exit(1)
        
    latest_lifer = lifers[-1]
    bird_name = latest_lifer['Common Name']
    sci_name = latest_lifer['Scientific Name']

    print(f"🐣 Latest Lifer: {bird_name} ({sci_name})")
    
    print(f"🌿 Fetching iNaturalist image for {sci_name}...")
    bird_image_data = get_inaturalist_image(sci_name)

    github_repo = os.environ.get("GITHUB_REPOSITORY", "your-username/eBird-card")
    
    card_title = "🐣 Newest Lifer"
    emoji_pattern = re.compile(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF]+')
    emoji_match = emoji_pattern.search(card_title)
    
    if emoji_match:
        emoji_str = emoji_match.group()
        text_part = emoji_pattern.sub('', card_title).strip()
        twemoji_group = get_twemoji_inline_svg_compact(emoji_str)
        if twemoji_group:
            title_svg = f'{twemoji_group}<text x="38" y="22" class="title">{text_part}</text>'
        else:
            title_svg = f'<text x="16" y="22" class="title">{card_title}</text>'
    else:
        title_svg = f'<text x="16" y="22" class="title">{card_title}</text>'

    # 초미니 사이즈 둥근 모서리 사각형 이미지 영역 (60x60)
    if bird_image_data:
        image_element = f'''
        <clipPath id="rect-clip-tiny">
            <rect x="274" y="17" width="60" height="60" rx="8" ry="8" />
        </clipPath>
        <rect x="274" y="17" width="60" height="60" rx="8" ry="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="1px"/>
        <image x="274" y="17" width="60" height="60" href="{bird_image_data}" preserveAspectRatio="xMidYMid slice" clip-path="url(#rect-clip-tiny)"/>
        '''
    else:
        image_element = '''
        <rect x="274" y="17" width="60" height="60" rx="8" ry="8" fill="#f6f8fa" stroke="#d0d7de" stroke-width="1px"/>
        <text x="304" y="47" style="font: 400 9px 'Segoe UI', Ubuntu, Sans-Serif; fill: #57606a; text-anchor: middle;" dominant-baseline="central">No Photo</text>
        '''

    svg_template = f"""
    <svg width="350" height="94" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 350 94">
        <a xlink:href="https://github.com/{github_repo}" target="_blank">
            <style>
                .bg {{ fill: #ffffff; stroke: #d0d7de; stroke-width: 1px; rx: 8px; }}
                .title {{ font: 600 13px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #24292e; cursor: pointer; }}
                .bird-name {{ font: 700 15px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #1f2328; }}
                .sci-name {{ font: italic 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #57606a; }}
            </style>
            
            <rect width="100%" height="100%" class="bg"/>
            {title_svg}
            
            <text x="16" y="48" class="bird-name">{bird_name}</text>
            <text x="16" y="67" class="sci-name">{sci_name}</text>
            
            {image_element}
            
            <rect width="100%" height="100%" fill="transparent" cursor="pointer"/>
        </a>
    </svg>
    """

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())
        
    print(f"✅ Successfully generated Tiny Compact New Lifer Card at {output_path}!")

if __name__ == "__main__":
    main()
