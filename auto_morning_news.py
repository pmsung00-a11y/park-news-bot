# ==============================================================================
# 박씨네 보험톡 방송국 - 그랜드 마스터 에디션 (최종본)
# (뉴스 9개 꽉 찬 배열, 우측 출처 정렬, 하단 문구 복구, 고급 명함 아웃트로)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# ------------------------------------------------------------------------------
# 1. 뉴스 크롤러 (언론사 출처를 맨 뒤로 이동)
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
            if ' - ' in title:
                parts = title.rsplit(' - ', 1)
                clean_title = f"{parts[0]} [{parts[1]}]"
            else:
                clean_title = title
                
            if len(clean_title) > 8:
                return clean_title
    except Exception:
        pass
    return f"{keyword} 최신 뉴스를 업데이트 중입니다. [시스템]"

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news_items.append(fetch_one_top_news(keyword))
    return news_items

# ------------------------------------------------------------------------------
# 2. 경제 지표 수집 (해외 깃허브 차단 없는 야후 글로벌 API 우회 적용)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "수집 오류", "kosdaq": "수집 오류", "usd": "수집 오류"}
    try:
        req = urllib.request.Request("https://query1.finance.yahoo.com/v7/finance/quote?symbols=^KS11,^KQ11,KRW=X", headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=5)
        data = json.loads(res.read().decode('utf-8'))
        
        for res_data in data['quoteResponse']['result']:
            sym = res_data['symbol']
            price = res_data.get('regularMarketPrice', 0)
            change = res_data.get('regularMarketChangePercent', 0)
            sign = "▲" if change > 0 else "▼" if change < 0 else "-"
            
            if sym == "^KS11":
                indicators["kospi"] = f"{price:,.2f} ({sign}{abs(change):.2f}%)"
            elif sym == "^KQ11":
                indicators["kosdaq"] = f"{price:,.2f} ({sign}{abs(change):.2f}%)"
            elif sym == "KRW=X":
                indicators["usd"] = f"{price:,.2f}원 ({sign}{abs(change):.2f}%)"
    except Exception as e:
        pass
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

# [핵심] 뉴스 9개 완벽 정렬 렌더링 (번호 부여, 자동 줄바꿈, 출처 우측 정렬)
import textwrap

def draw_news_list(draw, items, font_num, font_main, font_pub, color, start_y):
    y = start_y
    for idx, item in enumerate(items, 1):
        num_str = f"{idx:02d}. "
        
        # 제목과 출처 분리
        match = re.search(r'^(.*?)(\s*\[.*?\])$', item)
        if match:
            title = match.group(1).strip()
            pub = match.group(2).strip()
        else:
            title = item
            pub = ""
            
        # 1. 번호 그리기
        draw.text((40, y), num_str, fill=color, font=font_num, anchor="la")
        text_x = 40 + draw.textlength(num_str, font=font_num)
        
        # 2. 제목 내어쓰기(Hanging Indent) 그리기
        wrapped = textwrap.wrap(title, 26) # 9개 꽉 차게 텍스트 너비 최적화
        for line in wrapped:
            draw.text((text_x, y), line, fill=(255, 255, 255, 255), font=font_main, anchor="la")
            y += 32 # 본문 줄 간격
            
        # 3. 출처는 다음 줄 우측 끝으로 완벽 정렬
        if pub:
            pub_w = draw.textlength(pub, font=font_pub)
            draw.text((680 - pub_w, y), pub, fill=color, font=font_pub, anchor="la")
            y += 38 # 다음 뉴스와의 넉넉한 간격
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
    print(f"[{today_str}] 그랜드 마스터 에디션 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
        
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 26) 
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 24) 
        font_pub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 18)
    except:
        font_huge = font_large = font_title = font_num = font_body = font_pub = font_small = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    # 9개 꽉 찬 뉴스 키워드
    health_news = fetch_category_news(["건강보험공단", "실손보험", "요양병원", "보건복지부", "비급여 진료", "국민연금", "암보험", "의료 정책", "건강 팁"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축", "월세 동향"])
    finance_news = fetch_category_news(["국내 증시 KOSPI", "미국 증시 나스닥", "원달러 환율", "퇴직연금", "가상화폐 비트코인", "금값", "배당금", "개미 투자자", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "고용 노동", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 팁", "정부 지원금", "소상공인 혜택", "알뜰폰", "절세 방법", "청년 지원", "할인 혜택", "대중교통비", "카드 혜택"])

    def make_short_script(intro, news_list):
        first_news = re.sub(r'\s*\[.*?\]', '', news_list[0]) 
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {first_news} 입니다. 그 외 화면의 주요 소식들도 함께 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (100, 180, 255), "bg_keyword": "bg_health", "items": health_news, "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (80, 220, 150), "bg_keyword": "bg_estate", "items": econ_news, "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (255, 180, 50), "bg_keyword": "bg_finance", "items": finance_news, "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (200, 120, 220), "bg_keyword": "bg_social", "items": social_news, "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (255, 120, 100), "bg_keyword": "bg_tip", "items": tip_news, "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
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
            draw_ov.rounded_rectangle([40, 110, 360, 170], fill=data["accent"]+(200,), radius=10)
            draw_ov.text((60, 140), f"{data['category']} (9선)", fill=(255, 255, 255, 255), font=font_title, anchor="lm")
            
            draw_ov.rounded_rectangle([25, 200, img_width - 25, 1160], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            
            # [핵심] 뉴스 9개 그리기 함수 호출
            draw_news_list(draw_ov, data['items'][:9], font_num, font_body, font_pub, data["accent"]+(255,), 230)
            
            # [형이 원했던 하단 문구 완벽 부활!]
            draw_ov.rounded_rectangle([40, 1180, img_width - 40, 1240], fill=(0, 0, 0, 230), outline=(80, 90, 110, 255), width=1, radius=10)
            draw_ov.text((img_width//2, 1210), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
        elif data["type"] == "outro":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (280, 280))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 140, 180), avatar)
                    
            draw_ov.text((img_width//2, 520), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 600), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            # 고급 명함 아웃트로 박스 (이모티콘 깨짐 방지를 위해 세련된 영문 텍스트 뱃지 적용)
            box_w = 480
            box_x = (img_width - box_w) // 2
            draw_ov.rounded_rectangle([box_x, 700, box_x + box_w, 920], fill=(30, 35, 45, 240), outline=(100, 110, 130, 255), width=2, radius=15)
            
            info_start_y = 740
            badge_x = box_x + 40
            text_x = badge_x + 60
            
            # 전화번호
            draw_ov.rounded_rectangle([badge_x, info_start_y, badge_x+45, info_start_y+24], fill=(241, 196, 15, 255), radius=5)
            draw_ov.text((badge_x + 22, info_start_y + 12), "TEL", fill=(0,0,0,255), font=font_small, anchor="mm")
            draw_ov.text((text_x, info_start_y - 4), "010-2062-4600", fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            # 카카오톡
            draw_ov.rounded_rectangle([badge_x, info_start_y+65, badge_x+45, info_start_y+89], fill=(46, 204, 113, 255), radius=5)
            draw_ov.text((badge_x + 22, info_start_y + 65 + 12), "TALK", fill=(0,0,0,255), font=font_small, anchor="mm")
            draw_ov.text((text_x, info_start_y+65 - 4), "PMSUNGOO", fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            # 블로그
            draw_ov.rounded_rectangle([badge_x, info_start_y+130, badge_x+45, info_start_y+154], fill=(52, 152, 219, 255), radius=5)
            draw_ov.text((badge_x + 22, info_start_y + 130 + 12), "WEB", fill=(0,0,0,255), font=font_small, anchor="mm")
            draw_ov.text((text_x, info_start_y+130), "blog.naver.com/insureeasy", fill=(180, 200, 230, 255), font=font_pub, anchor="la")
            
            draw_ov.text((img_width//2, 1100), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 230, 255), font=font_pub, anchor="mm")

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
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 (최종 마스터 에디션)"
    
    body = "형! 하단 문구까지 완벽하게 부활한 진짜 최종 마스터본이야! 수고 많았어!"
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
