# ==============================================================================
# 박씨네 보험톡 - 최종 마스터 (일레븐랩스 + 앱 스타일 카드 뉴스 + 캐릭터 디자인)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
import subprocess
import requests
import difflib
import time
from email.utils import parsedate_to_datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WORK_DIR = "work"
os.makedirs(WORK_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://m.stock.naver.com/'
}

MAX_AGE_HOURS = 36  

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
    except:
        fb = ['ffmpeg', '-y', '-i', input_path, '-af', 'apad=pad_dur=1.0', '-ar', '44100', '-ac', '1', output_path]
        _run_ffmpeg(fb)
        return output_path

# --- 🎤 일레븐랩스(형님 목소리) 생성 함수 ---
def generate_elevenlabs_audio(text, output_path):
    api_key = os.environ.get('ELEVENLABS_API_KEY')
    voice_id = os.environ.get('ELEVENLABS_VOICE_ID')
    
    if not api_key or not voice_id:
        raise ValueError("깃허브 금고에 일레븐랩스 열쇠가 없습니다.")
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2", 
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

# --- 📰 뉴스 및 지표 수집 ---
def _split_title(title):
    publisher, news_title = "", title
    if ' - ' in title:
        news_title, publisher = title.rsplit(' - ', 1)
    elif title.startswith('['):
        m = re.match(r'^\[(.*?)\]\s*(.*)', title)
        if m: publisher, news_title = m.group(1), m.group(2)
    return news_title.strip(), publisher.strip()

def fetch_fresh_candidates(keyword, per_keyword=3):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(keyword + ' when:1d')}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
    except: return []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    out = []
    for it in root.findall('.//item')[:10]:
        t, pd = it.findtext('title'), it.findtext('pubDate')
        if not t or not pd: continue
        try:
            dt = parsedate_to_datetime(pd)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=datetime.timezone.utc)
        except: continue
        if (now - dt).total_seconds() / 3600 > MAX_AGE_HOURS: continue
        
        title, pub = _split_title(t)
        if len(title) > 8: out.append({"title": title, "pub": pub, "dt": dt, "kw": keyword})
    out.sort(key=lambda x: x["dt"], reverse=True)
    return out[:per_keyword]

def _norm(t): return re.sub(r'[^가-힣a-zA-Z0-9]', '', t)

def fetch_category_news(keywords_list, max_items=6): # 모바일 가독성을 위해 한 페이지당 6개로 조정
    pool = []
    for kw in keywords_list: pool.extend(fetch_fresh_candidates(kw))
    pool.sort(key=lambda x: x["dt"], reverse=True)

    picked, per_kw = [], {}
    for c in pool:
        if per_kw.get(c["kw"], 0) >= 2: continue
        if any(difflib.SequenceMatcher(None, _norm(c["title"]), _norm(p["title"])).ratio() > 0.55 for p in picked): continue
        picked.append(c)
        per_kw[c["kw"]] = per_kw.get(c["kw"], 0) + 1
        if len(picked) >= max_items: break

    if not picked: return ["오늘의 주요 뉴스를 취합 중입니다.|[시스템]"]
    return [f"{p['title']}|[{p['pub']}]" if p['pub'] else f"{p['title']}|" for p in picked]

def fetch_usd_krw():
    try:
        data = requests.get("https://open.er-api.com/v6/latest/USD", timeout=5).json()
        price = float(data['rates']['KRW'])
        return f"{price:,.2f}원"
    except: return "수집 실패"

def fetch_economic_indicators():
    indicators = {"kospi": "수집 실패", "kosdaq": "수집 실패", "usd": "수집 실패"}
    for key, code in (("kospi", "KOSPI"), ("kosdaq", "KOSDAQ")):
        try:
            r = requests.get(f"https://m.stock.naver.com/api/index/{code}/basic", headers=HEADERS, timeout=5).json()
            c = float(str(r['compareToPreviousClosePrice']).replace(',', ''))
            s = "▲" if c > 0 else "▼" if c < 0 else "-"
            indicators[key] = f"{r['closePrice']} ({s}{abs(float(r['fluctuationsRatio'])):.2f}%)"
        except: pass
    indicators["usd"] = fetch_usd_krw()
    return indicators

def wrap_pixels(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if font.getlength(cur + ch) > max_w and cur:
            lines.append(cur.strip())
            cur = ch
        else: cur += ch
    if cur.strip(): lines.append(cur.strip())
    return lines or [""]

def find_image(keyword):
    for file in os.listdir('.'):
        if keyword.lower() in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')): return file
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
    except: return None

# --- 🎬 비디오 렌더링 (디자인 개편) ---
def create_full_news_video_with_audio():
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    
    filename = f"일일 2분요약뉴스_{today_dt.strftime('%Y%m%d')}.mp4"
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
    font_card_title = load_font(True, 24)
    font_pub = load_font(False, 18)
    font_footer = load_font(True, 26)

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "비급여 진료"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF"])
    finance_news = fetch_category_news(["코스피 마감", "미국 증시", "원달러 환율", "금융 당국"])
    tip_news = fetch_category_news(["정부 지원금", "소상공인 지원", "절세 방법", "청년 혜택"])

    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        clean_news = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', first_news)
        clean_news = re.sub(r'\s+', ' ', clean_news).strip()
        return f"{intro} 첫 번째 뉴스는, {clean_news} 입니다. 화면의 다른 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 소식", "accent": (231, 76, 60), "icon": "🏥", "items": health_news, "footer": "건강이 최고의 자산입니다!", "script": make_short_script("건강, 보험 소식입니다.", health_news)},
        {"category": "부동산 · 경제 흐름", "accent": (46, 204, 113), "icon": "🏢", "items": econ_news, "footer": "안전한 자산 관리의 시작!", "script": make_short_script("부동산, 경제 흐름입니다.", econ_news)},
        {"category": "국내외 금융 시황", "accent": (52, 152, 219), "icon": "📈", "items": finance_news, "footer": "현명한 투자가 미래를 바꿉니다!", "script": make_short_script("금융 시황 브리핑입니다.", finance_news)},
        {"category": "놓치면 아쉬운 꿀팁", "accent": (243, 156, 18), "icon": "💡", "items": tip_news, "footer": "알아두면 돈이 되는 정보!", "script": make_short_script("놓치면 안 될 생활 꿀팁입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은, {today_str} 입니다."}]
    for cat in news_database: slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "items": cat["items"], "footer": cat["footer"], "script": cat["script"]})
    slides_data.append({"type": "outro", "script": "보험이 궁금할 땐, 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 기분 좋은 하루 보내시길 바랍니다."})

    brand_yellow = (255, 215, 0, 255)
    bg_warm = (248, 249, 250, 255) # 아주 밝고 따뜻한 라이트 그레이/베이지 (앱 배경 느낌)

    clips = []
    for slide_no, data in enumerate(slides_data, start=1):
        slide = Image.new("RGBA", (img_width, img_height), color=bg_warm)
        draw = ImageDraw.Draw(slide)

        if data["type"] == "cover":
            # 메인 커버: 노란색 테마와 프로필
            draw.rectangle([0, 0, img_width, 600], fill=brand_yellow) # 상단 노란색 배경
            
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (320, 320))
                if avatar: slide.paste(avatar, (img_width//2 - 160, 100), avatar)
                
            draw.text((img_width//2, 480), "박씨네 보험톡", fill=(50, 50, 50, 255), font=font_huge, anchor="mm")
            draw.text((img_width//2, 570), "일일 주요뉴스", fill=(0, 0, 0, 255), font=font_huge, anchor="mm")
            
            # 경제 지표 카드 (토스 앱 스타일)
            dash_y = 700
            draw.rounded_rectangle([40, dash_y, img_width - 40, dash_y + 400], fill=(255, 255, 255, 255), outline=(230, 230, 230, 255), width=2, radius=30)
            draw.text((img_width//2, dash_y + 60), "오늘의 주요 경제 지표", fill=(50, 50, 50, 255), font=font_title, anchor="mm")
            draw.line([(80, dash_y + 110), (img_width-80, dash_y + 110)], fill=(240, 240, 240, 255), width=2)
            
            draw.text((80, dash_y + 170), "📈 KOSPI", fill=(100, 100, 100, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 170), eco_data["kospi"], fill=(231, 76, 60, 255) if "▲" in eco_data["kospi"] else (52, 152, 219, 255), font=font_title, anchor="rm")
            
            draw.text((80, dash_y + 250), "📉 KOSDAQ", fill=(100, 100, 100, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 250), eco_data["kosdaq"], fill=(231, 76, 60, 255) if "▲" in eco_data["kosdaq"] else (52, 152, 219, 255), font=font_title, anchor="rm")
            
            draw.text((80, dash_y + 330), "💵 환율 (USD)", fill=(100, 100, 100, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 330), eco_data["usd"], fill=(50, 50, 50, 255), font=font_title, anchor="rm")

            draw.text((img_width//2, 1180), f"발행일 : {today_str}", fill=(150, 150, 150, 255), font=font_card_title, anchor="mm")

        elif data["type"] == "news":
            # 헤더 디자인 (박씨네 노란색 라벨)
            draw.rectangle([0, 0, img_width, 180], fill=brand_yellow)
            draw.rounded_rectangle([40, 90, img_width - 40, 160], fill=(255, 255, 255, 255), radius=20)
            draw.text((img_width//2, 125), data['category'], fill=(0, 0, 0, 255), font=font_large, anchor="mm")
            
            # 캐릭터 배치 (톡톡이 또는 톡순이가 있으면 헤더 우측에 귀엽게 빼꼼)
            char_file = find_image("toktok") or find_image("toksun")
            if char_file:
                try:
                    char_img = Image.open(char_file).convert("RGBA")
                    # 캐릭터 크기를 비율에 맞게 조절 (높이 150px)
                    w_pct = (150 / float(char_img.size[1]))
                    h_size = int((float(char_img.size[0]) * float(w_pct)))
                    char_img = char_img.resize((h_size, 150), Image.Resampling.LANCZOS)
                    slide.paste(char_img, (img_width - h_size - 20, 20), char_img)
                except: pass

            # 개별 뉴스 카드 그리기
            start_y = 210
            for item in data['items'][:6]: # 최대 6개 
                title, _, pub = item.rpartition('|') if '|' in item else (item, '', '')
                wrapped = wrap_pixels(title, font_card_title, 550) # 텍스트 너비 조절
                
                card_h = len(wrapped) * 35 + 45
                # 하얀색 카드 배경
                draw.rounded_rectangle([30, start_y, img_width - 30, start_y + card_h], fill=(255, 255, 255, 255), outline=(220, 220, 220, 255), width=2, radius=15)
                
                # 포인트 색상 왼쪽 띠
                draw.rounded_rectangle([30, start_y, 40, start_y + card_h], fill=data["accent"]+(255,), radius=15)
                # 띠의 오른쪽 둥근 모서리를 직각으로 덮기 (왼쪽만 둥글게)
                draw.rectangle([35, start_y, 40, start_y + card_h], fill=data["accent"]+(255,))

                # 텍스트 쓰기
                text_y = start_y + 22
                for line in wrapped:
                    draw.text((60, text_y), line, fill=(40, 40, 40, 255), font=font_card_title, anchor="la")
                    text_y += 35
                
                # 우측 하단 언론사 배지 (토스 스타일)
                if pub:
                    pub = pub.replace('[', '').replace(']', '')
                    pub_w = draw.textlength(pub, font=font_pub)
                    pub_box_x = img_width - 45 - pub_w - 20
                    pub_box_y = start_y + card_h - 35
                    draw.rounded_rectangle([pub_box_x, pub_box_y, img_width - 45, pub_box_y + 25], fill=(240, 240, 240, 255), radius=8)
                    draw.text((pub_box_x + 10, pub_box_y + 2), pub, fill=(120, 120, 120, 255), font=font_pub, anchor="la")
                
                start_y += card_h + 15
            
            # 말풍선 푸터 (톡순이 톤의 힐링 메시지)
            draw.rounded_rectangle([80, 1150, img_width - 80, 1220], fill=(255, 255, 255, 255), outline=brand_yellow, width=3, radius=35)
            draw.polygon([(img_width//2 - 10, 1150), (img_width//2 + 10, 1150), (img_width//2, 1130)], fill=brand_yellow)
            draw.text((img_width//2, 1185), data["footer"], fill=(50, 50, 50, 255), font=font_footer, anchor="mm")

        elif data["type"] == "outro":
            draw.rectangle([0, 0, img_width, img_height], fill=brand_yellow)
            
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (340, 340))
                if avatar: slide.paste(avatar, (img_width//2 - 170, 200), avatar)
                
            draw.text((img_width//2, 600), "보험이 궁금할 땐?", fill=(50, 50, 50, 255), font=font_large, anchor="mm")
            draw.text((img_width//2, 680), "박씨네 보험톡", fill=(0, 0, 0, 255), font=font_huge, anchor="mm")
            
            draw.rounded_rectangle([80, 800, img_width - 80, 1050], fill=(255, 255, 255, 255), radius=30)
            
            draw.text((120, 860), "📞 전화 상담", fill=(100, 100, 100, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 120, 860), "010-2062-4600", fill=(50, 50, 50, 255), font=font_title, anchor="rm")
            
            draw.text((120, 940), "💬 카카오톡", fill=(100, 100, 100, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 120, 940), "PMSUNGOO", fill=(50, 50, 50, 255), font=font_title, anchor="rm")

            draw.text((img_width//2, 1180), "오늘도 기분 좋은 하루 보내세요!", fill=(50, 50, 50, 255), font=font_large, anchor="mm")

        slide = slide.convert("RGB")
        img_path = os.path.join(WORK_DIR, f"slide_{slide_no}.png")
        slide.save(img_path)
        
        audio_path = os.path.join(WORK_DIR, f"audio_{slide_no}.mp3")
        
        try:
            print(f"[{slide_no}번 슬라이드] 일레븐랩스(형님 목소리) 음성 생성 시도...")
            generate_elevenlabs_audio(data["script"], audio_path)
            final_audio = AudioFileClip(audio_path)
        except Exception as e:
            print(f"⚠️ 일레븐랩스 실패, gTTS 전환: {e}")
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            fast_audio_path = os.path.join(WORK_DIR, f"fast_audio_{slide_no}.wav")
            voice_clip_path = speedup_audio_ffmpeg(audio_path, fast_audio_path, speed=1.4)
            final_audio = AudioFileClip(voice_clip_path)

        try:
            img_clip = ImageClip(img_path).set_duration(final_audio.duration)
            video_clip = img_clip.set_audio(final_audio)
        except:
            video_clip = ImageClip(img_path).set_duration(6.0)
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(filename, fps=10, preset="ultrafast", threads=4, codec="libx264", bitrate="1000k", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    return filename, today_str

def upload_to_youtube(video_path, today_str):
    client_id = os.environ.get('YOUTUBE_CLIENT_ID')
    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]): 
        return None

    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=client_id, client_secret=client_secret)
    youtube = build("youtube", "v3", credentials=creds)
    
    body = {
        "snippet": {
            "title": f"[{today_str}] 박씨네 보험톡 일일 주요뉴스 브리핑 (경제/건강/생활)",
            "description": f"안녕하십니까! 박씨네 보험톡입니다.\n오늘({today_str})의 핵심 뉴스를 브리핑해 드립니다.\n\n📞 010-2062-4600\n💬 카카오톡: PMSUNGOO",
            "tags": ["박씨네보험톡", "보험뉴스", "경제뉴스", "건강보험", "오늘의뉴스"],
            "categoryId": "25"
        },
        "status": {"privacyStatus": "private"}
    }
    try:
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
        return f"https://youtu.be/{response['id']}"
    except: 
        return None

def send_email_with_video(video_path, receiver_email, today_str, youtube_link):
    sender_email = "pmsung00@gmail.com"
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')
    
    if not sender_password: return
    
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender_email, receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {today_str} 주요뉴스 및 카톡 전송용 링크"
    
    email_body = f"""형님! 오늘의 뉴스 영상이 완성되었습니다.
아래 링크를 복사해서 카카오톡으로 고객님들께 전송해 주십시오!

↓↓↓↓↓ [여기서부터 복사] ↓↓↓↓↓

활기찬 아침입니다! 고객님의 든든한 파트너 박씨네 보험톡입니다.
오늘({today_str}) 놓치지 말아야 할 2분 핵심 뉴스를 준비했습니다.

▶️ 오늘의 영상 보기 : {youtube_link if youtube_link else '유튜브 업로드 지연'}

바쁜 출근길, 유익한 정보 챙겨가시고 오늘 하루도 기분 좋은 일만 가득하시길 진심으로 응원합니다. 늘 감사합니다!

↑↑↑↑↑ [여기까지 복사] ↑↑↑↑↑
"""
    msg.attach(MIMEText(email_body, 'plain'))
    
    try:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('video', 'mp4')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={urllib.parse.quote(os.path.basename(video_path))}")
        msg.attach(part)
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except: pass

if __name__ == "__main__":
    video_file, date_str = create_full_news_video_with_audio()
    yt_link = upload_to_youtube(video_file, date_str)
    send_email_with_video(video_file, "pmsung00@gmail.com", date_str, yt_link)
