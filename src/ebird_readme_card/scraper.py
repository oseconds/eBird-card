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

if __name__ == "__main__":
    # 로컬 테스트용 실행 코드 (.env 파일에 EBIRD_USER_ID가 적혀있어야 합니다)
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        scraper = EBirdProfileScraper()
        scraper.fetch_recent_checklist_ids()
    except Exception as e:
        print(e)
