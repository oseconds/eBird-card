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

        # 3. Securely extract in-memory using BytesIO
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
    
    # Get environment variables with smart fallbacks
    location_mode = os.environ.get("LOCATION_MODE", "location").strip().lower()
    if not location_mode:
        location_mode = "location"
        
    card_title_env = os.environ.get("CARD_TITLE", "").strip()
    card_title = card_title_env if card_title_env else "🪶 My Feathered Log"
    
    # Get the latest observation record details (Date, Bird Name, Location)
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        latest_row = df.loc[df['Date'].idxmax()]
        last_date = latest_row['Date'].strftime("%Y-%m-%d")
        last_bird = str(latest_row.get('Common Name', 'N/A'))
        
        # Determine location display based on mode
        if location_mode == "state":
            raw_location = str(latest_row.get('State/Province', 'N/A'))
        elif location_mode == "country":
            state_val = str(latest_row.get('State/Province', ''))
            raw_location = state_val.split('-')[0] if '-' in state_val else state_val
        elif location_mode == "none":
            raw_location = ""
        else:  # default: 'location'
            raw_location = str(latest_row.get('Location', 'N/A'))
            
        # Truncate location if too long (> 18 chars)
        max_len = 18
        if len(raw_location) > max_len:
            last_location = raw_location[:max_len] + "..."
        else:
            last_location = raw_location
            
    except Exception as e:
        print(f"⚠️ Warning during latest record parsing: {e}")
        last_date = "N/A"
        last_bird = "N/A"
        last_location = "N/A"

    today_date = datetime.now().strftime("%Y-%m-%d")

    # 6. Generate SVG Profile Card Design
    print("🎨 Generating profile card (SVG)...")
    
    right_details_svg = ""
    if location_mode != "none" and last_location:
        right_details_svg += f"""
        <text x="260" y="128" class="sub-label">Location:</text>
        <text x="315" y="128" class="sub-value" title="{raw_location}">{last_location}</text>
        """
    
    right_details_svg += f"""
    <text x="260" y="150" class="sub-label">Sighted:</text>
    <text x="315" y="150" class="sub-value" style="fill: #58a6ff;">{last_bird}</text>
    """

    svg_template = f"""
    <svg width="450" height="200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 200">
        <style>
            .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
            .title {{ font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
            .stat-label {{ font: 400 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .stat-value {{ font: 700 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .sub-label {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .sub-value {{ font: 600 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .footer {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; }}
        </style>
        
        <rect width="100%" height="100%" class="bg"/>
        <text x="30" y="40" class="title">{card_title}</text>
        
        <!-- Left Stats -->
        <text x="30" y="85" class="stat-label">Total Species:</text>
        <text x="180" y="85" class="stat-value">{total_species}</text>
        
        <text x="30" y="115" class="stat-label">Total Checklists:</text>
        <text x="180" y="115" class="stat-value">{total_checklists}</text>
        
        <text x="30" y="145" class="stat-label">Total Observations:</text>
        <text x="180" y="145" class="stat-value">{total_observations}</text>

        <!-- Right Side: Last Birding & Details -->
        <text x="260" y="85" class="stat-label">Last Birding:</text>
        <text x="260" y="105" class="stat-value" style="fill: #3fb950;">{last_date}</text>

        {right_details_svg}

        <!-- Footer Date -->
        <text x="30" y="180" class="footer">Last updated: {today_date}</text>
    </svg>
    """

    output_path = os.environ.get("OUTPUT_PATH", "ebird-card.svg")
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())

    print(f"✅ Successfully generated {output_path}!")

if __name__ == "__main__":
    main()
