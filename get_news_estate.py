import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import datetime

def get_google_news(query, max_articles=10):
    # 한국어 검색어 변환 및 구글 뉴스 공식 주소 연결
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    # 구글 뉴스 요청
    req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        channel = root.find('channel')
        
        collected_data = []
        
        # 뉴스 기사 쏙쏙 뽑아내기
        for item in channel.findall('item')[:max_articles]:
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
            f.write("기사를 수집하지 못했습니다.\n")
        return

    with open(filename, "w", encoding="utf-8") as f:
        for i, data in enumerate(data_list, 1):
            f.write(f"[{i}번 기사]\n")
            f.write(f"제목: {data['title']}\n")
            f.write(f"출처: {data['source']}\n")
            f.write(f"발행일: {data['date']}\n")
            f.write("-" * 50 + "\n\n")

if __name__ == "__main__":
    search_keyword = "대구 부동산 경매"
    
    # 구글 뉴스에서 핵심 기사 10개를 긁어옵니다.
    news_data = get_google_news(search_keyword, max_articles=10)
    
    today = datetime.datetime.now().strftime("%Y%m%d")
    file_name = f"대구부동산뉴스_{today}.txt"
    
    save_to_txt(news_data, filename=file_name)
