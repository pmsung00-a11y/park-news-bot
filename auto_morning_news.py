# ==============================================================================
# 박씨네 보험톡 - 최종 마스터 (구글 드라이브 업로드 & 랜덤 명언 & 블로그 자동화)
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
import random  # 매일 새로운 명언을 뽑기 위한 부품 추가
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

def fetch_category_news(keywords_list, max_items=6): 
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
    for root, dirs, files in os.walk('.'):
        for file in files:
            if keyword.lower() in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')):
                return os.path.join(root, file)
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

def crop_transparent(img):
    try:
        bbox = img.split()[-1].getbbox()
        if bbox: return img.crop(bbox)
    except: pass
    return img

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
    font_large = load_font(True, 38)
    font_title = load_font(True, 32)
    font_card_title = load_font(True, 30)
    font_pub = load_font(True, 16)
    font_footer = load_font(True, 24)

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "비급여 진료"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF"])
    finance_news = fetch_category_news(["코스피 마감", "미국 증시", "원달러 환율", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "사회 이슈", "교육 정책", "지역 뉴스"]) 
    tip_news = fetch_category_news(["생활 꿀팁", "살림 노하우", "생활 정보", "유용한 상식", "생활비 절약"])

    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        clean_news = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', first_news)
        clean_news = re.sub(r'\s+', ' ', clean_news).strip()
        return f"{intro} 첫 번째 뉴스는, {clean_news} 입니다. 화면의 다른 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 소식", "accent": (231, 76, 60), "bg": "bg_health", "items": health_news, "footer": "건강이 최고의 자산입니다!", "script": make_short_script("건강, 보험 소식입니다.", health_news)},
        {"category": "부동산 · 경제 흐름", "accent": (46, 204, 113), "bg": "bg_estate", "items": econ_news, "footer": "안전한 자산 관리의 시작!", "script": make_short_script("부동산, 경제 흐름입니다.", econ_news)},
        {"category": "국내외 금융 시황", "accent": (52, 152, 219), "bg": "bg_finance", "items": finance_news, "footer": "현명한 투자가 미래를 바꿉니다!", "script": make_short_script("금융 시황 브리핑입니다.", finance_news)},
        {"category": "사회 · 일상 뉴스", "accent": (155, 89, 182), "bg": "bg_social", "items": social_news, "footer": "우리가 알아야 할 사회 소식!", "script": make_short_script("사회 및 일상 소식입니다.", social_news)},
        {"category": "놓치면 아쉬운 꿀팁", "accent": (243, 156, 18), "bg": "bg_tip", "items": tip_news, "footer": "알아두면 돈이 되는 정보!", "script": make_short_script("놓치면 안 될 생활 꿀팁입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은, {today_str} 입니다."}]
    for cat in news_database: slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg": cat["bg"], "items": cat["items"], "footer": cat["footer"], "script": cat["script"]})
    slides_data.append({"type": "outro", "script": "보험이 궁금할 땐, 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 기분 좋은 하루 보내시길 바랍니다."})

    brand_yellow = (255, 215, 0, 255)
    dark_bg = (15, 20, 30, 255)

    clips = []
    for slide_no, data in enumerate(slides_data, start=1):
        if data["type"] in ["cover", "outro"]:
            slide = Image.new("RGBA", (img_width, img_height), color=dark_bg)
        else:
            bg_file = find_image(data["bg"])
            if bg_file and os.path.exists(bg_file):
                try:
                    slide = Image.open(bg_file).convert("RGBA")
                    slide = ImageOps.fit(slide, (img_width, img_height), Image.Resampling.LANCZOS)
                except:
                    slide = Image.new("RGBA", (img_width, img_height), color=dark_bg)
            else:
                slide = Image.new("RGBA", (img_width, img_height), color=dark_bg)

            overlay_dark = Image.new("RGBA", (img_width, img_height), (12, 16, 25, 210))
            slide = Image.alpha_composite(slide, overlay_dark)

        draw = ImageDraw.Draw(slide)

        if data["type"] == "cover":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (300, 300))
                if avatar: slide.paste(avatar, (img_width//2 - 150, 110), avatar)
                
            draw.text((img_width//2, 470), "박씨네 보험톡", fill=(255, 255, 255, 255), font=font_huge, anchor="mm")
            draw.text((img_width//2, 550), "일일 주요뉴스", fill=brand_yellow, font=font_huge, anchor="mm")
            
            dash_y = 650
            draw.rounded_rectangle([40, dash_y, img_width - 40, dash_y + 440], fill=(20, 28, 42, 240), outline=(80, 95, 120, 255), width=2, radius=25)
            draw.text((img_width//2, dash_y + 45), "〓 오늘의 주요 경제 지표 〓", fill=brand_yellow, font=font_title, anchor="mm")
            draw.line([(80, dash_y + 90), (img_width-80, dash_y + 90)], fill=(80, 95, 120, 255), width=1)
            
            draw.text((80, dash_y + 160), "KOSPI", fill=(200, 215, 235, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 160), eco_data["kospi"], fill=(255, 100, 100, 255) if "▲" in eco_data["kospi"] else (100, 180, 255, 255), font=font_title, anchor="rm")
            
            draw.text((80, dash_y + 245), "KOSDAQ", fill=(200, 215, 235, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 245), eco_data["kosdaq"], fill=(255, 100, 100, 255) if "▲" in eco_data["kosdaq"] else (100, 180, 255, 255), font=font_title, anchor="rm")
            
            draw.text((80, dash_y + 330), "환율 (USD)", fill=(200, 215, 235, 255), font=font_card_title, anchor="lm")
            draw.text((img_width - 80, dash_y + 330), eco_data["usd"], fill=(255, 255, 255, 255), font=font_title, anchor="rm")

            draw.text((img_width//2, 1190), f"발행일 : {today_str}", fill=brand_yellow, font=font_footer, anchor="mm")

        elif data["type"] == "news":
            title_box_w = 340
            box_x1 = int(img_width//2 - title_box_w//2)
            box_y1 = 70
            box_x2 = int(img_width//2 + title_box_w//2)
            box_y2 = 135
            
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], fill=(20, 28, 42, 240), outline=data["accent"], width=2, radius=12)
            draw.text((img_width//2, 102), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            
            char_height = 190
            toktok_file = find_image("toktok")
            if toktok_file and os.path.exists(toktok_file):
                try:
                    t_img = Image.open(toktok_file).convert("RGBA")
                    t_img = crop_transparent(t_img) 
                    t_pct = (char_height / float(t_img.size[1]))
                    t_w = int((float(t_img.size[0]) * float(t_pct)))
                    t_img = t_img.resize((t_w, char_height), Image.Resampling.LANCZOS)
                    slide.paste(t_img, (35, int(box_y1 - 65)), t_img)
                except: pass

            toksun_file = find_image("toksun")
            if toksun_file and os.path.exists(toksun_file):
                try:
                    s_img = Image.open(toksun_file).convert("RGBA")
                    s_img = crop_transparent(s_img) 
                    s_pct = (char_height / float(s_img.size[1]))
                    s_w = int((float(s_img.size[0]) * float(s_pct)))
                    s_img = s_img.resize((s_w, char_height), Image.Resampling.LANCZOS)
                    slide.paste(s_img, (img_width - s_w - 35, int(box_y1 - 65)), s_img)
                except: pass

            start_y = 150
            slot_h = (1130 - 150) / 6
            for i, item in enumerate(data['items'][:6]):
                title, _, pub = item.rpartition('|') if '|' in item else (item, '', '')
                wrapped = wrap_pixels(title, font_card_title, 530)
                
                card_h = len(wrapped) * 38 + 26
                card_y = int(start_y + (i * slot_h) + (slot_h - card_h) / 2)
                
                draw.rounded_rectangle([30, card_y, img_width - 30, card_y + card_h], fill=(255, 255, 255, 255), outline=data["accent"], width=3, radius=12)
                draw.rounded_rectangle([30, card_y, 42, card_y + card_h], fill=data["accent"], radius=12)
                draw.rectangle([36, card_y, 42, card_y + card_h], fill=data["accent"])

                text_y = card_y + 12
                for line in wrapped:
                    draw.text((60, text_y), line, fill=(20, 20, 20, 255), font=font_card_title, anchor="la")
                    text_y += 38
                
                if pub:
                    pub = pub.replace('[', '').replace(']', '')
                    pub_w = draw.textlength(pub, font=font_pub)
                    pub_box_x = int(img_width - 35 - pub_w - 20)
                    pub_box_y = int(card_y + card_h + 3)
                    
                    draw.rounded_rectangle([pub_box_x, pub_box_y, img_width - 30, pub_box_y + 22], fill=(0, 0, 0, 255), radius=6)
                    draw.text((pub_box_x + 10, pub_box_y + 3), pub, fill=(255, 255, 255, 255), font=font_pub, anchor="la")
            
            draw.rounded_rectangle([60, 1150, img_width - 60, 1220], fill=(20, 28, 42, 240), outline=brand_yellow, width=2, radius=18)
            draw.text((img_width//2, 1185), data["footer"], fill=brand_yellow, font=font_footer, anchor="mm")

        elif data["type"] == "outro":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (240, 240))
                if avatar: slide.paste(avatar, (img_width//2 - 120, 80), avatar)
                
            draw.text((img_width//2, 350), "보험이 궁금할 땐?", fill=(220, 230, 245, 255), font=font_large, anchor="mm")
            draw.text((img_width//2, 410), "박씨네 보험톡", fill=brand_yellow, font=font_huge, anchor="mm")
            
            font_outro_small = load_font(True, 19)
            dash_y = 520
            box_w = 540  
            box_h = 240
            o_x1 = int(img_width//2 - box_w//2)
            o_x2 = int(img_width//2 + box_w//2)
            
            draw.rounded_rectangle([o_x1, dash_y, o_x2, dash_y + box_h], fill=(20, 28, 42, 240), outline=(80, 95, 120, 255), width=2, radius=18)
            
            draw.text((o_x1 + 30, dash_y + 45), "▶ 전화 상담", fill=(200, 215, 235, 255), font=font_outro_small, anchor="lm")
            draw.text((o_x2 - 30, dash_y + 45), "010-2062-4600", fill=(255, 255, 255, 255), font=font_outro_small, anchor="rm")
            draw.line([(o_x1 + 20, dash_y + 80), (o_x2 - 20, dash_y + 80)], fill=(60, 75, 100, 255), width=1)

            draw.text((o_x1 + 30, dash_y + 120), "▶ 카카오톡", fill=(200, 215, 235, 255), font=font_outro_small, anchor="lm")
            draw.text((o_x2 - 30, dash_y + 120), "PMSUNGOO", fill=(255, 255, 255, 255), font=font_outro_small, anchor="rm")
            draw.line([(o_x1 + 20, dash_y + 155), (o_x2 - 20, dash_y + 155)], fill=(60, 75, 100, 255), width=1)

            draw.text((o_x1 + 30, dash_y + 195), "▶ 공식 블로그", fill=(200, 215, 235, 255), font=font_outro_small, anchor="lm")
            draw.text((o_x2 - 30, dash_y + 195), "blog.naver.com/insureeasy", fill=(255, 255, 255, 255), font=font_outro_small, anchor="rm")

            draw.text((img_width//2, 880), "오늘도 기분 좋은 하루 보내세요!", fill=brand_yellow, font=font_title, anchor="mm")
            draw.text((img_width//2, 1180), "박씨네 보험톡과 함께 든든한 하루를 시작하세요!", fill=(180, 190, 210, 255), font=font_footer, anchor="mm")

        slide = slide.convert("RGB")
        img_path = os.path.join(WORK_DIR, f"slide_{slide_no}.png")
        slide.save(img_path)
        
        audio_path = os.path.join(WORK_DIR, f"audio_{slide_no}.mp3")
        
        try:
            print(f"[{slide_no}번 슬라이드] 일레븐랩스 음성 생성 시도...")
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
    final_video.write_videofile(filename, fps=24, preset="medium", threads=4, codec="libx264", bitrate="5000k", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    
    blog_text = ""
    for idx, cat in enumerate(news_database, start=1):
        blog_text += f"\n▶ {idx}. {cat['category']}\n"
        for item in cat['items'][:6]:
            title = item.split('|')[0]
            blog_text += f" - {title}\n"
    
    return filename, today_str, blog_text

def upload_to_drive(video_path, file_name):
    client_id = os.environ.get('YOUTUBE_CLIENT_ID')
    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]): 
        return "토큰 에러: 깃허브 설정(Secrets)을 확인하세요."

    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token", client_id=client_id, client_secret=client_secret)
    
    try:
        print("\n[구글 드라이브] 영상 자동 업로드를 시작합니다...")
        drive_service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_name}
        media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
        
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        file_id = file.get('id')
        drive_link = file.get('webViewLink')
        
        drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        return drive_link
    except Exception as e:
        print(f"[구글 드라이브] 업로드 에러 발생: {e}")
        return "구글 드라이브 업로드 지연 (에러 발생)"

def send_email_with_video(video_path, receiver_email, today_str, drive_link, blog_text):
    sender_email = "pmsung00@gmail.com"
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')
    
    if not sender_password: return
    
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender_email, receiver_email
    msg['Subject'] = f"[블로그용] {today_str} 박씨네 보험톡 아침뉴스 완성본"
    
    # 🌟 박씨네 보험톡 맞춤형 에이스 명언 50개 리스트
    quotes = [
        "건강은 가장 큰 재산이며, 긍정적인 마음은 가장 강한 무기입니다.",
        "성공은 매일 반복된 작은 노력들의 합입니다. - 로버트 콜리어",
        "위대한 일은 갑자기 이루어지지 않습니다. 작은 일들이 모여 이루어집니다. - 빈센트 반 고흐",
        "행복의 문 하나가 닫히면 다른 문이 열립니다. - 헬렌 켈러",
        "오늘 하루를 어떻게 보내느냐가 당신의 미래를 결정합니다.",
        "기회는 일어나는 것이 아니라 만들어내는 것입니다. - 크리스 그로서",
        "성공으로 가는 길은 항상 공사 중입니다. - 릴리 톰린",
        "어제보다 나은 오늘을 만드는 것은 바로 지금 이 순간의 다짐입니다.",
        "도전하지 않는 사람에게는 실패도, 성공도 찾아오지 않습니다.",
        "가장 빛나는 별은 아직 발견되지 않은 당신의 내면에 있습니다.",
        "어려움 속에는 항상 새로운 기회가 숨어 있습니다. - 알베르트 아인슈타인",
        "우리의 가장 큰 영광은 한 번도 실패하지 않는 것이 아니라, 넘어질 때마다 일어서는 데 있습니다. - 공자",
        "오늘 나무 그늘에서 쉴 수 있는 이유는 누군가 오래전에 나무를 심었기 때문입니다. - 워런 버핏",
        "아무리 작은 변화라도 꾸준히 지속하면 위대한 결과를 만듭니다.",
        "당신이 할 수 있다고 믿든 할 수 없다고 믿든, 당신이 믿는 대로 될 것입니다. - 헨리 포드",
        "건강한 신체에 건강한 정신이 깃든다. - 유베날리스",
        "가장 좋은 투자는 나 자신과 내 가족의 미래를 지키는 것입니다.",
        "행복은 성취의 기쁨과 창조적 노력이 주는 스릴 속에 있습니다. - 프랭클린 루스벨트",
        "우리가 두려워해야 할 것은 실패가 아니라, 시도조차 하지 않는 것입니다.",
        "마음만을 가지고 있어서는 안 됩니다. 반드시 실천하여야 합니다. - 이소룡",
        "오늘의 준비가 내일의 평안을 만듭니다.",
        "인생에서 가장 큰 위험은 아무런 위험도 감수하지 않는 것입니다. - 마크 주커버그",
        "자신을 믿는 순간부터 어떻게 살아갈지 알게 됩니다. - 괴테",
        "성공이란 열정을 잃지 않고 실패를 거듭할 수 있는 능력입니다. - 윈스턴 처칠",
        "당신의 하루를 지배하십시오. 그렇지 않으면 하루가 당신을 지배할 것입니다. - 짐 론",
        "비온 뒤에 땅이 굳어지듯, 우리의 삶도 시련을 통해 더 단단해집니다.",
        "모든 성취의 시작점은 마음속의 갈망입니다. - 나폴레온 힐",
        "어떤 일이든 시작이 가장 중요합니다. 오늘 당장 시작하세요!",
        "긍정적인 생각은 부정적인 생각보다 모든 것을 훨씬 더 낫게 만듭니다. - 지그 지글러",
        "미래는 현재 우리가 무엇을 하고 있는가에 달려 있습니다. - 마하트마 간디",
        "웃음은 돈이 들지 않지만, 그 가치는 계산할 수 없을 만큼 큽니다.",
        "인생은 자전거를 타는 것과 같습니다. 균형을 잡으려면 계속 움직여야 합니다. - 아인슈타인",
        "지금의 작은 땀방울이 미래의 큰 미소를 만듭니다.",
        "준비된 자에게 기회는 반드시 찾아옵니다.",
        "마음이 즐거우면 몸도 건강해집니다. 오늘 하루도 크게 한번 웃어보세요!",
        "우리는 우리가 매일 하는 행동 그 자체입니다. - 아리스토텔레스",
        "행복은 목적지가 아니라, 여행하는 과정 그 자체입니다.",
        "시간은 우리가 가진 가장 귀중한 자산입니다.",
        "당신의 미소가 누군가에게는 하루를 살아갈 큰 힘이 됩니다.",
        "위기는 또 다른 이름의 기회입니다.",
        "행동이 항상 행복을 가져다주지는 않을지 몰라도, 행동 없이는 행복도 없습니다.",
        "인생은 폭풍우가 지나가길 기다리는 것이 아니라 빗속에서 춤추는 법을 배우는 것입니다.",
        "지금 당장 행동하지 않으면 미래도 바뀌지 않습니다.",
        "내가 변하면 세상이 변합니다. 긍정의 힘을 믿으세요!",
        "시작하는 데 있어 너무 늦은 때란 없습니다.",
        "건강을 잃으면 모든 것을 잃는 것입니다. 오늘 하루도 무조건 건강 챙기십시오!",
        "우리가 꿈꿀 수 있다면, 우리는 그것을 이룰 수도 있습니다. - 월트 디즈니",
        "인생의 가장 큰 실수는 실수할까 봐 두려워하는 것입니다.",
        "자신의 길을 믿고 끝까지 걸어가십시오. 당신의 선택이 옳습니다.",
        "오늘 당신이 베푼 작은 친절이 내일 더 큰 행운으로 돌아옵니다."
    ]
    daily_quote = random.choice(quotes)
    
    email_body = f"""형님! 오늘의 뉴스 영상 제작 및 구글 드라이브 업로드가 완료되었습니다.

🎥 [영상 다운로드 링크]
{drive_link}
(위 링크를 눌러 우측 상단 '다운로드' 버튼으로 영상을 받으신 후 블로그에 올려주세요.)

=========================================
👇 [아래 텍스트를 복사해서 블로그에 바로 올리세요] 👇
=========================================

[제목] {today_str} 알면 돈이 되는 아침 뉴스 브리핑 (박씨네 보험톡)

💡 오늘의 명언
"{daily_quote}"

활기찬 아침입니다! 고객님의 든든한 파트너 박씨네 보험톡입니다.
오늘 하루도 기분 좋게 시작하실 수 있도록, 꼭 알아야 할 핵심 뉴스를 준비했습니다.

▶️ 오늘의 뉴스 영상 보러 가기 : [여기에 발행된 블로그 URL 붙여넣기]
{blog_text}
#박씨네보험톡 #오늘의뉴스 #경제뉴스 #부동산뉴스 #건강보험 #보험리모델링 #생활꿀팁 #대구보험설계사 #실손보험청구
=========================================
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
    video_file, date_str, news_blog_text = create_full_news_video_with_audio()
    gdrive_link = upload_to_drive(video_file, video_file)
    send_email_with_video(video_file, "pmsung00@gmail.com", date_str, gdrive_link, news_blog_text)
