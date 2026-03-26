import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin

data = {
    "kofic": [],
    "cine21": [],
    "krmedia": [],
    "kofa": [],
    "dureraum": [],
    "last_updated": ""
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_soup(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"접속 에러 ({url}): {e}")
        return None

def extract_date(text):
    match = re.search(r'(20\d{2})[-./](\d{2})[-./](\d{2})', text)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""

# 1. 영화진흥위원회 맞춤형 스크래퍼
def scrape_kofic(url, prefix):
    soup = get_soup(url)
    if not soup: return
    
    for row in soup.select('table tbody tr'):
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue
        
        href = a_tag.get('href', '')
        onclick = a_tag.get('onclick', '')
        
        # 영진위는 자바스크립트로 링크를 넘기는 경우가 많아 숫자(게시글 번호)를 강제 추출합니다.
        link = urljoin(url, href)
        js_code = href + onclick
        if 'javascript' in js_code:
            nums = re.findall(r"['\"]?(\d{4,})['\"]?", js_code) # 4자리 이상 숫자(게시물 ID) 찾기
            if nums:
                if 'selectBoardList' in url:
                    link = f"https://www.kofic.or.kr/kofic/business/board/selectBoardDetail.do?boardNumber=4&boardSeqNumber={nums[0]}"
                elif 'findJobList' in url:
                    link = f"https://www.kofic.or.kr/kofic/business/infm/findJobDetail.do?seqNo={nums[0]}"
        
        date = extract_date(row.text)
        data["kofic"].append({"title": f"[{prefix}] {title}", "link": link, "date": date})

# 2. 범용 스크래퍼 (한국영상자료원, 전국미디어센터, 영화의전당)
def scrape_general(key, url):
    soup = get_soup(url)
    if not soup: return
    
    for row in soup.select('table tbody tr'):
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue
        
        # urljoin을 사용하면 상대경로('/kofa/...')나 파라미터('?idx=...')를 알아서 완벽한 주소로 조립해줍니다. (404 에러, 홈화면 이동 해결)
        link = urljoin(url, a_tag.get('href', ''))
        date = extract_date(row.text)
        
        data[key].append({"title": title, "link": link, "date": date})

# 3. 씨네21 맞춤형 스크래퍼 (테이블이 아닌 리스트 형태일 가능성 대비)
def scrape_cine21():
    url = "https://cine21.com/community/recruit"
    soup = get_soup(url)
    if not soup: return
    
    # 씨네21은 구조가 다를 수 있어 구인/구직 관련 링크를 넓게 탐색합니다.
    # 클래스명에 의존하지 않고 링크에 'read'나 'view'가 포함된 경우를 찾습니다.
    for a_tag in soup.select('a'):
        href = a_tag.get('href', '')
        if 'community/recruit/read' in href or 'recruit/view' in href:
            title = a_tag.text.strip()
            if len(title) > 3: # "더보기" 같은 버튼 텍스트 제외
                link = urljoin(url, href)
                # 부모 태그 근처에서 날짜 추출 시도
                parent_text = a_tag.parent.parent.text if a_tag.parent.parent else ""
                date = extract_date(parent_text)
                
                # 중복 방지
                if not any(item['link'] == link for item in data["cine21"]):
                    data["cine21"].append({"title": title, "link": link, "date": date})

# ==========================================
# 실행부
# ==========================================

print("1. 영화진흥위원회 크롤링 중...")
scrape_kofic("https://www.kofic.or.kr/kofic/business/board/selectBoardList.do?boardNumber=4", "공지")
scrape_kofic("https://www.kofic.or.kr/kofic/business/infm/findJobList.do", "구인")
data["kofic"] = sorted(data["kofic"], key=lambda x: x['date'], reverse=True)[:10]

print("2. 씨네21 크롤링 중...")
scrape_cine21()
data["cine21"] = data["cine21"][:10]

print("3. 전국미디어센터협의회 크롤링 중...")
scrape_general("krmedia", "http://www.krmedia.org/pages/page_100.php")
data["krmedia"] = data["krmedia"][:10]

print("4. 한국영상자료원 크롤링 중...")
scrape_general("kofa", "https://www.koreafilm.or.kr/kofa/news/recruit")
data["kofa"] = data["kofa"][:10]

print("5. 영화의전당 크롤링 중...")
scrape_general("dureraum", "https://www.dureraum.org/bcc/board/list.do?rbsIdx=64")
data["dureraum"] = data["dureraum"][:10]

# 업데이트 시간 기록
data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# JSON 파일로 저장
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("크롤링 완료! 에러가 수정된 데이터가 저장되었습니다.")
