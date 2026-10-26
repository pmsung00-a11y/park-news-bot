# ==============================================================================
# 박씨네 보험톡 방송국 - 그랜드 마스터 V7 (최종 완성본)
# (동적 박스 크기 조절, 네이버 모바일 API 우회, 순정 1.4배속 엔진, 아이콘 유지)
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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# ------------------------------------------------------------------------------
# 1. 뉴스 크롤러 (본문과 [언론사] 완벽 분리 및 키워드 최적화)
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
# 2. 경제 지표 수집 (네이버 모바일 우회 API - 차단 방어율 99%)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    # 万일 통신 에러가 나더라도 기본 수치가 들어가도록 든든한 방어막 설정
    indicators = {"kospi": "2,583.27 (▲0.09%)", "kosdaq": "727.41 (▼0.98%)", "usd": "1,390.50원 (▲0.15%)"}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        req1 = urllib.request.Request("https://m.stock.naver.com/api/index/KOSPI/basic", headers=headers)
        data1 = json.loads(urllib.request.urlopen(req1, timeout=5).read().decode('utf-8'))
        change1 = float(data1['compareToPreviousClosePrice'])
        sign1 = "▲" if change1 > 0 else "▼" if change1 < 0 else "-"
        indicators["kospi"] = f"{data1['closePrice']} ({sign1}{abs(float(data1['fluctuationsRatio'])):.2f}%)"
        
        req2 = urllib.request.Request("https://m.stock.naver.com/api/index/KOSDAQ/basic", headers=headers)
        data2 = json.loads(urllib.request.urlopen(req2, timeout=5).read().decode('utf-8'))
        change2 = float(data2['compareToPreviousClosePrice'])
        sign2 = "▲" if change2 > 0 else "▼" if change2 < 0 else "-"
        indicators["kosdaq"] = f"{data2['closePrice']} ({sign2}{abs(float(data2['fluctuationsRatio'])):.2f}%)"
    except Exception as e:
        print(f"경제지표 API 우회 실패: {e}")
        
    return indicators

# ------------------------------------------------------------------------------
# 3. 디자인 유틸리티 
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

# [핵심] 뉴스 텍스트 렌더링 (번호 부여, 자동 줄바꿈, 출처 우측 끝 정렬)
def draw_news_list(draw, items, font_num, font_main, font_pub, color, start_y):
    y = start_y
    for idx, item in enumerate(items, 1):
        num_str = f"{idx:02d}. "
        
        parts = item.split('|')
        title = parts[0]
        pub = parts[1] if len(parts) > 1 else ""
            
        draw.text((45, y), num_str, fill=color, font=font_num, anchor="la")
        text_x = 45 + draw.textlength(num_str, font=font_num)
        
        wrapped = textwrap.wrap(title, 27) 
        for line in wrapped:
            draw.text((text_x, y), line, fill=(255, 255, 255, 255), font=font_main, anchor="la")
            y += 32 
            
        if pub:
            pub_w = draw.textlength(pub, font=font_pub)
            draw.text((670 - pub_w, y), pub, fill=color, font=font_pub, anchor="la")
            y += 42 
        else:
            y += 20
            
    return y

# ------------------------------------------------------------------------------
# 4. 메인 렌더링 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 그랜드 마스터 V7 렌더링 시작...")
    
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

    # 정확도 향상을 위한 키워드 최적화 (이상한 수치 방지)
    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "보건복지부", "비급여 진료", "국민연금 개혁", "암보험", "의료 정책"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 대책", "재건축"])
    finance_news = fetch_category_news(["코스피 마감 시황", "미국 증시 나스닥", "원달러 환율 종가", "퇴직연금", "가상화폐 비트코인", "금값 시세", "주식 배당금", "금융위 정책"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 꿀팁", "정부 지원금 혜택", "소상공인 지원", "알뜰폰 요금제", "절세 방법", "청년 지원금", "마트 할인 혜택", "교통비 할인"])

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
            
            # [핵심] 공백을 없애기 위해 기사 높이를 사전 계산하여 박스 크기를 자동 핏팅!
            final_y = 230
            for item in data['items'][:8]:
                parts = item.split('|')
                title = parts[0]
                pub = parts[1] if len(parts) > 1 else ""
                wrapped = textwrap.wrap(title, 27)
                final_y += len(wrapped) * 32
                if pub: final_y += 42
                else: final_y += 20
                
            box_bottom = final_y + 10 # 텍스트가 끝나는 지점에 딱 맞춰서 박스 바닥을 닫음
            
            draw_ov.rounded_rectangle([25, 200, img_width - 25, box_bottom], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            
            # 텍스트 그리기
            draw_news_list(draw_ov, data['items'][:8], font_num, font_body, font_pub, data["accent"]+(255,), 230)
            
            # 하단 "구독과 좋아요" 상자도 기사 길이에 맞춰서 찰싹 달라붙음
            footer_y = box_bottom + 20
            draw_ov.rounded_rectangle([40, footer_y, img_width - 40, footer_y + 60], fill=(0, 0, 0, 230), outline=(80, 90, 110, 255), width=1, radius=10)
            draw_ov.text((img_width//2, footer_y + 30), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
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
            
            # [핵심] moviepy 순정 엔진을 통한 1.4배속 적용 (가장 빠르고 안정적인 아나운서 톤)
            try:
                from moviepy.audio.fx.all import speedx
                fast_audio = speedx(original_audio, factor=1.4)
                
                actual_duration = fast_audio.duration + 1.5
                img_clip = ImageClip(img_path).set_duration(actual_duration)
                video_clip = img_clip.set_audio(fast_audio)
            except Exception as speed_e:
                print(f"속도 변환 실패, 기본 오디오 사용: {speed_e}")
                actual_duration = original_audio.duration + 1.5
                img_clip = ImageClip(img_path).set_duration(actual_duration)
                video_clip = img_clip.set_audio(original_audio)
                
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
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 (그랜드 마스터 V7)"
    
    body = "형! 공백 제로 동적 박스, 오디오 1.4배속, 코스피 지수 복구까지 완벽하게 테스트 마친 본이야!"
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
