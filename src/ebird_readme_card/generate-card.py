import os
import io
import zipfile
import requests
import pandas as pd
from datetime import datetime

def main():
    # 1. GitHub Actions에서 넘겨준 ZIP 다운로드 링크 가져오기
    zip_url = os.environ.get("ZIP_URL")
    
    if not zip_url:
        print("❌ 에러: ZIP_URL 환경변수가 없습니다. 링크를 제대로 입력했는지 확인해주세요.")
        exit(1)

    print("📥 eBird 데이터 다운로드 중...")
    
    try:
        # 2. 링크에서 ZIP 파일 다운로드
        response = requests.get(zip_url)
        response.raise_for_status()

        # 3. 보안: 하드디스크에 저장하지 않고 메모리(io.BytesIO)에서 압축 해제
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            csv_filename = [name for name in z.namelist() if name.endswith('.csv')][0]
            print(f"📄 CSV 파일 발견: {csv_filename}")
            
            # 4. 메모리 상에서 Pandas로 CSV 읽기
            with z.open(csv_filename) as csv_file:
                df = pd.read_csv(csv_file)
                
    except Exception as e:
        print(f"❌ 데이터를 다운로드하거나 읽는 중 오류가 발생했습니다: {e}")
        exit(1)

    # 5. 통계 데이터 분석
    print("📊 데이터 분석 중...")
    total_species = df['Common Name'].nunique()
    total_checklists = df['Submission ID'].nunique()
    total_observations = len(df)
    
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        last_birding_date = df['Date'].max().strftime("%Y-%m-%d")
    except:
        last_birding_date = "N/A"

    today_date = datetime.now().strftime("%Y-%m-%d")

    # 6. SVG 카드 디자인 및 생성
    print("🎨 프로필 카드(SVG) 생성 중...")
    
    svg_template = f"""
    <svg width="450" height="200" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 200">
        <style>
            .bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
            .title {{ font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif; fill: #58a6ff; }}
            .stat-label {{ font: 400 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
            .stat-value {{ font: 700 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
            .footer {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #484f58; }}
            .icon {{ fill: #3fb950; }}
        </style>
        
        <rect width="100%" height="100%" class="bg"/>
        <text x="30" y="40" class="title">🔭 My eBird Exploration</text>
        
        <text x="30" y="85" class="stat-label">Total Species:</text>
        <text x="180" y="85" class="stat-value">{total_species} 종</text>
        
        <text x="30" y="115" class="stat-label">Total Checklists:</text>
        <text x="180" y="115" class="stat-value">{total_checklists} 개</text>
        
        <text x="30" y="145" class="stat-label">Total Observations:</text>
        <text x="180" y="145" class="stat-value">{total_observations} 건</text>

        <text x="280" y="85" class="stat-label">Last Birding:</text>
        <text x="280" y="110" class="stat-value" style="fill: #3fb950;">{last_birding_date}</text>

        <text x="30" y="180" class="footer">Last updated: {today_date}</text>
    </svg>
    """

    # 7. 환경변수(OUTPUT_PATH)로 저장 경로 지정 (없으면 기본값 "ebird-card.svg")
    output_path = os.environ.get("OUTPUT_PATH", "ebird-card.svg")
    
    # 지정한 경로에 폴더가 없으면 자동으로 생성
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template.strip())

    print(f"✅ 성공적으로 {output_path} 파일을 생성했습니다!")

if __name__ == "__main__":
    main()
