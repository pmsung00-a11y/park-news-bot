# ==============================================================================
# 해외 도서 AI 큐레이터 - 기본 뼈대 (영상제작 + 유튜브 자동 업로드 비공개 세팅 완료)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
import subprocess
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# 유튜브 업로드용 라이브러리
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WORK_DIR = "work"
os.makedirs(WORK_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- (이하 영상 제작부: 추후 해외 도서 크롤링 로직으로 교체할 기본 뼈대) ---

def _run_ffmpeg(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode('utf-8', 'ignore')[-600:])

def speedup_audio_ffmpeg(input_path, output_path, speed=1.4):
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-f', 'lavfi', '-i', 'anullsrc=channel_layout=mono:sample_rate=44100:d=1.0',
        '-filter_complex',
        f'[0:a]atempo={speed},aresample=44100,aformat=sample_fmts=s16:channel_layouts=mono[a1];'
        f'[1:a]aformat=sample_fmts=s16:channel_layouts=mono[a2];'
        f'[a1][a2]concat=n=2:v=0:a=1[aout]',
        '-map', '[aout]', '-ar', '44100', '-ac', '1', output_path
    ]
    try:
        _run_ffmpeg(cmd)
        return output_path
    except Exception as e:
        print(f"오디오 가속 실패: {e}")
        fb = [
            'ffmpeg', '-y', '-i', input_path,
            '-af', 'apad=pad_dur=1.0', '-ar', '44100', '-ac', '1', output_path
        ]
        _run_ffmpeg(fb)
        return output_path

def fetch_one_top_news(keyword):
    search_query_1d = f"{keyword} when:1d"
    url_1d = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query_1d)}&hl=ko&gl=KR&ceid=KR:ko"
    search_query_all = keyword
    url_all = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query_all)}&hl=ko&gl=KR&ceid=KR:ko"
    
    for target_url in [url_1d, url_all]:
        try:
            response = requests.get(target_url, headers=HEADERS, timeout=10)
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            if len(items) > 0:
                title = items[0].find('title').text
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
        except Exception: continue
    return None

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news = fetch_one_top_news(keyword)
        if news: news_items.append(news)
    if not news_items:
        news_items.append("도서 정보를 취합 중입니다.|[시스템]")
    return news_items

def fetch_economic_indicators():
    indicators = {"kospi": "수집 실패", "kosdaq": "수집 실패", "usd": "수집 실패"}
    try:
        r1 = requests.get("https://m.stock.naver.com/api/index/KOSPI/basic", headers=HEADERS, timeout=5).json()
        c1 = float(r1['compareToPreviousClosePrice'])
        s1 = "▲" if c1 > 0 else "▼" if c1 < 0 else "-"
        indicators["kospi"] = f"{r1['closePrice']} ({s1}{abs(float(r1['fluctuationsRatio'])):.2f}%)"
    except Exception: pass
    try:
        r2 = requests.get("https://m.stock.naver.com/api/index/KOSDAQ/basic", headers=HEADERS, timeout=5).json()
        c2 = float(r2['compareToPreviousClosePrice'])
        s2 = "▲" if c2 > 0 else "▼" if c2 < 0 else "-"
        indicators["kosdaq"] = f"{r2['closePrice']} ({s2}{abs(float(r2['fluctuationsRatio'])):.2f}%)"
    except Exception: pass
    try:
        url = "https://m.stock.naver.com/front-api/v1/marketIndex/prices?category=exchange&reutersCode=FX_USDKRW"
        r3 = requests.get(url, headers=HEADERS, timeout=5).json()
        price = r3['result']['closePrice']
        c_rate = r3['result']['fluctuationsRatio']
        c_val = r3['result']['compareToPreviousClosePrice']
        s3 = "▲" if float(c_val) > 0 else "▼" if float(c_val) < 0 else "-"
        indicators["usd"] = f"{price}원 ({s3}{abs(float(c_rate)):.2f}%)"
    except Exception: pass
    return indicators

def wrap_pixels(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) > max_w and cur:
            lines.append(cur.strip())
            cur = ch
        else:
            cur += ch
    if cur.strip():
        lines.append(cur.strip())
    return lines or [""]

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

def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 렌더링 시작...")
    
    filename = f"book_review_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    def load_font(bold, size):
        names = ["NanumGothicBold.ttf" if bold else "NanumGothic.ttf"]
        dirs = ["/usr/share/fonts/truetype/nanum", "/usr/share/fonts/nanum", ".", "fonts"]
        for d in dirs:
            for nm in names:
                path = os.path.join(d, nm)
                if os.path.exists(path): return ImageFont.truetype(path, size)
        raise RuntimeError("한글 폰트를 찾을 수 없습니다.")

    font_huge = load_font(True, 65)
    font_large = load_font(True, 40)
    font_title = load_font(True, 34)
    font_num = load_font(True, 26)
    font_main = load_font(True, 24)
    font_pub = load_font(False, 20)
    font_small = load_font(False, 14)
    font_footer = load_font(True, 30)
    font_healing = load_font(True, 34)

    eco_data = fetch_economic_indicators()
    test_news = fetch_category_news(["베스트셀러", "신간 도서", "해외 문학", "자기계발서"])

    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        first_news = re.sub(r'^\d+\.\s*', '', first_news)
        clean_news = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', first_news)
        clean_news = re.sub(r'\s+', ' ', clean_news).strip()
        return f"{intro} 오늘 주목할 도서는 {clean_news}입니다. 그 외 화면의 추천 도서도 확인해 보십시오."

    news_database = [
        {"category": "해외 우수 도서 추천", "accent": (52, 152, 219), "bg_keyword": "bg_health", "items": test_news, "footer": "좋은 책 한 권이 인생을 바꿉니다!", "script": make_short_script("해외 도서 추천 소식입니다.", test_news)},
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, AI 글로벌 도서 큐레이터입니다. 오늘 추천 도서 발행일은 {today_str}입니다."}]
    for cat in news_database: slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg_keyword": cat["bg_keyword"], "items": cat["items"], "footer": cat["footer"], "script": cat["script"]})
    slides_data.append({"type": "outro", "script": "더 많은 인생 책이 궁금하시다면 구독과 좋아요를 부탁드립니다. 오늘도 행복한 하루 보내세요."})

    clips = []
    for slide_no, data in enumerate(slides_data, start=1):
        if data["type"] in ["cover", "outro"]: slide = Image.new("RGB", (img_width, img_height), color=(12, 18, 32))
        else:
            slide = Image.new("RGB", (img_width, img_height), color=(15, 20, 30))
            bg_file = find_image(data.get("bg_keyword", "xxxxx"))
            if bg_file:
                try:
                    bg_img = Image.open(bg_file)
                    bg_img = ImageOps.fit(bg_img, (img_width, img_height), Image.Resampling.LANCZOS)
                    slide.paste(bg_img, (0, 0))
                except Exception: pass
            
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        if data["type"] == "cover":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (340, 340))
                if avatar: overlay.paste(avatar, (img_width//2 - 170, 140), avatar)
            draw_ov.text((img_width//2, 540), "AI 글로벌", fill=(255, 255, 255, 255), font=font_huge, anchor="mm")
            draw_ov.text((img_width//2, 640), "우수 도서 큐레이션", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            draw_ov.rounded_rectangle([img_width//2 - 120, 730, img_width//2 + 120, 780], fill=(255, 255, 255, 20), radius=25)
            draw_ov.text((img_width//2, 755), f"발행일 : {today_str}", fill=(180, 200, 230, 255), font=font_pub, anchor="mm")
            dash_y = 860
            draw_ov.rounded_rectangle([70, dash_y, img_width - 70, dash_y + 260], fill=(0, 0, 0, 150), outline=(80, 90, 110, 255), width=2, radius=15)
            draw_ov.text((img_width//2, dash_y + 40), "〓  오늘의 글로벌 경제 지표 (참고)  〓", fill=(255, 215, 0, 255), font=font_pub, anchor="mm")
            draw_ov.line([(90, dash_y + 80), (img_width-90, dash_y + 80)], fill=(80, 90, 110, 255), width=1)
            draw_ov.text((100, dash_y + 120), "KOSPI", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 120), eco_data["kospi"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")
            draw_ov.text((100, dash_y + 175), "KOSDAQ", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 175), eco_data["kosdaq"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")
            draw_ov.text((100, dash_y + 230), "환율 (USD)", fill=(200, 210, 230, 255), font=font_pub, anchor="lm")
            draw_ov.text((img_width - 100, dash_y + 230), eco_data["usd"], fill=(255, 255, 255, 255), font=font_num, anchor="rm")

        elif data["type"] == "news":
            cat_w = draw_ov.textlength(data['category'], font=font_title)
            title_box_w = cat_w + 80
            draw_ov.rectangle([0, 70, img_width, 80], fill=data["accent"]+(255,))
            draw_ov.rounded_rectangle([360 - title_box_w // 2, 110, 360 + title_box_w // 2, 170], fill=(data["accent"][0]//3, data["accent"][1]//3, data["accent"][2]//3, 255), radius=10)
            draw_ov.text((img_width//2, 140), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            
            start_y, total_text_height, parsed_items = 230, 0, []
            num_w = draw_ov.textlength('00. ', font=font_num)
            for item in data['items'][:8]:
                title, _, pub = item.rpartition('|') if '|' in item else (item, '', '')
                wrapped = wrap_pixels(title, font_main, 670 - 45 - num_w - 15)
                item_h = len(wrapped) * 34 + (28 if pub else 0)
                total_text_height += item_h
                parsed_items.append({"title": wrapped, "pub": pub})
                
            gap_per_item = max(10, min(((1120 - start_y) - total_text_height) / len(parsed_items), 45)) if parsed_items else 20
            
            calculated_bottom = start_y
            for item in parsed_items: calculated_bottom += len(item["title"]) * 34 + (28 if item["pub"] else 0) + gap_per_item
            box_bottom = calculated_bottom - gap_per_item + 20
            
            draw_ov.rounded_rectangle([25, 200, 695, box_bottom], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            current_y = start_y
            for item_n, item in enumerate(parsed_items, 1):
                num_str = f"{item_n:02d}. "
                draw_ov.text((45, current_y), num_str, fill=data["accent"]+(255,), font=font_num, anchor="la")
                text_x = 45 + draw_ov.textlength(num_str, font=font_num)
                text_color = (255, 255, 255, 255) if item_n % 2 != 0 else (180, 250, 180, 255)
                for line in item["title"]:
                    draw_ov.text((text_x, current_y), line, fill=text_color, font=font_main, anchor="la")
                    current_y += 34
                if item["pub"]:
                    pub_w = draw_ov.textlength(item["pub"], font=font_pub)
                    draw_ov.text((670 - pub_w, current_y), item["pub"], fill=data["accent"]+(255,), font=font_pub, anchor="la")
                    current_y += 28
                current_y += gap_per_item
            
            footer_y = box_bottom + 20
            draw_ov.rounded_rectangle([25, footer_y, 695, footer_y + 55], fill=(255, 255, 255, 255), outline=(220, 50, 50, 255), width=3, radius=15)
            draw_ov.text((img_width//2, footer_y + 27), data["footer"], fill=(0, 0, 0, 255), font=font_healing, anchor="mm")
            
        elif data["type"] == "outro":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (280, 280))
                if avatar: overlay.paste(avatar, (img_width//2 - 140, 130), avatar)
            draw_ov.text((img_width//2, 500), "인생 책이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 580), "AI 글로벌 북 큐레이터", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            draw_ov.text((img_width//2, 1080), "오늘도 독서로 성장하는 하루 보내세요!", fill=(255, 215, 0, 255), font=font_footer, anchor="mm")

        slide.paste(overlay, (0, 0), overlay)
        img_path = os.path.join(WORK_DIR, f"slide_{slide_no}.png")
        slide.save(img_path)
        
        audio_path = os.path.join(WORK_DIR, f"audio_{slide_no}.mp3")
        fast_audio_path = os.path.join(WORK_DIR, f"fast_audio_{slide_no}.wav")
        try:
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            voice_clip_path = speedup_audio_ffmpeg(audio_path, fast_audio_path, speed=1.4)
            final_audio = AudioFileClip(voice_clip_path)
            img_clip = ImageClip(img_path).set_duration(final_audio.duration)
            video_clip = img_clip.set_audio(final_audio)
        except Exception:
            video_clip = ImageClip(img_path).set_duration(6.0)
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(filename, fps=10, preset="ultrafast", threads=4, codec="libx264", bitrate="1000k", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    print(f"동영상 렌더링 완료: {filename}")
    return filename, today_str

def send_email_with_video(video_path, receiver_email, today_str):
    sender_email = "pmsung00@gmail.com"  
    sender_password = "eurhztmevmaxlqki"
    
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender_email, receiver_email
    msg['Subject'] = f"[AI 도서 큐레이터] {today_str} 해외 추천 도서 영상"
    msg.attach(MIMEText(f"{today_str} AI가 추천하는 해외 우수 도서 영상을 첨부합니다.", 'plain'))
    
    try:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(video_path)}")
        msg.attach(part)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("이메일 발송 성공!")
    except Exception as e: print(f"이메일 발송 실패: {e}")


# ------------------------------------------------------------------------------
# 📺 6. 대망의 유튜브 자동 업로드 모듈! (해외 도서 추천 테마 적용 완료)
# ------------------------------------------------------------------------------
def upload_to_youtube(video_path, today_str):
    print("유튜브 업로드를 시작합니다...")
    
    client_id = os.environ.get('YOUTUBE_CLIENT_ID')
    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')

    if not all([client_id, client_secret, refresh_token]):
        print("⚠️ 깃허브 금고(Secrets)에 유튜브 키가 없어서 업로드를 건너뜁니다.")
        return

    # 마스터 키(Refresh Token)를 이용해 권한 부여
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    youtube = build("youtube", "v3", credentials=creds)
    
    # 1. 제목 설정 (해외 도서 테마)
    title = f"[{today_str}] AI가 추천하는 오늘의 해외 우수 도서 베스트 (3분 요약)"
    
    # 2. 본문 내용 설정 (해외 도서 테마)
    description = f"""안녕하세요! AI 글로벌 도서 큐레이터입니다.
오늘({today_str}) 주목해야 할 해외 우수 도서를 엄선하여 3분 만에 핵심만 요약해 드립니다.

📚 매일 업데이트되는 세계의 양서 리뷰!
구독과 좋아요를 누르시면 인생의 인사이트를 넓혀줄 글로벌 베스트셀러를 가장 먼저 만나보실 수 있습니다.

해외 도서 및 비즈니스 문의:
📧 pmsung00@gmail.com"""

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["해외도서", "책추천", "AI도서리뷰", "베스트셀러", "자기계발서", "북튜버"],
            "categoryId": "27"  # 교육
        },
        "status": {
            # 3. 공개 여부: '비공개(private)'로 설정
            "privacyStatus": "private"  
        }
    }

    try:
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        print(f"🎉 유튜브 자동 업로드 대성공! 영상 링크: https://youtu.be/{response['id']}")
    except Exception as e:
        print(f"❌ 유튜브 업로드 실패: {e}")

if __name__ == "__main__":
    video_file, date_str = create_full_news_video_with_audio()
    send_email_with_video(video_file, "pmsung00@gmail.com", date_str)
    # 깃허브 금고 열쇠를 이용한 유튜브 자동 업로드 실행!
    upload_to_youtube(video_file, date_str)
# --- END OF CODE ---
