import os
import io
import re
import base64
import zipfile
import argparse
import requests
import pandas as pd

def get_inaturalist_image(scientific_name):
    if not scientific_name or pd.isna(scientific_name): return None
    url = "https://api.inaturalist.org/v1/taxa"
    params = {"q": scientific_name, "is_active": "true", "rank": "species", "per_page": 1}
    try:
        response = requests.get(url, params=params, timeout=5).json()
        results = response.get("results", [])
        if not results: return None
        data = results[0]
        photo_url = data.get("default_photo", {}).get("medium_url")
        if photo_url:
            img_res = requests.get(photo_url, timeout=5)
            if img_res.status_code == 200:
                encoded = base64.b64encode(img_res.content).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded}"
        return None
    except: return None

def get_twemoji_inline_svg_compact(emoji_str, x_offset):
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
                return f'<g transform="translate({x_offset}, 16) scale(0.26)">{inner_content}</g>'
    except: return None
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip-url", required=True)
    parser.add_argument("--output", default="./assets/new-lifer-compact.svg")
    args = parser.parse_args()

    try:
        response = requests.get(args.zip_url)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_file = [name for name in z.namelist() if name.endswith('.csv')][0]
            with z.open(csv_file) as f: df = pd.read_csv(f)
    except: exit(1)

    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by='Date')
    latest = df.drop_duplicates(subset=['Common Name'], keep='last').iloc[-1]
    bird_name, sci_name = latest['Common Name'], latest.get('Scientific Name', '')
    bird_image_data = get_inaturalist_image(sci_name)

    # 너비 계산 로직 (여백 없는 이미지 폭 80 + 텍스트 영역 반영)
    max_char_len = max(len("Newest Lifer"), len(bird_name), len(sci_name))
    svg_width = 92 + int(max_char_len * 6.5) + 15
    
    # 사진을 왼쪽 끝에 여백 없이 꽉 채우기 (80x80 풀블리드)
    image_element = f'''
        <rect x="0" y="0" width="80" height="80" fill="#f6f8fa"/>
        <image x="0" y="0" width="80" height="80" href="{bird_image_data}" preserveAspectRatio="xMidYMid slice"/>
    ''' if bird_image_data else '''
        <rect x="0" y="0" width="80" height="80" fill="#f6f8fa"/>
    '''

    twemoji_svg = get_twemoji_inline_svg_compact('🐣', 92) or ''

    svg_template = f"""
    <svg width="{svg_width}" height="80" viewBox="0 0 {svg_width} 80" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
        <defs>
            <clipPath id="card-clip">
                <rect width="{svg_width}" height="80" rx="8" ry="8"/>
            </clipPath>
        </defs>
        <a xlink:href="https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}" target="_blank">
            <g clip-path="url(#card-clip)">
                <style>
                    .bg {{ fill: #ffffff; stroke: #d0d7de; stroke-width: 1px; rx: 8px; }}
                    .title {{ font: 600 11px sans-serif; fill: #24292e; }}
                    .bird-name {{ font: 700 13px sans-serif; fill: #1f2328; }}
                    .sci-name {{ font: italic 400 9px sans-serif; fill: #57606a; }}
                </style>
                <rect width="100%" height="100%" class="bg"/>
                {image_element}
                {twemoji_svg}
                <text x="105" y="24" class="title">Newest Lifer</text>
                <text x="92" y="44" class="bird-name">{bird_name}</text>
                <text x="92" y="62" class="sci-name">{sci_name}</text>
            </g>
        </a>
    </svg>
    """
    with open(args.output, "w", encoding="utf-8") as f: f.write(svg_template.strip())

if __name__ == "__main__": main()
