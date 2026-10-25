# ==============================================================================
# 박씨네 보험톡 방송국 - 자동 뉴스 브리핑 & Gmail 발송 파이썬 스크립트
# 작성일: 2026년 10월 26일
# 목적: 5대 주요 분야 뉴스 카드 이미지를 생성하여 Gmail로 자동 발송
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont

def create_news_briefing_image():
    """
    Pillow를 이용해 깔끔하고 선명한 9:16 세로형 뉴스 브리핑 카드 이미지를 생성합니다.
    """
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 뉴스 브리핑 카드 이미지 생성 시작...")
    
    filename = f"park_news_{datetime.datetime.now().strftime('%Y%m%d')}.png"
    
    # 1. 9:16 세로형 뉴스 카드 이미지 생성 (가로 720, 세로 1280)
    img_width, img_height = 720, 1280
    card = Image.new("RGB", (img_width, img_height), color=(245, 247, 250))
    draw = ImageDraw.Draw(card)
    
    # 상단 헤더 박스 (남색 계열)
    draw.rectangle([0, 0, img_width, 180], fill=(20, 35, 60))
    
    # 시스템 기본 폰트 사용 (오류 원천 차단)
    font = ImageFont.load_default()

    # 타이틀 및 내용 작성
    draw.text((40, 50), "박씨네 보험톡 조간 뉴스 브리핑", fill=(255, 255, 255), font=font)
    draw.text((40, 110), f"발행일: {today_str}", fill=(180, 200, 220), font=font)
    
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
        draw.text((50, y_pos + 60), item, fill=(30, 30, 30), font=font)
        y_pos += 180

    # 하단 푸터
    draw.rectangle([0, img_height - 100, img_width, img_height], fill=(40, 50, 70))
    draw.text((50, img_height - 60), "진행: 박씨네 보험톡 AI 방송국", fill=(255, 255, 255), font=font)

    # 이미지 저장
    card.save(filename)
    print(f"뉴스 카드 이미지 생성 완료: {filename}")
    return filename

def send_email_with_news(image_path, receiver_email):
    """
    생성된 뉴스 카드 이미지를 형님의 Gmail(465 보안 포트)로 자동 발송합니다.
    """
    sender_email = "pmsung00@gmail.com"  
    sender_password = "efumyhjmxxugdfaw"  # 형님이 새로 알려주신 16자리 앱 비밀번호 반영
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 조간 뉴스 브리핑 카드"
    
    body = f"""
안녕하세요, 문성 형님!
오늘 조간 5대 분야 핵심 뉴스 브리핑 카드 뉴스가 완성되었습니다.

첨부된 이미지 파일(PNG)을 다운로드하시어 형님의 카카오톡이나 방송 채널에 간편하게 공유해 주세요.

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
    
    # 이미지 파일 첨부
    try:
        with open(image_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(image_path)}")
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
        print(f"이메일 발송 성공: {receiver_email}로 뉴스가 전송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    # 1. 뉴스 카드 이미지 생성 실행
    news_image = create_news_briefing_image()
    
    # 2. 형님의 지메일로 자동 발송
    receiver_email = "pmsung00@gmail.com"
    print(f"지메일 발송 준비 중... 수신자: {receiver_email}")
    send_email_with_news(news_image, receiver_email)
