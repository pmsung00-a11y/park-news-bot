# ==============================================================================
# 박씨네 보험톡 방송국 - 그랜드 마스터 V24 (하단 박스 본문 길이 100% 핏팅)
# (오디오 기계음 제거, 하단 힐링박스 가로길이 본문과 동일, 전일종가 국내API 고정)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
import textwrap
import subprocess
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import moviepy.audio.fx.all as afx  # 기계음 방지용 페이드아웃 효과

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# ------------------------------------------------------------------------------
# 1. FFmpeg 1.4배속 쾌속 엔진 
# ------------------------------------------------------------------------------
def speedup_audio_ffmpeg(input_path, output_path, speed=1.4):
    cmd = ['ffmpeg', '-y', '-i', input_path, '-filter:a', f'atempo={speed}', '-ar', '44100', output_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"오디오 가속 실패, 원본 변환: {e}")
        fallback_cmd = ['ffmpeg', '-y', '-i', input_path, '-ar', '44100', output_path]
        try:
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path
        except:
            pass
    return input_path

# ------------------------------------------------------------------------------
# 2. 뉴스 크롤러 
# ------------------------------------------------------------------------------
def fetch_one_top_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        root = ET.fromstring(response.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            
            publisher = ""
            news_title = title
            
            if ' - ' in title:
                parts = title.rsplit(' - ', 1)
                news_title = parts[0]
                publisher = parts[1]
            elif title.startswith('['):
                match = re.match(r'^\[(.*?)\]\s*(.*)', title)
                if match:
                    publisher = match.group(1)
                    news_title = match.group(2)
                    
            if len(news_title) > 8:
                if publisher:
                    return f"{news_title.strip()}|[{publisher.strip()}]"
                else:
                    return f"{news_title.strip()}|"
    except Exception:
        pass
    return f"{keyword} 최신 뉴스를 업데이트 중입니다.|[시스템]"

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news_items.append(fetch_one_top_news(keyword))
    return news_items

# ------------------------------------------------------------------------------
# 3. 경제 지표 수집 (국내 증시 전일 마감 종가 정밀 타겟팅)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "2,583.27 (▲0.09%)", "kosdaq": "727.41 (▼0.98%)", "usd": "1,390.50원"}
    
    try:
        daum_headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'}
        k_res = requests.get("https://finance.daum.net/api/domestic/sectors/KOSPI/quotes", headers=daum_headers, timeout=5).json()
        s1 = "▲" if k_res['changeRate'] > 0 else "▼" if k_res['changeRate'] < 0 else "-"
        indicators["kospi"] = f"{k_res['tradePrice']:,.2f} ({s1}{abs(k_res['changeRate']*100):.2f}%)"
        
        kd_res = requests.get("https://finance.daum.net/api/domestic/sectors/KOSDAQ/quotes", headers=daum_headers, timeout=5).json()
        s2 = "▲" if kd_res['changeRate'] > 0 else "▼" if kd_res['changeRate'] < 0 else "-"
        indicators["kosdaq"] = f"{kd_res['tradePrice']:,.2f} ({s2}{abs(kd_res['changeRate']*100):.2f}%)"
    except Exception:
        try:
            q_kospi = urllib.parse.quote("코스피지수")
            res1 = requests.get(f"https://m.search.naver.com/search.naver?query={q_kospi}", headers=HEADERS, timeout=5).text
            m_p1 = re.search(r'<strong>([\d,.]+)</strong>\s*<span class="blind">코스피지수', res1)
            m_c1 = re.search(r'em class="(up|down)">([\d,.]+)%</em>', res1)
            if m_p1:
                p = m_p1.group(1)
                sign = "▲" if (m_c1 and m_c1.group(1)=="up") else "▼"
                rate = m_c1.group(2) if m_c1 else "0.00"
                indicators["kospi"] = f"{p} ({sign}{rate}%)"
                
            q_kosdaq = urllib.parse.quote("코스닥지수")
            res2 = requests.get(f"https://m.search.naver.com/search.naver?query={q_kosdaq}", headers=HEADERS, timeout=5).text
            m_p2 = re.search(r'<strong>([\d,.]+)</strong>\s*<span class="blind">코스닥지수', res2)
            m_c2 = re.search(r'em class="(up|down)">([\d,.]+)%</em>', res2)
            if m_p2:
                p = m_p2.group(1)
                sign = "▲" if (m_c2 and m_c2.group(1)=="up") else "▼"
                rate = m_c2.group(2) if m_c2 else "0.00"
                indicators["kosdaq"] = f"{p} ({sign}{rate}%)"
        except Exception:
            pass

    try:
        q_usd = urllib.parse.quote("달러환율")
        res3 = requests.get(f"https://m.search.naver.com/search.naver?query={q_usd}", headers=HEADERS, timeout=5).text
        m_p3 = re.search(r'<strong>([\d,.]+)</strong>', res3)
        if m_p3:
            indicators["usd"] = f"{m_p3.group(1)}원"
    except Exception:
        pass
        
    return indicators

# ------------------------------------------------------------------------------
# 4. 디자인 유틸리티 
# ------------------------------------------------------------------------------
def find_image(keyword):
    for file in os.listdir('.'):
        if keyword.lower() in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')):
            return file
    return None

def get_circular_avatar(img_path, size=(300, 300)):
    try:
        img = Image.open(img_path).convert("RGBA")
        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        output = Image.new('RGBA', size, (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        return output
    except Exception:
        return None

# ------------------------------------------------------------------------------
# 5. 메인 렌더링 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 그랜드 마스터 V24 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
        
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 26) 
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 24) 
        font_pub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 14)
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 30)
        
        # 하단 힐링 문구용 글씨 크기 (큰 박스에 맞게 시원하게 28pt)
        font_healing = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 28)
    except:
        font_huge = font_large = font_title = font_num = font_main = font_pub = font_small = font_footer = font_healing = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "보건복지부", "비급여 진료", "국민연금 개혁", "암보험", "건강 상식"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축"])
    finance_news = fetch_category_news(["코스피 마감 시황", "미국 증시 나스닥", "원달러 환율 종가", "퇴직연금", "비트코인 시세", "금값 시세", "주식 배당금", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 꿀팁", "정부 지원금", "소상공인 지원", "알뜰폰 요금제", "절세 방법", "청년 혜택", "할인 행사", "카드 혜택"])

    # 오디오 버벅임(숨고르기 멈춤) 방지를 위한 강력 정제
    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        first_news = re.sub(r'^\d+\.\s*', '', first_news)
        clean_news = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', first_news)
        clean_news = re.sub(r'\s+', ' ', clean_news).strip()
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {clean_news}입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (52, 152, 219), "bg_keyword": "bg_health", "items": health_news, "footer": "오늘도 건강하고 활기찬 하루 보내세요!", "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (46, 204, 113), "bg_keyword": "bg_estate", "items": econ_news, "footer": "당신의 소중한 자산, 든든하게 지켜드릴게요!", "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (243, 156, 18), "bg_keyword": "bg_finance", "items": finance_news, "footer": "현명한 금융 습관이 밝은 미래를 만듭니다!", "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "bg
