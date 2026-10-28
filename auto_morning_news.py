# ==============================================================================
# 박씨네 보험톡 - 최종 마스터 (일레븐랩스 형님 목소리 탑재 + 에러 방어 로직)
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
        "model_id": "eleven_multilingual_v2", # 한국어를 가장 자연스럽게 읽는 모델
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

def fetch_category_news(keywords_list, max_items=8):
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
        return f"{price:,.2f}원 (-)"
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

# --- 🎬 비디오 렌더링 ---
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
    font_num = load_font(True, 26)
    font_main = load_font(True, 24)
    font_pub = load_font(False, 20)
    font_small = load_font(False, 14)
    font_footer = load_font(True, 30)
    font_healing = load_font(True, 34)

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
        return f"{intro} 오늘 주목할 첫 번째 뉴스는, {clean_news} 입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (52, 152, 219), "bg_keyword": "bg_health", "items": health_news, "footer": "오늘도 건강하고 활기찬 하루 보내세요!", "script": make_short_script("건강, 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (46, 204, 113), "bg_keyword": "bg_estate", "items": econ_news, "footer": "당신의 소중한 자산, 든든하게 지켜드릴게요!", "script": make_short_script("부동산, 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (243, 156, 18), "bg_keyword": "bg_finance", "items": finance_news, "footer": "현명한 금융 습관이 밝은 미래를 만듭니다!", "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "bg_social", "items": social_news, "footer": "세상을 밝히는 따뜻한 소식이 더 많아지길!", "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (231, 76, 60), "bg_keyword": "bg_tip", "items": tip_news, "footer": "작은 상식 하나가 모여 큰 지혜가 됩니다!", "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 주요뉴스입니다. 오늘 발행일은, {today_str} 입니다."}]
    for cat in news_database: slides_data.append({"type": "news", "category": cat["category"], "accent": cat["accent"], "bg_keyword": cat["bg_keyword"], "items": cat["items"], "footer": cat["footer"], "script": cat["script"]})
    slides_data.append({"type": "outro", "script": "보험이 궁금할 땐, 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 행복한 하루 보내시길 응원합니다."})

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
                except: pass
            
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        if data["type"] == "cover":
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (340, 340))
                if avatar: overlay.paste(avatar, (img_width//2 - 170, 140), avatar)
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
            draw_ov.text((img_width//2, 500), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 580), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            t1, t2, t3 = "010-2062-4600", "PMSUNGOO", "blog.naver.com/insureeasy"
            max_text_w = max(draw_ov.textlength(t1, font=font_num), draw_ov.textlength(t2, font=font_num), draw_ov.textlength(t3, font=font_pub))
            out_box_w = 24 + 15 + max_text_w + 80
            out_box_x = (img_width - out_box_w) / 2
            draw_ov.rounded_rectangle([out_box_x, 680, out_box_x + out_box_w, 900], fill=(30, 35, 45, 255), outline=(100, 110, 130, 255), width=2, radius=15)
            
            info_start_y, ix = 715, out_box_x + 35
            text_x = ix + 40
            draw_ov.rounded_rectangle([ix, info_start_y, ix+24, info_start_y+38], radius=4, fill=(241, 196, 15, 255))
            draw_ov.rectangle([ix+3, info_start_y+4, ix+21, info_start_y+30], fill=(30, 35, 45, 255))
            draw_ov.ellipse([ix+10, info_start_y+33, ix+14, info_start_y+35], fill=(255, 255, 255, 255))
            draw_ov.text((text_x, info_start_y + 6), t1, fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            iy = info_start_y + 65
            draw_ov.ellipse([ix-3, iy+2, ix+27, iy+28], fill=(250, 225, 0, 255))
            draw_ov.polygon([(ix+4, iy+24), (ix+8, iy+36), (ix+12, iy+26)], fill=(250, 225, 0, 255))
            draw_ov.text((ix+12, iy+15), "TALK", fill=(0, 0, 0, 255), font=font_small, anchor="mm")
            draw_ov.text((text_x, iy + 6), t2, fill=(255, 255, 255, 255), font=font_num, anchor="la")
            
            iy += 65
            draw_ov.ellipse([ix, iy, ix+24, iy+24], fill=(52, 152, 219, 255))
            draw_ov.ellipse([ix+3, iy, ix+21, iy+24], outline=(255, 255, 255, 255), width=1)
            draw_ov.line([(ix, iy+12), (ix+24, iy+12)], fill=(255, 255, 255, 255), width=1)
            draw_ov.line([(ix+12, iy), (ix+12, iy+24)], fill=(255, 255, 255, 255), width=1)
            draw_ov.text((text_x, iy + 3), t3, fill=(180, 200, 230, 255), font=font_pub, anchor="la")
            draw_ov.text((img_width//2, 1080), "오늘도 행복한 하루 보내세요!", fill=(255, 215, 0, 255), font=font_footer, anchor="mm")

        slide.paste(overlay, (0, 0), overlay)
        img_path = os.path.join(WORK_DIR, f"slide_{slide_no}.png")
        slide.save(img_path)
        
        audio_path = os.path.join(WORK_DIR, f"audio_{slide_no}.mp3")
        
        # 💡 핵심 방어 로직: 일레븐랩스로 형님 목소리 시도, 실패 시 gTTS 기계음으로 알아서 대타!
        try:
            print(f"[{slide_no}번 슬라이드] 일레븐랩스(형님 목소리) 음성 생성 시도...")
            generate_elevenlabs_audio(data["script"], audio_path)
            # 형님 본연의 목소리를 위해 속도 조절(speedup) 없이 원본 속도로 병합
            final_audio = AudioFileClip(audio_path)
            print(f"[{slide_no}번 슬라이드] 형님 목소리 적용 완료!")
        except Exception as e:
            print(f"⚠️ 일레븐랩스 실패, gTTS로 비상 전환합니다. (사유: {e})")
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

def get_daily_greeting():
    korea_timezone_offset = datetime.timedelta(hours=9)
    now = datetime.datetime.utcnow() + korea_timezone_offset
    weekday = now.weekday() 

    greetings = [
        "활기찬 월요일 아침입니다! 주말의 에너지를 듬뿍 받아 이번 주도 힘차게 시작하시길 응원합니다. 💪", 
        "화창한 화요일입니다! 어제보다 더 환하게 웃을 수 있는 기분 좋은 하루 보내시길 바랍니다. 😊", 
        "한 주의 절반을 달려온 수요일입니다! 조금은 지칠 수 있지만, 따뜻한 차 한 잔의 여유를 꼭 챙기세요. ☕", 
        "든든한 목요일 아침입니다! 목표를 향해 꾸준히 나아가는 고객님의 오늘을 진심으로 응원합니다. 🏃‍♂️", 
        "기다리던 금요일입니다! 오늘 하루만 더 힘내시면 즐거운 주말이 기다리고 있으니, 마지막까지 화이팅입니다! 🎉", 
        "여유로운 토요일 아침입니다! 평일의 무거운 짐은 잠시 내려놓고, 사랑하는 사람들과 편안한 주말 보내세요. 🌿", 
        "편안한 일요일입니다! 몸과 마음을 푹 쉬어주며, 다가올 새로운 한 주를 상쾌하게 준비하시는 하루 되시길 바랍니다. ☀️" 
    ]
    return greetings[weekday]

def send_email_with_video(video_path, receiver_email, today_str, youtube_link):
    sender_email = "pmsung00@gmail.com"
    sender_password = os.environ.get('GMAIL_APP_PASSWORD')
    
    print("\n[이메일 발송 단계 시작]")
    if not sender_password: 
        print("❌ 실패 원인: 깃허브 환경변수(GMAIL_APP_PASSWORD)를 불러오지 못했습니다. .yml 파일을 꼭 확인해주세요.")
        return
    
    msg = MIMEMultipart()
    msg['From'], msg['To'] = sender_email, receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {today_str} 주요뉴스 및 카톡 전송용 링크"
    
    daily_greeting = get_daily_greeting()
    
    email_body = f"""형님! 오늘의 뉴스 영상 제작 및 유튜브 업로드가 완료되었습니다.
아래 화살표 안쪽의 내용만 쏙 복사해서 카톡으로 보내시면 됩니다!

↓↓↓↓↓ [여기서부터 아래로 복사] ↓↓↓↓↓

{daily_greeting}

바쁜 아침, 핵심만 담은 2분 영상으로 유익한 정보 챙겨가시고,
오늘 하루도 기분 좋은 일만 가득하시기를 진심으로 바랍니다. 
늘 감사합니다!

▶️ 오늘의 2분 요약뉴스 보기 : {youtube_link if youtube_link else '유튜브 업로드 지연 (첨부파일을 확인해 주세요)'}

↑↑↑↑↑ [여기까지 복사 끝] ↑↑↑↑↑
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
        print("🎉 이메일 발송 최종 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 중 에러 발생: {e}")

if __name__ == "__main__":
    video_file, date_str = create_full_news_video_with_audio()
    yt_link = upload_to_youtube(video_file, date_str)
    send_email_with_video(video_file, "pmsung00@gmail.com", date_str, yt_link)
# --- END OF CODE ---
