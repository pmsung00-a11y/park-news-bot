# ==============================================================================
# 박씨네 보험톡 방송국 - 더 리턴 오브 V30 마스터 (새벽 7시 완벽 송출용)
# (1분 20초 길이의 가장 완벽했던 V30 오디오 엔진 & 대본 100% 원상복구)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# ------------------------------------------------------------------------------
# 1. FFmpeg 오디오 엔진 (V30 시절의 가장 부드러웠던 페이드아웃 코드 복구)
# ------------------------------------------------------------------------------
def speedup_audio_ffmpeg(input_path, output_path, speed=1.4):
    import moviepy.editor as mpy
    try:
        temp_clip = mpy.AudioFileClip(input_path)
        duration = temp_clip.duration
        temp_clip.close()
        
        new_duration = duration / speed
        fade_start = max(0, new_duration - 0.3)
        
        cmd = [
            'ffmpeg', '-y', '-i', input_path, 
            '-filter:a', f'atempo={speed},afade=t=out:st={fade_start}:d=0.3', 
            '-ar', '44100', output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"오디오 가속 실패, 원본 변환: {e}")
        fallback_cmd = ['ffmpeg', '-y', '-i', input_path, '-ar', '44100', output_path]
        try:
            subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return output_path
        except:
            pass
    return input_path

# ------------------------------------------------------------------------------
# 2. 뉴스 크롤러 (뉴스가 없으면 에러 멘트 대신 '스킵' 하는 스마트 로직)
# ------------------------------------------------------------------------------
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
        except Exception:
            continue
            
    return None

def fetch_category_news(keywords_list):
    news_items = []
    for keyword in keywords_list:
        news = fetch_one_top_news(keyword)
        if news:
            news_items.append(news)
            
    if not news_items:
        news_items.append("오늘의 주요 뉴스를 취합 중입니다.|[시스템]")
        
    return news_items

# ------------------------------------------------------------------------------
# 3. 경제 지표 수집 (환율 수집 완벽 해결본)
# ------------------------------------------------------------------------------
def fetch_economic_indicators():
    indicators = {"kospi": "수집 실패", "kosdaq": "수집 실패", "usd": "수집 실패"}
    
    try:
        r1 = requests.get("https://m.stock.naver.com/api/index/KOSPI/basic", headers=HEADERS, timeout=5).json()
        c1 = float(r1['compareToPreviousClosePrice'])
        s1 = "▲" if c1 > 0 else "▼" if c1 < 0 else "-"
        indicators["kospi"] = f"{r1['closePrice']} ({s1}{abs(float(r1['fluctuationsRatio'])):.2f}%)"
    except:
        try:
            r1 = requests.get("https://finance.daum.net/api/domestic/sectors/KOSPI/quotes", headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'}, timeout=5).json()
            s1 = "▲" if r1['changeRate'] > 0 else "▼" if r1['changeRate'] < 0 else "-"
            indicators["kospi"] = f"{r1['tradePrice']:,.2f} ({s1}{abs(r1['changeRate']*100):.2f}%)"
        except:
            try:
                res1 = requests.get(f"https://m.search.naver.com/search.naver?query=" + urllib.parse.quote("코스피지수"), headers=HEADERS, timeout=5).text
                m_p1 = re.search(r'<strong>([\d,.]+)</strong>\s*<span class="blind">코스피지수', res1)
                m_c1 = re.search(r'em class="(up|down|eq)">([\d,.]+)%</em>', res1)
                if m_p1:
                    s1 = "▲" if (m_c1 and m_c1.group(1)=="up") else "▼" if (m_c1 and m_c1.group(1)=="down") else "-"
                    indicators["kospi"] = f"{m_p1.group(1)} ({s1}{m_c1.group(2) if m_c1 else '0.00'}%)"
            except: pass

    try:
        r2 = requests.get("https://m.stock.naver.com/api/index/KOSDAQ/basic", headers=HEADERS, timeout=5).json()
        c2 = float(r2['compareToPreviousClosePrice'])
        s2 = "▲" if c2 > 0 else "▼" if c2 < 0 else "-"
        indicators["kosdaq"] = f"{r2['closePrice']} ({s2}{abs(float(r2['fluctuationsRatio'])):.2f}%)"
    except:
        try:
            r2 = requests.get("https://finance.daum.net/api/domestic/sectors/KOSDAQ/quotes", headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.daum.net/'}, timeout=5).json()
            s2 = "▲" if r2['changeRate'] > 0 else "▼" if r2['changeRate'] < 0 else "-"
            indicators["kosdaq"] = f"{r2['tradePrice']:,.2f} ({s2}{abs(r2['changeRate']*100):.2f}%)"
        except:
            try:
                res2 = requests.get(f"https://m.search.naver.com/search.naver?query=" + urllib.parse.quote("코스닥지수"), headers=HEADERS, timeout=5).text
                m_p2 = re.search(r'<strong>([\d,.]+)</strong>\s*<span class="blind">코스닥지수', res2)
                m_c2 = re.search(r'em class="(up|down|eq)">([\d,.]+)%</em>', res2)
                if m_p2:
                    s2 = "▲" if (m_c2 and m_c2.group(1)=="up") else "▼" if (m_c2 and m_c2.group(1)=="down") else "-"
                    indicators["kosdaq"] = f"{m_p2.group(1)} ({s2}{m_c2.group(2) if m_c2 else '0.00'}%)"
            except: pass

    try:
        url = "https://m.stock.naver.com/front-api/v1/marketIndex/prices?category=exchange&reutersCode=FX_USDKRW"
        r3 = requests.get(url, headers=HEADERS, timeout=5).json()
        price = r3['result']['closePrice']
        c_rate = r3['result']['fluctuationsRatio']
        c_val = r3['result']['compareToPreviousClosePrice']
        s3 = "▲" if float(c_val) > 0 else "▼" if float(c_val) < 0 else "-"
        indicators["usd"] = f"{price}원 ({s3}{abs(float(c_rate)):.2f}%)"
    except:
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/KRW=X?interval=1d"
            res_y = requests.get(url, headers=HEADERS, timeout=5).json()
            data_y = res_y['chart']['result'][0]['meta']
            price_y = data_y['regularMarketPrice']
            prev_close_y = data_y['chartPreviousClose']
            change_y = price_y - prev_close_y
            change_pct_y = (change_y / prev_close_y) * 100
            s3_y = "▲" if change_y > 0 else "▼" if change_y < 0 else "-"
            indicators["usd"] = f"{price_y:,.2f}원 ({s3_y}{abs(change_pct_y):.2f}%)"
        except:
            try:
                res3 = requests.get(f"https://m.search.naver.com/search.naver?query=" + urllib.parse.quote("달러환율"), headers=HEADERS, timeout=5).text
                m_p3 = re.search(r'<strong>([\d,.]+)</strong>', res3)
                m_c3 = re.search(r'em class="(up|down|eq)">([\d,.]+)%</em>', res3)
                if m_p3:
                    s3 = "▲" if (m_c3 and m_c3.group(1)=="up") else "▼" if (m_c3 and m_c3.group(1)=="down") else "-"
                    indicators["usd"] = f"{m_p3.group(1)}원 ({s3}{m_c3.group(2) if m_c3 else '0.00'}%)"
            except: pass
        
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
    print(f"[{today_str}] 더 리턴 오브 V30 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_huge = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 65)
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 40)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
        
        font_num = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 26) 
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 24) 
        font_pub = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 14)
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 30)
        font_healing = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 34)
    except:
        font_huge = font_large = font_title = font_num = font_main = font_pub = font_small = font_footer = font_healing = ImageFont.load_default()

    eco_data = fetch_economic_indicators()

    health_news = fetch_category_news(["건강보험공단", "실손보험 청구", "요양병원 정책", "보건복지부", "비급여 진료", "국민연금 개혁", "암보험", "건강 상식"])
    econ_news = fetch_category_news(["서울 아파트값", "전세 대출", "한국은행 금리", "부동산 PF", "신규 분양", "청약 경쟁률", "부동산 정책", "재건축"])
    finance_news = fetch_category_news(["코스피 마감 시황", "미국 증시 나스닥", "원달러 환율 종가", "퇴직연금", "비트코인 시세", "금값 시세", "주식 배당금", "금융 당국"])
    social_news = fetch_category_news(["사건 사고", "생활 안전", "기상 날씨", "교통 패스", "지자체 소식", "교육 정책", "복지 정책", "사회 공헌"])
    tip_news = fetch_category_news(["연말정산 꿀팁", "정부 지원금", "소상공인 지원", "알뜰폰 요금제", "절세 방법", "청년 혜택", "할인 행사", "카드 혜택"])

    # [핵심] V30 시절 멘트가 전혀 짤리지 않았던 완벽한 대본 엔진 100% 원상복구!
    def make_short_script(intro, news_list):
        first_news = news_list[0].split('|')[0]
        first_news = re.sub(r'^\d+\.\s*', '', first_news)
        first_news = re.split(r'[:|\[\-]', first_news)[0]
        clean_news = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', first_news)
        clean_news = re.sub(r'\s+', ' ', clean_news).strip()
        return f"{intro} 오늘 주목할 첫 번째 뉴스는 {clean_news}입니다. 그 외 화면의 주요 소식들도 확인해 보십시오."

    news_database = [
        {"category": "건강 · 보험 뉴스", "accent": (52, 152, 219), "bg_keyword": "bg_health", "items": health_news, "footer": "오늘도 건강하고 활기찬 하루 보내세요!", "script": make_short_script("건강 보험 소식입니다.", health_news)},
        {"category": "부동산 경제 뉴스", "accent": (46, 204, 113), "bg_keyword": "bg_estate", "items": econ_news, "footer": "당신의 소중한 자산, 든든하게 지켜드릴게요!", "script": make_short_script("부동산 경제 소식입니다.", econ_news)},
        {"category": "국내외 금융 뉴스", "accent": (243, 156, 18), "bg_keyword": "bg_finance", "items": finance_news, "footer": "현명한 금융 습관이 밝은 미래를 만듭니다!", "script": make_short_script("국내외 금융 소식입니다.", finance_news)},
        {"category": "주요 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "bg_social", "items": social_news, "footer": "세상을 밝히는 따뜻한 소식이 더 많아지길!", "script": make_short_script("오늘의 주요 사회 소식입니다.", social_news)},
        {"category": "알뜰 상식 뉴스", "accent": (231, 76, 60), "bg_keyword": "bg_tip", "items": tip_news, "footer": "작은 상식 하나가 모여 큰 지혜가 됩니다!", "script": make_short_script("놓치면 안 될 생활 상식입니다.", tip_news)}
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
            title_box_x1 = 360 - title_box_w // 2
            title_box_x2 = 360 + title_box_w // 2
            
            r, g, b = data["accent"]
            draw_ov.rectangle([0, 70, img_width, 80], fill=data["accent"]+(255,))
            draw_ov.rounded_rectangle([title_box_x1, 110, title_box_x2, 170], fill=(r//3, g//3, b//3, 255), radius=10)
            draw_ov.text((img_width//2, 140), data['category'], fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            
            start_y = 230
            parsed_items = []
            total_text_height = 0
            
            for item in data['items'][:8]:
                parts = item.split('|')
                title = parts[0]
                pub = parts[1] if len(parts) > 1 else ""
                
                wrapped = textwrap.wrap(title, 27)
                item_h = len(wrapped) * 34 
                if pub: item_h += 28       
                
                total_text_height += item_h
                parsed_items.append({"title": wrapped, "pub": pub})
                
            available_gap = (1120 - start_y) - total_text_height
            gap_per_item = max(10, min(available_gap / len(parsed_items), 45)) if parsed_items else 20
            
            calculated_bottom = start_y
            for item in parsed_items:
                calculated_bottom += len(item["title"]) * 34
                if item["pub"]: calculated_bottom += 28
                calculated_bottom += gap_per_item
            
            box_bottom = calculated_bottom - gap_per_item + 20
            
            draw_ov.rounded_rectangle([25, 200, 695, box_bottom], fill=(0, 0, 0, 200), outline=data["accent"]+(150,), width=2, radius=15)
            
            current_y = start_y
            for idx, item in enumerate(parsed_items, 1):
                num_str = f"{idx:02d}. "
                draw_ov.text((45, current_y), num_str, fill=data["accent"]+(255,), font=font_num, anchor="la")
                text_x = 45 + draw_ov.textlength(num_str, font=font_num)
                
                text_color = (255, 255, 255, 255) if idx % 2 != 0 else (180, 250, 180, 255)
                
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
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 140, 130), avatar)
                    
            draw_ov.text((img_width//2, 500), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 580), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_huge, anchor="mm")
            
            t1 = "010-2062-4600"
            t2 = "PMSUNGOO"
            t3 = "blog.naver.com/insureeasy"
            
            w1 = draw_ov.textlength(t1, font=font_num)
            w2 = draw_ov.textlength(t2, font=font_num)
            w3 = draw_ov.textlength(t3, font=font_pub)
            max_text_w = max(w1, w2, w3)
            
            out_box_w = 24 + 15 + max_text_w + 80
            out_box_x = (img_width - out_box_w) / 2
            
            draw_ov.rounded_rectangle([out_box_x, 680, out_box_x + out_box_w, 900], fill=(30, 35, 45, 255), outline=(100, 110, 130, 255), width=2, radius=15)
            
            info_start_y = 715
            ix = out_box_x + 35
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
        img_path = f"slide_{idx}.png"
        slide.save(img_path)
        
        audio_path = f"audio_{idx}.mp3"
        fast_audio_path = f"fast_audio_{idx}.wav"
        
        try:
            tts = gTTS(text=data["script"], lang="ko")
            tts.save(audio_path)
            
            final_audio_file = speedup_audio_ffmpeg(audio_path, fast_audio_path, speed=1.4)
            audio_clip = AudioFileClip(final_audio_file)
            
            # [핵심] 1분 20초의 기적을 만들었던 V30의 "영상 길이 + 1초" 로직 100% 완전 복구!!
            # 파이썬 억지 버벅임을 막아주는 유일하고 완벽한 마법의 1초입니다.
            actual_duration = audio_clip.duration + 1.0 
            
            img_clip = ImageClip(img_path).set_duration(actual_duration)
            video_clip = img_clip.set_audio(audio_clip)
        except Exception as e:
            print(f"오디오 치명적 예외: {e}")
            video_clip = ImageClip(img_path).set_duration(6.0)
            
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(filename, fps=10, preset="ultrafast", threads=4, codec="libx264", bitrate="1000k", audio_codec="aac", temp_audiofile="temp-audio.m4a", remove_temp=True, logger=None)
    print(f"최종 마스터 동영상 렌더링 완료: {filename}")
    return filename

def send_email_with_video(video_path, receiver_email):
    korea_timezone_offset = datetime.timedelta(hours=9)
    today_dt = datetime.datetime.utcnow() + korea_timezone_offset
    mail_date_str = today_dt.strftime('%Y년 %m월 %d일')
    
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {mail_date_str} 요약뉴스 (진·얼티밋 마스터 V34)"
    
    body = "형! 오디오가 가장 완벽했던 1분 20초(V30) 로직으로 토씨 하나 안 틀리고 원복했습니다! 발송 완료!"
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(video_path)}")
        msg.attach(part)
    except Exception as e:
        print(f"파일 첨부 중 에러 발생: {e}")
        return

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("이메일 발송 성공!")
    except Exception as e:
        print(f"이메일 발송 실패 원인: {e}")

if __name__ == "__main__":
    video_file = create_full_news_video_with_audio()
    send_email_with_video(video_file, "pmsung00@gmail.com")
# --- END OF CODE ---
