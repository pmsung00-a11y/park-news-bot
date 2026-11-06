import os
import requests
import textwrap
from PIL import Image, ImageOps
import numpy as np
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip
from moviepy.video.fx.all import crop, fadein, crossfadein

# --- 작업 폴더 설정 ---
WORK_DIR = "radio_work"
ASSET_DIR = "radio_images"
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(ASSET_DIR, exist_ok=True)

# --- 1. 인물별 보이스 ID 매핑 ---
VOICE_MAPPING = {
    "소영": "lxYfHSkYm1EzQzGhdbfc",  
    "중현": "86GErZIiGJsPO3g7QNxZ", 
    "순이": "4p0HBzAAGyju0nYfNntV", 
    "문수": "s07IwTCOrCDCaETjUVjx", 
    "봉규": "wAGzRVkxKEs8La0lmdrE", 
    "수호": "ZJCNdZEjYwkOElxugmW2"
}

# --- 대본 및 씬(배경 이미지) 매칭 데이터 (총 78컷 중 일부 예시, 실제로는 전체 다 넣어주세요) ---
radio_scenes = [
    {"no": 1, "speaker": "소영", "img": "img_thumb.png", "script": "기막힌 보험사연 라디오. 300만원 합의의 치명적인 함정, 지금 시작합니다."},
    {"no": 2, "speaker": "중현", "img": "img_scene_1.png", "script": "여보, 방금 보험사에서 전화 왔어. 합의금 제안이 왔는데 300만원이래."},
    {"no": 3, "speaker": "순이", "img": "img_scene_1.png", "script": "300만원? 그게 적당한 거예요?"},
    {"no": 4, "speaker": "중현", "img": "img_scene_1.png", "script": "보상 담당자 말이 전치 2주 타박상은 이 정도가 기준이라고. 빨리 합의하면 처리가 더 깔끔하다고 하던데."},
    {"no": 5, "speaker": "순이", "img": "img_scene_1.png", "script": "보험사 말을 그냥 믿어도 되는거예요? 보험사에서 나온 금액이면 적절하게 계산한 거 맞겠지요?"},
    {"no": 6, "speaker": "중현", "img": "img_scene_1.png", "script": "그렇겠지 뭐. 여보, 우리 그냥 합의하자."},
    {"no": 7, "speaker": "소영", "img": "img_scene_1.png", "script": "그 전화 한 통이 결국 수술비 3,000만원을 고스란히 본인 부담으로 만들었습니다. 이미경 씨가 사고를 당한 건 2024년 10월, 평범한 오후였습니다."},
    {"no": 8, "speaker": "순이", "img": "img_scene_2.png", "script": "재민 씨, 나 사고 났어. 횡단보도에서 우회전하는 차한테 치였어."},
    {"no": 9, "speaker": "중현", "img": "img_scene_2.png", "script": "뭐? 여보, 많이 다쳤어? 지금 어디야?"},
    {"no": 10, "speaker": "순이", "img": "img_scene_2.png", "script": "아니, 크게 다친 것 같지는 않아요. 일어날 수 있어요. 근데 머리가 좀 울리고 어깨가 아파."},
    {"no": 11, "speaker": "중현", "img": "img_scene_2.png", "script": "지금 당장, 병원 가야 해 여보. 거기 있어, 내가 갈게."},
    {"no": 12, "speaker": "소영", "img": "img_scene_2.png", "script": "가해 차량 기사는 연신 죄송하다고 했어요. 보험이 있으니 다 해결해주겠다고도요. 응급실에서 받은 진단은 경추 염좌, 어깨 타박상이었습니다. 전치 2주 판정이 나왔습니다."},
    {"no": 13, "speaker": "문수", "img": "img_scene_3.png", "script": "크게 다치신 건 아닌데요. 목이랑 어깨 충격이 있었으니까 며칠 푹 쉬세요. 목 뻐근한 거는 물리치료 받으시면 나아질 거예요."},
    {"no": 14, "speaker": "순이", "img": "img_scene_3.png", "script": "선생님, 다행이네요. 별거 아닌 거 맞죠?"},
    {"no": 15, "speaker": "문수", "img": "img_scene_3.png", "script": "네, 환자분, 지금은 그렇습니다. 그냥 잘 쉬시면 돼요."},
    {"no": 16, "speaker": "소영", "img": "img_scene_3.png", "script": "사고 다음 날, 가해자 측 보험사 담당자에게서 연락이 왔습니다."},
    {"no": 17, "speaker": "봉규", "img": "img_scene_4.png", "script": "안녕하세요, 피해자 이미경 고객님 맞으시죠? 저는 담당 보상직원 조 보상라고 합니다. 사고 건 처리 도와드리려고 연락드렸어요."},
    {"no": 18, "speaker": "순이", "img": "img_scene_4.png", "script": "네. 이미경 맞습니다."},
    {"no": 19, "speaker": "봉규", "img": "img_scene_4.png", "script": "고객님 진단이 전치 2주로 나왔는데요. 치료비 다 처리해드리고, 위자료랑 합의금까지 해서 300만원 드리려고 합니다. 어떻게 생각하세요?"},
    {"no": 20, "speaker": "순이", "img": "img_scene_4.png", "script": "300만원이요. 적당한 건가요?"},
    {"no": 21, "speaker": "봉규", "img": "img_scene_4.png", "script": "고객님 부상 정도 기준으로 저희가 산정한 금액이에요. 솔직히 빨리 합의하시면 서로 편하거든요. 저희도 절차 간소하게 처리해드릴 수 있고, 고객님도 빨리 마음 편하게 지내실 수 있으니까요."},
    {"no": 22, "speaker": "순이", "img": "img_scene_4.png", "script": "근데 저 아직 치료 중인데, 치료 끝나고 해도 되나요?"},
    {"no": 23, "speaker": "봉규", "img": "img_scene_4.png", "script": "그러셔도 되는데요. 치료비는 저희가 계속 내드리고, 합의는 치료 끝나고 하시면 돼요. 근데 전치 2주면 2에서 3주 내에 보통 다 나으시거든요. 이 정도 부상은 빨리 마무리하시는 게 서로 편해요."},
    {"no": 24, "speaker": "순이", "img": "img_scene_5.png", "script": "그럼, 남편이랑 얘기해볼게요. 재민 씨, 보험사에서 300만원에 합의하자고 하는데."},
    {"no": 25, "speaker": "중현", "img": "img_scene_5.png", "script": "300만원? 그게 맞는 거야?"},
    {"no": 26, "speaker": "순이", "img": "img_scene_5.png", "script": "나도 잘 모르겠어. 담당자가 이 정도 부상이면 이게 기준이라고 하던데."},
    {"no": 27, "speaker": "중현", "img": "img_scene_5.png", "script": "어차피 병원비는 따로 내준다고 했지?"},
    {"no": 28, "speaker": "순이", "img": "img_scene_5.png", "script": "응. 치료비는 따로 내주고, 합의금으로 300 준다고."},
    {"no": 29, "speaker": "중현", "img": "img_scene_5.png", "script": "그럼 뭐, 괜찮은 거 아냐? 사고 빨리 잊어버리는 게 낫지. 이거 질질 끌면 스트레스만 더 받잖아."},
    {"no": 30, "speaker": "순이", "img": "img_scene_5.png", "script": "그래요. 나도 그냥 빨리 끝내고 싶어요. 우리 보험사와 합의해요."},
    {"no": 31, "speaker": "소영", "img": "img_scene_6.png", "script": "이미경 씨는 사고 3주 만에 합의서에 도장을 찍었습니다. 합의서에는 이런 문구가 있었어요. 향후 이 사고와 관련하여 어떠한 추가 청구도 하지 않겠습니다. 이미경 씨는 그 문장을 꼼꼼히 읽지 않았습니다."},
    {"no": 32, "speaker": "순이", "img": "img_scene_6.png", "script": "재민 씨, 요즘 머리가 너무 자주 아파. 목도 당기고."},
    {"no": 33, "speaker": "중현", "img": "img_scene_6.png", "script": "사고 후유증 아니야? 얼른 병원 가봐요."},
    {"no": 34, "speaker": "순이", "img": "img_scene_6.png", "script": "그게, 우리 보험사랑 합의했잖아요. 이제 보험 처리는 안 되는 거 아니예요?"},
    {"no": 35, "speaker": "중현", "img": "img_scene_6.png", "script": "그냥 우리 건강보험으로 한번 가봐요. 많이 아파?"},
    {"no": 36, "speaker": "순이", "img": "img_scene_6.png", "script": "어. 어지럼증도 있고. 자다가 팔이 저려서 깨기도 하고."},
    {"no": 37, "speaker": "소영", "img": "img_scene_7.png", "script": "병원에서 MRI를 찍었습니다. 그리고 결과를 들었어요."},
    {"no": 38, "speaker": "문수", "img": "img_scene_7.png", "script": "경추 사번, 오번 사이에 디스크가 심하게 눌려 있어요. 신경을 압박하고 있는 상태인데, 이게 교통사고 충격으로 악화된 거거든요. 수술을 고려하셔야 할 것 같아요."},
    {"no": 39, "speaker": "순이", "img": "img_scene_7.png", "script": "수술이요?"},
    {"no": 40, "speaker": "문수", "img": "img_scene_7.png", "script": "네. 지금 상태 계속 두면 팔 감각이 더 나빠질 수 있어요."},
    {"no": 41, "speaker": "순이", "img": "img_scene_7.png", "script": "근데 저 6개월 전에 교통사고로 합의 끝냈거든요. 그것 때문인 거 맞죠?"},
    {"no": 42, "speaker": "문수", "img": "img_scene_7.png", "script": "사고 충격이 원인일 가능성이 높아요. 이런 경추 신경 손상은 초기에는 증상이 안 나타나다가 시간이 지나면서 발현되는 경우가 많거든요."},
    {"no": 43, "speaker": "순이", "img": "img_scene_7.png", "script": "재민 씨, 이거 수술해야 한대."},
    {"no": 44, "speaker": "중현", "img": "img_scene_7.png", "script": "얼마나 해?"},
    {"no": 45, "speaker": "문수", "img": "img_scene_7.png", "script": "입원에 수술비에, 재활까지 하면 3,000만원 가까이 보시면 됩니다."},
    {"no": 46, "speaker": "중현", "img": "img_scene_7.png", "script": "보험사에 다시 청구할 수 있는 거 아닌가요? 사고 때문에 생긴 거잖아요."},
    {"no": 47, "speaker": "문수", "img": "img_scene_7.png", "script": "보호자님, 그건 저도 잘 몰라서요. 법적인 부분은 따로 상담받아 보시는 게 좋을 것 같아요."},
    {"no": 48, "speaker": "중현", "img": "img_scene_8.png", "script": "여보세요, 혹시 6개월 전에 아내 사고 건 처리하신 조 보상 담당자님 맞으세요?"},
    {"no": 49, "speaker": "봉규", "img": "img_scene_8.png", "script": "아, 이미경 고객님 남편분이시죠? 이미 합의 처리 완료된 건인데요."},
    {"no": 50, "speaker": "중현", "img": "img_scene_8.png", "script": "그게, 합의 후에 후유증이 심하게 나타났어요. 경추 디스크 수술을 해야 한다는데. 이게 사고 때문인 거거든요. 추가 처리가 안 되나요?"},
    {"no": 51, "speaker": "봉규", "img": "img_scene_8.png", "script": "죄송하지만 고객님, 합의서 작성하실 때 향후 추가 청구를 하지 않겠다고 서명하셨잖아요. 저희가 해드릴 게 없어요."},
    {"no": 52, "speaker": "중현", "img": "img_scene_8.png", "script": "그게 이런 상황까지 포함된 거예요? 합의 당시에는 이런 후유증이 있을지 몰랐는데."},
    {"no": 53, "speaker": "봉규", "img": "img_scene_8.png", "script": "저도 안타깝습니다만, 합의 이후에는 법적으로 저희가 추가 보상을 드리기가 어렵습니다."},
    {"no": 54, "speaker": "중현", "img": "img_scene_8.png", "script": "그럼 우리가 3,000만원을 다 내야 한다는 거예요?"},
    {"no": 55, "speaker": "봉규", "img": "img_scene_8.png", "script": "죄송합니다."},
    {"no": 56, "speaker": "소영", "img": "img_scene_9.png", "script": "한재민 씨는 전화를 끊고 한참을 앉아 있었습니다. 아내는 옆에서 아무 말도 못 했어요. 이렇게 될 줄 알았더라면 300만원에 합의하지 않았을 텐데. 그 말이 목 끝까지 올라왔지만 내뱉지 못했습니다. 지인의 소개로 손해사정사를 만났습니다."},
    {"no": 57, "speaker": "수호", "img": "img_scene_9.png", "script": "상황 들었습니다. 안타깝지만 솔직하게 말씀드릴게요. 합의 후 추가 청구가 전혀 불가능한 건 아니에요. 대법원 판례에서도, 합의 당시 예측할 수 없었던 손해가 발생했고, 그 손해가 워낙 중대해서 당사자가 알았더라면 그 금액으로 합의하지 않았을 것이라고 볼 수 있는 경우에는 추가 청구를 인정한 사례가 있어요."},
    {"no": 58, "speaker": "중현", "img": "img_scene_9.png", "script": "그러면 우리도 되는 거 아닌가요?"},
    {"no": 59, "speaker": "수호", "img": "img_scene_9.png", "script": "문제는 증명입니다. 사고 당시 경추 신경 손상이 이미 있었는데 의사가 제대로 진단을 못 했다는 걸 입증해야 하고, 합의 당시 이 후유증이 예측 불가능했다는 것도 증명해야 해요. 그리고 보험사는 전치 2주 부상이었으니 예측 가능한 범위였다고 주장할 거예요."},
    {"no": 60, "speaker": "순이", "img": "img_scene_9.png", "script": "그러면 소송을 해야 하는 건가요?"},
    {"no": 61, "speaker": "수호", "img": "img_scene_9.png", "script": "소송으로 가야 할 가능성이 높아요. 그리고 솔직히 결과를 장담하기가 어려워요. 보험사 측 자문의가 이 정도 사고면 이런 후유증은 예측 가능했다는 소견을 낼 수도 있거든요."},
    {"no": 62, "speaker": "중현", "img": "img_scene_9.png", "script": "소송 비용은요?"},
    {"no": 63, "speaker": "수호", "img": "img_scene_9.png", "script": "1심에 수백만원이 들어가고요. 기간도 최소 1년은 봐야 해요. 그리고 지더라도 비용은 돌아오지 않아요."},
    {"no": 64, "speaker": "순이", "img": "img_scene_9.png", "script": "그냥 우리가 내는 게 낫겠네요."},
    {"no": 65, "speaker": "수호", "img": "img_scene_9.png", "script": "결정은 두 분이 하셔야 해요. 근데 제가 드리고 싶은 말씀은, 이런 일이 생기는 이유가 처음에 합의를 너무 빨리 해서예요. 보험사는 항상 빠른 합의를 원해요. 피해자는 빨리 끝내고 싶어하고요. 그 타이밍에서 손해를 보는 건 늘 피해자예요."},
    {"no": 66, "speaker": "중현", "img": "img_scene_9.png", "script": "왜 아무도 그 얘기를 안 해줬을까요."},
    {"no": 67, "speaker": "수호", "img": "img_scene_9.png", "script": "그게 이 업계의 현실이에요."},
    {"no": 68, "speaker": "소영", "img": "img_scene_10.png", "script": "이미경 씨는 결국 소송을 포기했습니다. 3,000만원 가까운 수술비를 대출을 받아서 냈어요. 수술은 성공적이었습니다. 팔 저림 증상은 많이 나아졌어요. 그런데 어깨 결림과 어지럼증은 아직 남아 있어요. 의사는 이것도 사고 후유증일 가능성이 높다고 했어요."},
    {"no": 69, "speaker": "순이", "img": "img_scene_10.png", "script": "재민 씨, 나 그때 300만원 합의하기 전에 좀 더 알아봤어야 했는데."},
    {"no": 70, "speaker": "중현", "img": "img_scene_10.png", "script": "그게 어디 당신 잘못이야. 보험 담당자가 이 정도가 적절하다고 하니까 믿은 거지. 우리가 어떻게 알아."},
    {"no": 71, "speaker": "순이", "img": "img_scene_10.png", "script": "근데 있잖아요. 담당자가 그때 빨리 합의하면 서로 편하다고 했잖아요. 서로 편한 게 아니었어요. 담당자 회사가 편한 거였던 거잖아요."},
    {"no": 72, "speaker": "중현", "img": "img_scene_10.png", "script": "그렇지."},
    {"no": 73, "speaker": "순이", "img": "img_scene_10.png", "script": "이 얘기를 다른 사람들은 알았으면 좋겠어요. 나처럼 이런 일 생기는 사람이 없었으면 해서."},
    {"no": 74, "speaker": "소영", "img": "img_scene_11.png", "script": "이미경 씨 이야기, 어떠셨나요. 오늘 꼭 기억하셔야 할 내용을 정리해드릴게요. 첫 번째 오해입니다. 보험사가 제시한 합의금은 적절하게 계산된 금액이다? 틀렸습니다. 보험사의 합의금은 보험사가 지급해야 할 최소한의 금액으로 시작합니다. 보험사 직원은 피해자 편이 아닙니다. 조기에 낮은 금액으로 사건을 종결하는 것이 보험사에 유리합니다. 전치 2주 진단이 나왔더라도 위자료, 향후 치료비, 일실수입, 후유장해 가능성까지 모두 고려해야 해요. 규모가 큰 사고라면 반드시 손해사정사나 변호사 상담을 먼저 받으세요."},
    {"no": 75, "speaker": "소영", "img": "img_scene_12.png", "script": "두 번째 오해입니다. 빨리 합의하면 서로 편하다? 보험사에게만 편합니다. 교통사고 후유증은 사고 직후 나타나지 않는 경우가 많습니다. 경추, 허리, 무릎 같은 부위는 초기에는 경미해 보여도 수개월 후에 심각한 증상이 나타날 수 있어요. 전문가들은 치료가 완전히 끝나고 후유증 여부가 확정된 다음에 합의하는 것이 피해자에게 유리하다고 강조합니다."},
    {"no": 76, "speaker": "소영", "img": "img_scene_13.png", "script": "세 번째 오해입니다. 합의하면 완전히 끝이다? 원칙은 그렇습니다. 하지만 예외가 있어요. 대법원은 합의 당시 예측할 수 없었던 손해가 발생했고, 알았더라면 그 금액으로 합의하지 않았을 것이라 볼 만큼 손해가 중대한 경우에는 추가 청구를 인정했습니다. 대법원 2001년 9월 14일 선고, 구십구다 사이칠구칠 판결입니다. 단, 이를 입증하는 과정이 매우 어렵고 시간과 비용이 많이 들어요. 합의 전에 신중하게 결정하는 것이 훨씬 중요합니다."},
    {"no": 77, "speaker": "소영", "img": "img_scene_14.png", "script": "오늘 꼭 기억하셔야 할 것, 딱 세 가지입니다. 첫째, 교통사고 후 보험사가 빠른 합의를 권유하면 일단 멈추세요. 둘째, 합의금이 적정한지 혼자 판단하지 마세요. 손해사정사나 변호사에게 먼저 상담받으세요. 셋째, 합의서의 모든 문구를 꼼꼼히 읽으세요. 특히 향후 어떠한 추가 청구도 하지 않겠습니다 라는 문구가 있다면, 무엇을 의미하는지 정확히 이해하고 서명하셔야 합니다."},
    {"no": 78, "speaker": "소영", "img": "img_scene_14.png", "script": "보험금 못 받는 사람들의 공통점은 단 하나입니다. 몰랐다는 겁니다. 오늘 이야기, 여기서 마칩니다. 다음 이야기도 기다려주세요."}
]

def generate_elevenlabs_audio(text, output_path, speaker):
    """ElevenLabs API 호출: 화자에 맞는 보이스 ID 사용"""
    api_key = os.environ.get('ELEVENLABS_API_KEY')
    voice_id = VOICE_MAPPING.get(speaker, os.environ.get('ELEVENLABS_VOICE_ID', 'j9UrvurLWeTchpuBcUAg'))
    
    if not api_key:
        print(f"⚠️ 경고: ELEVENLABS_API_KEY 없음. ({speaker} 더빙 스킵)")
        return
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        else:
            print(f"[{response.status_code}] ElevenLabs API 호출 실패 ({speaker}): {response.text}")
    except Exception as e:
        print(f"ElevenLabs 요청 중 에러 발생 ({speaker}): {e}")

# 3D 카메라 줌 인 효과 함수 (이미지가 서서히 커지는 느낌)
def zoom_in_effect(clip, zoom_ratio=1.05):
    def effect(get_frame, t):
        scale = 1.0 + (zoom_ratio - 1.0) * (t / clip.duration)
        img = Image.fromarray(get_frame(t))
        w, h = img.size
        new_w, new_h = int(w * scale), int(h * scale)
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        right = left + w
        bottom = top + h
        img_cropped = img_resized.crop((left, top, right, bottom))
        return np.array(img_cropped)
    return clip.fl(effect)

def create_radio_broadcast_video():
    output_video_filename = "교통사고합의_라디오방송_최종.mp4"
    img_width, img_height = 1920, 1080
    clips = []
    
    print("--- 라디오 방송 다중 화자 영상 생성 시작 ---")
    prev_img = None
    
    for data in radio_scenes:
        scene_no = data["no"]
        speaker = data["speaker"]
        script = data["script"]
        print(f"▶ [{scene_no:02d}/{len(radio_scenes)}] 화자: {speaker} | 대사: {script[:15]}...")
        
        # 1. 16:9 이미지 워터마크 제거 (하단 잘라내기)
        img_path = os.path.join(ASSET_DIR, data["img"])
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGB")
            img = ImageOps.fit(img, (img_width, img_height), Image.Resampling.LANCZOS)
            processed_img_path = os.path.join(WORK_DIR, f"slide_{scene_no}.png")
            img.save(processed_img_path)
            
            img_clip = ImageClip(processed_img_path)
            img_clip = crop(img_clip, y1=0, y2=1050) # 하단 워터마크 영역 30px 자르기
            img_clip = img_clip.resize(height=1080)  # 다시 1080으로 꽉 채우기
        else:
            img = Image.new("RGB", (img_width, img_height), color=(30, 30, 35))
            processed_img_path = os.path.join(WORK_DIR, f"slide_{scene_no}.png")
            img.save(processed_img_path)
            img_clip = ImageClip(processed_img_path)
        
        # 2. 오디오 생성 및 길이 측정
        audio_path = os.path.join(WORK_DIR, f"audio_{scene_no}.mp3")
        generate_elevenlabs_audio(script, audio_path, speaker)
        
        duration = 4.0 # 오디오 실패 시 기본 길이
        if os.path.exists(audio_path):
            try:
                final_audio = AudioFileClip(audio_path)
                duration = final_audio.duration
            except:
                pass
        
        img_clip = img_clip.set_duration(duration)
        
        # 3. 카메라 무빙(줌 인) 및 디졸브(장면 전환) 효과
        img_clip = zoom_in_effect(img_clip, zoom_ratio=1.03) # 아주 서서히 카메라가 다가가는 효과
        
        if data["img"] != prev_img and len(clips) > 0:
            # 배경 이미지가 바뀌면 자연스럽게 서서히 나타나는(Fade in) 효과
            img_clip = fadein(img_clip, 0.6)
            
        prev_img = data["img"]
        
        # 4. 하단 말풍선(자막) 합성 (MoviePy TextClip 활용)
        try:
            # 긴 대사를 40글자씩 줄바꿈
            wrapped_text = "\n".join(textwrap.wrap(script, width=40))
            # 폰트는 시스템에 설치된 나눔고딕 등 기본 한글 폰트를 불러옵니다.
            txt_clip = TextClip(wrapped_text, fontsize=45, color='white', font='NanumGothicBold', bg_color='rgba(0,0,0,0.6)')
            # 화면 중앙 하단에 배치
            txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(duration).margin(bottom=70, opacity=0)
            
            # 이미지와 자막 결합
            video_clip = CompositeVideoClip([img_clip, txt_clip])
        except Exception as e:
            # 깃허브 액션 환경에 폰트(ImageMagick)가 제대로 없으면 자막 없이 영상만 렌더링
            video_clip = img_clip

        # 최종 오디오 입히기
        if os.path.exists(audio_path):
            try:
                final_audio = AudioFileClip(audio_path)
                video_clip = video_clip.set_audio(final_audio)
            except:
                pass
        
        clips.append(video_clip)

    print("\n--- 모든 클립 병합 및 최종 렌더링 진행 ---")
    if clips:
        # padding=-0.3을 주어 각 클립이 0.3초씩 겹치면서(크로스페이드) 넘어가도록 합니다
        final_video = concatenate_videoclips(clips, method="compose", padding=-0.3)
        final_video.write_videofile(
            output_video_filename, 
            fps=24, 
            preset="medium", 
            threads=4, 
            codec="libx264", 
            bitrate="5000k", 
            audio_codec="aac", 
            temp_audiofile="temp-audio.m4a", 
            remove_temp=True
        )
        print(f"✅ 화자 분리 + 자막 + 장면전환 적용 완료! 파일명: {output_video_filename}")

if __name__ == "__main__":
    create_radio_broadcast_video()
