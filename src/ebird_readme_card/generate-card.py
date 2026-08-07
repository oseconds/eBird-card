import os
import io
import re
import zipfile
import base64
import requests
import pandas as pd
from datetime import datetime

def get_twemoji_base64(emoji_str):
    """이모지 문자열을 Twemoji 공식 SVG에서 PNG(Base64)로 변환해 가져옵니다."""
    try:
        codepoints = [f"{ord(c):x}" for c in emoji_str if ord(c) != 0xfe0f]
        hex_code = "-".join(codepoints)
        
        url = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg/{hex_code}.svg"
        res = requests.get(url, timeout=5)
        
        if res.status_code == 200:
            # SVG를 PNG 바이트로 변환 (모바일 호환성 확보)
            png_bytes = cairosvg.svg2png(bytestring=res.content, scale=2.0)
            b64_data = base64.b64encode(png_bytes).decode('utf-8')
            return f"data:image/png;base64,{b64_data}"
    except Exception as e:
        print(f"⚠️ Twemoji PNG 변환 실패 ({emoji_str}): {e}")
    return None

def main():
    zip_url = os.environ.get("ZIP_URL")
    if not zip_url:
        print("❌ Error: ZIP_URL environment variable is missing.")
        exit(1)

    print("📥 Downloading eBird data...")
    try:
        response = requests.get(zip_url)
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"❌ Error downloading or reading the data: {e}")
        exit(1)

    print("📊 Analyzing data...")
    total_species = df['Common Name'].nunique()
    total_checklists = df['Submission ID'].nunique()
    total_observations = len(df)
    
    location_mode = os.environ.get("LOCATION_MODE", "location").strip().lower()
    card_title_env = os.environ.get("CARD_TITLE", "").strip()
    card_title = card_title_env if card_title_env else "🪶 My Feathered Log"
    output_format = os.environ.get("OUTPUT_FORMAT", "svg").strip().lower()
    output_path_env = os.environ.get("OUTPUT_PATH", "./assets/ebird-card.svg")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "your-username/eBird-card")

    try:
        df['Date'] = pd.to_datetime(df['Date'])
        latest_row = df.loc[df['Date'].idxmax()]
        last_date = latest_row['Date'].strftime("%Y-%m-%d")
        last_bird = str(latest_row.get('Common Name', 'N/A'))
        
        if location_mode == "state":
            raw_location = str(latest_row.get('State/Province', 'N/A'))
        elif location_mode == "country":
            state_val = str(latest_row.get('State/Province', ''))
            raw_location = state_val.split('-')[0] if '-' in state_val else state_val
        elif location_mode == "none":
            raw_location = ""
        else:
            raw_location = str(latest_row.get('Location', 'N/A'))
            
        max_len = 18
        last_location = (raw_location[:max_len] + "...") if len(raw_location) > max_len else raw_location
    except Exception as e:
        print(f"⚠️ Warning during latest record parsing: {e}")
        last_date, last_bird, last_location = "N/A", "N/A", "N/A"

    today_date = datetime.now().strftime("%Y-%m-%d")

    print("🎨 Processing title Twemoji & Generating profile card...")
    
    # 💡 이모지 감지 정규식
    emoji_pattern = re.compile(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF]+')
    emoji_match = emoji_pattern.search(card_title)
    
    if emoji_match:
        emoji_str = emoji_match.group()
        text_part = emoji_pattern.sub('', card_title).strip()
        twemoji_b64 = get_twemoji_base64(emoji_str)
        
        if twemoji_b64:
            # 💡 CairoSVG(PNG 변환) 호환을 위해 xlink:href와 href를 동시에 지정
            title_svg_element = f'''
            <image x="30" y="21" width="22" height="22" href="{twemoji_b64}" xlink:href="{twemoji_b64}"/>
            <text x="58" y="40" class="title">{text_part}</text>
            '''
        else:
            title_svg_element = f'<text x="30" y="40" class="title">{card_title}</text>'
    else:
        title_svg_element = f'<text x="30" y="40" class="title">{card_title}</text>'

    right_details_svg = ""
    # 💡 last_bird
    right_details_svg += f"""
    <text x="260" y="125" style="font: 700 18px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff;" title="{last_bird}">{last_bird}</text>
    """
    
    # 💡 last_location
    if location_mode != "none" and last_location:
        right_details_svg += f"""
        <text x="260" y="145" class="sub-value" title="{raw_location}" style="fill: #8b949e;">{last_location}</text>
        """

    svg_template = f"""
    <svg width="450" height="200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 200">
        <style>
            .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
            .title {{ font: 600 20px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
            .stat-label {{ font: 400 14px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .stat-value {{ font: 700 16px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .sub-label {{ font: 400 11px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .sub-value {{ font: 600 11px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .footer {{ font: 400 11px 'Noto Sans CJK KR', 'Noto Sans CJK JP', 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; }}
        </style>
        
        <rect width="100%" height="100%" class="bg"/>
        {title_svg_element}
        
        <text x="30" y="85" class="stat-label">Total Species:</text>
        <text x="180" y="85" class="stat-value">{total_species}</text>
        
        <text x="30" y="115" class="stat-label">Total Checklists:</text>
        <text x="180" y="115" class="stat-value">{total_checklists}</text>
        
        <text x="30" y="145" class="stat-label">Total Observations:</text>
        <text x="180" y="145" class="stat-value">{total_observations}</text>

        <text x="260" y="85" class="stat-label">Last Bird:</text>
        <text x="260" y="102" style="font: 500 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #3fb950;">{last_date}</text>

        {right_details_svg}

        <text x="300" y="180" class="footer">Last updated: {today_date}</text>
        <metadata>
            Generated with eBird-card by 0seconds (https://github.com/oseconds/eBird-Card)
        </metadata>
    </svg>
    """

    svg_content = svg_template.strip()
    
    base, ext = os.path.splitext(output_path_env)
    svg_path = output_path_env if ext.lower() == '.svg' else f"{output_path_env}.svg"
    png_path = f"{base}.png" if ext.lower() == '.svg' else f"{output_path_env}.png"

    clean_svg_path = svg_path.lstrip("./")
    clean_png_path = png_path.lstrip("./")

    if output_format in ["svg", "both"]:
        os.makedirs(os.path.dirname(svg_path) if os.path.dirname(svg_path) else ".", exist_ok=True)
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"✅ Successfully generated {svg_path}!")

    if output_format in ["png", "both"]:
        os.makedirs(os.path.dirname(png_path) if os.path.dirname(png_path) else ".", exist_ok=True)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), write_to=png_path, scale=2.0)
            print(f"✅ Successfully generated {png_path} (High Resolution with Twemoji)!")
        except Exception as e:
            print(f"⚠️ Failed to generate PNG: {e}")

    # Write to GitHub Actions Step Summary
    step_summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_path:
        try:
            svg_url = f"https://raw.githubusercontent.com/{github_repo}/main/{clean_svg_path}"
            png_url = f"https://raw.githubusercontent.com/{github_repo}/main/{clean_png_path}"

            summary_lines = [
                "### 🎉 eBird Card Update Complete!",
                "",
                "Here are your generated cards. You can preview them below or use the **copy button** to grab the markdown code:",
                "",
                "---",
                "#### 📄 SVG Card (GitHub / Notion)",
                f"![SVG Card Preview]({svg_url})",
                f"- **Direct Link**: [Open SVG in new tab]({svg_url})",
                "- **Markdown Code**:",
                "```markdown",
                f"![eBird Card]({svg_url})",
                "```",
                "",
                "---",
                "#### 🖼️ PNG Card (Discord / Blog / Slack)",
                f"![PNG Card Preview]({png_url})",
                f"- **Direct Link**: [Open PNG in new tab]({png_url})",
                "- **Markdown Code**:",
                "```markdown",
                f"![eBird Card]({png_url})",
                "```"
            ]
            
            with open(step_summary_path, "a", encoding="utf-8") as f:
                f.write("\n".join(summary_lines))
                
            print("✨ Successfully published results to GitHub Actions Step Summary!")
        except Exception as e:
            print(f"⚠️ Failed to write step summary: {e}")

    print("\n" + "="*60)
    print("🎉 CARD UPDATE COMPLETE!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
