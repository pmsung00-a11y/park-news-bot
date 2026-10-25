# ==============================================================================
# 박씨네 보험톡 방송국 - 완벽 버전 (글자 줄바꿈 + 5대 뉴스 100% 풀낭독)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import textwrap # 긴 글자를 잘라주는 마법의 도구

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# ------------------------------------------------------------------------------
# 1. 뉴스 크롤러 (글자 자르지 않고 원본 그대로 다 가져오기)
# ------------------------------------------------------------------------------
def fetch_latest_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    headlines = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            # 뒤에 붙는 ' - 언론사명'만 딱 떼고 글자 길이는 자르지 않음!
            clean_title = title.rsplit(' - ', 1)[0]
            headlines.append(clean_title)
    except Exception as e:
        print(f"뉴스 수집 에러 ({keyword}): {e}")
        
    while len(headlines) < 5:
        headlines.append("관련 뉴스를 수집 중입니다.")
    return headlines

# ------------------------------------------------------------------------------
# 2. 업로드 이미지 찾기 
# ------------------------------------------------------------------------------
def find_image(keyword):
    for file in os.listdir('.'):
        if keyword.lower() in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')):
            return file
    for fallback in ['domestic_econ', 'insurance', 'social']:
        for file in os.listdir('.'):
            if fallback in file.lower() and file.endswith(('.png', '.jpg', '.jpeg')):
                return file
    return None

# ------------------------------------------------------------------------------
# 3. 원형 프로필 만들기
# ------------------------------------------------------------------------------
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
# 4. 메인 렌더링 엔진
# ------------------------------------------------------------------------------
def create_full_news_video_with_audio():
    today_dt = datetime.datetime.now()
    today_str = today_dt.strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 5대 뉴스 100% 풀낭독 렌더링 시작...")
    
    filename = f"park_news_{today_dt.strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 52)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 40)
        # 긴 제목을 두 줄로 쓸 수 있게 폰트 크기 살짝 조정
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 22) 
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", 20)
    except:
        font_large = font_title = font_body = font_small = ImageFont.load_default()

    health_news = fetch_latest_news("건강보험 OR 실손보험 OR 요양병원")
    econ_news = fetch_latest_news("부동산 OR 아파트 OR 주택담보대출")
    finance_news = fetch_latest_news("증시 OR 금리 인하 OR 환율")
    social_news = fetch_latest_news("날씨 OR 안전 대책 OR 사회 공헌")
    tip_news = fetch_latest_news("연말정산 OR 절세 OR 정부 지원금")

    # [핵심] 5개 뉴스를 빠짐없이 전부 읽어주는 대본(Script) 자동 생성 로직!
    def make_script(intro, news_list):
        script = intro + " "
        for i, news in enumerate(news_list, 1):
            script += f" {news}."
        return script

    news_database = [
        {
            "category": "건강 · 보험 뉴스", "accent": (52, 152, 219), "bg_keyword": "insurance",
            "items": health_news,
            "script": make_script("첫 번째 건강 보험 소식입니다.", health_news)
        },
        {
            "category": "부동산 경제 뉴스", "accent": (46, 204, 113), "bg_keyword": "domestic_econ",
            "items": econ_news,
            "script": make_script("두 번째 경제 소식입니다.", econ_news)
        },
        {
            "category": "국내외 금융 뉴스", "accent": (243, 156, 18), "bg_keyword": "finance",
            "items": finance_news,
            "script": make_script("세 번째 금융 소식입니다.", finance_news)
        },
        {
            "category": "따뜻한 사회 뉴스", "accent": (155, 89, 182), "bg_keyword": "social",
            "items": social_news,
            "script": make_script("네 번째 사회 소식입니다.", social_news)
        },
        {
            "category": "알뜰 상식 뉴스", "accent": (231, 76, 60), "bg_keyword": "tip",
            "items": tip_news,
            "script": make_script("마지막 상식 소식입니다.", tip_news)
        }
    ]

    slides_data = [{"type": "cover", "script": f"안녕하십니까, 박씨네 보험톡 일일 요약뉴스입니다. 오늘 발행일은 {today_str}입니다."}]
    
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({
            "type": "news", "category": cat["category"], "accent": cat["accent"],
            "bg_keyword": cat["bg_keyword"], "subtitle": f"오늘의 핵심 뉴스 ({i}/5)",
            "items": cat["items"], "script": cat["script"]
        })
        
    slides_data.append({"type": "outro", "script": "보험이 궁금할 땐 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 행복한 하루 보내시길 바랍니다."})

    clips = []
    
    for idx, data in enumerate(slides_data, start=1):
        slide = Image.new("RGB", (img_width, img_height), color=(15, 20, 30))
        
        bg_file = find_image(data.get("bg_keyword", "domestic_econ"))
        if bg_file:
            try:
                bg_img = Image.open(bg_file)
                bg_img = ImageOps.fit(bg_img, (img_width, img_height), Image.Resampling.LANCZOS)
                slide.paste(bg_img, (0, 0))
            except: pass
            
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)

        if data["type"] == "cover":
            draw_ov.rectangle([0, 0, img_width, img_height], fill=(15, 20, 30, 200))
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (340, 340))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 170, 300), avatar)
            
            draw_ov.text((img_width//2, 720), "박씨네 보험톡", fill=(255, 255, 255, 255), font=font_large, anchor="mm")
            draw_ov.text((img_width//2, 800), "일일 요약뉴스", fill=(180, 200, 230, 255), font=font_title, anchor="mm")
            draw_ov.text((img_width//2, 920), "박씨네 보험톡 제공", fill=(255, 215, 0, 255), font=font_body, anchor="mm")
            draw_ov.text((img_width//2, 980), f"발행일: {today_str}", fill=(130, 150, 180, 255), font=font_small, anchor="mm")
            
        elif data["type"] == "news":
            draw_ov.rectangle([0, 100, img_width, 110], fill=data["accent"]+(255,))
            draw_ov.rectangle([20, 120, img_width - 20, 1120], fill=(0, 0, 0, 230), outline=data["accent"]+(255,), width=3)
            
            draw_ov.text((50, 160), f"■ {data['category']}", fill=data["accent"]+(255,), font=font_large)
            draw_ov.text((50, 230), data['subtitle'], fill=(180, 200, 220, 255), font=font_body)
            
            y_start = 320 # 텍스트 시작 위치를 좀 더 위로 올림
            for i, item in enumerate(data['items']):
                # [핵심] 긴 문장을 30글자 단위로 예쁘게 두 줄로 접어줌
                wrapped_text = textwrap.fill(item, width=32) 
                draw_ov.text((50, y_start), f"• {wrapped_text}", fill=(255, 255, 255, 255), font=font_body, anchor="la")
                # 두 줄이 될 수 있으므로 줄 사이 간격을 넉넉히 띄움
                y_start += 150 
            
            draw_ov.line([(40, 1150), (img_width-40, 1150)], fill=(80, 90, 110, 255), width=1)
            draw_ov.text((img_width//2, 1200), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(200, 210, 220, 255), font=font_small, anchor="mm")
            
        elif data["type"] == "outro":
            draw_ov.rectangle([0, 0, img_width, img_height], fill=(15, 20, 30, 200))
            profile_file = find_image("profile")
            if profile_file:
                avatar = get_circular_avatar(profile_file, (240, 240))
                if avatar:
                    overlay.paste(avatar, (img_width//2 - 120, 180), avatar)
                    
            draw_ov.text((img_width//2, 480), "보험이 궁금할 땐?", fill=(255, 255, 255, 255), font=font_title, anchor="mm")
            draw_ov.text((img_width//2, 560), "박씨네 보험톡", fill=(255, 215, 0, 255), font=font_large, anchor="mm")
            
            draw_ov.rectangle([80, 680, img_width - 80, 960], fill=(0, 0, 0, 220), outline=(100, 120, 150, 255), width=2)
            draw_ov.text((img_width//2, 750), "📞 문의전화: 010-2062-4600", fill=(255, 255, 255, 255), font=font_body, anchor="mm")
            draw_ov.text((img_width//2, 820), "💬 카카오톡 ID: PMSUNGOO", fill=(255, 255, 255, 255), font=font_body, anchor="mm")
            draw_ov.text((img_width//2, 890), "🌐 블로그: blog.naver.com/insureeasy", fill=(255, 255, 255, 255), font=font_body, anchor="mm")
            
            draw_ov.text((img_width//2, 1100), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 230, 255), font=font_body, anchor="mm")

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
        except Exception as e:
            print(f"슬라이드 {idx} 오디오 예외: {e}")
            video_clip = ImageClip(img_path).set_duration(10.0)
            
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
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 요약뉴스 퍼펙트 마스터본"
    
    body = f"""
형! 아침 방송 준비 완벽하게 끝냈어!

1. 뉴스 전체 낭독: 이제 5개 기사 처음부터 끝까지 형 목소리로 빠짐없이 싹 다 읽어줘!
2. 글자 안 잘림: 기사 제목이 아무리 길어도 절대 안 자르고 두 줄로 예쁘게 접어서 끝까지 다 보여줘!
3. 오디오 잘림 방지: 문장 다 끝나고 2.5초 여유 둬서 끝맺음 멘트까지 짱짱하게 잘 나와!

이제 깃허브 한 번만 돌리고 시원하게 카톡에 공유하자고 형!!
    """
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
