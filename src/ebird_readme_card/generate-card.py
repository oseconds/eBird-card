import os
import io
import zipfile
import requests
import pandas as pd
from datetime import datetime

def main():
    # 1. Get the ZIP download link from GitHub Actions environment variables
    zip_url = os.environ.get("ZIP_URL")
    
    if not zip_url:
        print("❌ Error: ZIP_URL environment variable is missing. Please provide the download link.")
        exit(1)

    print("📥 Downloading eBird data...")
    
    try:
        # 2. Download the ZIP file from the link
        response = requests.get(zip_url)
        response.raise_for_status()

        # 3. Securely extract in-memory (no hard disk save) using BytesIO
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
            print(f"📄 CSV file found: {csv_filename}")
            
            # 4. Read CSV into Pandas via memory
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
                
    except Exception as e:
        print(f"❌ Error downloading or reading the data: {e}")
        exit(1)

    # 5. Analyze data statistics
    print("📊 Analyzing data...")
    total_species = df['Common Name'].nunique()
    total_checklists = df['Submission ID'].nunique()
    total_observations = len(df)
    
    # Get the latest observation record details
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        latest_row = df.loc[df['Date'].idxmax()]
        last_date = latest_row['Date'].strftime("%Y-%m-%d")
        last_bird = latest_row['Common Name']
        last_location = latest_row['Location Name']
    except Exception:
        last_date = "N/A"
        last_bird = "N/A"
        last_location = "N/A"

    today_date = datetime.now().strftime("%Y-%m-%d")

    # 6. Generate SVG Profile Card Design (English UI)
    print("🎨 Generating profile card (SVG)...")
    
    svg_template = f"""
    <svg width="450" height="240" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 240">
        <style>
            .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
            .title {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
            .stat-label {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .stat-value {{ font: 700 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .sub-value {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .footer {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; }}
        </style>
        
        <rect width="100%" height="100%" class="bg"/>
        <text x="30" y="35" class="title">🔭 My eBird Exploration</text>
        
        <!-- Overall Stats -->
        <text x="30" y="70" class="stat-label">Total Species:</text>
        <text x="160" y="70" class="stat-value">{total_species}</text>
        
        <text x="30" y="95" class="stat-label">Total Checklists:</text>
        <text x="160" y="95" class="stat-value">{total_checklists}</text>
        
        <text x="30" y="120" class="stat-label">Total Observations:</text>
        <text x="160" y="120" class="stat-value">{total_observations}</text>

        <!-- Last Birding Session Details -->
        <text x="30" y="155" class="stat-label">Last Birding:</text>
        <text x="160" y="155" class="stat-value" style="fill: #3fb950;">{last_date}</text>

        <text x="50" y="180" class="stat-label">📍 Location:</text>
        <text x="135" y="180" class="sub-value">{last_location}</text>

        <text x="50" y="202" class="stat-label">🦅 Bird Sighted:</text>
        <text x="135" y="202" class="sub-value" style="fill: #58a6ff;">{last_bird}</text>

        <!-- Footer Date -->
        <text x="30" y="226" class="footer">Last updated: {today_date}</text>
    </svg>
    """

    # 7. Save output path via environment variable (default: "ebird-card.svg")
    output_path = os.environ.get("OUTPUT_PATH", "ebird-card.svg")
    
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())

    print(f"✅ Successfully generated {output_path}!")

if __name__ == "__main__":
    main()
