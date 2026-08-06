import os
import io
import zipfile
import requests
import pandas as pd
from datetime import datetime

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
            print(f"📄 CSV file found: {csv_filename}")
            
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
                
    except Exception as e:
        print(f"❌ Error downloading or reading the data: {e}")
        exit(1)

    print("📊 Analyzing data...")
    total_species = df['Common Name'].nunique()
    total_checklists = df['Submission ID'].nunique()
    total_observations = len(df)
    
    # Get latest observation details & Location Mode option
    location_mode = os.environ.get("LOCATION_MODE", "location").lower()
    
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        latest_row = df.loc[df['Date'].idxmax()]
        last_date = latest_row['Date'].strftime("%Y-%m-%d")
        
        # Determine location display based on mode
        if location_mode == "state":
            last_location = str(latest_row.get('State/Province', 'N/A'))
        elif location_mode == "country":
            # eBird data typically uses State/Province codes (like KR-11, JP-26). 
            # We can extract country code or show a general label if needed, 
            # but let's derive it or fallback to State/Province prefix.
            state_val = str(latest_row.get('State/Province', ''))
            last_location = state_val.split('-')[0] if '-' in state_val else state_val
        elif location_mode == "none":
            last_location = ""
        else:  # default: 'location'
            last_location = str(latest_row.get('Location', 'N/A'))
            
    except Exception as e:
        print(f"⚠️ Warning during location parsing: {e}")
        last_date = "N/A"
        last_location = "N/A"

    today_date = datetime.now().strftime("%Y-%m-%d")

    print("🎨 Generating profile card (SVG)...")
    
    # Dynamically adjust SVG height if location is hidden ('none')
    svg_height = 170 if location_mode == "none" else 200
    
    location_row_svg = ""
    if location_mode != "none" and last_location:
        location_row_svg = f"""
        <text x="30" y="145" class="stat-label">Last Location:</text>
        <text x="145" y="145" class="stat-value" style="font-size: 13px; fill: #8b949e;">{last_location}</text>
        """

    svg_template = f"""
    <svg width="450" height="{svg_height}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 {svg_height}">
        <style>
            .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
            .title {{ font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
            .stat-label {{ font: 400 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .stat-value {{ font: 700 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .footer {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; }}
        </style>
        
        <rect width="100%" height="100%" class="bg"/>
        <text x="30" y="40" class="title">🔭 My eBird Exploration</text>
        
        <!-- Left Stats -->
        <text x="30" y="85" class="stat-label">Total Species:</text>
        <text x="180" y="85" class="stat-value">{total_species}</text>
        
        <text x="30" y="115" class="stat-label">Total Checklists:</text>
        <text x="180" y="115" class="stat-value">{total_checklists}</text>
        
        <!-- Right Side: Last Birding -->
        <text x="275" y="85" class="stat-label">Last Birding:</text>
        <text x="275" y="110" class="stat-value" style="fill: #3fb950;">{last_date}</text>

        {location_row_svg}

        <!-- Footer Date -->
        <text x="30" y="{svg_height - 20}" class="footer">Last updated: {today_date}</text>
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
