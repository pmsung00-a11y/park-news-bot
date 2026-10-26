# ==============================================================================
# 박씨네 보험톡 방송국 - 그랜드 마스터 에디션 (V4)
# (FFmpeg 2배속, 8개 꽉찬 정렬, 우측 출처 정렬, 수제작 아이콘 아웃트로)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import json
import subprocess
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# ------------------------------------------------------------------------------
# 1. FFmpeg 2.0배속 오디오 강제 변환기 (음소거 오류 원천 차단)
# ------------------------------------------------------------------------------
def speedup_audio(input_file, output_file, speed=2.0):
    cmd = ['ffmpeg', '-y', '-i', input_file, '-filter:a', f'atempo={speed}', output_file]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return output_file
    except Exception as e:
        print(f"FFmpeg 2배속 변환 오류 (원본 사용): {e}")
        return input_file

# ------------------------------------------------------------------------------
# 2. 뉴스 크롤러 (본문과 [언론사] 완벽 분리)
# ------------------------------------------------------------------------------
def fetch_one_top_news(keyword):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item'):
            title = item.find('title').text
            
            publisher = ""
            news_title = title
            
            # 언론사명이 뒤에 있는
