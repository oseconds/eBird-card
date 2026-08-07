import os
import io
import re
import zipfile
import argparse
import requests
import pandas as pd
from datetime import datetime

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
    parser = argparse.ArgumentParser(description="Generate eBird Frequency Ranking Card")
    parser.add_argument("--zip-url", type=str, help="eBird Data Download URL", required=True)
    parser.add_argument("--output", type=str, help="Output SVG path", default="./assets/freq-ranking.svg")
    args = parser.parse_args()

    print("📥 Downloading eBird data for ranking...")
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

    print("📊 Calculating Frequently Seen Birds (Top 5)...")
    top_birds = df['Common Name'].value_counts().head(5)

    github_repo = os.environ.get("GITHUB_REPOSITORY", "your-username/eBird-card")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    ranking_svg_elements = ""
    y_offset = 90
    rank_colors = ["#ffd700", "#c0c0c0", "#cd7f32", "#8b949e", "#8b949e"]
    
    for i, (bird, count) in enumerate(top_birds.items()):
        rank = i + 1
        color = rank_colors[i]
        
        ranking_svg_elements += f"""
        <text x="35" y="{y_offset}" style="font: 700 15px 'Segoe UI', Ubuntu, Sans-Serif; fill: {color};">{rank}.</text>
        <text x="65" y="{y_offset}" style="font: 500 15px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9;" title="{bird}">{bird}</text>
        <text x="410" y="{y_offset}" style="font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; text-anchor: end;">{count} times</text>
        """
        y_offset += 32

    card_title = "🐦 Frequently Seen Birds"
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

    svg_template = f"""
    <svg width="450" height="260" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 450 260">
        <a xlink:href="https://github.com/oseconds/eBird-card" target="_blank">
        <metadata>
            Generated with eBird-card (https://github.com/oseconds/eBird-card)
        </metadata>
            <style>
                .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
                .title {{ font: 600 20px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; cursor: pointer; }}
                .footer {{ font: 400 11px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; text-anchor: end; }}
                .divider {{ stroke: #21262d; stroke-width: 1px; }}
            </style>
            
            <rect width="100%" height="100%" class="bg"/>
            {title_svg}
            
            <line x1="30" y1="55" x2="420" y2="55" class="divider"/>
            {ranking_svg_elements}
            
            <text x="420" y="240" class="footer">Updated • {today_date}</text>
            <rect width="100%" height="100%" fill="transparent" cursor="pointer"/>
        </a>
    </svg>
    """

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())
        
    print(f"✅ Successfully generated Ranking Card at {output_path}!")

if __name__ == "__main__":
    main()
