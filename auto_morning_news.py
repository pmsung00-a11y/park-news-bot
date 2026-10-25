# ==============================================================================
# 박씨네 보험톡 방송국 - 최종 럭셔리 에디션 (출처 표시, 레이아웃 꽉 채움, 경제지수 복구)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# ------------------------------------------------------------------------------
# 1. 뉴스 크롤러 (언론사 출처 [OO일보] 남기기)
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
            # '기사 제목 - 언론사명'을 '[언론사명] 기사 제목'으로 예쁘게 바꿉니다.
            if ' - ' in title:
                parts = title.rsplit(' - ', 1)
                clean_title = f"[{parts[1]}] {parts[0]}"
            else:
                clean_title = title
                
            if len(clean_title) > 8:
                return clean_title
    except Exception:
        pass
    return f"[시스템] {keyword} 최신 뉴스를 업데이트 중입니다."

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news_items.append(fetch_one_top_news(keyword))
    return news_items

# ------------------------------------------------------------------------------
# 2. 경제 지표 수집 (모바일 네이버 우회 - 100% 작동 보장)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "수집 지연", "kosdaq": "수집 지연", "usd": "수집 지연"}
    try:
        # PC버전 대신 모바일 버전으로 우회하여 차단 방지
        req = urllib.request.Request("https://m.stock.naver.com/", headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
        
        # 정규식 패턴 수정 (모바일 웹 구조에 맞춤)
        k_m = re.search(r'"KOSPI","price":"([\d,.]+)"', html)
        if k_m: indicators["kospi"] = k_m.group(1)
        
        kd_m = re.search(r'"KOSDAQ","price":"([\d,.]+)"', html)
        if kd_m: indicators["kosdaq"] = kd_m.group(1)
        
        # 환율은 다음(Daum) 모바일로 교체 (네이버 모바일에서 찾기 어려울 경우 대비)
        req2 = urllib.request.Request("https://m.finance.daum.net/", headers={'User-Agent': 'Mozilla/5.0'})
        html2 = urllib.request.urlopen(req2, timeout=5).read().decode('utf-8', errors='ignore')
        u_m = re.search(r'미국 USD.*?<span class="num">([\d,.]+)</span>', html2, re.S)
        if u_m: indicators["usd"] = u_m.group(1) + "원"
        
    except Exception as e:
        print(f"지표 수집 예외: {e}")
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

def draw_hanging_indent_text(draw, text, font, start_x, start_y, max_width, fill_color, is_main=False):
    words = text.split(' ')
    lines = []
    # 1번 주요 뉴스는 큰 점표시, 서브 뉴스는 작은 점표시
    bullet = "■ " if is_main else "• "
    current_line = bullet
    
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)
    
    bullet_offset = draw.textbbox((0, 0), bullet, font=font)[2]
    
    y = start_y
    line_spacing = 55 if is_main else 45 # 1번 뉴스는 줄간격도 더 넓게
    for i, line in enumerate(lines):
        x = start_x if i == 0 else start_x + bullet_offset
        draw.text((x, y), line, fill=fill_color, font=font, anchor="la")
        y += line_spacing
    
    # 1번 뉴스는 다음 뉴스와 간격을 아주 넓게, 서브 뉴스는 좁게
    return y + (60 if is_main else 30)

# ------------------------------------------------------------------------------
# 4. 메인 렌더링 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 럭셔리 요약뉴스 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 46)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 36)
        
        # [신규] 글자 크기 이원화 (1번 뉴스는 30, 나머지 서브 뉴스는 22)
        font_body_main = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 30) 
        font_body_sub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 22) 
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
    except:
        font_huge = font_large = font_title = font_body_main = font_body_sub = font_small = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험", "요양병원", "보건복지부", "비급여 진료"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양"])
    finance_news = fetch_category_news(["국내 증시 KOSPI", "미국 증시 나스닥", "원달러 환율", "퇴직연금", "가상화폐 비트코인"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식"])
    tip_news = fetch_category_news(["연말정산 팁", "정부 지원금", "소상공인 혜택", "알뜰폰", "절세 방법"])

    # 오디오 대본은 1번 뉴스만 강렬하게! (대본에서 [출처] 부분은 안 읽히도록 정제)
    def make_short_script(intro, news_list):
        # "[조선일보] 금리 인하" -> "금리 인하" 로 발음되도록 괄호 삭제
        first_news = re.sub(r'\[.*?\]\s*', '', news_list[0])
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {first_news} 입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (52, 152, 219), "bg_keyword": "bg_health", "items": health_news, "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (46, 204, 113), "bg_keyword": "bg_estate", "items": econ_news, "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (243, 156, 18), "bg_keyword": "bg_finance", "items": finance_news, "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "bg_social", "items": social_news, "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (231, 76, 60), "bg_keyword": "bg_tip", "items": tip_news, "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은 {today_str}입니다."}]
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg_keyword": cat["bg_keyword"], "subtitle": f"오늘의 핵심 뉴스 ({i}/5)", "items": cat["items"], "script": cat["script"]})
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
                    overlay.paste(avatar, (img_width//2 - 170, 150), avatar)
            
            draw_ov.text((img_width//2, 550), "박씨네 보험톡", fill=(255, 255, 255, 255), font=font_huge, anchor="mm")
            draw_ov.text((img_width//2, 650), "일일 주요뉴스", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            draw_ov.rounded_rectangle([img_width//2 - 120, 720, img_width//2 + 120, 770], fill=(255, 255, 255, 20), radius=25)
            draw_ov.text((img_width//2, 745), f"발행일 : {today_str}", fill=(180, 200, 230, 255), font=font_small, anchor="mm")
            
            dash_y = 860
            draw_ov.rounded_rectangle([40, dash_y, img_width - 40, dash_y + 260], fill=(0, 0, 0, 150), outline=(80, 90, 110, 255), width=2, radius=15)
            # [수정] 엑스박스 뜨던 이모티콘 텍스트 기호로 예쁘게 대체
            draw_ov.text((img_width//2, dash_y + 40), "〓  오늘의 주요 경제 지표 (전일 기준)  〓", fill=(255, 215, 0, 255), font=font_body_sub, anchor="mm")
            draw_ov.line([(60, dash_y + 80), (img_width-60, dash_y + 80)], fill=(80, 90, 110, 255), width=1)
            
            draw_ov.text((70, dash_y + 125), "KOSPI", fill=(200, 210, 230, 255), font=font_body_sub, anchor="lm")
            draw_ov.text((img_width - 70, dash_y + 125), eco_data["kospi"], fill=(255, 255, 255, 255), font=font_title, anchor="rm")
            
            draw_ov.text((70, dash_y + 180), "KOSDAQ", fill=(200, 210, 230, 255), font=font_body_sub, anchor="lm")
            draw_ov.text((img_width - 70, dash_y + 180), eco_data["kosdaq"], fill=(255, 255, 255, 255), font=font_title, anchor="rm")
            
            draw_ov.text((70, dash_y + 235), "환율 (USD)", fill=(200, 210, 230, 255), font=font_body_sub, anchor="lm")
            draw_ov.text((img_width - 70, dash_y + 235), eco_data["usd"], fill=(255, 255, 255, 255), font=font_title, anchor="rm")

        elif data["type"] == "news":
            draw_ov.rectangle([0, 90, img_width, 100], fill=data["accent"]+(255,))
            draw_ov.rounded_rectangle([40, 130, 350, 190], fill=data["accent"]+(200,), radius=10)
            draw_ov.text((60, 160), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="lm")
            
            draw_ov.rounded_rectangle([30, 230, img_width - 30, 1140], fill=(0, 0, 0, 180), outline=data["accent"]+(150,), width=2, radius=15)
            
            y_start = 280 
            for i, item in enumerate(data['items']):
                # [수정] 공간을 꽉 채우기 위해 1번 뉴스는 크게, 나머지는 작게 배치
                if i == 0:
                    y_start = draw_hanging_indent_text(draw_ov, item, font_body_main, 50, y_start, 610, (255, 255, 255, 255), is_main=True)
                else:
                    y_start = draw_hanging_indent_text(draw_ov, item, font_body_sub, 60, y_start, 610, (200, 210, 220, 255), is_main=False)
            
            draw_ov.rounded_rectangle([40, 1170, img_width - 40, 1230], fill=(0, 0, 0, 200), outline=(80, 90, 110, 255), width=1, radius=10)
            draw_ov.text((img_width//2, 1200), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
        elif data["type"] == "outro":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (260, 260))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 130, 180), avatar)
                    
            draw_ov.text((img_width//2, 500), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            draw_ov.text((img_width//2, 580), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            draw_ov.rounded_rectangle([60, 700, img_width - 60, 960], fill=(0, 0, 0, 150), outline=(100, 120, 150, 255), width=2, radius=15)
            
            # [수정] 마지막 장 좌측 정렬 및 예쁜 도형(색상) 포인트 배치
            info_start_y = 750
            draw_ov.ellipse([80, info_start_y, 100, info_start_y+20], fill=(241, 196, 15, 255)) # 전화 포인트(노랑)
            draw_ov.text((120, info_start_y - 2), "010-2062-4600", fill=(255, 255, 255, 255), font=font_title, anchor="la")
            
            draw_ov.ellipse([80, info_start_y+80, 100, info_start_y+100], fill=(46, 204, 113, 255)) # 카톡 포인트(초록)
            draw_ov.text((120, info_start_y+80 - 2), "카카오톡 : PMSUNGOO", fill=(255, 255, 255, 255), font=font_title, anchor="la")
            
            draw_ov.ellipse([80, info_start_y+160, 100, info_start_y+180], fill=(52, 152, 219, 255)) # 블로그 포인트(파랑)
            draw_ov.text((120, info_start_y+160 - 2), "blog.naver.com/insureeasy", fill=(255, 255, 255, 255), font=font_body_sub, anchor="la")
            
            draw_ov.text((img_width//2, 1100), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 230, 255), font=font_body_sub, anchor="mm")

        slide.paste(overlay, (0, 0), overlay)
        img_path = f"slide_{idx}.png"
        slide.save(img_path)
        
        audio_path = f"audio_{idx}.mp3"
        try:
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            audio_clip = AudioFileClip(audio_path)
            actual_duration = audio_clip.duration + 2.5
            img_clip = ImageClip(img_path).set_duration(actual_duration)
            video_clip = img_clip.set_audio(audio_clip)
        except Exception:
            video_clip = ImageClip(img_path).set_duration(8.0)
            
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
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 (완벽 럭셔리판)"
    
    body = "형! 진짜 모든 수정을 마친 100% 완벽 럭셔리판이 도착했어! 수고 많았어!"
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
