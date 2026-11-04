import requests
from bs4 import BeautifulSoup
import datetime

def get_news(query, max_articles=10):
    search_url = f"https://search.naver.com/search.naver?where=news&query={query}"
    
    # 봇 차단 방지용 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 뉴스 기사 단위 박스
    articles = soup.select("div.news_wrap.api_ani_send")
    
    collected_data = []
    
    for article in articles[:max_articles]:
        try:
            # 제목 추출
            title_tag = article.select_one("a.news_tit")
            title = title_tag.text.strip() if title_tag else "제목 없음"
            
            # 언론사 추출 ('언론사 선정' 같은 불필요한 글자 제거)
            source_tag = article.select_one("a.info.press")
            source = source_tag.text.replace("언론사 선정", "").strip() if source_tag else "출처 없음"
            
            # 본문 미리보기 추출
            content_tag = article.select_one("div.news_dsc")
            content = content_tag.text.strip() if content_tag else "내용 없음"
            
            collected_data.append({
                "title": title,
                "source": source,
                "content": content
            })
        except Exception as e:
            continue

    return collected_data

def save_to_txt(data_list, filename):
    # 만약 수집된 기사가 0개일 경우, 빈 깡통 대신 안내 문구를 적어줍니다.
    if not data_list:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("기사를 수집하지 못했습니다. 네이버 검색 결과가 없거나 깃허브 접속이 차단되었습니다.\n")
        return

    # 정상적으로 수집되었을 경우 텍스트 파일 작성
    with open(filename, "w", encoding="utf-8") as f:
        for i, data in enumerate(data_list, 1):
            f.write(f"[{i}번 기사]\n")
            f.write(f"제목: {data['title']}\n")
            f.write(f"출처: {data['source']}\n")
            f.write(f"본문 요약: {data['content']}\n")
            f.write("-" * 50 + "\n\n")

if __name__ == "__main__":
    search_keyword = "대구 부동산 경매"
    
    # NotebookLM이 넉넉하게 읽을 수 있도록 핵심 기사 10개를 긁어옵니다.
    news_data = get_news(search_keyword, max_articles=10)
    
    today = datetime.datetime.now().strftime("%Y%m%d")
    file_name = f"대구부동산뉴스_{today}.txt"
    
    save_to_txt(news_data, filename=file_name)
