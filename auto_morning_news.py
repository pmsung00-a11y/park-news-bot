# ==============================================================================
# 박씨네 보험톡 방송국 - 일일 요약뉴스 마스터 버전 (배경 이미지 합성 & 완벽 싱크)
# 작성일: 2026년 10월 26일
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

def create_full_news_video_with_audio():
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 박씨네 보험톡 일일 요약뉴스 마스터 렌더링 시작...")
    
    filename = f"park_news_{datetime.datetime.now().strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    # 폰트 설정 (나눔고딕)
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        font_large = ImageFont.truetype(font_path, 42)
        font_title = ImageFont.truetype(font_path, 34)
        font_body = ImageFont.truetype(font_path, 21)
        font_small = ImageFont.truetype(font_path, 18)
    except:
        font_large = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    clips = []
    
    # 25가지 상세 뉴스 항목과 오디오 낭독용 대본
    news_database = [
        {
            "category": "건강 · 보험 뉴스",
            "accent": (41, 128, 185), # Blue
            "bg_img": "insurance.png", # 올려주신 보험 이미지 연동
            "items": [
                "• 실손24 보험금 청구 전산화 본격 시행",
                "• 요양병원 간병비 건강보험 급여화 확대",
                "• 비급여 1인실 및 도수치료 심사 강화",
                "• 3대 비급여 특약 보장 범위 조정",
                "• 고령층 전용 간편고지 보험 가입 완화"
            ],
            "script": "첫 번째 건강 보험 소식입니다. 실손24 청구 전산화 시행, 요양병원 간병비 급여화, 비급여 치료 심사 강화, 특약 보장 조정, 고령층 간편 가입 완화 소식입니다."
        },
        {
            "category": "부동산 경제 뉴스",
            "accent": (39, 174, 96), # Green
            "bg_img": "domestic_econ.png", # 올려주신 경제 이미지 연동
            "items": [
                "• 스트레스 DSR 2단계 본격 적용",
                "• 서울 주요 지역 아파트 전세가 상승세",
                "• 주택담보대출 한도 규제 및 금리 동향",
                "• 신생아 특례 대출 요건 완화 검토",
                "• 오피스텔 및 빌라 시장 회복세 점검"
            ],
            "script": "두 번째 부동산 경제 소식입니다. 스트레스 DSR 2단계 적용, 서울 전세가 상승세, 주택담보대출 한도 규제, 신생아 특례 대출 완화, 빌라 시장 회복세 점검 소식입니다."
        },
        {
            "category": "국내외 금융 뉴스",
            "accent": (211, 84, 0), # Orange
            "bg_img": "domestic_econ.png", # 경제 이미지 공용 활용
            "items": [
                "• 인공지능 반도체 수출 호조세 지속",
                "• 퇴직연금 실물이전 서비스 전격 시행",
                "• 기준금리 인하 기대 속 증시 변동성",
                "• 원달러 환율 안정세 및 외국인 수급",
                "• 가상자산 과세 유예 논의 재점화"
            ],
            "script": "세 번째 금융 소식입니다. AI 반도체 수출 호조, 퇴직연금 실물이전 시행, 기준금리 인하 기대, 원달러 환율 안정, 가상자산 과세 유예 논의 소식입니다."
        },
        {
            "category": "따뜻한 사회 뉴스",
            "accent": (142, 68, 173), # Purple
            "bg_img": "social.png", # 올려주신 사회 이미지 연동
            "items": [
                "• 독도의 날 맞이 전국 기념 행사 개최",
                "• 환절기 대형 산불 예방 특별 경계령",
                "• 겨울철 대비 생활 안전 종합 대책",
                "• 취약계층 김장 나눔 행사 본격 시작",
                "• 대중교통 이용 요금 할인 혜택 안내"
            ],
            "script": "네 번째 사회 소식입니다. 독도의 날 기념 행사, 환절기 산불 예방 특별 경계, 겨울철 생활 안전 대책, 취약계층 김장 나눔, 대중교통 요금 할인 안내입니다."
        },
        {
            "category": "알뜰 상식 뉴스",
            "accent": (192, 57, 43), # Coral
            "bg_img": "none",
            "items": [
                "• 숨은 보험금 10.3조원 통합 조회 서비스",
                "• 겨울철 주거 난방비 절감 맞춤 솔루션",
                "• 연말정산 대비 절세 가이드 및 팁",
                "• 에너지 바우처 신청 접수 시작",
                "• 자동차 보험료 비교 견적 활용법"
            ],
            "script": "마지막 상식 소식입니다. 숨은 보험금 10조 원 통합 조회, 난방비 절감 맞춤 솔루션, 연말정산 절세 가이드, 에너지 바우처 신청, 자동차 보험료 비교 팁입니다."
        }
    ]

    slides_data = []
    
    slides_data.append({
        "type": "cover",
        "script": f"안녕하십니까, 박씨네 보험톡 일일 요약뉴스입니다. 오늘 발행일은 {today_str}입니다.",
        "duration": 6.0
    })
    
    for i, cat in enumerate(news_database, start=1):
        slides_data.append({
            "type": "news",
            "category": cat["category"],
            "accent": cat["accent"],
            "bg_img": cat["bg_img"],
            "subtitle": f"오늘의 핵심 소식 ({i}/5)",
            "items": cat["items"],
            "script": cat["script"],
            "duration": 12.0 # 기본값, 오디오가 길면 자동으로 연장됨
        })
        
    slides_data.append({
        "type": "outro",
        "script": "보험이 궁금할 땐 언제든지 박씨네 보험톡을 찾아주세요. 오늘도 행복한 하루 보내시길 바랍니다.",
        "duration": 7.0
    })

    for idx, data in enumerate(slides_data, start=1):
        # 1. 배경 화면 처리
        slide = Image.new("RGB", (img_width, img_height), color=(250, 248, 242)) # 기본 신문지 컬러
        
        # 외부 배경 이미지가 지정되어 있고, 깃허브 폴더에 실제 파일이 존재할 경우 배경으로 꽉 차게 렌더링
        if data.get("bg_img") and os.path.exists(data["bg_img"]):
            try:
                bg_image = Image.open(data["bg_img"]).resize((img_width, img_height))
                slide.paste(bg_image, (0, 0))
            except Exception as e:
                print(f"배경 이미지 적용 실패: {e}")

        # RGBA(투명도 지원) 드로우 객체 생성
        overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw = ImageDraw.Draw(slide)
        
        if data["type"] == "cover":
            draw.rectangle([0, 0, img_width, img_height], fill=(20, 35, 60))
            if os.path.exists("profile.png.png"):
                try:
                    profile_img = Image.open("profile.png.png").resize((280, 280))
                    slide.paste(profile_img, (220, 240))
                except Exception as e:
                    pass
            draw.text((img_width//2, 570), "박씨네 보험톡", fill=(255, 255, 255), font=font_large, anchor="mm")
            draw.text((img_width//2, 640), "일일 요약뉴스", fill=(180, 200, 220), font=font_title, anchor="mm")
            draw.text((img_width//2, 740), "박씨네 보험톡 제공", fill=(255, 220, 100), font=font_body, anchor="mm")
            draw.text((img_width//2, 830), f"발행일: {today_str}", fill=(150, 170, 190), font=font_small, anchor="mm")
            
        elif data["type"] == "news":
            # 상단 헤더
            draw_ov.rectangle([0, 0, img_width, 180], fill=(20, 35, 60, 255))
            draw_ov.rectangle([0, 170, img_width, 185], fill=data["accent"] + (255,))
            
            draw_ov.text((40, 45), f"박씨네 보험톡 | {data['category']}", fill=(255, 255, 255, 255), font=font_title)
            draw_ov.text((40, 105), data['subtitle'], fill=(180, 200, 220, 255), font=font_small)
            
            # 본문 카드 박스 (배경이 살짝 비치는 고급스러운 90% 불투명도 흰색 박스)
            card_color = (255, 255, 255, 235)
            draw_ov.rectangle([30, 210, img_width - 30, 1100], fill=card_color, outline=data["accent"] + (255,), width=4)
            draw_ov.line([(30, 280), (img_width-30, 280)], fill=data["accent"] + (255,), width=2)
            draw_ov.text((img_width//2, 245), "■ 주요 뉴스 요약 ■", fill=data["accent"] + (255,), font=font_body, anchor="mm")

            items = data['items']
            y_start = 340
            for i, item in enumerate(items):
                draw_ov.text((55, y_start + (i * 140)), item, fill=(30, 30, 30, 255), font=font_body, anchor="lm")
            
            # 하단 푸터
            draw_ov.rectangle([0, img_height - 80, img_width, img_height], fill=(40, 50, 70, 255))
            draw_ov.text((50, img_height - 40), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(255, 255, 255, 255), font=font_small, anchor="lm")
            
            # 반투명 레이어를 원본 슬라이드에 합성
            slide.paste(overlay, (0, 0), overlay)

        elif data["type"] == "outro":
            draw.rectangle([0, 0, img_width, img_height], fill=(20, 35, 60))
            draw.text((img_width//2, 380), "보험이 궁금할 땐?", fill=(255, 255, 255), font=font_title, anchor="mm")
            draw.text((img_width//2, 460), "박씨네 보험톡", fill=(255, 220, 100), font=font_large, anchor="mm")
            
            draw.rectangle([100, 560, img_width - 100, 840], outline=(70, 90, 120), width=2)
            draw.text((img_width//2, 630), "문의전화: 010-2062-4600", fill=(220, 230, 240), font=font_body, anchor="mm")
            draw.text((img_width//2, 700), "카카오톡 ID: PMSUNGOO", fill=(220, 230, 240), font=font_body, anchor="mm")
            draw.text((img_width//2, 770), "블로그: blog.naver.com/insureeasy", fill=(220, 230, 240), font=font_body, anchor="mm")
            
            draw.text((img_width//2, 1020), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 220), font=font_small, anchor="mm")

        img_path = f"slide_{idx}.png"
        slide.save(img_path)
        
        # [핵심] 오디오 생성 및 잘림 방지 완벽 싱크 처리
        audio_path = f"audio_{idx}.mp3"
        video_clip = None
        try:
            # 낭독 속도 최적화 (slow=False)
            tts = gTTS(text=data["script"], lang="ko", slow=False)
            tts.save(audio_path)
            audio_clip = AudioFileClip(audio_path)
            
            # 오디오 길이가 영상에 배정된 시간보다 길면, 오디오 길이에 맞춰 무조건 영상 시간을 넉넉하게 연장
            actual_duration = max(data["duration"], audio_clip.duration + 0.5)
            img_clip = ImageClip(img_path).set_duration(actual_duration)
            video_clip = img_clip.set_audio(audio_clip)
        except Exception as e:
            print(f"슬라이드 {idx} 오디오 생성 예외: {e}")
            video_clip = ImageClip(img_path).set_duration(data["duration"])
            
        clips.append(video_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(filename, fps=24, codec="libx264", audio_codec="aac", logger=None)
    print(f"일일 요약뉴스 마스터 동영상 렌더링 완료: {filename}")
    return filename

def send_email_with_video(video_path, receiver_email):
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 일일 요약뉴스 마스터본 발행"
    
    body = f"""
안녕하세요, 문성 형님!
완벽한 오디오 싱크, 배경 이미지 합성 기술이 적용된 '박씨네 보험톡 일일 요약뉴스 마스터본'입니다.

[적용 및 개선 완료 사항]
1. 완벽한 5대 뉴스 낭독: 오디오가 잘리지 않도록 길이를 자동 계산하여 영상 싱크를 100% 맞췄습니다.
2. 배경 포스터 합성: 올려주신 포스터 이미지(경제, 보험, 사회)가 배경으로 깔리고, 글씨가 뚜렷하게 보이도록 반투명 화이트 카드가 얹혀집니다.
3. 완벽한 표지/클로징: 남색의 고급스러운 포맷에 '박씨네 보험톡 제공' 문구가 반영되었습니다.

편안한 밤 되시고, 푹 주무십시오 형님!
- 박씨네 보험톡 방송국 AI 시스템 -
    """
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with open(video_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(video_path)}")
        msg.attach(part)
    except Exception as e:
        print(f"파일 첨부 중 오류 발생: {e}")
        return

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print(f"이메일 발송 성공: {receiver_email}로 마스터 동영상이 전송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    video_file = create_full_news_video_with_audio()
    receiver_email = "pmsung00@gmail.com"
    send_email_with_video(video_file, receiver_email)
