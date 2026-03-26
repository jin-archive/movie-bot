import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# 결과를 담을 딕셔너리 (요청하신 순서대로 키 구성)
data = {
    "kofic": [],      # 영화진흥위원회 (공지, 구인구직 통합)
    "cine21": [],     # 씨네21
    "krmedia": [],    # 전국미디어센터협의회
    "kofa": [],       # 한국영상자료원
    "dureraum": [],   # 영화의전당
    "last_updated": ""
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def dummy_scrape(source_key, title_prefix):
    """
    실제 크롤링 로직이 들어갈 자리입니다.
    현재는 웹페이지에 렌더링 테스트를 할 수 있도록 임시 데이터를 생성합니다.
    """
    for i in range(1, 6):
        data[source_key].append({
            "title": f"[{title_prefix}] 테스트 게시글 제목 {i}입니다.",
            "link": "#",
            "date": "2024-05-01"
        })

# 실제 구현 시에는 requests와 BeautifulSoup을 이용해 아래 함수들을 완성합니다.
# fetch_kofic_boards()
# fetch_cine21()
# fetch_krmedia()
# fetch_kofa()
# fetch_dureraum()

# 임시 데이터 삽입 (테스트용)
dummy_scrape("kofic", "영화진흥위원회")
dummy_scrape("cine21", "씨네21")
dummy_scrape("krmedia", "전국미디어센터협의회")
dummy_scrape("kofa", "한국영상자료원")
dummy_scrape("dureraum", "영화의전당")

# 업데이트 시간 기록 (KST 기준 처리가 필요하다면 pytz 등 활용)
data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# JSON 파일로 저장 (웹페이지에서 이 파일을 읽어들임)
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("Scraping completed and saved to data.json")
