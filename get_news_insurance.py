import feedparser
from datetime import datetime, timedelta
import os

# 1. 보험 및 금융 공기관 / 전문 매체 RSS 소스 딕셔너리 정의
NEWS_SOURCES = {
    "금융위원회": "https://www.fsc.go.kr/rss/bbs0199.xml",
    "금융감독원": "https://www.fss.or.kr/fss/bbs/B0000199/rss.do",
    "보험신보": "https://www.insnews.co.kr/_custom/insnews/-rss/rss.xml",
    "한국보험신문": "https://www.insn.co.kr/rss/allArticle.xml",
    "보험매일": "https://www.fins.co.kr/rss/allArticle.xml",
    "보험저널": "https://www.insjournal.co.kr/rss/allArticle.xml"
}

def collect_insurance_news():
    print("=== [박씨네 보험톡] 주간 보험·금융 뉴스 자동 수집 시작 ===")
    
    collected_articles = []
    # 기준일: 최근 7일 이내 기사만 필터링
    one_week_ago = datetime.now() - timedelta(days=7)
    
    for source_name, url in NEWS_SOURCES.items():
        try:
            print(f"수집 중: {source_name} ({url})")
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                # 발행일 파싱
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6])
                else:
                    pub_date = datetime.now()
                
                # 최근 7일 이내 기사만 선별
                if pub_date >= one_week_ago:
                    title = entry.title.strip()
                    link = entry.link.strip()
                    summary = getattr(entry, 'summary', title).strip()
                    
                    # 괄호 짝 오류 수정 완료 부분
                    collected_articles.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "summary": summary
                    })
            print(f" -> {source_name}: {len(feed.entries)}개 중 최근 기사 필터링 완료")
        except Exception as e:
            print(f" [오류 발생] {source_name} 수집 실패: {e}")

    # 2. 결과물 텍스트 파일(주간보험뉴스.txt)로 저장
    output_filename = "주간보험뉴스.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"=== [박씨네 보험톡] 주간 보험·금융 이슈 수집 결과 ({datetime.now().strftime('%Y-%m-%d')}) ===\n\n")
        
        for idx, article in enumerate(collected_articles, 1):
            f.write(f"[{idx}] [{article['source']}] {article['title']}\n")
            f.write(f"- 날짜: {article['date']}\n")
            f.write(f"- 링크: {article['link']}\n")
            f.write(f"- 내용: {article['summary']}\n")
            f.write("-" * 80 + "\n")
            
    print(f"=== 총 {len(collected_articles)}개의 뉴스가 '{output_filename}'에 성공적으로 저장되었습니다. ===")

if __name__ == "__main__":
    collect_insurance_news()
