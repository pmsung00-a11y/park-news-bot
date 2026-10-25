# ==============================================================================
# 박씨네 보험톡 방송국 - 일일 80초 요약뉴스 (네이버 뉴스 실시간 100% 연동)
# 작성일: 2026년 10월 26일
# 특징: 네이버 뉴스 실시간 크롤링, 프리미엄 다크모드, 1.25배속 오디오 완벽 싱크
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import requests
import urllib.parse
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import moviepy.audio.fx.all as afx

# ------------------------------------------------------------------------------
# 1. 네이버 뉴스 실시간 자동 수집기 (형님 지정 주소 기반)
# ------------------------------------------------------------------------------
def fetch_naver_realtime_news(keyword):
    """실행되는 그 날, 그 시간의 '네이버 뉴스' 최신 기사를 5개씩 자동으로 긁어옵니다."""
    encoded_keyword = urllib.parse.quote(keyword)
    # 네이버 뉴스 검색 URL 활용 (가장 정확하고 빠른 최신 뉴스 추출)
    url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    headlines = []
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        html = res.text
        
        # 네이버 뉴스 제목 HTML 태그 정규식 추출
        matches = re.findall(r'<a href="[^"]+" class="news_tit"[^>]*title="([^"]+)"', html)
        
        for title in matches:
            # 특수문자 정제
            clean_title = title.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            if clean_title not in headlines:
                if len(clean_title) > 28:
                    clean_title = clean_title[:28] + "..."
                headlines.append(clean_title)
            if len(headlines) == 5:
                break
    except Exception as e:
        print(f"네이버 뉴스 수집 에러 ({keyword}): {e}")
        
    # 만약 뉴스가 5개가 안 채워지면 빈칸 채우기
    while len(headlines) < 5:
        headlines.append(f"네이버 실시간 뉴스 수집 대기 중입니다.")
        
    return headlines

# ------------------------------------------------------------------------------
# 2. 스마트 이미지 자동 인식
# ------------------------------------------------------------------------------
def find_uploaded_image(keyword):
    for file in os.listdir('.'):
        if keyword.lower() in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')):
            return file
    return None

# ------------------------------------------------------------------------------
# 3. 메인 영상 제작 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    today_dt = datetime.datetime.now()
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 네이버 뉴스 실시간 수집 및 영상 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    # 폰트 로드
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        font_large = ImageFont.truetype(font_path, 46)
        font_title = ImageFont.truetype(font_path, 36)
        font_body = ImageFont.truetype(font_path, 22)
        font_small = ImageFont.truetype(font_path, 18)
    except:
        font_large = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    clips = []
    
    # 각 분야별 네이버 최신 뉴스 크롤링 (키워드 최적화)
    health_news = fetch_naver_realtime_news("건강보험 실손보험")
    econ_news = fetch_naver_realtime_news("부동산 아파트 전세")
    finance_news = fetch_naver_realtime_news("증시 금리 환율")
    social_news = fetch_naver_realtime_news("생활 안전 대책")
    tip_news = fetch_naver_realtime_news("연말정산 지원금 혜택")

    # 오디오 낭독은 핵심 상위 2개 뉴스만 임팩트 있게 낭독! (화면엔 5개가 꽉 차게 뜸)
    news_database = [
        {
            "category": "건강 · 보험 뉴스",
            "accent": (52, 152, 219),
            "bg_keyword": "insurance", 
            "items": health_news,
            "script": f"첫 번째 건강 보험 소식입니다. {health_news[0]}, 그리고 {health_news[1]} 등의 네이버 최신 소식이 있습니다."
        },
        {
            "category": "부동산 경제 뉴스",
            "accent": (46, 204, 113),
            "bg_keyword": "domestic_econ", 
            "items": econ_news,
            "script": f"두 번째 부동산 경제 소식입니다. {econ_news[0]}, 그리고 {econ_news[1]} 등의 소식입니다."
        },
        {
            "category": "국내외 금융 뉴스",
            "accent": (243, 156, 18),
            "bg_keyword": "domestic_econ", 
            "items": finance_news,
            "script": f"세 번째 금융 소식입니다. {finance_news[0]}, 그리고 {finance_news[1]} 관련 소식이 있습니다."
        },
        {
            "category": "따뜻한 사회 뉴스",
            "accent": (155, 89, 182),
            "bg_keyword": "social", 
            "items": social_news,
            "script": f"네 번째 사회 소식입니다. {social_news[0]} 소식을 포함한 생활 안전 대책을 전해드립니다."
        },
        {
            "category": "알뜰 상식 뉴스",
            "accent": (231, 76, 60),
            "bg_keyword": "tip", 
            "items": tip_news,
            "script": f"마지막 알뜰 상식 소식입니다. {tip_news[0]}, 그리고 {tip_news[1]} 등의 유용한 혜택 소식입니다."
        }
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 요약뉴스입니다. 오늘 발행일은 {today_str}입니다."}]
    
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({
            "type": "news", "category": cat["category"], "accent": cat["accent"],
            "bg_keyword": cat["bg_keyword"], "subtitle": f"오늘의 핵심 소식 ({i}/5)",
            "items": cat["items"], "script": cat["script"]
        })
        
    slides_data.append({"type": "outro", "script": "자세한 사항이나 보험 관련 문의는 언제든 박씨네 보험톡을 찾아주세요. 활기찬 하루 보내십시오!"})

    dark_bg = (20, 24, 36)
    card_bg = (32, 38, 52)
    text_light = (240, 245, 250)

    for idx, data in enumerate(slides_data, start=1):
        slide = Image.new("RGB", (img_width, img_height), color=dark_bg)
        draw = ImageDraw.Draw(slide)
        
        if data["type"] == "cover":
            profile_file = find_uploaded_image("profile")
            if profile_file:
                try:
                    profile_img = Image.open(profile_file).convert("RGBA").resize((300, 300))
                    slide.paste(profile_img, (210, 260), profile_img if profile_img.mode == 'RGBA' else None)
                except: pass
                    
            draw.text((img_width//2, 630), "박씨네 보험톡", fill=text_light, font=font_large, anchor="mm")
            draw.text((img_width//2, 710), "일일 요약뉴스", fill=(180, 200, 230), font=font_title, anchor="mm")
            draw.text((img_width//2, 830), "박씨네 보험톡 제공", fill=(255, 215, 0), font=font_body, anchor="mm")
            draw.text((img_width//2, 900), f"발행일: {today_str}", fill=(130, 150, 180), font=font_small, anchor="mm")
            
        elif data["type"] == "news":
            actual_bg_file = find_uploaded_image(data["bg_keyword"])
            if actual_bg_file:
                try:
                    top_img = Image.open(actual_bg_file)
                    top_img = ImageOps.fit(top_img, (img_width, 450), Image.Resampling.LANCZ
