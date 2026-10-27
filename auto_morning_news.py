# ==============================================================================
# 해외 도서 AI 큐레이터 - 기본 뼈대 (영상제작 + 유튜브 자동 업로드 세팅 완료)
# ==============================================================================

import os
import datetime
import smtplib
import urllib.parse
import xml.etree.ElementTree as ET
import re
import subprocess
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

# 유튜브 업로드용 라이브러리
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

WORK_DIR = "work"
os.makedirs(WORK_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- (이하 영상 제작부: 추후 해외 도서 크롤링 로직으로 교체할 기본 뼈대) ---

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
    except Exception as e:
        print(f"오디오 가속 실패: {e}")
        fb = [
            'ffmpeg', '-y', '-i', input_path,
            '-af', 'apad=pad_dur=1.0', '-ar', '44100', '-ac', '1', output_path
        ]
        _run_ffmpeg(fb)
        return output_path

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
