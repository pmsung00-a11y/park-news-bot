import requests
from bs4 import BeautifulSoup
import datetime

def get_naver_news(query, max_articles=5):
    """
    네이버 뉴스에서 특정 키워드로 검색하여 기사 링크를 수집하고,
    제목, 언론사, 날짜, 본문을 추출하여 텍스트 파일로 저장합니다.
    """
    # 네이버 뉴스 검색 URL (정확도 순)
    search_url = f"https://search.naver.com/search.naver?where=news&query={query}"
    
    # 봇 차단을 막기 위한 User-Agent 설정
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 네이버 뉴스 링크만 추출 (언론사 자체 링크 제외)
    articles = soup.select("div.info_group > a.info:nth-of-type(2)")
    
    collected_data = []
    
    for article in articles[:max_articles]:
        news_url = article["href"]
        try:
            news_resp = requests.get(news_url, headers=headers)
            news_soup = BeautifulSoup(news_resp.text, 'html.parser')
            
            # 제목 추출
            title = news_soup.select_one("h2#title_area > span").text.strip()
            
            # 언론사 추출
            source = news_soup.select_one("a.media_end_head_top_logo > img")["title"]
            
            # 날짜 추출
            date_time = news_soup.select_one("span.media_end_head_info_datestamp_time").text.strip()
            
            # 본문 추출
            content = news_soup.select_one("article#dic_area").text.strip()
            # 본문 내 불필요한 줄바꿈 및 공백 정리
            content = " ".join(content.split()) 
            
            collected_data.append({
                "title": title,
                "source": source,
                "date": date_time,
                "content": content
            })
            print(f"수집 완료: {title}")
            
        except Exception as e:
            print(f"수집 실패 ({news_url}): {e}")
            continue

    return collected_data

def save_to_txt(data_list, filename="weekly_news.txt"):
    """수집된 기사 데이터를 NotebookLM 업로드용 텍스트 파일로 저장합니다."""
    with open(filename, "w", encoding="utf-8") as f:
        for i, data in enumerate(data_list, 1):
            f.write(f"[{i}번 기사]\n")
            f.write(f"제목: {data['title']}\n")
            f.write(f"출처: {data['source']}\n")
            f.write(f"날짜: {data['date']}\n")
            f.write(f"본문: {data['content']}\n")
            f.write("-" * 50 + "\n\n")
    print(f"\n총 {len(data_list)}개의 기사가 '{filename}'에 저장되었습니다.")

# --- 실행 부분 ---
if __name__ == "__main__":
    # 검색어 및 수집할 기사 개수 설정
    search_keyword = "대구 부동산 경매"
    
    print(f"[{search_keyword}] 뉴스 수집을 시작합니다...")
    news_data = get_naver_news(search_keyword, max_articles=5)
    
    # 오늘 날짜를 파일명에 포함하여 저장
    today = datetime.datetime.now().strftime("%Y%m%d")
    save_to_txt(news_data, filename=f"대구부동산뉴스_{today}.txt")
