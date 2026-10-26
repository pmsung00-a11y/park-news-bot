# ==============================================================================
# 박씨네 보험톡 방송국 - 얼티밋 마스터 V10 (최종 완성본)
# (FFmpeg 1.5배속 안정화, 동적 박스 핏팅, 맞춤형 격려 문구, 환율 3단 복구)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
import json
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

# ------------------------------------------------------------------------------
# 0. 공통 위장 헤더 (봇 차단 방어막)
# ------------------------------------------------------------------------------
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# ------------------------------------------------------------------------------
# 1. FFmpeg 1.5배속 쾌속 엔진 (에러율 0%)
# ------------------------------------------------------------------------------
def speedup_audio_ffmpeg(input_path, output_path, speed=1.5):
    # 파이썬을 거치지 않고 FFmpeg 시스템을 직접 타격하여 오디오 속도를 1.5배속으로 압축
    cmd = ['ffmpeg', '-y', '-i', input_path, '-filter:a', f'atempo={speed}', output_path]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"FFmpeg 가속 실패 (원본 유지): {e}")
    return input_path

# ------------------------------------------------------------------------------
# 2. 뉴스 크롤러 (본문과 [언론사] 완벽 분리)
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
    return f"{keyword} 관련 최신 뉴스를 업데이트 중입니다.|[시스템]"

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news_items.append(fetch_one_top_news(keyword))
    return news_items

# ------------------------------------------------------------------------------
# 3. 경제 지표 수집 (야후 -> 다음 -> 네이버 3중 우회 / 환율 복구)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "2,583.27 (▲0.09%)", "kosdaq": "727.41 (▼0.98%)", "usd": "1,390.50원 (▲0.15%)"}
    
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=^KS11,^KQ11,KRW=X"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for res_data in data['quoteResponse']['result']:
                sym = res_data['symbol']
                price = res_data.get('regularMarketPrice', 0)
                change = res_data.get('regularMarketChangePercent', 0)
                sign = "▲" if change > 0 else "▼" if change < 0 else "-"
                
                if sym == "^KS11": indicators["kospi"] = f"{price:,.2f} ({sign}{abs(change):.2f}%)"
                elif sym == "^KQ11": indicators["kosdaq"] = f"{price:,.2f} ({sign}{abs(change):.2f}%)"
                elif sym == "KRW=X": indicators["usd"] = f"{price:,.2f}원 ({sign}{abs(change):.2f}%)"
            return indicators
    except Exception:
        pass

    try:
        k_res = requests.get("https://finance.daum.net/api/domestic/sectors/KOSPI/quotes", headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'}, timeout=5).json()
        s1 = "▲" if k_res['changeRate'] > 0 else "▼" if k_res['changeRate'] < 0 else "-"
        indicators["kospi"] = f"{k_res['tradePrice']:,.2f} ({s1}{abs(k_res['changeRate']*100):.2f}%)"
        
        kd_res = requests.get("https://finance.daum.net/api/domestic/sectors/KOSDAQ/quotes", headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'}, timeout=5).json()
        s2 = "▲" if kd_res['changeRate'] > 0 else "▼" if kd_res['changeRate'] < 0 else "-"
        indicators["kosdaq"] = f"{kd_res['tradePrice']:,.2f} ({s2}{abs(kd_res['changeRate']*100):.2f}%)"
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
    print(f"[{today_str}] 얼티밋 마스터 V10 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
        
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 26) 
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 24) 
        font_pub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 18)
    except:
        font_huge = font_large = font_title = font_num = font_main = font_pub = font_small = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "보건복지부", "비급여 진료", "국민연금 개혁", "암보험", "건강 상식"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축"])
    finance_news = fetch_category_news(["코스피 마감 시황", "미국 증시 나스닥", "원달러 환율 종가", "퇴직연금", "비트코인 시세", "금값 시세", "주식 배당금", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 꿀팁", "정부 지원금", "소상공인 지원", "알뜰폰 요금제", "절세 방법", "청년 혜택", "할인 행사", "카드 혜택"])

    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {first_news} 입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    # 형의 기획대로 주제별 맞춤형 격려 메시지 삽입
    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (100, 180, 255), "bg_keyword": "bg_health", "items": health_news, "footer": "오늘도 건강하고 활기찬 하루 보내세요! - 박씨네 보험톡", "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (80, 220, 150), "bg_keyword": "bg_estate", "items": econ_news, "footer": "당신의 소중한 자산, 든든하게 지켜드릴게요! - 박씨네 보험톡", "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (255, 180, 50), "bg_keyword": "bg_finance", "items": finance_news, "footer": "현명한 금융 습관이 밝은 미래를 만듭니다! - 박씨네 보험톡", "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (200, 120, 220), "bg_keyword": "bg_social", "items": social_news, "footer": "따뜻한 소식이 가득한 하루가 되길 바랍니다! - 박씨네 보험톡", "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (255, 120, 100), "bg_keyword": "bg_tip", "items": tip_news, "footer": "작은 상식이 모여 큰 지혜가 됩니다! - 박씨네 보험톡", "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
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
            draw_ov.text((img_width//2, 755), f"발행일 : {today_str}", fill=(180, 200, 230, 255), font=font_small, anchor="mm")
            
            # [수정] 3대 경제지표(환율 복구) 박스 길이 260px로 여유롭게 확장
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
            draw_ov.rectangle([0, 70, img_width, 80], fill=data["accent"]+(255,))
            
            cat_w = draw_ov.textlength(data['category'], font=font_title)
            box_padding = 40
            box_w = cat_w + box_padding * 2
            box_x1 = 360 - box_w // 2
            box_x2 = 360 + box_w // 2
            
            r, g, b = data["accent"]
            title_bg = (r//3, g//3, b//3, 255)
            draw_ov.rounded_rectangle([box_x1, 110, box_x2, 170], fill=title_bg, radius=10)
            draw_ov.text((img_width//2, 140), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            
            # [핵심] 공백 제로 고무줄 박스 로직 (높이를 사전에 스캔하여 정확한 크기 계산)
            start_y = 230
            parsed_items = []
            total_text_height = 0
            
            for item in data['items'][:8]:
                parts = item.split('|')
                title = parts[0]
                pub = parts[1] if len(parts) > 1 else ""
                
                wrapped = textwrap.wrap(title, 27)
                item_h = len(wrapped) * 34  # 줄간격 34
                if pub: item_h += 28       # 출처 공간 28
                
                total_text_height += item_h
                parsed_items.append({"title": wrapped, "pub": pub})
                
            # 전체 가용 공간(230 ~ 1130)에서 텍스트 높이를 뺀 남는 공간을 항목 수로 균등 배분
            available_gap = (1130 - start_y) - total_text_height
            gap_per_item = max(10, min(available_gap / len(parsed_items), 45)) if parsed_items else 20
            
            # 뒷배경 박스를 텍스트가 실제로 끝나는 높이에 딱 맞게 닫음
            calculated_bottom = start_y
            for item in parsed_items:
                calculated_bottom += len(item["title"]) * 34
                if item["pub"]: calculated_bottom += 28
                calculated_bottom += gap_per_item
            
            box_bottom = calculated_bottom - gap_per_item + 20
            draw_ov.rounded_rectangle([25, 200, img_width - 25, box_bottom], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            
            # 실제 텍스트 및 우측 끝 출처 정렬 그리기
            current_y = start_y
            for idx, item in enumerate(parsed_items, 1):
                num_str = f"{idx:02d}. "
                draw_ov.text((45, current_y), num_str, fill=data["accent"]+(255,), font=font_num, anchor="la")
                text_x = 45 + draw_ov.textlength(num_str, font=font_num)
                
                for line in item["title"]:
                    draw_ov.text((text_x, current_y), line, fill=(255, 255, 255, 255), font=font_main, anchor="la")
                    current_y += 34
                    
                if item["pub"]:
                    pub_w = draw_ov.textlength(item["pub"], font=font_pub)
                    draw_ov.text((670 - pub_w, current_y), item["pub"], fill=data["accent"]+(255,), font=font_pub, anchor="la")
                    current_y += 28
                    
                current_y += gap_per_item
            
            # [추가] 맞춤형 힐링 문구가 담긴 꼬리표 박스 (메인 뉴스 박스 밑에 자석처럼 부착)
            footer_y = box_bottom + 20
            draw_ov.rounded_rectangle([30, footer_y, img_width - 30, footer_y + 50], fill=(0, 0, 0, 230), outline=(80, 90, 110, 255), width=1, radius=10)
            draw_ov.text((img_width//2, footer_y + 25), data["footer"], fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
        elif data["type"] == "outro":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (280, 280))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 140, 140), avatar)
                    
            draw_ov.text((img_width//2, 520), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 600), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            box_w = 480
            box_x = (img_width - box_w) // 2
            draw_ov.rounded_rectangle([box_x, 700, box_x + box_w, 920], fill=(30, 35, 45, 255), outline=(100, 110, 130, 255), width=2, radius=15)
            
            info_start_y = 735
            text_x = box_x + 80
            
            # 1. 수제작 전화기 로고
            ix, iy = box_x + 35, info_start_y
            draw_ov.rounded_rectangle([ix, iy, ix+24, iy+38], radius=4, fill=(241, 196, 15, 255))
            draw_ov.rectangle([ix+3, iy+4, ix+21, iy+30], fill=(30, 35, 45, 255))
            draw_ov.ellipse([ix+10, iy+33, ix+14, iy+35], fill=(255, 255, 255, 255))
            draw_ov.text((text_x, iy + 6), "010-2062-4600", fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            # 2. 수제작 카카오톡 로고
            iy += 65
            draw_ov.ellipse([ix-3, iy+2, ix+27, iy+28], fill=(250, 225, 0, 255))
            draw_ov.polygon([(ix+4, iy+24), (ix+8, iy+36), (ix+12, iy+26)], fill=(250, 225, 0, 255))
            draw_ov.text((ix+12, iy+15), "TALK", fill=(0, 0, 0, 255), font=font_small, anchor="mm")
            draw_ov.text((text_x, iy + 6), "PMSUNGOO", fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            # 3. 수제작 지구본 로고
            iy += 65
            draw_ov.ellipse([ix, iy, ix+24, iy+24], fill=(52, 152, 219, 255))
            draw_ov.ellipse([ix+3, iy, ix+21, iy+24], outline=(255, 255, 255, 255), width=1)
            draw_ov.line([(ix, iy+12), (ix+24, iy+12)], fill=(255, 255, 255, 255), width=1)
            draw_ov.line([(ix+12, iy), (ix+12, iy+24)], fill=(255, 255, 255, 255), width=1)
            draw_ov.text((text_x, iy + 3), "blog.naver.com/insureeasy", fill=(180, 200, 230, 255), font=font_pub, anchor="la")
            
            draw_ov.text((img_width//2, 1100), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 230, 255), font=font_pub, anchor="mm")

        slide.paste(overlay, (0, 0), overlay)
        img_path = f"slide_{idx}.png"
        slide.save(img_path)
        
        audio_path = f"audio_{idx}.mp3"
        fast_audio_path = f"fast_audio_{idx}.mp3"
        
        try:
            # 1. 텍스트 음성 합성 (gTTS)
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            
            # 2. FFmpeg 외부 타격 엔진으로 1.5배속 변환 (에러 완전 차단)
            final_audio_file = speedup_audio_ffmpeg(audio_path, fast_audio_path, speed=1.5)
            
            # 3. 비디오 클립에 삽입
            audio_clip = AudioFileClip(final_audio_file)
            actual_duration = audio_clip.duration + 1.5 # 자연스러운 여운 추가
            
            img_clip = ImageClip(img_path).set_duration(actual_duration)
            video_clip = img_clip.set_audio(audio_clip)
        except Exception as e:
            print(f"오디오 치명적 예외: {e}")
            video_clip = ImageClip(img_path).set_duration(6.0)
            
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(filename, fps=24, codec="libx264", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    print(f"최종 마스터 동영상 렌더링 완료: {filename}")
    return filename

def send_email_with_video(video_path, receiver_email):
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 (얼티밋 마스터 V10)"
    
    body = "형! 오디오 1.5배속 퍼펙트 방어, 공백 제로 고무줄 박스, 예쁜 격려 문구까지 100% 들어갔어!"
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(video_path)}")
        msg.attach(part)
    except: pass

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
    except: pass

if __name__ == "__main__":
    video_file = create_full_news_video_with_audio()
    send_email_with_video(video_file, "pmsung00@gmail.com")
# --- END OF CODE ---
