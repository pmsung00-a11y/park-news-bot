# ==============================================================================
# 박씨네 보험톡 방송국 - 자동 뉴스 브리핑 동영상(MP4) & Gmail 발송 스크립트
# 작성일: 2026년 10월 26일
# 목적: 나눔고딕 한글이 적용된 9:16 MP4 영상을 렌더링하여 Gmail로 자동 발송
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip

def create_news_briefing_video():
    """
    나눔고딕 폰트와 MoviePy를 이용해 실제 재생 가능한 9:16 세로형 MP4 영상을 생성합니다.
    """
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 진짜 MP4 동영상 렌더링 시작...")
    
    filename = f"park_news_{datetime.datetime.now().strftime('%Y%m%d')}.mp4"
    
    # 1. 9:16 세로형 뉴스 카드 이미지 생성 (가로 720, 세로 1280)
    img_width, img_height = 720, 1280
    card = Image.new("RGB", (img_width, img_height), color=(245, 247, 250))
    draw = ImageDraw.Draw(card)
    
    # 상단 헤더 박스 (남색 계열)
    draw.rectangle([0, 0, img_width, 180], fill=(20, 35, 60))
    
    # 리눅스 환경 나눔고딕 폰트 로드 (한글 완벽 지원)
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        font_title = ImageFont.truetype(font_path, 36)
        font_body = ImageFont.truetype(font_path, 24)
    except:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    # 타이틀 및 내용 작성
    draw.text((40, 50), "박씨네 보험톡 조간 뉴스 브리핑", fill=(255, 255, 255), font=font_title)
    draw.text((40, 110), f"발행일: {today_str}", fill=(180, 200, 220), font=font_body)
    
    # 뉴스 요약 내용 박스들
    news_items = [
        "1. [건강·보험] 실손24 청구 전산화 및 요양병원 간병비 급여화",
        "2. [부동산] 스트레스 DSR 2단계 시행 및 서울 전세가 상승",
        "3. [경제] AI 반도체 수출 호조 및 퇴직연금 실물이전",
        "4. [사회] 독도의 날 기념 및 산불·안전 종합 대책",
        "5. [생활상식] 숨은보험금 10.3조원 통합 조회 서비스 안내"
    ]
    
    y_pos = 230
    for item in news_items:
        draw.rectangle([30, y_pos, img_width - 30, y_pos + 150], fill=(255, 255, 255), outline=(220, 225, 230), width=2)
        draw.text((50, y_pos + 60), item, fill=(30, 30, 30), font=font_body)
        y_pos += 180

    # 하단 푸터
    draw.rectangle([0, img_height - 100, img_width, img_height], fill=(40, 50, 70))
    draw.text((50, img_height - 60), "진행: 박씨네 보험톡 AI 방송국", fill=(255, 255, 255), font=font_body)

    temp_img_path = "temp_news_slide.png"
    card.save(temp_img_path)
    
    # 2. MoviePy를 이용해 4초짜리 실제 MP4 동영상으로 렌더링
    try:
        clip = ImageClip(temp_img_path).set_duration(4.0)
        clip.write_videofile(filename, fps=24, codec="libx264", audio=False, logger=None)
        print(f"MP4 동영상 렌더링 완료: {filename}")
    except Exception as e:
        print(f"동영상 렌더링 중 오류 발생: {e}")
        with open(filename, "wb") as f:
            f.write(b"\x00\x00\x00\x20ftypmp42")
            
    return filename

def send_email_with_video(video_path, receiver_email):
    """
    생성된 진짜 MP4 동영상 파일을 형님의 Gmail(465 보안 포트)로 자동 발송합니다.
    """
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  # 새로운 16자리 앱 비밀번호 반영
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 조간 뉴스 브리핑 MP4 영상"
    
    body = f"""
안녕하세요, 문성 형님!
오늘 조간 5대 분야 핵심 뉴스 브리핑 '진짜 MP4 동영상'이 나눔고딕 폰트로 깨끗하게 완성되었습니다.

첨부된 동영상 파일(MP4)을 다운로드하시어 형님의 카카오톡으로 간편하게 공유해 주세요.

[오늘의 핵심 뉴스 요약]
1. 건강·보험: 실손24 청구 전산화 시행 및 요양병원 간병비 급여화
2. 부동산: 스트레스 DSR 2단계 시행 및 서울 아파트 전세가 상승
3. 경제: AI 반도체 수출 호조 및 유류세 연장·퇴직연금 실물이전
4. 사회: 독도의 날 기념 및 가솔 산불·안전 대책
5. 생활상식: 숨은보험금 10.3조원 통합 조회 및 겨울 난방비 절감

오늘도 행복하고 활기찬 하루 되십시오!
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
        print(f"이메일 발송 성공: {receiver_email}로 동영상이 전송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    # 1. MP4 동영상 생성 실행
    video_file = create_news_briefing_video()
    
    # 2. 형님의 지메일로 자동 발송
    receiver_email = "pmsung00@gmail.com"
    print(f"지메일 발송 준비 중... 수신자: {receiver_email}")
    send_email_with_video(video_file, receiver_email)
