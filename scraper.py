import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# 결과를 담을 딕셔너리
data = {
    "kofic": [],
    "cine21": [],
    "krmedia": [],
    "kofa": [],
    "dureraum": [],
    "last_updated": ""
}

# 봇(Bot) 차단을 막기 위한 일반 브라우저 헤더 위장
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_soup(url):
    """URL에 접속하여 BeautifulSoup 객체를 반환합니다."""
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        # 한글 깨짐 방지를 위한 인코딩 설정
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"접속 에러 ({url}): {e}")
        return None

def extract_date(text):
    """텍스트에서 YYYY-MM-DD 또는 YYYY.MM.DD 형태의 날짜를 똑똑하게 찾아냅니다."""
    match = re.search(r'(20\d{2})[-./](\d{2})[-./](\d{2})', text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return ""

def scrape_general_board(url, base_url, board_type=""):
    """일반적인 테이블(Table) 구조 게시판을 위한 범용 크롤링 함수입니다."""
    results = []
    soup = get_soup(url)
    if not soup: return results

    # 대부분의 국내 게시판은 table > tbody > tr 구조를 가집니다.
    rows = soup.select('table tbody tr')
    
    for row in rows:
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue # 제목이 비어있으면 건너뜀
        if board_type: title = f"[{board_type}] {title}"
        
        # 링크 절대경로 변환
        link = a_tag.get('href', '')
        if link.startswith('/'):
            link = base_url + link
        elif not link.startswith('http') and not link.startswith('javascript'):
            link = url.split('?')[0] + link if link.startswith('?') else base_url + "/" + link

        # 해당 게시판 행(tr)의 텍스트 전체에서 날짜 형식을 추출
        date = extract_date(row.text)
        
        results.append({
            "title": title,
            "link": link,
            "date": date
        })
        
        # 각 게시판당 최신 글 10개만 가져오기
        if len(results) >= 10: break
            
    return results

# ==========================================
# 각 기관별 크롤링 실행
# ==========================================

# 1. 영화진흥위원회 (공지사항 & 구인구직 통합)
print("영화진흥위원회 크롤링 중...")
data["kofic"].extend(scrape_general_board("https://www.kofic.or.kr/kofic/business/board/selectBoardList.do?boardNumber=4", "https://www.kofic.or.kr", "공지"))
data["kofic"].extend(scrape_general_board("https://www.kofic.or.kr/kofic/business/infm/findJobList.do", "https://www.kofic.or.kr", "구인"))
# 날짜 순으로 재정렬 (최신순)
data["kofic"] = sorted(data["kofic"], key=lambda x: x['date'], reverse=True)[:10]

# 2. 씨네21 (일반 테이블 구조가 아닐 수 있어 링크 패턴으로 탐색)
print("씨네21 크롤링 중...")
cine_soup = get_soup("https://cine21.com/community/recruit")
if cine_soup:
    for a in cine_soup.select('a[href*="/community/recruit/read"]'):
        title = a.text.strip()
        if title:
            link = "https://cine21.com" + a['href'] if a['href'].startswith('/') else a['href']
            date = extract_date(a.parent.parent.text) # 주변 텍스트에서 날짜 추출
            
            # 중복 데이터 삽입 방지
            if not any(item['link'] == link for item in data["cine21"]): 
                data["cine21"].append({"title": title, "link": link, "date": date})
        if len(data["cine21"]) >= 10: break

# 3. 전국미디어센터협의회
print("전국미디어센터협의회 크롤링 중...")
data["krmedia"].extend(scrape_general_board("http://www.krmedia.org/pages/page_100.php", "http://www.krmedia.org"))

# 4. 한국영상자료원
print("한국영상자료원 크롤링 중...")
data["kofa"].extend(scrape_general_board("https://www.koreafilm.or.kr/kofa/news/recruit", "https://www.koreafilm.or.kr"))

# 5. 영화의전당
print("영화의전당 크롤링 중...")
data["dureraum"].extend(scrape_general_board("https://www.dureraum.org/bcc/board/list.do?rbsIdx=64", "https://www.dureraum.org"))

# 업데이트 시간 기록
data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# JSON 파일로 저장
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("크롤링 완료! data.json 파일이 생성되었습니다.")
