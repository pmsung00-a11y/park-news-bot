# ==============================================================================
# 박씨네 보험톡 방송국 - 그랜드 마스터 V22 (진정한 최종 완성본)
# (오디오 기계음 팝핑 방지 페이드아웃, 하단 박스 본문 길이 동기화 및 글씨 확대)
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
from moviepy.audio.fx.all import audio_fadeout  # 기계음 방지용 페이드아웃 효과

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# ------------------------------------------------------------------------------
# 1. FFmpeg 오디오 엔진 
# ------------------------------------------------------------------------------
def speedup_audio_ffmpeg(input_path, output_path, speed=1.4):
    cmd = ['ffmpeg', '-y', '-i', input_path, '-filter:a', f'atempo={speed}', '-ar', '44100', output_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"오디오 가속 실패, 원본 WAV 변환: {e}")
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
    return f"{keyword} 관련 뉴스를 업데이트 중입니다.|[시스템]"

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news_items.append(fetch_one_top_news(keyword))
    return news_items

# ------------------------------------------------------------------------------
# 3. 경제 지표 수집
# ------------------------------------------------------------------------------
def get_yahoo_chart_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d"
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()['chart']['result'][0]['meta']
            price = data['regularMarketPrice']
            prev_close = data['chartPreviousClose']
            change = price - prev_close
            change_pct = (change / prev_close) * 100
            sign = "▲" if change > 0 else "▼" if change < 0 else "-"
            return f"{price:,.2f} ({sign}{abs(change_pct):.2f}%)"
    except Exception:
        pass
    return "데이터 확인중"

def fetch_economic_indicators():
    indicators = {
        "kospi": get_yahoo_chart_data("^KS11"),
        "kosdaq": get_yahoo_chart_data("^KQ11"),
        "usd": get_yahoo_chart_data("KRW=X")
    }
    
    if "확인중" in indicators["kospi"]:
        try:
            r1 = requests.get("https://m.stock.naver.com/api/index/KOSPI/basic", headers=HEADERS, timeout=5).json()
            c1 = float(r1['compareToPreviousClosePrice'])
            s1 = "▲" if c1 > 0 else "▼" if c1 < 0 else "-"
            indicators["kospi"] = f"{r1['closePrice']} ({s1}{abs(float(r1['fluctuationsRatio'])):.2f}%)"
        except Exception: pass
        
    if "확인중" in indicators["kosdaq"]:
        try:
            r2 = requests.get("https://m.stock.naver.com/api/index/KOSDAQ/basic", headers=HEADERS, timeout=5).json()
            c2 = float(r2['compareToPreviousClosePrice'])
            s2 = "▲" if c2 > 0 else "▼" if c2 < 0 else "-"
            indicators["kosdaq"] = f"{r2['closePrice']} ({s2}{abs(float(r2['fluctuationsRatio'])):.2f}%)"
        except Exception: pass
        
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
    print(f"[{today_str}] 마스터 피스 V22 렌더링 시작...")
    
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
        
        # [수정] 힐링 문구용 폰트를 기존 26pt에서 34pt로 대폭 키움 (가독성 폭발)
        font_healing = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
    except:
        font_huge = font_large = font_title = font_num = font_main = font_pub = font_small = font_footer = font_healing = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "보건복지부", "비급여 진료", "국민연금 개혁", "암보험", "건강 상식"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축"])
    finance_news = fetch_category_news(["코스피 마감 시황", "미국 증시 나스닥", "원달러 환율 종가", "퇴직연금", "비트코인 시세", "금값 시세", "주식 배당금", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 꿀팁", "정부 지원금", "소상공인 지원", "알뜰폰 요금제", "절세 방법", "청년 혜택", "할인 행사", "카드 혜택"])

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
        {"category": "주요 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "bg_social", "items": social_news, "footer": "세상을 밝히는 따뜻한 소식이 더 많아지길!", "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (231, 76, 60), "bg_keyword": "bg_tip", "items": tip_news, "footer": "작은 상식 하나가 모여 큰 지혜가 됩니다!", "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은 {today_str}입니다."}]
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg_keyword": cat["bg_keyword"], "items": cat["items"], "footer": cat["footer"], "script": cat["script"]})
    slides_data.append({"type": "outro", "script": "보험이 궁금할 땐 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 행복한 하루 보내시길 응원합니다."})

    clips = []
    
    for idx, data in enumerate(slides_data, start=1):
        if data["type"] in ["cover", "outro"]:
            slide = Image.new("RGB", (img_width, img_height), color=(12, 18, 32))
        else:
            slide = Image.new("RGB", (img_width, img_height), color=(15, 20, 30))
            bg_file = find_image(data.get("bg_keyword", "xxxxx"))
            if bg_file:
                try:
                    bg_img = Image.open(bg_file)
                    bg_img = ImageOps.fit(bg_img, (img_width, img_height), Image.Resampling.LANCZOS)
                    slide.paste(bg_img, (0, 0))
                except: pass
            
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        if data["type"] == "cover":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (340, 340))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 170, 140), avatar)
            
            draw_ov.text((img_width//2, 540), "박씨네 보험톡", fill=(255, 255, 255, 255), font=font_huge, anchor="mm")
            draw_ov.text((img_width//2, 640), "일일 주요뉴스", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            draw_ov.rounded_rectangle([img_width//2 - 120, 730, img_width//2 + 120, 780], fill=(255, 255, 255, 20), radius=25)
            draw_ov.text((img_width//2, 755), f"발행일 : {today_str}", fill=(180, 200, 230, 255), font=font_pub, anchor="mm")
            
            dash_y = 860
            draw_ov.rounded_rectangle([70, dash_y, img_width - 70, dash_y + 260], fill=(0, 0, 0, 150), outline=(80, 90, 110, 255), width=2, radius=15)
            draw_ov.text((img_width//2, dash_y + 40), "〓  오늘의 주요 경제 지표 (전일 기준)  〓", fill=(255, 215, 0, 255), font=font_pub, anchor="mm")
            draw_ov.line([(90, dash_y + 80), (img_width-90, dash_y + 80)], fill=(80, 90, 110, 255), width=1)
            
            draw_ov.text((100, dash_y + 120), "KOSPI", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 120), eco_data["kospi"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")
            
            draw_ov.text((100, dash_y + 175), "KOSDAQ", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 175), eco_data["kosdaq"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")

            draw_ov.text((100, dash_y + 230), "환율 (USD)", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 230), eco_data["usd"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")

        elif data["type"] == "news":
            cat_w = draw_ov.textlength(data['category'], font=font_title)
            
            # 상단 제목 박스는 글자 길이에 맞춰서 생성
            title_box_w = cat_w + 80
            title_box_x1 = 360 - title_box_w // 2
            title_box_x2 = 360 + title_box_w // 2
            
            r, g, b = data["accent"]
            draw_ov.rectangle([0, 70, img_width, 80], fill=data["accent"]+(255,))
            draw_ov.rounded_rectangle([title_box_x1, 110, title_box_x2, 170], fill=(r//3, g//3, b//3, 255), radius=10)
            draw_ov.text((img_width//2, 140), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            
            start_y = 230
            parsed_items = []
            total_text_height = 0
            
            for item in data['items'][:8]:
                parts = item.split('|')
                title = parts
