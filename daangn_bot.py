import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def crawl_daangn_market(keyword):
  # 1. 크롬 브라우저 옵션 설정 (안전한 실행을 위함)
  options = Options()
  # options.add_argument("--headless")  # 브라우저 창을 띄우지 않고 백그라운드로 실행하려면 주석 해제
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")

  # 2. 크롬 드라이버 자동 세팅 및 실행
  service = Service(ChromeDriverManager().install())
  driver = webdriver.Chrome(service=service, options=options)

  try:
    # 3. 당근마켓 통합 검색 페이지 접속 (예: 대구 지역 검색 또는 키워드 검색)
    # URL 구조 예시 (검색어 인코딩)
    url = f"https://www.daangn.com/search/{keyword}"
    print(f"[*] '{keyword}' 검색 페이지에 접속합니다...")
    driver.get(url)

    # 페이지가 로딩될 때까지 대기
    time.sleep(3)

    # 4. 스크롤을 내려서 더 많은 매물 불러오기 (필요시 반복)
    for _ in range(2):
      driver.execute_script(
          "window.scrollTo(0, document.body.scrollHeight);"
      )
      time.sleep(2)

    # 5. 매물 리스트 요소 수집 (당근마켓 웹 구조에 맞는 태그 선택자 활용)
    # 주의: 당근마켓 웹 UI 구조에 따라 클래스명은 변경될 수 있습니다.
    items = driver.find_elements(By.CSS_SELECTOR, "article.flea-market-article")

    print(f"[*] 총 {len(items)}개의 물품을 수집했습니다.\n" + "=" * 40)

    results = []
    for item in items:
      try:
        title = item.find_element(
            By.CSS_SELECTOR, "span.article-title"
        ).text
        price = item.find_element(
            By.CSS_SELECTOR, "span.article-price"
        ).text
        link = item.find_element(By.CSS_SELECTOR, "a.flea-market-link").get_attribute(
            "href"
        )

        print(f"- 제목: {title}")
        print(f"- 가격: {price}")
        print(f"- 링크: {link}")
        print("-" * 30)

        results.append({"title": title, "price": price, "link": link})
      except Exception as e:
        # 일부 광고나 레이아웃이 다른 항목 예외 처리
        continue

    return results

  finally:
    # 작업 완료 후 브라우저 종료
    driver.quit()


# 실행 테스트 (예: '컴퓨터 본체' 검색)
if __name__ == "__main__":
  search_keyword = "컴퓨터 본체"
  crawl_daangn_market(search_keyword)
