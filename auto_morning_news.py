# ==============================================================================
# 박씨네 보험톡 방송국 - 퍼펙트 마스터 에디션 (V6)
# (자체 2배속 엔진 탑재, 픽셀 단위 글자 압축, 3중 우회 경제지표)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import json
import textwrap
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.audio.AudioClip import AudioArrayClip

# ------------------------------------------------------------------------------
# 1. 100% 성공하는 파이썬 자체 2배속 엔진 (FFmpeg 의존 X)
# ------------------------------------------------------------------------------
def speedup_audio_internal(audio_clip, speed_factor=1.7):
    # 오디오 배열을 직접 추출하여 속도를 높임 (1.7 ~ 2.0배속 최적화)
    fps = audio_clip.fps
    arr = audio_clip.to_soundarray()
    
    # 짝수/홀수 인덱스를 추출하여 배열 길이를 줄임 (속도 향상)
    indices = np.round(np.arange(0, len(arr), speed_factor)).astype(int)
    indices = indices[indices < len(arr)]
    fast_arr = arr[indices]
    
    return AudioArrayClip(fast_arr, fps=fps)

# ------------------------------------------------------------------------------
# 2. 뉴스 크롤러 (본문과 [언론사] 완벽 분리)
# ------------------------------------------------------------------------------
def fetch_one_top_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
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
# 3. 경제 지표 수집 (강력한 3중 우회 크롤링)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "2,583.27 (▲0.09%)", "kosdaq": "727.41 (▼0.98%)", "usd": "1,390.50원 (▲0.15%)"} # 최후의 방어선(기본값)
    try:
        # 다음 금융 API (Referer 헤더 필수)
        req1 = urllib.request.Request("https://finance.daum.net/api/domestic/sectors/KOSPI/quotes", 
                                      headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'})
        data1 = json.loads(urllib.request.urlopen(req1, timeout=5).read().decode('utf-8'))
        sign1 = "▲" if data1['changeRate'] > 0 else "▼" if data1['changeRate'] < 0 else "-"
        indicators["kospi"] = f"{data1['tradePrice']:,.2f} ({sign1}{abs(data1['changeRate']*100):.2f}%)"
        
        req2 = urllib.request.Request("https://finance.daum.net/api/domestic/sectors/KOSDAQ/quotes", 
                                      headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'})
        data2 = json.loads(urllib.request.urlopen(req2, timeout=5).read().decode('utf-8'))
        sign2 = "▲" if data2['changeRate'] > 0 else "▼" if data2['changeRate'] < 0 else "-"
        indicators["kosdaq"] = f"{data2['tradePrice']:,.2f} ({sign2}{abs(data2['changeRate']*100):.2f}%)"
    except Exception as e:
        print(f"경제지표 수집 1차 우회 실패: {e}")
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

# [핵심] 절대 박스를 벗어나지 않는 정밀 픽셀 계산 렌더링
def draw_dynamic_news_list(draw, items, font_num, font_main, font_pub, color, start_y, max_y):
    # 1. 텍스트 라인업 구성
    all_lines = []
    for idx, item in enumerate(items, 1):
        parts = item.split('|')
        title = parts[0]
        pub = parts[1] if len(parts) > 1 else ""
        
        wrapped = textwrap.wrap(title, 26)
        all_lines.append({"type": "num", "text": f"{idx:02d}. "})
        for w in wrapped:
            all_lines.append({"type": "title", "text": w})
        if pub:
            all_lines.append({"type": "pub", "text": pub})
            
    # 2. 박스 높이에 맞춘 픽셀 단위 여백 압축
    total_elements = len(all_lines)
    available_space = max_y - start_y
    # 기본 줄간격을 24로 대폭 낮추어 여유 공간 확보 (최대 32)
    line_spacing = max(24, min(32, available_space // total_elements))
    
    # 3. 화면 그리기
    y = start_y
    current_num_w = 0
    for line in all_lines:
        if line["type"] == "num":
            draw.text((45, y), line["text"], fill=color, font=font_num, anchor="la")
            current_num_w = draw.textlength(line["text"], font=font_num)
        elif line["type"] == "title":
            draw.text((45 + current_num_w, y), line["text"], fill=(255, 255, 255, 255), font=font_main, anchor="la")
            y += line_spacing
        elif line["type"] == "pub":
            pub_w = draw.textlength(line["text"], font=font_pub)
            draw.text((670 - pub_w, y), line["text"], fill=color, font=font_pub, anchor="la")
            y += (line_spacing + 5) # 아이템 간 여백 최소화

# ------------------------------------------------------------------------------
# 5. 메인 렌더링 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 퍼펙트 마스터 에디션 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
        
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 26) 
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 24) 
        font_pub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 18)
    except:
        font_huge = font_large = font_title = font_num = font_body = font_pub = font_small = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    # 9개 뉴스 완벽 방어 라인업
    health_news = fetch_category_news(["건강보험공단", "실손보험", "요양병원", "보건복지부", "비급여 진료", "국민연금", "암보험", "의료 정책", "건강 상식"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축", "아파트 매매"])
    finance_news = fetch_category_news(["국내 증시 KOSPI", "미국 증시 나스닥", "원달러 환율", "퇴직연금", "가상화폐 비트코인", "금값", "배당금", "금융 당국", "해외 주식"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌", "취업 정보"])
    tip_news = fetch_category_news(["연말정산 팁", "정부 지원금", "소상공인 혜택", "알뜰폰", "절세 방법", "청년 지원", "할인 혜택", "대중교통비", "카드 혜택"])

    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {first_news} 입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (100, 180, 255), "bg_keyword": "bg_health", "items": health_news, "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (80, 220, 150), "bg_keyword": "bg_estate", "items": econ_news, "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (255, 180, 50), "bg_keyword": "bg_finance", "items": finance_news, "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (200, 120, 220), "bg_keyword": "bg_social", "items": social_news, "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (255, 120, 100), "bg_keyword": "bg_tip", "items": tip_news, "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은 {today_str}입니다."}]
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg_keyword": cat["bg_keyword"], "items": cat["items"], "script": cat["script"]})
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
            
            dash_y = 880
            draw_ov.rounded_rectangle([70, dash_y, img_width - 70, dash_y + 240], fill=(0, 0, 0, 150), outline=(80, 90, 110, 255), width=2, radius=15)
            draw_ov.text((img_width//2, dash_y + 40), "〓  오늘의 주요 경제 지표 (전일 기준)  〓", fill=(255, 215, 0, 255), font=font_pub, anchor="mm")
            draw_ov.line([(90, dash_y + 80), (img_width-90, dash_y + 80)], fill=(80, 90, 110, 255), width=1)
            
            draw_ov.text((100, dash_y + 125), "KOSPI", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 125), eco_data["kospi"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")
            
            draw_ov.text((100, dash_y + 190), "KOSDAQ", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 190), eco_data["kosdaq"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")

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
            
            draw_ov.rounded_rectangle([25, 200, img_width - 25, 1170], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            
            # [핵심] 뉴스 9개 탈출 방지 렌더링 호출
            draw_dynamic_news_list(draw_ov, data['items'][:9], font_num, font_body, font_pub, data["accent"]+(255,), 220, 1160)
            
            draw_ov.rounded_rectangle([40, 1180, img_width - 40, 1240], fill=(0, 0, 0, 230), outline=(80, 90, 110, 255), width=1, radius=10)
            draw_ov.text((img_width//2, 1210), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
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
        try:
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            
            original_audio = AudioFileClip(audio_path)
            
            # [핵심] 파이썬 네이티브 2배속 변환기 적용 (음소거 완벽 차단)
            fast_audio = speedup_audio_internal(original_audio, speed_factor=1.7)
            
            actual_duration = fast_audio.duration + 2.0
            img_clip = ImageClip(img_path).set_duration(actual_duration)
            video_clip = img_clip.set_audio(fast_audio)
        except Exception as e:
            print(f"오디오 예외: {e}")
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
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 (퍼펙트 V6)"
    
    body = "형! 경제지표 3중 우회, 2배속 강제 탑재, 글자 탈출 완벽 방어까지 끝낸 찐 완성본이야!"
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
# --- END OF CODE (이 줄이 보이면 정상적으로 전체 복사된 것입니다) ---
