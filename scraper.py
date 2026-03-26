import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from urllib.parse import urljoin
import urllib3

# [추가] 로카 등 소규모 사이트의 SSL 인증서 경고를 숨기고 접속을 강제하기 위함
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

data = {
    "kofic": [],
    "cine21": [],
    "krmedia": [],
    "kofa": [],
    "dureraum": [],
    "kmrb": [],
    "theloca": [],
    "last_updated": ""
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_soup(url):
    try:
        # [수정] verify=False를 추가하여 보안 인증서 에러를 무시하고 긁어옵니다.
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"접속 에러 ({url}): {e}")
        return None

def extract_date(text):
    match = re.search(r'(20\d{2})[-./](\d{2})[-./](\d{2})', text)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""

# 1. 영화진흥위원회 맞춤형 스크래퍼 (포함 및 제외 키워드 필터 기능 추가)
def scrape_kofic(url, prefix, include_keyword="", exclude_keyword=""):
    soup = get_soup(url)
    if not soup: return
    
    for row in soup.select('table tbody tr'):
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue
        
        # [조건 1] 포함해야 할 단어("채용")가 제목에 없으면 건너뜁니다.
        if include_keyword and include_keyword not in title:
            continue
            
        # [조건 2] 제외해야 할 단어("합격")가 제목에 있으면 건너뜁니다.
        if exclude_keyword and exclude_keyword in title:
            continue
        
        href = a_tag.get('href', '')
        onclick = a_tag.get('onclick', '')
        
        link = urljoin(url, href)
        js_code = href + onclick
        if 'javascript' in js_code:
            nums = re.findall(r"['\"]?(\d{4,})['\"]?", js_code)
            if nums:
                if 'selectBoardList' in url:
                    link = f"https://www.kofic.or.kr/kofic/business/board/selectBoardDetail.do?boardNumber=4&boardSeqNumber={nums[0]}"
                elif 'findJobList' in url:
                    link = f"https://www.kofic.or.kr/kofic/business/infm/findJobDetail.do?seqNo={nums[0]}"
        
        date = extract_date(row.text)
        data["kofic"].append({"title": f"[{prefix}] {title}", "link": link, "date": date})      
        
# 2. 범용 스크래퍼 (한국영상자료원, 영화의전당, 아카데미 로카 통합 처리용)
def scrape_general(key, url, include_keyword="", exclude_keyword=""):
    soup = get_soup(url)
    if not soup: return
    
    # [수정] <tbody> 태그가 생략된 로카 게시판을 위한 예외 처리 (없으면 table tr로 찾음)
    rows = soup.select('table tbody tr')
    if not rows:
        rows = soup.select('table tr')
        
    for row in rows:
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue
        
        if include_keyword and include_keyword not in title: continue
        if exclude_keyword and exclude_keyword in title: continue
        
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

# 4. 영상물등급위원회 맞춤형 스크래퍼
def scrape_kmrb(url, include_keyword="", exclude_keyword=""):
    soup = get_soup(url)
    if not soup: return
    
    for row in soup.select('table tbody tr'):
        a_tag = row.select_one('a')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        if not title: continue
        
        if include_keyword and include_keyword not in title: continue
        if exclude_keyword and exclude_keyword in title: continue
        
        # [수정] <a> 태그뿐만 아니라 <tr> 전체 HTML에서 게시글 고유 번호를 샅샅이 뒤져 찾아냅니다.
        row_html = str(row)
        link = "#"
        
        # 4자리 이상의 숫자를 모두 찾습니다.
        nums = re.findall(r"\d{4,}", row_html)
        nttSn = None
        for num in nums:
            # 메뉴번호(1111), 게시판번호(1009), 연도(2024~2027)를 제외한 첫 번째 큰 숫자가 무조건 게시글 고유번호(nttSn)입니다.
            if num not in ["1111", "1009", "2024", "2025", "2026", "2027"]:
                nttSn = num
                break
        
        if nttSn:
            link = url.replace('selectNttList.do', 'selectNttInfo.do') + f"&nttSn={nttSn}"
        else:
            href = a_tag.get('href', '')
            if href and href != "#" and "javascript" not in href:
                link = urljoin(url, href)
        
        date = extract_date(row.text)
        data["kmrb"].append({"title": title, "link": link, "date": date})

# ==========================================
# 실행부
# ==========================================

print("1. 영화진흥위원회 크롤링 중...")
# 1) 공지사항 수집: "채용"은 포함하고, "합격"은 제외합니다.
scrape_kofic("https://www.kofic.or.kr/kofic/business/board/selectBoardList.do?boardNumber=4", "공지", "채용", "합격")

# 2) 구인정보 수집: 키워드 제한 없이 모두 가져옵니다.
scrape_kofic("https://www.kofic.or.kr/kofic/business/infm/findJobList.do", "구인")

# 위에서부터 총 10개만 웹페이지에 노출합니다.
data["kofic"] = data["kofic"][:10]

print("2. 씨네21 크롤링 중...")
scrape_cine21()
data["cine21"] = data["cine21"][:10]

print("3. 전국미디어센터협의회 크롤링 중...")
# 키워드 없이 호출하여 기존처럼 모든 글을 가져옵니다.
scrape_general("krmedia", "http://www.krmedia.org/pages/page_100.php")
data["krmedia"] = data["krmedia"][:10]

print("4. 한국영상자료원 크롤링 중...")
# "채용"이 들어간 글만 수집하고, "합격"이 들어간 글은 제외합니다.
scrape_general("kofa", "https://www.koreafilm.or.kr/kofa/news/recruit", "채용", "합격")
data["kofa"] = data["kofa"][:10]

print("5. 영화의전당 크롤링 중...")
# "채용"이 들어간 글만 수집하고, "합격"이 들어간 글은 제외합니다.
scrape_general("dureraum", "https://www.dureraum.org/bcc/board/list.do?rbsIdx=64", "채용", "합격")
data["dureraum"] = data["dureraum"][:10]

print("6. 영상물등급위원회 크롤링 중...")
# "채용" 단어가 들어간 글은 수집하고, "합격" 단어가 들어간 글은 제외합니다.
scrape_kmrb("https://www.kmrb.or.kr/main/na/ntt/selectNttList.do?mi=1111&bbsId=1009", "채용", "합격")
data["kmrb"] = data["kmrb"][:10]

print("7. 아카데미 로카 크롤링 중...")
# 세션ID(PHPSESSID)를 제거한 깔끔한 원본 URL 사용
scrape_general("theloca", "https://www.theloca.kr/HyAdmin/list.php?bbs_id=bo05")
data["theloca"] = data["theloca"][:10]

# 업데이트 시간 기록
data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# JSON 파일로 저장
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("크롤링 완료! 에러가 수정된 데이터가 저장되었습니다.")
