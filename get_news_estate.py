import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import datetime

def get_google_news(query, max_articles=10):
    # 핵심: 검색어 뒤에 'when:7d'를 붙여 무조건 최근 1주일 기사만 가져오도록 강제합니다.
    search_query = f"{query} when:7d"
    encoded_query = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        channel = root.find('channel')
        
        collected_data = []
        if channel is not None:
            for item in channel.findall('item'):
                # 정해진 개수까지만 수집
                if len(collected_data) >= max_articles:
                    break
                
                title = item.find('title').text if item.find('title') is not None else "제목 없음"
                source = item.find('source').text if item.find('source') is not None else "출처 없음"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "날짜 없음"
                
                collected_data.append({
                    "title": title,
                    "source": source,
                    "date": pub_date
                })
        return collected_data
        
    except Exception as e:
        print("에러 발생:", e)
        return []

def save_to_txt(data_list, filename):
    if not data_list:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("최근 1주일간의 기사를 수집하지 못했습니다.\n")
        return

    with open(filename, "w", encoding="utf-8") as f:
        for i, data in enumerate(data_list, 1):
            # 전국 기사가 섞일 수 있으므로 카테고리를 달아줍니다.
            f.write(f"[{i}번 기사]\n")
            f.write(f"제목: {data['title']}\n")
            f.write(f"출처: {data['source']}\n")
            f.write(f"발행일: {data['date']}\n")
            f.write("-" * 50 + "\n\n")

if __name__ == "__main__":
    # 1단계: 대구/경북 지역 뉴스를 우선적으로 찾습니다.
    local_keyword = "대구 OR 경북 부동산 (경매 OR 매매 OR 분양)"
    news_data = get_google_news(local_keyword, max_articles=10)
    
    # 2단계: 지역 뉴스가 10개에 못 미치면, 부족한 개수만큼 전국 핫이슈를 긁어와 채웁니다.
    if len(news_data) < 10:
        shortage = 10 - len(news_data)
        # 전국구 주요 키워드: 대출, 금리, 규제, 정책 등
        national_keyword = "부동산 (대출 OR 금리 OR 규제 OR 정책 OR 아파트)"
        national_news = get_google_news(national_keyword, max_articles=shortage)
        news_data.extend(national_news)
    
    file_name = "주간부동산뉴스.txt"
    
    save_to_txt(news_data, filename=file_name)
