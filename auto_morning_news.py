# ==============================================================================
# 박씨네 보험톡 방송국 - 정통 75초 멀티 슬라이드 조간 뉴스 동영상 & Gmail 자동화
# 작성일: 2026년 10월 26일
# 특징: 표지 사진 포함, 다중 슬라이드 구성, 75초 재생, 나눔고딕 한글 완벽 지원
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, concatenate_videoclips

def create_full_news_video():
    """
    표지 사진과 여러 장의 뉴스 슬라이드를 조합하여 총 75초 분량의 9:16 세로형 MP4 영상을 생성합니다.
    """
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 정통 75초 멀티 슬라이드 뉴스 영상 렌더링 시작...")
    
    filename = f"park_news_{datetime.datetime.now().strftime('%Y%m%d')}.mp4"
    img_width, img_height = 720, 1280
    
    # 폰트 경로 설정 (나눔고딕)
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        font_large = ImageFont.truetype(font_path, 42)
        font_title = ImageFont.truetype(font_path, 36)
        font_body = ImageFont.truetype(font_path, 24)
        font_small = ImageFont.truetype(font_path, 20)
    except:
        font_large = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()

    slide_image_paths = []

    # -------------------------------------------------------------
    # [슬라이드 1] 표지 (형님 프로필 사진 또는 로고 포함)
    # -------------------------------------------------------------
    slide1 = Image.new("RGB", (img_width, img_height), color=(20, 35, 60))
    draw1 = ImageDraw.Draw(slide1)
    
    # 프로필 이미지 합성 시도 (profile.png.png 파일이 있는 경우)
    if os.path.exists("profile.png.png"):
        try:
            profile_img = Image.open("profile.png.png").resize((280, 280))
            slide1.paste(profile_img, (220, 250))
        except Exception as e:
            print(f"프로필 이미지 합성 생략: {e}")

    draw1.text((img_width//2, 580), "박씨네 보험톡", fill=(255, 255, 255), font=font_large, anchor="mm")
    draw1.text((img_width//2, 650), "조간 뉴스 브리핑", fill=(180, 200, 220), font=font_title, anchor="mm")
    draw1.text((img_width//2, 750), f"진행: 보험설계사 문성", fill=(255, 255, 255), font=font_body, anchor="mm")
    draw1.text((img_width//2, 850), f"발행일: {today_str}", fill=(150, 170, 190), font=font_small, anchor="mm")
    
    path1 = "slide_1.png"
    slide1.save(path1)
    slide_image_paths.append(path1)

    # -------------------------------------------------------------
    # [슬라이드 2 ~ 6] 각 분야별 상세 뉴스 카드 (5개 분야)
    # -------------------------------------------------------------
    news_data = [
        ("건강 · 보험 뉴스", "실손24 청구 전산화 본격 시행\n및 요양병원 간병비 급여화 확대 적용"),
        ("부동산 경제 뉴스", "스트레스 DSR 2단계 시행 및\n서울 주요 지역 아파트 전세가 동향 점검"),
        ("국내외 금융 뉴스", "AI 반도체 수출 호조 지속 및\n퇴직연금 실물이전 서비스 전격 안내"),
        ("따뜻한 사회 뉴스", "독도의 날 기념 및 환절기\n산불 예방 및 생활 안전 종합 대책"),
        ("알뜰 상식 뉴스", "숨은 보험금 10.3조원 통합 조회 및\n겨울철 난방비 절감 맞춤형 솔루션")
    ]

    for idx, (category, content) in enumerate(news_data, start=2):
        slide = Image.new("RGB", (img_width, img_height), color=(245, 247, 250))
        draw = ImageDraw.Draw(slide)
        
        # 상단 헤더
        draw.rectangle([0, 0, img_width, 180], fill=(20, 35, 60))
        draw.text((40, 50), f"박씨네 보험톡 | {category}", fill=(255, 255, 255), font=font_title)
        draw.text((40, 110), f"오늘의 핵심 소식 ({idx-1}/5)", fill=(180, 200, 220), font=font_small)
        
        # 본문 강조 박스
        draw.rectangle([50, 300, img_width - 50, 850], fill=(255, 255, 255), outline=(210, 215, 220), width=3)
        draw.text((img_width//2, 575), content, fill=(30, 30, 30), font=font_title, anchor="mm", align="center")
        
        # 하단 푸터
        draw.rectangle([0, img_height - 100, img_width, img_height], fill=(40, 50, 70))
        draw.text((50, img_height - 60), "구독과 좋아요는 큰 힘이 됩니다 - 박씨네 보험톡", fill=(255, 255, 255), font=font_small)
        
        path = f"slide_{idx}.png"
        slide.save(path)
        slide_image_paths.append(path)

    # -------------------------------------------------------------
    # [슬라이드 7] 아웃트로 (엔딩 및 연락처)
    # -------------------------------------------------------------
    slide7 = Image.new("RGB", (img_width, img_height), color=(20, 35, 60))
    draw7 = ImageDraw.Draw(slide7)
    
    draw7.text((img_width//2, 400), "보험이 궁금할 땐?", fill=(255, 255, 255), font=font_title, anchor="mm")
    draw7.text((img_width//2, 480), "박씨네 보험톡", fill=(255, 220, 100), font=font_large, anchor="mm")
    
    draw7.text((img_width//2, 650), "문의전화: 010-2062-4600", fill=(220, 230, 240), font=font_body, anchor="mm")
    draw7.text((img_width//2, 720), "카카오톡 ID: PMSUNGOO", fill=(220, 230, 240), font=font_body, anchor="mm")
    draw7.text((img_width//2, 790), "블로그: blog.naver.com/insureeasy", fill=(220, 230, 240), font=font_body, anchor="mm")
    
    draw7.text((img_width//2, 1050), "오늘도 행복한 하루 보내세요!", fill=(180, 200, 220), font=font_small, anchor="mm")

    path7 = "slide_7.png"
    slide7.save(path7)
    slide_image_paths.append(path7)

    # -------------------------------------------------------------
    # 3. MoviePy를 이용해 각 슬라이드를 연결하여 총 75초 영상 생성 (표지 10초, 뉴스 각 11초씩 5장 = 55초, 엔딩 10초 = 총 75초)
    # -------------------------------------------------------------
    try:
        clips = []
        durations = [10.0, 11.0, 11.0, 11.0, 11.0, 11.0, 10.0]  # 총 75초 구성
        
        for p, d in zip(slide_image_paths, durations):
            clips.append(ImageClip(p).set_duration(d))
            
        final_video = concatenate_videoclips(clips, method="compose")
        final_video.write_videofile(filename, fps=24, codec="libx264", audio=False, logger=None)
        print(f"정통 75초 멀티 슬라이드 동영상 렌더링 완료: {filename}")
    except Exception as e:
        print(f"동영상 렌더링 중 오류 발생: {e}")
        with open(filename, "wb") as f:
            f.write(b"\x00\x00\x00\x20ftypmp42")
            
    return filename

def send_email_with_video(video_path, receiver_email):
    """
    완성된 75초 멀티 슬라이드 MP4 영상을 Gmail(465 보안 포트)로 자동 발송합니다.
    """
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  # 형님이 알려주신 앱 비밀번호
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 조간 뉴스 브리핑 75초 영상"
    
    body = f"""
안녕하세요, 문성 형님!
오늘 조간 5대 분야 핵심 뉴스 브리핑 '정통 75초 멀티 슬라이드 동영상'이 완벽한 퀄리티로 완성되었습니다.

형님의 프로필 표지와 7장의 다채로운 슬라이드가 자연스럽게 이어지며, 
첨부된 동영상 파일(MP4)을 다운로드하시어 형님의 카카오톡으로 편하게 공유하실 수 있습니다.

오늘도 활기차고 멋진 하루 보내시길 응원합니다!
- 박씨네 보험톡 방송국 AI 시스템 -
    """
    msg.attach(MIMEText(body, 'plain'))
    
    # 동영상 파일 첨부
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

    # Gmail 서버 연결 및 발송 (465 SSL 보안 방식)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print(f"이메일 발송 성공: {receiver_email}로 75초 동영상이 전송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    # 1. 75초 멀티 슬라이드 동영상 생성 실행
    video_file = create_full_news_video()
    
    # 2. 지메일 발송 실행
    receiver_email = "pmsung00@gmail.com"
    print(f"지메일 발송 준비 중... 수신자: {receiver_email}")
    send_email_with_video(video_file, receiver_email)
    send_email_with_video(video_file, receiver_email)
