# ==============================================================================
# 해든부동산 오픈 준비 - 당근마켓 실시간 꿀매물 모니터링 & 지메일 알림 봇
# ==============================================================================

import os
import smtplib
import time
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def check_daangn_market_and_notify():
  sender_email = "pmsung00@gmail.com"
  sender_password = os.environ.get("GMAIL_APP_PASSWORD")

  if not sender_password:
    print("[!] 지메일 앱 비밀번호(GMAIL_APP_PASSWORD)가 설정되지 않았습니다.")
    return

  # 깃허브 액션 서버 환경을 위한 크롬 헤드리스 옵션
  options = Options()
  options.add_argument("--headless")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")

  try:
    print("[*] 크롬 웹드라이버를 초기화합니다...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
  except Exception as e:
    print(f"[!] 웹드라이버 실행 실패: {e}")
    return

  # 검색할 키워드 목록 (필요에 따라 추가/수정 가능)
  keywords = ["컴퓨터 본체", "27인치 모니터"]
  collected_items = []

  try:
    for keyword in keywords:
      url = f"https://www.daangn.com/search/{urllib.parse.quote(keyword)}"
      print(f"[*] 당근마켓 '{keyword}' 검색 페이지 접속 중...")
      driver.get(url)
      time.sleep(3)

      items = driver.find_elements(By.CSS_SELECTOR, "article.flea-market-article")
      print(f"[*] '{keyword}' 검색 결과: {len(items)}개 발견")

      for item in items[:3]:  # 최신 상위 3개 추출
        try:
          title = item.find_element(
              By.CSS_SELECTOR, "span.article-title"
          ).text
          price = item.find_element(
              By.CSS_SELECTOR, "span.article-price"
          ).text
          link = item.find_element(
              By.CSS_SELECTOR, "a.flea-market-link"
          ).get_attribute("href")

          collected_items.append(
              f"• 검색어: {keyword}\n  - 제목: {title}\n  - 가격:"
              f" {price}\n  - 링크: {link}\n"
          )
        except Exception as ex:
          print(f"[파싱 예외 무시]: {ex}")
          continue
  finally:
    driver.quit()
    print("[*] 브라우저를 종료합니다.")

  # 수집된 매물이 있는 경우에만 지메일 발송
  if collected_items:
    print("[*] 수집된 매물이 있어 지메일 발송을 준비합니다...")
    msg = MIMEMultipart()
    msg["From"], msg["To"] = sender_email, sender_email
    msg["Subject"] = "[해든부동산 오픈준비] 당근마켓 실시간 꿀매물 수집 리포트"

    body = (
        "형님! 해든 부동산중개사사무소 오픈용으로 수집된 당근마켓 실시간"
        " 매물입니다.\n\n" + "\n".join(collected_items) + "\n빠르게 확인해 보세요!"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
      server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
      server.login(sender_email, sender_password)
      server.sendmail(sender_email, sender_email, msg.as_string())
      server.quit()
      print(
          "[*] 당근마켓 꿀매물 리포트가 지메일로 성공적으로 발송되었습니다!"
      )
    except Exception as e:
      print(f"[!] 지메일 메일 발송 실패: {e}")
  else:
    print("[*] 조건에 맞는 새로운 당근마켓 매물이 없습니다.")


if __name__ == "__main__":
  check_daangn_market_and_notify()
