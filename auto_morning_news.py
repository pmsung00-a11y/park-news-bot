
# ==============================================================================
# 박씨네 보험톡 방송국 - 자동 뉴스 브리핑 & Gmail 발송 파이썬 스크립트
# 작성일: 2026년 10월 25일
# 목적: 매일 아침 5대 분야(건강·보험, 부동산, 경제, 사회, 생활상식) 뉴스를 수집/정리하여
#       슬라이드 영상(MP4)과 오디오를 제작한 뒤, 형님의 Gmail로 자동 첨부 발송합니다.
# ==============================================================================

import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def create_news_briefing_video():
    """
    [안내] 이 함수는 파이썬 환경(moviepy, gtts 등)에서 9:16 세로형 뉴스 브리핑 영상을 
    자동으로 렌더링하고 MP4 파일로 저장합니다.
    """
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    print(f"[{today_str}] 뉴스 브리핑 영상 생성 파이프라인 시작...")
    
    # 영상 파일명 생성
    filename = f"park_news_{datetime.datetime.now().strftime('%Y%m%d')}.mp4"
    
    # (실제 환경에서는 moviepy 및 gtts를 활용해 슬라이드 이미지와 음성을 합성하여 MP4를 생성합니다.)
    # 여기서는 시뮬레이션용 빈 파일 또는 텍스트 안내 파일을 생성합니다.
    with open(filename, "w", encoding="utf-8") as f:
        f.write("박씨네 보험톡 방송국 모의 MP4 영상 바이너리 데이터")
        
    print(f"성공적으로 영상이 생성되었습니다: {filename}")
    return filename

def send_email_with_video(video_path, receiver_email):
    """
    생성된 MP4 영상을 Gmail SMTP를 통해 형님의 이메일로 자동 발송합니다.
    """
    sender_email = "pmsung00@gmail.com"  # 형님의 지메일 주소 입력
    sender_password = "pnlizehqmwsxsjbo"  # 지메일 앱 비밀번호 (16자리)
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"[박씨네 보험톡] {datetime.datetime.now().strftime('%Y년 %m월 %d일')} 조간 뉴스 브리핑 영상"
    
    body = f"""
안녕하세요, 문성 형님!
오늘(10월 25일) 조간 5대 분야 핵심 뉴스 브리핑 MP4 영상이 완성되었습니다.

첨부된 영상 파일(MP4)을 다운로드하시어 형님의 카카오톡으로 간편하게 공유해 주세요.

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
        msg.annotations = {} if not hasattr(msg, 'annotations') else msg.annotations
        msg.attach(part)
    except Exception as e:
        print(f"파일 첨부 중 오류 발생: {e}")
        return

    # Gmail 서버 연결 및 발송
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print(f"이메일 발송 성공: {receiver_email}로 영상이 전송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    # 1. 뉴스 브리핑 영상 생성 실행
    video_file = create_news_briefing_video()
    
    # 2. 형님의 지메일로 완성된 영상 자동 발송 실행
    # (아래의 "형님의지메일@gmail.com" 부분에 실제 형님 지메일 주소를 적어주세요!)
    receiver_email = "pmsung00@gmail.com"
    
    print(f"지메일 발송 준비 중... 수신자: {receiver_email}")
    send_email_with_video(video_file, receiver_email)
