import os
import re
import requests
from bs4 import BeautifulSoup

class EBirdProfileScraper:
    def __init__(self):
        self.user_id = os.environ.get("EBIRD_USER_ID")
        
        if not self.user_id:
            raise ValueError("❌ 환경 변수 'EBIRD_USER_ID'가 설정되지 않았습니다.")

    def fetch_recent_checklist_ids(self, limit: int = 3) -> list:
        """유저의 eBird 프로필 페이지에서 최근 체크리스트 subId 목록을 추출합니다."""
        url = f"https://ebird.org{self.user_id}/world"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"❌ 프로필 페이지 접근 실패 (Status Code: {response.status_code})")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            html_content = str(soup)
            
            # HTML 소스에서 'subId=S12345678' 형태의 정규식 패턴 추출
            checklist_ids = re.findall(r'subId=(S\d+)', html_content)
            
            # 순서가 보장된 상태로 중복 제거 (최근 기록 순 유지)
            unique_ids = []
            for cid in checklist_ids:
                if cid not in unique_ids:
                    unique_ids.append(cid)
                    
            print(f"🔍 스크래핑 성공! 발견된 최근 체크리스트 번호: {unique_ids[:limit]}")
            return unique_ids[:limit]
            
        except Exception as e:
            print(f"❌ 스크래핑 중 예외 발생: {e}")
            return []



              
from jinja2 import Template

def get_data_and_render():
    # 1. 기존에 만들어둔 스크래퍼와 API 로직을 돌려 데이터를 가져옵니다.
    # (앞선 디버깅 워크플로우에서 검증한 결합 데이터 구조를 그대로 활용)
    scraper = EBirdProfileScraper()
    sub_ids = scraper.fetch_recent_checklist_ids(limit=3)
    
    # 여기에 공식 API 정보를 바인딩하여 템플릿용 리스트로 포맷팅
    formatted_checklists = []
    for sid in sub_ids:
        # 이전에 api.py나 인라인 코드로 검증에 성공한 API 호출 파트
        api_url = f"https://ebird.org{sid}"
        api_key = os.environ.get("EBIRD_API_KEY")
        api_res = requests.get(api_url, headers={"X-eBirdApiToken": api_key}, timeout=10)
        
        if api_res.status_code == 200:
            data = api_res.json()
            loc_name = data.get('loc', {}).get('name', 'Unknown Location')
            if len(loc_name) > 30: loc_name = loc_name[:27] + "..."
            
            date = data.get('obsDt', '').split(' ')[0] # 날짜만 추출
            birds = [obs.get('comName') for obs in data.get('obs', []) if obs.get('comName')]
            birds_summary = ", ".join(birds[:2]) + (f" 외 {len(birds)-2}종" if len(birds) > 2 else "") if birds else "기록된 종 없음"
            if len(birds_summary) > 42: birds_summary = birds_summary[:39] + "..."
            
            formatted_checklists.append({
                "loc_name": loc_name,
                "date": date,
                "birds_summary": birds_summary
            })

    # 2. default.svg 템플릿을 읽어와서 데이터 주입
    # src/ebird_readme_card/templates/default.svg 경로를 정확히 동적으로 탐색합니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, 'templates', 'default.svg')
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = Template(f.read())
        
    svg_output = template.render(checklists=formatted_checklists)
    
    # 3. 최상위 루트 경로에 카드로 저장
    with open("ebird-card.svg", "w", encoding="utf-8") as f:
        f.write(svg_output)
    print("🎉 성공적으로 ebird-card.svg 카드가 기본 템플릿으로 빌드되었습니다.")

if __name__ == "__main__":
    # 이제 스크래퍼 파일을 단독 호출하면 렌더링까지 한 번에 완료됩니다.
    get_data_and_render()

